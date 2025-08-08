
# FastAPI router for user registration, password reset, and Google login endpoints
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
# Import database models and utility functions
from database import (
    User, get_db, Photo,
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

# Load environment variables from .env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

router = APIRouter()

# Enum for user gender
class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


# Enum for user age group
class AgeGroup(str, Enum):
    Child = "6-12" 
    Teen = "13-19"    
    Adult= "20-59"
    Senior = "60+"  
    

# Pydantic model for user registration request
class UserRegistration(BaseModel):
    gender: Gender = None
    age_group: AgeGroup = None
    username: str = None
    password: str = None
    email: str = None
    phoneNumber: str = None
    fullName: str = None
    birthdate: str = None
    register_method: str = "email"  # registration method: email, sms, google
    client_id: str = "0"  # client identifier
    

# Pydantic model for registration response
class UserRegistrationResponse(BaseModel):
    userId: str
    message: str


# Pydantic model for password reset request
class PasswordResetRequest(BaseModel):
    email: str


# Pydantic model for password reset confirmation
class PasswordReset(BaseModel):
    token: str
    new_password: str


# Utility function to format Hong Kong phone numbers to +852 format
def format_hk_phone_number(phone: str) -> str:
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+852'):
        return phone
    if phone.startswith('852'):
        return '+' + phone
    if phone.startswith('+'):
        return phone
    return '+852' + phone


# Endpoint: Register a new user
# Hashes password, creates user record, and inserts into database
@router.post("/register", response_model=UserRegistrationResponse)
def register_user(user: UserRegistration, request: Request, db: Session = Depends(get_db)):
    # Uncomment below to check for duplicate email or phone number
    # if db.query(User).filter(User.email == user.email).first():
    #     raise HTTPException(status_code=409, detail="Email already registered")
    # if user.phoneNumber!='' and db.query(User).filter(User.phoneNumber == user.phoneNumber).first():
    #     raise HTTPException(status_code=409, detail="Phone number already registered")

    # Hash the password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    # Generate unique user ID
    user_id = str(uuid.uuid4())

    # Prepare user data for insertion
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
    # Insert user into database
    insert_user(user_data, db)

    # Uncomment below to send confirmation email or SMS
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


# Endpoint: Confirm user email (commented out)
# Decodes token, confirms user account, and updates confirmation status
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


# Endpoint: Request password reset
# Generates a reset token and sends a reset link to the user's email
@router.post("/reset-password-request")
def reset_password_request(data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Always return success message to avoid leaking user existence
        return {"message": "If this email is registered, a reset link has been sent."}
    # Generate JWT reset token valid for 1 hour
    reset_token = jwt.encode({"userId": user.userId, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
    base_url = str(request.base_url).rstrip('/')
    reset_url = f"{base_url}/v1/register/reset-password?token={reset_token}"
    subject = "Reset your password"
    body = f"<p>Hi {user.username},</p><p>Click the link below to reset your password (valid for 1 hour):</p><p><a href='{reset_url}'>{reset_url}</a></p>"
    send_email(user.email, subject, body)
    return {"message": "If this email is registered, a reset link has been sent."}


# Endpoint: Reset password using token
# Verifies token, hashes new password, and updates user record
@router.post("/reset-password")
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    try:
        # Decode JWT token
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("userId")
        user = fetch_user_by_id(user_id, db)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token.")
        # Hash and update new password
        hashed_pw = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_user(user_id, {"password": hashed_pw, "lastUpdatedAt": datetime.utcnow()}, db)
        return {"message": "Password reset successful."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid or expired token. {str(e)}")
    

# Endpoint: Login or register user using Google ID token
# Verifies Google token, checks for existing user, or creates new user with Google info
@router.post("/login/google", response_model=UserRegistrationResponse)
def google_login(id_token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Login or register user using Google ID token from frontend (Flutter).
    """
    # Verify token with Google
    google_api = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    resp = requests.get(google_api)
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google token.")
    info = resp.json()
    email = info.get("email")
    fullName = info.get("name")
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email.")
    # Check if user exists by email
    user = db.query(User).filter(User.email == email).first()
    if user:
        user_id = user.userId
        message = "Login successful."
    else:
        # Create new user with Google account info
        user_id = str(uuid.uuid4())
        user_data = {
            "userId": user_id,
            "username": email.split("@")[0],
            "gender": None,
            "email": email,
            "phoneNumber": None,
            "fullName": fullName,
            "birthdate": None,
            "password": None,
            "ageGroup": None,
            "createdAt": datetime.utcnow(),
            "lastUpdatedAt": datetime.utcnow(),
            "register_method": "google",
            "confirmed": True,
            "confirmed_at": datetime.utcnow(),
            "client_id": "0"
        }
        insert_user(user_data, db)
        message = "Account created with Google login."
    return UserRegistrationResponse(userId=user_id, message=message)


# Endpoint: Send SMS code for phone verification (commented out)
# Uses Twilio API to send SMS code to user's phone number
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
# Endpoint: Verify SMS code for phone verification (commented out)
# Checks SMS code using Twilio API and updates user confirmation status
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
# Utility: Check SMS verification status using Twilio API (commented out)
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