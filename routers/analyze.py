from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse


# Standard imports
import os
import io
import base64
import json
import numpy as np
from datetime import datetime, timedelta

# Third-party imports
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from PIL import Image


# Project helpers (use absolute imports)
from .helper_functions.image_analysis_helpers import (
    run_yolo_inference,
    get_class_labels,
    count_class_pixels,
    count_class_objects,
    save_mask_and_id,
    get_user_info_and_update_history
)
from .helper_functions.pdf_report_helpers import generate_pdf_report
from .helper_functions.chart_data_helpers import generate_chart_data

from ultralytics import YOLO
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..","models", "6_30best_aug.pt")
yolo_model = YOLO(MODEL_PATH)
yolo_model.to(device)

router = APIRouter()


@router.get("/analysis/mask/{userid}")
async def get_mask_image(
    userid: str,
    time: str = Query("latest", description="get the corresponding file"),
    filename: str = Query("none", description="only used when time is none")
):
    user_dir = os.path.join("masks", userid)
    if not os.path.exists(user_dir):
        raise HTTPException(status_code=404, detail="User mask folder not found")
    # Get all timestamp folders
    subfolders = [f for f in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, f))]
    if not subfolders and time != "none":
        raise HTTPException(status_code=404, detail="No mask images found for user")
    if time == "latest":
        # Use latest timestamp folder
        latest_folder = max(subfolders, key=lambda x: x)
        mask_path = os.path.join(user_dir, latest_folder, "mask.png")
        if not os.path.exists(mask_path):
            raise HTTPException(status_code=404, detail="Mask image not found")
        return FileResponse(mask_path, media_type="image/png")
    elif time == "all":
        # Return all mask image paths
        mask_paths = []
        for folder in sorted(subfolders):
            mask_path = os.path.join(user_dir, folder, "mask.png")
            if os.path.exists(mask_path):
                mask_paths.append(f"{userid}/{folder}/mask.png")
        if not mask_paths:
            raise HTTPException(status_code=404, detail="No mask images found for user")
        return JSONResponse(content={"mask_paths": mask_paths})
    elif time == "none":
        # Read image by filename
        if not filename:
            raise HTTPException(status_code=400, detail="filename required when time=none")
        mask_path = os.path.join("masks", filename)
        if not os.path.exists(mask_path):
            raise HTTPException(status_code=404, detail="Mask image not found")
        return FileResponse(mask_path, media_type="image/png")

