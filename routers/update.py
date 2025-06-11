from fastapi import APIRouter, Depends, HTTPException,status
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

class UpdateUserInfo(BaseModel): #这是更新时输入的核心数据，封装为class
    username: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[str] = None

class UserInfoResponse(BaseModel):#这是完成put请求后返回的响应数据，也封装为class
    username: Optional[str]
    gender: Optional[str]
    ageGroup: Optional[str]
    message: str

# 辅助函数
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

@router.put("/{userId}", status_code=status.HTTP_200_OK)  # Full path will be /v1/users/{userId}
def update_user_info(
    userId: str,
    update_data: UpdateUserInfo,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Permission check
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
    # Validate gender
    if update_data.gender and update_data.gender not in ["M", "F"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid gender value. Accepted values: M, F"
        )
    # Prepare update fields
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    if update_fields:
        update_fields["lastUpdatedAt"] = datetime.utcnow()
        update_user(userId, update_fields, db)
    # Fetch updated user
    updated_user = fetch_user_by_id(userId, db)
    return UserInfoResponse(
        username=updated_user.username,
        gender=updated_user.gender,
        ageGroup=updated_user.ageGroup,
        message="User information updated successfully")