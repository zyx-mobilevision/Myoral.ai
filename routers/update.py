from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
import os

class UpdateUserInfo(BaseModel): # core update input
    username: Optional[str] = None
    fullName: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[str] = None
    birthdate: Optional[str] = None
    phoneNumber: Optional[str] = ""
    appointDate: Optional[str] = None  # 精确到小时的预约时间（如：2024-06-10 15:00）

class UserInfoResponse(BaseModel): # put response
    username: Optional[str]
    fullName: Optional[str]
    gender: Optional[str]
    ageGroup: Optional[str]
    birthdate: Optional[str]
    phoneNumber: Optional[str]
    appointDate: Optional[str]  # 精确到小时的预约时间
    message: str

# helper
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

router = APIRouter()

@router.put("/users/{userId}", status_code=status.HTTP_200_OK)
def update_user_info(
    userId: str,
    username: Optional[str] = Form(None),
    fullName: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    ageGroup: Optional[str] = Form(None),
    birthdate: Optional[str] = Form(None),
    phoneNumber: Optional[str] = Form(""),
    appointDate: Optional[str] = Form(None),  # 精确到小时的预约时间
    photo: UploadFile = File(None),
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # check permission
    if userId != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Not allowed to modify other users"
        )
    user = fetch_user_by_id(userId, db)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    # gender check
    if gender and gender not in ["M", "F", "O"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid gender value. Accepted values: M, F, O"
        )
    # update fields
    update_fields = {}
    if username is not None:
        update_fields["username"] = username
    if fullName is not None:
        update_fields["fullName"] = fullName
    if gender is not None:
        update_fields["gender"] = gender
    if ageGroup is not None:
        update_fields["ageGroup"] = ageGroup
    if birthdate is not None:
        update_fields["birthdate"] = birthdate
    if phoneNumber is not None:
        update_fields["phoneNumber"] = phoneNumber
    if appointDate is not None:
        update_fields["appointDate"] = appointDate
    if update_fields:
        update_fields["lastUpdatedAt"] = datetime.utcnow()
        update_user(userId, update_fields, db)
    # save photo
    if photo is not None:
        os.makedirs("users", exist_ok=True)
        photo_path = os.path.join("users", f"{userId}.jpg")
        with open(photo_path, "wb") as f:
            f.write(photo.file.read())
    # get updated user
    updated_user = fetch_user_by_id(userId, db)
    return UserInfoResponse(
        username=updated_user.username,
        fullName=updated_user.fullName,
        gender=updated_user.gender,
        ageGroup=updated_user.ageGroup,
        birthdate=updated_user.birthdate,
        phoneNumber=updated_user.phoneNumber,
        appointDate=getattr(updated_user, "appointDate", None),  # 新增
        message="User information updated successfully"
    )