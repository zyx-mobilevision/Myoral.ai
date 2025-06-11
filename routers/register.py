from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db, Photo,
    insert_user, fetch_user_by_name, fetch_user_by_id, fetch_user_by_token,
    fetch_user_by_email, fetch_user_by_phone, update_user, delete_user
)
import uuid
from datetime import datetime
from enum import Enum
# 用户注册相关的API
# Full name, emai address  username, password, gender:M/F/other, age group (6-12 child, 13-19 teen, 20-59 adult, >60 senior), phone number, 
class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "other"

class AgeGroup(str, Enum):
    CHILD = "6-12"      # child
    TEEN = "13-19"      # teen
    ADULT = "20-59"     # adult
    SENIOR = "60+"      # senior
    


class UserRegistration(BaseModel):
    fullName: str
    email: str
    username: str
    password: str
    gender: Gender
    age_group: AgeGroup
    phoneNumber: str
    
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
    #     )    # Check for duplicate username
    existing_user = fetch_user_by_name(user.username, db)
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username already registered"
        )

    # Check for duplicate email
    if fetch_user_by_email(user.email, db):
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    # Check for duplicate phone number
    if fetch_user_by_phone(user.phoneNumber, db):
        raise HTTPException(
            status_code=409,
            detail="Phone number already registered"
        )

    # Create user record
    user_id = str(uuid.uuid4())
    user_data = {
        "userId": user_id,
        "fullName": user.fullName,
        "email": user.email,
        "username": user.username,
        "password": user.password,  # Should hash in production
        "gender": user.gender,
        "ageGroup": user.age_group,
        "phoneNumber": user.phoneNumber,
        "createdAt": datetime.utcnow(),
        "lastUpdatedAt": datetime.utcnow(),
    }
    insert_user(user_data, db)
    return UserRegistrationResponse(
        userId=user_id,
        message="Account created successfully"
    )