from fastapi import APIRouter, Depends, HTTPException, Response
import os
from sqlalchemy.orm import Session
from database import get_db, Photo


def get_photo(db: Session, photo_id: str):
    return db.query(Photo).filter(Photo.id == photo_id).first()

router = APIRouter()
@router.get("/photo/{photo_id}")
async def read_photo(photo_id: str, db: Session = Depends(get_db)):
    photo_record = get_photo(db, photo_id)
    if not photo_record:
        raise HTTPException(status_code=404, detail="Photo not found")

    # 读取文件内容
    file_path = photo_record.image_data
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "rb") as img_file:  # 以二进制模式读取文件
        return Response(content=img_file.read(), media_type="image/jpeg")
    #用Response（内置类）生成响应式http