@router.post(
    "/analysis",
    status_code=200,
    responses={
        400: {"description": "Invalid image format"},
        401: {"description": "Unauthorized"},
        404: {"description": "User not found"},
        500: {"description": "Processing error"}
    }
)
async def analyze_photos(
    image: UploadFile = File(..., description="Oral photo in JPEG/PNG format"),
    userId: str = Form("0", description="User ID")
):
    try:
        # 1. Read and preprocess the uploaded image
        contents = await image.read()
        uploaded_img = Image.open(io.BytesIO(contents)).convert("RGB")

        # 2. Run YOLO inference
        results = run_yolo_inference(yolo_model, uploaded_img, device)

        # 3. Post-process YOLO output to get mask and class ids (original logic)
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

        # 4. Get class labels and counts
        class_labels = get_class_labels()
        class_counts = count_class_pixels(mask, class_labels)
        report_classes = ["Tooth", "Caries", "GumInflam", "Recession"]
        class_object_counts = count_class_objects(class_ids, class_labels, report_classes)

        # 5. Render mask overlay (original logic)
        h, w = mask.shape
        color_map = [
            (255, 255, 255),     # 0: white
            (255, 0, 0),         # 1: bright red
            (0, 255, 0),         # 2: bright blue
            (255, 255, 0),       # 3: bright yellow
            (255, 255, 255),     # 4: white
            (0, 0, 255),         # 5: blue
            (255, 0, 255),       # 6: magenta
            (0, 255, 255),       # 7: cyan
            (255, 128, 0),       # 8: orange
            (0, 0, 0),           # 9: black
        ]
        render_alpha = 150  # alpha
        color_mask = np.zeros((h, w, 4), dtype=np.uint8)
        render_classes = [1, 2, 3, 5, 6]
        for v in range(len(color_map)):
            color = color_map[v]
            if v in render_classes:
                color_mask[mask == v, :3] = color
                color_mask[mask == v, 3] = render_alpha
            else:
                color_mask[mask == v, :3] = (255, 255, 255)
                color_mask[mask == v, 3] = render_alpha
        color_mask_pil = Image.fromarray(color_mask, mode="RGBA")
        mask_np = np.array(mask)

        # Draw contour
        contour_img = np.array(color_mask_pil).copy()
        for class_id in np.unique(mask_np):
            if (class_id == 0) or (class_id == 4):
                continue
            binary = (mask_np == class_id).astype(np.uint8) * 255
            import cv2
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(contour_img, contours, -1, (0, 0, 0, 255), 2)
        contour_mask_pil = Image.fromarray(contour_img).convert("RGBA")
        original_img = uploaded_img.resize(contour_mask_pil.size).convert("RGBA")
        blended = Image.alpha_composite(original_img, color_mask_pil)
        blended = Image.alpha_composite(blended, contour_mask_pil)
        blended = blended.convert("RGB")

        # 6. Guest mode (userId == "0")
        if userId == "0":
            buf = io.BytesIO()
            blended.save(buf, format="PNG")
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            pdf_buf = generate_pdf_report(class_object_counts, timestamp, blended, color_map, class_labels)
            pdf_base64 = base64.b64encode(pdf_buf.read()).decode()
            return StreamingResponse(buf, media_type="image/png", headers={
                "X-Report-PDF-Base64": pdf_base64
            })
        # 7. Registered user mode
        else:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            user_mask_dir = os.path.join("masks", userId, datetime.utcnow().strftime("%Y%m%d%H%M%S"))
            os.makedirs(user_mask_dir, exist_ok=True)
            save_mask_and_id(blended, mask_np, user_mask_dir)
            # Fetch and update user info/history
            user_info, caries_history, recession_history = get_user_info_and_update_history(userId, class_object_counts)
            pdf_buf = generate_pdf_report(class_object_counts, timestamp, blended, color_map, class_labels, user_info, caries_history, recession_history)
            pdf_path = os.path.join(user_mask_dir, "report.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_buf.read())
            return {
                "results": {
                    "maskFileName": f"{userId}/{os.path.basename(user_mask_dir)}/mask.png",
                    "maskIdFileName": f"{userId}/{os.path.basename(user_mask_dir)}/mask_id.npy",
                    "reportFileName": f"{userId}/{os.path.basename(user_mask_dir)}/report.pdf"
                },
                "message": "Colored mask, mask id array, and PDF report generated successfully"
            }
    except Exception as e:
        print(f"Error processing image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Image processing error: {e}"
        )

@router.get("/analysis/maskid/{userid}")
async def get_mask_id_array(
    userid: str
):
    user_dir = os.path.join("masks", userid)
    if not os.path.exists(user_dir):
        raise HTTPException(status_code=404, detail="User mask folder not found")
    subfolders = [f for f in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, f))]
    if not subfolders:
        raise HTTPException(status_code=404, detail="No mask id files found for user")
    latest_folder = max(subfolders, key=lambda x: x)
    mask_id_path = os.path.join(user_dir, latest_folder, "mask_id.npy")
    if not os.path.exists(mask_id_path):
        raise HTTPException(status_code=404, detail="Mask id file not found")
    mask_id = np.load(mask_id_path)
    return {"mask_id": mask_id.tolist()}

@router.get("/analysis/report/pdf")
async def get_pdf_report(pdf_path: str):
    pdf_path=os.path.join('masks',pdf_path)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    filename = os.path.basename(pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )

@router.get("/analysis/charts/{userid}")
async def get_chart_data(
    userid: str
):
    """
    Get chart data for frontend plotting including caries, recession, and gum inflammation trends.
    
    Args:
        userid: User ID to fetch chart data for
        
    Returns:
        Dictionary containing chart data for all three charts with metadata
    """
    try:
        # Fetch user info and history data (same logic as in PDF generation)
        user_info = None
        caries_history = None
        recession_history = None
        
        try:
            from database import get_db, fetch_user_by_id
            db_gen = get_db()
            db = next(db_gen)
            user_obj = fetch_user_by_id(userid, db)
            
            if user_obj:
                user_info = {
                    "Name": user_obj.fullName,
                    "Gender": user_obj.gender,
                    "Birthdate": user_obj.birthdate,
                    "Email": user_obj.email,
                    "Phone": user_obj.phoneNumber
                }
                
                # Parse historical data
                if user_obj.caries_number:
                    try:
                        caries_history = json.loads(user_obj.caries_number)
                    except Exception:
                        caries_history = {}
                
                if user_obj.recession_number:
                    try:
                        recession_history = json.loads(user_obj.recession_number)
                    except Exception:
                        recession_history = {}
            
            db.close()
            
        except Exception as e:
            print(f"[WARNING] Could not fetch user data for charts: {e}")
            # Continue with None values for guest-like behavior
        
        # Generate chart data using helper function
        chart_data = generate_chart_data(user_info, caries_history, recession_history)
        
        return chart_data
        
    except Exception as e:
        print(f"[ERROR] get_chart_data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate chart data: {e}"
        )