from fastapi import FastAPI, HTTPException, status, Depends, File, UploadFile, Form, Response, APIRouter
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.sql import select
from sqlalchemy.orm import Session
import json
import os
import shutil
from PIL import Image
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_email, fetch_user_by_phone, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List

class PhotoMetadata(BaseModel):
    cameraModel: Optional[str] = None
    deviceModel: Optional[str] = None
    appVersion: Optional[str] = None

class PhotoUploadResponse(BaseModel):
    photoID: List[str]  # List of photo IDs
    photoUrls: dict
    captureTimestamp: str
    message: str
#辅助函数
security = HTTPBearer()
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    user = fetch_user_by_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user.userId
def validate_image(file: UploadFile) -> bool:
    try:
        # Read image to verify format and dimensions
        img = Image.open(file.file)
        width, height = img.size
        file.file.seek(0)  # Reset file pointer
        
        # Check dimensions
        if width < 1000 or height < 1000:
            return False
            
        # Check format
        if img.format.lower() not in ['jpeg', 'png']:
            return False
            
        # Check file size (10MB)
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset pointer
        if size > 10 * 1024 * 1024:
            return False
            
        return True
    except Exception:
        return False

router = APIRouter()
@router.post("/v1/upload/{userId}", response_model=PhotoUploadResponse)
async def upload_photos(
    userId: str,
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    captureTimestamp: str = Form(...),
    metadata: Optional[str] = Form(None),
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Permission check
    if userId != current_user_id:
        raise HTTPException(status_code=403, detail="Not allowed to upload photos for other users")

    # Validate timestamp format
    try:
        capture_time = datetime.fromisoformat(captureTimestamp.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO 8601 format (e.g., 2025-04-16T12:30:00Z)")

    # Validate metadata if provided
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            PhotoMetadata(**metadata_dict)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid metadata format")

    # Validate images
    photos = {"front": front, "left": left, "right": right}
    for name, photo in photos.items():
        if not validate_image(photo):
            raise HTTPException(status_code=400, detail=f"Invalid {name} image. Must be JPG/PNG, minimum 1000x1000px, under 10MB")

   # 保存图像到文件系统
    photo_paths = {}
    upload_dir = f"uploads/{userId}/{capture_time.isoformat().replace(':', '-')}"  # 使用时间戳创建唯一目录
#但是要注意，这样的目录名可能会有问题，因为文件系统不允许某些字符，比如冒号(:)，所以我们用'-'替换它们
#而且注意，这个目录是本地的，最终是服务器对应的文件系统路径，所以之后需要转换为可访问路径
    # 创建目录
    os.makedirs(upload_dir, exist_ok=True)
    #common_id= str(uuid.uuid4())  # 生成一个通用ID用于所有照片,ERROR!
    photos = {"front": front, "left": left, "right": right}
    photo_ids = []  # 用于存储所有照片的ID
    for photo_type, photo in photos.items():
        file_path = os.path.join(upload_dir, f"{photo_type}.jpg")  # 或者使用合适的文件扩展名
        with open(file_path, "wb") as img_file:
            img_file.write(await photo.read())  # 保存图像数据

        # 存储文件路径
        photo_paths[photo_type] = file_path
        
        db_photo = Photo(
            id=str(uuid.uuid4()),  # 生成唯一ID
            user_id=userId,
            image_type=photo_type,
            image_data=photo_paths[photo_type],  # 存储路径而不是二进制数据
            timestamp=capture_time.isoformat()
        )
        photo_ids.append(db_photo.id)  # 添加到ID列表
        db.add(db_photo)

    db.commit()
    return PhotoUploadResponse(
    photoID=photo_ids,
    photoUrls=photo_paths,
    captureTimestamp=capture_time.isoformat(),  # 包含时间戳
    message="Photos uploaded successfully"
)