from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_name, fetch_user_by_id, fetch_user_by_token, update_user, delete_user
)
import uuid
from datetime import datetime
from enum import Enum
# 用户注册相关的API
class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"

class AgeGroup(str, Enum):
    CHILD = "6-12"  # 儿童
    ADULT = ">13"    # 成人

class UserRegistration(BaseModel):
    gender: Gender
    age_group: AgeGroup
    username: str
    password: str
    
#响应模型
class UserRegistrationResponse(BaseModel):
    userId: str
    message: str

router = APIRouter()
@router.post("/register", response_model=UserRegistrationResponse)  # Full path will be /v1/users/register
def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    # # Validate usertype
    # if user.usertype not in ["enduser", "reviewer"]:
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Invalid usertype. Must be 'enduser' or 'reviewer'"
    #     )
    # Check for duplicate email
    existing_user = fetch_user_by_name(user.username, db)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Name already registered"
        )

    # Create user record
    user_id = str(uuid.uuid4())
    user_data = {
        "userId": user_id,
        "username": user.username,
        "gender": user.gender,
        "password": user.password,  # Should hash in production
        "ageGroup": user.age_group,
        "createdAt": datetime.utcnow(),
        "lastUpdatedAt": datetime.utcnow(),
    }
    insert_user(user_data, db)
    return UserRegistrationResponse(
        userId=user_id,
        message="Account created successfully"
    )