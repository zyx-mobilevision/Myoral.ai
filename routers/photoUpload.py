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
    insert_user, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
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
    photoID: List[str]  
    photoUrls: dict
    captureTimestamp: str
    message: str


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
        img = Image.open(file.file)
        file.file.seek(0)
        if img.format.lower() not in ['jpeg', 'png']:
            return False
        return True
    except Exception:
        return False

router = APIRouter()
@router.post("/upload/{userId}", response_model=PhotoUploadResponse)
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
    if userId != current_user_id:
        raise HTTPException(status_code=403, detail="Not allowed to upload photos for other users")
    try:
        capture_time = datetime.fromisoformat(captureTimestamp.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO 8601 format (e.g., 2025-04-16T12:30:00Z)")
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            PhotoMetadata(**metadata_dict)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid metadata format")
    photos = {"front": front, "left": left, "right": right}
    for name, photo in photos.items():
        if not validate_image(photo):
            raise HTTPException(status_code=400, detail=f"Invalid {name} image. Must be JPG/PNG")
    # Save images to file system
    photo_paths = {}
    upload_dir = f"uploads/{userId}/{capture_time.isoformat().replace(':', '-')}"
    os.makedirs(upload_dir, exist_ok=True)
    photo_ids = []
    for photo_type, photo in photos.items():
        file_path = os.path.join(upload_dir, f"{photo_type}.jpg")
        with open(file_path, "wb") as img_file:
            img_file.write(await photo.read())
        photo_paths[photo_type] = file_path
        db_photo = Photo(
            id=str(uuid.uuid4()),
            user_id=userId,
            image_type=photo_type,
            image_data=photo_paths[photo_type],
            timestamp=capture_time.isoformat()
        )
        photo_ids.append(db_photo.id)
        db.add(db_photo)
    db.commit()
    return PhotoUploadResponse(
        photoID=photo_ids,
        photoUrls=photo_paths,
        captureTimestamp=capture_time.isoformat(),
        message="Photos uploaded successfully"
    )