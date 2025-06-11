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

class UserDetailResponse(BaseModel): # 这是获取用户信息的响应模型，无需输入数据模型
    userId: str
    fullName: str
    gender:str
    ageGroup: str  
    createdAt: str
    lastUpdatedAt: str


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


# 获取用户信息
router = APIRouter()

@router.get("/api/users/{userId}", response_model=UserDetailResponse, status_code=200)
def get_user_info(
    userId: str,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Validate userId format (UUID)
    try:
        uuid.UUID(userId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid userId format")
    # Find user
    user = fetch_user_by_id(userId, db)
    if not user:
        raise HTTPException(status_code=404, detail="User with the specified userId does not exist.")
    # Access control: allow self or reviewer
    current_user = fetch_user_by_id(current_user_id, db)
    if current_user_id != userId and (not current_user or current_user.usertype != "reviewer"):
        raise HTTPException(status_code=403, detail="Not allowed to view other users' info")
    # Compose full name
    full_name = current_user.username
    # Use ISO format for createdAt/lastUpdatedAt, fallback to now if not present
    created_at = user.createdAt.isoformat() + "Z" if user.createdAt else datetime.utcnow().isoformat() + "Z"
    last_updated_at = user.lastUpdatedAt.isoformat() + "Z" if user.lastUpdatedAt else created_at
    return UserDetailResponse(
        userId=user.userId,
        fullName=full_name,
        gender=user.gender,
        ageGroup=user.ageGroup,
        createdAt=created_at,
        lastUpdatedAt=last_updated_at
    )