from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse

# Standard imports
import os
import io
import base64
import json
from datetime import datetime, timedelta

# Third-party imports
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from PIL import Image


# Project helpers (use absolute imports)
from Myoral.ai.routers.image_analysis_helpers import (
    run_yolo_inference,
    postprocess_yolo_output,
    get_class_labels,
    count_class_pixels,
    count_class_objects,
    render_mask_overlay,
    save_mask_and_id,
    fetch_and_update_user_info_and_history
)
from Myoral.ai.routers.pdf_report_helpers import generate_pdf_report


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

        # 2. Run YOLO inference and postprocess
        results = run_yolo_inference(uploaded_img)
        mask, class_ids = postprocess_yolo_output(results)

        # 3. Get class labels and counts
        class_labels = get_class_labels()
        class_counts = count_class_pixels(mask, class_labels)
        report_classes = ["Tooth", "Caries", "GumInflam", "Recession"]
        class_object_counts = count_class_objects(class_ids, class_labels, report_classes)

        # 4. Render mask overlay
        blended, mask_np, color_map, render_alpha = render_mask_overlay(uploaded_img, mask, results)

        # 5. Guest mode (userId == "0")
        if userId == "0":
            buf = io.BytesIO()
            blended.save(buf, format="PNG")
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            pdf_buf = generate_pdf_report(class_object_counts, timestamp, blended, color_map, class_labels)
            pdf_base64 = base64.b64encode(pdf_buf.read()).decode()
            return StreamingResponse(buf, media_type="image/png", headers={
                "X-Report-PDF-Base64": pdf_base64
            })
        # 6. Registered user mode
        else:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            user_mask_dir = os.path.join("masks", userId, datetime.utcnow().strftime("%Y%m%d%H%M%S"))
            os.makedirs(user_mask_dir, exist_ok=True)
            mask_path = os.path.join(user_mask_dir, "mask.png")
            blended.save(mask_path)
            mask_id_path = os.path.join(user_mask_dir, "mask_id.npy")
            save_mask_and_id(mask_np, mask_id_path)
            # Fetch and update user info/history
            user_info, caries_history, recession_history = fetch_and_update_user_info_and_history(userId, class_object_counts)
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
        raise HTTPException(
            status_code=500,
            detail="Image processing error"
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