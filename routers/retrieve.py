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

class UserDetailResponse(BaseModel):
    userId: str
    username: str
    email: str
    phoneNumber: str
    fullName: str
    birthdate: str
    gender:str
    ageGroup: str  
    createdAt: str
    lastUpdatedAt: str


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


# Get user info
router = APIRouter()

@router.get("/users/{userId}", response_model=UserDetailResponse, status_code=200)
def get_user_info(
    userId: str,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        uuid.UUID(userId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid userId format")
    user = fetch_user_by_id(userId, db)
    if not user:
        raise HTTPException(status_code=404, detail="User with the specified userId does not exist.")
    current_user = fetch_user_by_id(current_user_id, db)
    if current_user_id != userId and (not current_user or current_user.usertype != "reviewer"):
        raise HTTPException(status_code=403, detail="Not allowed to view other users' info")
    created_at = user.createdAt.isoformat() + "Z" if user.createdAt else datetime.utcnow().isoformat() + "Z"
    last_updated_at = user.lastUpdatedAt.isoformat() + "Z" if user.lastUpdatedAt else created_at
    return UserDetailResponse(
        userId=user.userId,
        username=user.username,
        email=user.email,
        phoneNumber=user.phoneNumber,
        fullName=user.fullName,
        birthdate=user.birthdate,
        gender=user.gender,
        ageGroup=user.ageGroup,
        createdAt=created_at,
        lastUpdatedAt=last_updated_at
    )