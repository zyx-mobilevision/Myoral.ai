from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import (
    User, get_db,Photo,
    insert_user, fetch_user_by_name, fetch_user_by_id, fetch_user_by_token, update_user, delete_user, send_email
)
import uuid
from datetime import datetime, timedelta
from enum import Enum
import jwt
import os
from dotenv import load_dotenv
import bcrypt
import requests

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"

class AgeGroup(str, Enum):
    Child = "6-12" 
    Teen = "13-19"    
    Adult= "20-59"
    Senior = "60+"  
    
class UserRegistration(BaseModel):
    gender: Gender = None
    age_group: AgeGroup = None
    username: str = None
    password: str = None
    email: str = None
    phoneNumber: str = None
    fullName: str = None
    birthdate: str = None
    register_method: str = "email"
    client_id: str = "0"  
    
class UserRegistrationResponse(BaseModel):
    userId: str
    message: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    token: str
    new_password: str

def format_hk_phone_number(phone: str) -> str:
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+852'):
        return phone
    if phone.startswith('852'):
        return '+' + phone
    if phone.startswith('+'):
        return phone
    return '+852' + phone

router = APIRouter()
@router.post("/register", response_model=UserRegistrationResponse)
def register_user(user: UserRegistration, request: Request, db: Session = Depends(get_db)):
    # 
    # if db.query(User).filter(User.email == user.email).first():
    #     raise HTTPException(
    #         status_code=409,
    #         detail="Email already registered"
    #     )
    # 
    # if user.phoneNumber!='' and db.query(User).filter(User.phoneNumber == user.phoneNumber).first():
    #     raise HTTPException(
    #         status_code=409,
    #         detail="Phone number already registered"
    #     )
   
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    # Create user record
    user_id = str(uuid.uuid4())
    
    user_data ={
        "userId":user_id,
        "username": user.username,
        "gender": user.gender,
        "email": user.email,
        "phoneNumber": user.phoneNumber,
        "fullName": user.fullName,
        "birthdate": user.birthdate, 
        "password": hashed_password,  
        "ageGroup": user.age_group,
        "createdAt": datetime.utcnow(),
        "lastUpdatedAt": datetime.utcnow(),
        "register_method": user.register_method,
        "confirmed": True,
        "confirmed_at": None,
        "client_id": user.client_id if hasattr(user, 'client_id') else "0"
    }
    insert_user(user_data, db)
    # if user.register_method == "email":
    #     confirm_token = jwt.encode({"userId": user_id, "exp": datetime.utcnow() + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)
    #     base_url = str(request.base_url).rstrip('/')
    #     confirm_url = f"{base_url}/v1/register/confirm/{confirm_token}"
    #     subject = "Confirm your account"
    #     body = f"<p>Hi {user.username},</p><p>Please confirm your email by clicking the link below:</p><p><a href='{confirm_url}'>{confirm_url}</a></p>"
    #     send_email(user.email, subject, body)
    #     return UserRegistrationResponse(userId=user_id, message="Account created. Please check your email to confirm.")
    # elif user.register_method == "sms":
    #     return UserRegistrationResponse(userId=user_id, message="Account created. Please verify your phone number via SMS.")
    # else:
    #     raise HTTPException(status_code=400, detail="register_method must be 'email' or 'sms'.")
    return UserRegistrationResponse(userId=user_id, message="Account created.")

# @router.get("/register/confirm/{token}") 
# def confirm_email(token: str, db: Session = Depends(get_db)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id = payload.get("userId")
#         user = fetch_user_by_id(user_id, db)
#         if not user:
#             return {"message": "Invalid or expired token."}
#         if user.confirmed:
#             return {"message": "Account already confirmed."}
#         update_user(user_id, {"confirmed": True, "confirmed_at": datetime.utcnow()}, db)
#         return {"message": "Account confirmed successfully."}
#     except Exception as e:
#         return {"message": f"Invalid or expired token. {str(e)}"}

@router.post("/reset-password-request")
def reset_password_request(data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If this email is registered, a reset link has been sent."}
    reset_token = jwt.encode({"userId": user.userId, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
    base_url = str(request.base_url).rstrip('/')
    reset_url = f"{base_url}/v1/register/reset-password?token={reset_token}"
    subject = "Reset your password"
    body = f"<p>Hi {user.username},</p><p>Click the link below to reset your password (valid for 1 hour):</p><p><a href='{reset_url}'>{reset_url}</a></p>"
    send_email(user.email, subject, body)
    return {"message": "If this email is registered, a reset link has been sent."}

@router.post("/reset-password")
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("userId")
        user = fetch_user_by_id(user_id, db)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token.")
        # hash to store password 
        hashed_pw = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_user(user_id, {"password": hashed_pw, "lastUpdatedAt": datetime.utcnow()}, db)
        return {"message": "Password reset successful."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or expired token. {str(e)}")
    

# @router.post("/send-sms-code")
# def send_sms_code(phoneNumber: str = Body(..., embed=True)):
#     phoneNumber = format_hk_phone_number(phoneNumber)
#     url = f"https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_SID}/Verifications"
#     data = {
#         "To": phoneNumber,
#         "Channel": "sms"
#     }
#     auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
#     response = requests.post(url, data=data, auth=auth)
#     if response.status_code == 201:
#         return {"message": "SMS code sent successfully."}
#     else:
#         return {"message": "Failed to send SMS code.", "detail": response.text}
#
# @router.post("/verify-sms-code")
# def verify_sms_code(phoneNumber: str = Body(...), sms_code: str = Body(...), db: Session = Depends(get_db)):
#     phoneNumber = format_hk_phone_number(phoneNumber)
#     user = db.query(User).filter(User.phoneNumber == phoneNumber).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found.")
#     if user.confirmed:
#         return {"message": "User already confirmed."}
#     sms_status = check_sms_verification(phoneNumber, sms_code)
#     if sms_status == "approved":
#         update_user(user.userId, {"confirmed": True, "confirmed_at": datetime.utcnow()}, db)
#         return {"message": "Phone verified and account activated."}
#     else:
#         raise HTTPException(status_code=400, detail="Invalid or expired SMS verification code.")
#
# def check_sms_verification(phone_number: str, code: str):
#     url = f"https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_SID}/VerificationCheck"
#     data = {
#         "To": phone_number,
#         "Code": code
#     }
#     auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
#     response = requests.post(url, data=data, auth=auth)
#     if response.status_code == 200:
#         result = response.json()
#         return result.get("status", "failed")
#     else:
#         print(f"[Twilio API Error] {response.status_code}: {response.text}")
#         return "failed"