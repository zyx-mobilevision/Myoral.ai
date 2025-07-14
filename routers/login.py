from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_name,fetch_user_by_email, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt

from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


class UserLogin(BaseModel):
    email: str
    password: str
class UserLoginResponse(BaseModel):
    userId: str
    token: str
    message: str

router = APIRouter()
@router.post("/login",  status_code=status.HTTP_200_OK)
def login_user(login: UserLogin, db: Session = Depends(get_db)):
    # 用email查找用户
    user = fetch_user_by_email(login.email, db)  # 假设fetch_user_by_name支持email查找
    print(f"[DEBUG] login received userid: {user.userId}") 
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: User not found or email not registered"
        )
    # 检查邮箱是否已确认
    # if not getattr(user, "confirmed", True):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Email not confirmed. Please check your email to activate your account."
    #     )
    # Password check (使用bcrypt校验)
    if not bcrypt.checkpw(login.password.encode('utf-8'), user.password.encode('utf-8')):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized, invalid password"
        )
    # Generate JWT token
    payload = {
        "userId": user.userId,
        "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    update_user(user.userId, {"token": token, "lastUpdatedAt": datetime.utcnow()}, db)
    return UserLoginResponse(
        userId=user.userId,
        token=token,
        message="Login successful"
    )