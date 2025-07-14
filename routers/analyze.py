from fastapi import APIRouter, UploadFile, File, HTTPException, status, Path, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from ultralytics import YOLO
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import os
import uuid
import torch
import base64
import glob
from datetime import datetime,timedelta
import cv2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import json



router = APIRouter()

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[DEBUG]  using device: {device}")
# 加载YOLOv8模型（只加载一次），指定device
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', '7_4best.pt')
yolo_model = YOLO(MODEL_PATH)
yolo_model.to(device)

# 通道字典（如需后续多通道mask可参考）
# RED_DICT = {
#     0: "No teeth",
#     1: "Upper left central incisor (perm)",
#     2: "Upper right central incisor (perm)",
#     3: "Lower left central incisor (perm)",
#     # ...补充完整...
# }
# GREEN_DICT = {
#     0: "No issue",
#     1: "Moderate caries",
#     2: "Severe caries",
#     # ...补充完整...
# }
# BLUE_DICT = {
#     0: "No issue",
#     1: "Moderate gum inflammation",
#     2: "Severe gum inflammation",
#     # ...补充完整...
# }

def mask_channel_to_label_image(mask: np.ndarray, channel: int, label_dict: dict) -> Image:
    """
    将mask的某一通道转换为文字标注图
    """
    img = Image.fromarray(mask[..., channel], mode="L").convert("RGB")
    draw = ImageDraw.Draw(img)
    font = None
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    h, w = mask.shape[:2]
    step = max(1, min(h, w) // 20)
    for y in range(0, h, step):
        for x in range(0, w, step):
            v = int(mask[y, x, channel])
            label = label_dict.get(v, str(v))
            draw.text((x, y), label, fill=(255, 0, 0), font=font)
    return img

@router.get("/analysis/mask/{userid}")
async def get_mask_image(
    userid: str,
    time: str = Query("latest", description="时间戳文件夹名，latest为最新，all为全部，none为按文件名"),
    filename: str = Query("none", description="mask文件名，仅当time=none时使用")
):
    user_dir = os.path.join("masks", userid)
    if not os.path.exists(user_dir):
        raise HTTPException(status_code=404, detail="User mask folder not found")
    # 获取所有时间戳文件夹
    subfolders = [f for f in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, f))]
    if not subfolders and time != "none":
        raise HTTPException(status_code=404, detail="No mask images found for user")
    if time == "latest":
        # 取最新时间戳文件夹
        latest_folder = max(subfolders, key=lambda x: x)
        mask_path = os.path.join(user_dir, latest_folder, "mask.png")
        if not os.path.exists(mask_path):
            raise HTTPException(status_code=404, detail="Mask image not found")
        return FileResponse(mask_path, media_type="image/png")
    elif time == "all":
        # 返回所有mask图片的文件路径
        mask_paths = []
        for folder in sorted(subfolders):
            mask_path = os.path.join(user_dir, folder, "mask.png")
            if os.path.exists(mask_path):
                mask_paths.append(f"{userid}/{folder}/mask.png")
        if not mask_paths:
            raise HTTPException(status_code=404, detail="No mask images found for user")
        return JSONResponse(content={"mask_paths": mask_paths})
    elif time == "none":
        # 通过filename读取图片
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

    # 动态选择 device
    
    print(f"[DEBUG] analyze_photos received userid: {userId}, using device: {device}")
    yolo_model.to(device)

    # 仅校验图像格式
    # if image.content_type not in ["image/jpeg", "image/png"]:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Invalid image format. Only JPEG/PNG accepted"
    #     )
    try:
        contents = await image.read()
        uploaded_img = Image.open(io.BytesIO(contents)).convert("RGB")
        # 使用YOLOv8模型推理，获取mask
        results = yolo_model(np.array(uploaded_img), device=device)
        # 合并所有牙齿的mask为一张类别分割图
        mask = None
        if hasattr(results[0], "masks") and results[0].masks is not None:
            masks = results[0].masks.data.cpu().numpy()  # (N, H, W)
            # 获取每个mask对应的类别ID
            if hasattr(results[0], "boxes") and hasattr(results[0].boxes, "cls"):
                class_ids = results[0].boxes.cls.cpu().numpy().astype(np.uint8)  # (N,)
            else:
                raise HTTPException(status_code=500, detail="Model did not return class ids")
            if masks.ndim == 3 and masks.shape[0] > 0 and masks.shape[0] == class_ids.shape[0]:
                max_probs = masks.max(axis=0)  # (H, W)
                mask_indices = masks.argmax(axis=0)  # (H, W), 取概率最大的mask索引
                # 构建类别ID图，背景为0
                mask = np.zeros_like(max_probs, dtype=np.uint8)
                for idx in range(masks.shape[0]):
                    mask[mask_indices == idx] = class_ids[idx] + 1  # 类别ID+1，0为背景
                mask[max_probs <= 0.5] = 0  # 阈值过滤，低于阈值为背景
            else:
                raise HTTPException(status_code=500, detail="Model did not return valid masks or class ids")
        else:
            raise HTTPException(status_code=500, detail="Model did not return a mask")
        # 类别英文标签
        class_labels = [
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
        # 统计各类别像素点数量
        class_counts = {label: int((mask == idx).sum()) for idx, label in enumerate(class_labels)}
        # 统计各类别目标数量（去除Background）
        # 只保留需要统计的类别
        report_classes = [
            "Tooth", "Caries", "GumInflam", "Recession"
        ]
        class_object_counts = {label: int((class_ids == idx-1).sum()) for idx, label in enumerate(class_labels) if label in report_classes}
        # 生成PDF报告，包含mask图片和颜色说明
        def generate_pdf_report(object_counts, timestamp, mask_img, color_map, class_labels, user_info=None):
            from reportlab.lib.utils import ImageReader
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            width, height = A4

            # 顶部logo与信息
            logo_y = height - 60
            LIGHT_BLUE = "#42A5F5"  # 浅蓝色
            c.setFont("Helvetica-Bold", 26)  # 标题更大
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawCentredString(width / 2, logo_y, "MyOral.ai")
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawCentredString(width / 2, logo_y - 16, "K11 Atelier, King's Road, Hong Kong")

            # 分割线
            c.setStrokeColor(colors.HexColor("#B0B0B0"))
            c.setLineWidth(1)
            c.line(40, logo_y - 28, width - 40, logo_y - 28)

            # 主标题
            c.setFont("Helvetica-Bold", 22)
            c.setFillColor(colors.black)
            c.drawCentredString(width / 2, logo_y - 55, "Primary Report")

            # 报告生成时间（中国时间），紧跟在主标题下且不加粗
            y = logo_y - 75
            from datetime import datetime, timedelta
            c.setFont("Helvetica", 11)
            c.setFillColor(colors.black)
            try:
                utc_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except Exception:
                utc_time = datetime.utcnow()
            china_time = utc_time + timedelta(hours=8)
            c.drawCentredString(width / 2, y, f"Report Generated At: {china_time.strftime('%Y-%m-%d %H:%M:%S')}")
            y -= 20

            # Patient Info
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawString(50, y, "Patient Info")
            y -= 18
            c.setFont("Helvetica", 11)
            c.setFillColor(colors.black)
            if user_info:
                if user_info.get("Name"):
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(60, y, "Full Name:")
                    c.setFont("Helvetica", 11)
                    c.drawString(140, y, str(user_info['Name']))
                    y -= 16
                if user_info.get("Gender"):
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(60, y, "Gender:")
                    c.setFont("Helvetica", 11)
                    c.drawString(140, y, str(user_info['Gender']))
                    y -= 16
                if user_info.get("Birthdate"):
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(60, y, "Birth Date:")
                    c.setFont("Helvetica", 11)
                    c.drawString(140, y, str(user_info['Birthdate']))
                    y -= 16
                if user_info.get("Phone"):
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(60, y, "Phone:")
                    c.setFont("Helvetica", 11)
                    c.drawString(140, y, str(user_info['Phone']))
                    y -= 16
                if user_info.get("Email"):
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(60, y, "Email:")
                    c.setFont("Helvetica", 11)
                    c.drawString(140, y, str(user_info['Email']))
                    y -= 16
                y -= 8
            else:
                c.drawString(60, y, "No patient info available.")
                y -= 16

            # Assessment
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawString(50, y, "Assessment")
            y -= 18
            c.setFont("Helvetica", 11)
            c.setFillColor(colors.black)
            tooth = object_counts.get("Tooth", 0)
            caries = object_counts.get("Caries", 0)
            gum_inflam = object_counts.get("GumInflam", 0)
            recession = object_counts.get("Recession", 0)
            # YOLO模型总结
            summary_line = f"Detected: {tooth} teeth, {caries} caries, {gum_inflam} gum inflammation, {recession} gum recession."
            c.drawString(60, y, summary_line)
            y -= 16
            assessment = "The patient appears in good health with no immediate concerns during the examination."
            if caries > 0:
                assessment = f"{caries} caries detected. Immediate dental attention is strongly recommended."
            elif gum_inflam > 0:
                assessment = f"{gum_inflam} gum inflammation area(s) found. Please enhance oral hygiene."
            elif recession > 0:
                assessment = f"{recession} gum recession area(s) detected. Consider professional advice."
            elif tooth == 0:
                assessment = "No teeth detected. Please check the uploaded image or retake the photo."
            c.drawString(60, y, assessment)
            y -= 24

            # Prescription
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawString(50, y, "Prescription")
            y -= 18
            c.setFont("Helvetica", 11)
            c.setFillColor(colors.black)
            prescription = "No prescription is necessary at this time, as the patient is in good health with no identified medical concerns."
            if caries > 0 or gum_inflam > 0 or recession > 0:
                prescription = "Please consult a dentist for further evaluation and treatment."
            elif tooth == 0:
                prescription = "No prescription due to missing teeth detection."
            c.drawString(60, y, prescription)
            y -= 30

            # 插入mask图片
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawString(50, y, "Segmentation Mask:")
            y -= 10
            img_buf = io.BytesIO()
            mask_img.save(img_buf, format="PNG")
            img_buf.seek(0)
            img_reader = ImageReader(img_buf)
            img_width = 220
            img_height = 180
            c.drawImage(img_reader, 50, y - img_height, width=img_width, height=img_height, mask='auto')

            # 颜色说明（legend），透明度与渲染一致
            legend_y = y - 10
            legend_x = 290
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(colors.HexColor(LIGHT_BLUE))  # 浅蓝色
            c.drawString(legend_x, legend_y, "Color Legend:")
            legend_y -= 22
            c.setFont("Helvetica", 11)
            alpha_mask = 25  # 与图片渲染一致
            for idx, label in enumerate(class_labels):
                if label in ["Tooth", "Caries", "GumInflam", "Recession"]:
                    color = color_map[idx]
                    c.setFillColorRGB(color[0]/255, color[1]/255, color[2]/255, alpha=alpha_mask/255)
                    c.rect(legend_x, legend_y, 16, 16, fill=1, stroke=0)
                    c.setFillColor(colors.black)
                    c.drawString(legend_x + 22, legend_y + 2, label)
                    legend_y -= 20

            y = y - img_height - 30

            # 免责声明
            disclaimer = "Disclaimer: This report is generated by MyOral.ai using AI analysis and is for reference only. For a professional diagnosis, please consult a licensed dentist."
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            max_width = width - 100
            words = disclaimer.split()
            line = ''
            for word in words:
                test_line = line + word + ' '
                if c.stringWidth(test_line, "Helvetica-Oblique", 9) < max_width:
                    line = test_line
                else:
                    c.drawString(50, y, line.strip())
                    y -= 12
                    line = word + ' '
            if line:
                c.drawString(50, y, line.strip())
                y -= 12

            # Footer
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor("#888888"))
            c.drawCentredString(width / 2, 32, "For inquiries and appointments, visit www.MyOral.ai")
            c.save()
            buf.seek(0)
            return buf

        h, w = mask.shape
        # 颜色渲染
        color_map = [
            (255, 255, 255),     # 0: Background (white)
            (255, 0, 0),         # 1: Tooth (red)
            (0, 255, 0),         # 2: Caries (green)
            (0, 0, 255),         # 3: GumInflam (blue)
            (255, 255, 255),     # 4: Mouth (white, same as background, not rendered)
            (255, 255, 0),       # 5: Gum (yellow)
            (255, 0, 255),       # 6: Recession (magenta)
            (0, 255, 255),       # 7: Ortho (cyan)
            (255, 128, 0),       # 8: Mucosa (orange)
            (0, 0, 0),           # 9: Splint (black)
        ]
        color_mask = np.zeros((h, w, 3), dtype=np.uint8)
        for v, color in enumerate(color_map):
            color_mask[mask == v] = color
        color_mask[(mask > len(color_map) - 1)] = (255, 255, 255)
        color_mask_pil = Image.fromarray(color_mask, mode="RGB").convert("RGBA")
        mask_np = np.array(mask)

        # 画轮廓线
        contour_img = np.array(color_mask_pil).copy()
        for class_id in np.unique(mask_np):
            if class_id == 0:
                continue
            binary = (mask_np == class_id).astype(np.uint8) * 255
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(contour_img, contours, -1, (255, 255, 255, 255), 2)
        contour_mask_pil = Image.fromarray(contour_img).convert("RGBA")
        # 叠加到原图，增加透明度
        original_img = uploaded_img.resize(contour_mask_pil.size).convert("RGBA")
        alpha_mask = 25  # 0-255, 80更透明
        color_mask_pil.putalpha(alpha_mask)
        contour_mask_pil.putalpha(alpha_mask)
        blended = Image.alpha_composite(original_img, color_mask_pil)
        blended = Image.alpha_composite(blended, contour_mask_pil)
        blended = blended.convert("RGB")

        if userId == "0":
            buf = io.BytesIO()
            blended.save(buf, format="PNG")
            # 生成PDF报告（无用户信息）
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            pdf_buf = generate_pdf_report(class_object_counts, timestamp, blended, color_map, class_labels)
            pdf_base64 = base64.b64encode(pdf_buf.read()).decode()
            return StreamingResponse(buf, media_type="image/png", headers={
                "X-Report-PDF-Base64": pdf_base64
            })
        else:
            # 以时间戳为文件夹名
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            user_mask_dir = os.path.join("masks", userId, datetime.utcnow().strftime("%Y%m%d%H%M%S"))
            os.makedirs(user_mask_dir, exist_ok=True)
            mask_path = os.path.join(user_mask_dir, "mask.png")
            blended.save(mask_path)
            # 保存类别ID图（二维数组，npy格式）
            mask_id_path = os.path.join(user_mask_dir, "mask_id.npy")
            np.save(mask_id_path, mask_np)
            # 查找用户信息（通过数据库）
            user_info = None
            try:
                from database import get_db, fetch_user_by_id
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
                db.close()
            except Exception:
                user_info = None
            # 生成PDF报告
            pdf_buf = generate_pdf_report(class_object_counts, timestamp, blended, color_map, class_labels, user_info)
            pdf_path = os.path.join(user_mask_dir, "report.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_buf.read())
            # 返回的文件名使用同一个timestamp
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
    """
    读取指定路径的PDF报告并返回，支持客户端下载。
    :param pdf_path: PDF文件的相对或绝对路径
    :return: FileResponse
    """
    pdf_path=os.path.join('masks',pdf_path)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    filename = os.path.basename(pdf_path)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )