import numpy as np
import os
import io
from PIL import Image
import json
from datetime import datetime
from fastapi import HTTPException

def preprocess_uploaded_image(image_file):
    contents = image_file
    uploaded_img = Image.open(io.BytesIO(contents)).convert("RGB")
    return uploaded_img

def run_yolo_inference(yolo_model, uploaded_img, device):
    results = yolo_model(np.array(uploaded_img), device=device)
    return results

def extract_mask_and_class_ids(results):
    mask = None
    if hasattr(results[0], "masks") and results[0].masks is not None:
        masks = results[0].masks.data.cpu().numpy()
        if hasattr(results[0], "boxes") and hasattr(results[0].boxes, "cls"):
            class_ids = results[0].boxes.cls.cpu().numpy().astype(np.uint8)
        else:
            raise HTTPException(status_code=500, detail="Model did not return class ids")
        if masks.ndim == 3 and masks.shape[0] > 0 and masks.shape[0] == class_ids.shape[0]:
            max_probs = masks.max(axis=0)
            mask_indices = masks.argmax(axis=0)
            mask = np.zeros_like(max_probs, dtype=np.uint8)
            for idx in range(masks.shape[0]):
                mask[mask_indices == idx] = class_ids[idx] + 1
            mask[max_probs <= 0.5] = 0
        else:
            raise HTTPException(status_code=500, detail="status 500")
    else:
        raise HTTPException(status_code=500, detail="error")
    return mask, class_ids

def get_class_labels():
    return [
        "Background",    # 0
        "Tooth",         # 1
        "Caries",        # 2
        "GumInflam",     # 3
        "Mouth",         # 4
        "Gum",           # 5
        "Recession",     # 6
        "Ortho",         # 7
        "Mucosa",        # 8
        "Splint",        # 9
    ]

def count_class_pixels(mask, class_labels):
    return {label: int((mask == idx).sum()) for idx, label in enumerate(class_labels)}

def count_class_objects(class_ids, class_labels, report_classes):
    return {label: int((class_ids == idx-1).sum()) for idx, label in enumerate(class_labels) if label in report_classes}

def save_mask_and_id(blended, mask_np, user_mask_dir):
    mask_path = os.path.join(user_mask_dir, "mask.png")
    blended.save(mask_path)
    mask_id_path = os.path.join(user_mask_dir, "mask_id.npy")
    np.save(mask_id_path, mask_np)

def get_user_info_and_update_history(userId, class_object_counts):
    user_info = None
    caries_history = None
    recession_history = None
    try:
        from database import get_db, fetch_user_by_id, update_user
        db_gen = get_db()
        db = next(db_gen)
        user_obj = fetch_user_by_id(userId, db)
        if user_obj:
            user_info = {
                "Name": user_obj.fullName,
                "Gender": user_obj.gender,
                "Birthdate": user_obj.birthdate,
                "Email": user_obj.email,
                "Phone": user_obj.phoneNumber
            }
            caries_dict = {}
            recession_dict = {}
            if user_obj.caries_number:
                try:
                    caries_dict = json.loads(user_obj.caries_number)
                except Exception:
                    caries_dict = {}
            if user_obj.recession_number:
                try:
                    recession_dict = json.loads(user_obj.recession_number)
                except Exception:
                    recession_dict = {}
            caries = class_object_counts.get("Caries", 0)
            recession = class_object_counts.get("Recession", 0)
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            caries_dict[today_str] = caries
            recession_dict[today_str] = recession
            def trim_dict(d, max_len=20):
                items = sorted(d.items(), key=lambda x: x[0])
                if len(items) > max_len:
                    items = items[-max_len:]
                return dict(items)
            caries_dict = trim_dict(caries_dict)
            recession_dict = trim_dict(recession_dict)
            update_user(userId, {
                "caries_number": json.dumps(caries_dict, ensure_ascii=False),
                "recession_number": json.dumps(recession_dict, ensure_ascii=False)
            }, db)
            db.close()
            caries_history = caries_dict
            recession_history = recession_dict
        else:
            caries_history = None
            recession_history = None
    except Exception:
        user_info = None
        caries_history = None
        recession_history = None
    return user_info, caries_history, recession_history
