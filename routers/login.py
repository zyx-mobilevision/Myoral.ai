from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_email, fetch_user_by_phone, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime


class UserLogin(BaseModel):
    userId: str = ""
    email: str = ""
    phoneNumber: str = ""
    password: str
class UserLoginResponse(BaseModel):
    userId: str
    usertype: str
    token: str
    message: str

router = APIRouter()
@router.post("/v1/users/login",  status_code=status.HTTP_200_OK)
def login_user(login: UserLogin, db: Session = Depends(get_db)):
    user = None
    # Try to find user by userId, email, or phoneNumber
    if login.userId:
        user = fetch_user_by_id(login.userId, db)
    elif login.email:
        user = fetch_user_by_email(login.email, db)
    elif login.phoneNumber:
        user = fetch_user_by_phone(login.phoneNumber, db)
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
        usertype=user.usertype,
        token=token,
        message="Login successful"
    )