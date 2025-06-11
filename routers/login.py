from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_name, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime


class UserLogin(BaseModel):
    userId: str = ""
    username: str = ""
    password: str
class UserLoginResponse(BaseModel):
    userId: str
    token: str
    message: str

router = APIRouter()
@router.post("/login",  status_code=status.HTTP_200_OK)  # Full path will be /v1/users/login
def login_user(login: UserLogin, db: Session = Depends(get_db)):
    user = None
    # Try to find user by userId, email, or phoneNumber
    if login.userId:
        user = fetch_user_by_id(login.userId, db)
    elif login.username:
        user = fetch_user_by_name(login.username, db)
    # User not found
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    # Password check
    if user.password != login.password:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    # Generate token
    token = str(uuid.uuid4())
    update_user(user.userId, {"token": token, "lastUpdatedAt": datetime.utcnow()}, db)
    return UserLoginResponse(
        userId=user.userId,
        token=token,
        message="Login successful"
    )