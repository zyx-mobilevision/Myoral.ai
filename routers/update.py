from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_email, fetch_user_by_phone, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

class UpdateUserInfo(BaseModel): #这是更新时输入的核心数据，封装为class
    surname: Optional[str] = None
    givename: Optional[str] = None
    sex: Optional[str] = None
    birthYear: Optional[int] = None

class UserInfoResponse(BaseModel):#这是完成put请求后返回的响应数据，也封装为class
    surname: Optional[str]
    givename: Optional[str]
    sex: Optional[str]
    birthYear: Optional[int]
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

@router.put("/v1/users/{userId}", status_code=status.HTTP_200_OK)
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
    # Validate sex
    if update_data.sex and update_data.sex not in ["M", "F"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sex value. Accepted values: M, F"
        )
    # Prepare update fields
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    if update_fields:
        update_fields["lastUpdatedAt"] = datetime.utcnow()
        update_user(userId, update_fields, db)
    # Fetch updated user
    updated_user = fetch_user_by_id(userId, db)
    return UserInfoResponse(
        surname=updated_user.surname,
        givename=updated_user.givename,
        sex=updated_user.sex,
        birthYear=updated_user.birthYear,
        message="User information updated successfully")