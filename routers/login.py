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
from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText

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

class ChangePasswordRequest(BaseModel):
    userId: str
    old_password: str
    new_password: str

router = APIRouter()
@router.post("/login",  status_code=status.HTTP_200_OK)
def login_user(login: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = fetch_user_by_email(login.email, db)
    print(f"[DEBUG] login received userid: {user.userId}") 
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: User not found or email not registered"
        )
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

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(data: ChangePasswordRequest, db: Session = Depends(get_db)):
    user = fetch_user_by_id(data.userId, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Check old password
    if not bcrypt.checkpw(data.old_password.encode('utf-8'), user.password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Old password is incorrect")
    # Update new password
    hashed_pw = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    update_user(user.userId, {"password": hashed_pw, "lastUpdatedAt": datetime.utcnow()}, db)
    return {"message": "Password changed successfully"}

def send_reset_email(to_email, reset_url):
    # Simple email sending (configure SMTP as needed)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "your@email.com")
    smtp_pass = os.getenv("SMTP_PASS", "yourpassword")
    msg = MIMEText(f"Please reset your password using the following link:\n{reset_url}")
    msg['Subject'] = "Password Reset Request"
    msg['From'] = smtp_user
    msg['To'] = to_email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

@router.post("/reset-generate", status_code=status.HTTP_200_OK)
def reset_generate(userId: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = fetch_user_by_id(userId, db)
    if not user or not user.email:
        raise HTTPException(status_code=404, detail="User not found or email not set")
    # Generate reset token
    reset_token = str(uuid.uuid4())
    update_user(userId, {"resetToken": reset_token, "resetTokenCreatedAt": datetime.utcnow()}, db)
    # Build reset URL (replace with actual frontend domain)
    reset_url = f"https://your-frontend-domain.com/reset-confirm?token={reset_token}"
    background_tasks.add_task(send_reset_email, user.email, reset_url)
    return {"message": "Reset token generated and email sent"}

class ResetConfirmRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-confirm", status_code=status.HTTP_200_OK)
def reset_confirm(data: ResetConfirmRequest, db: Session = Depends(get_db)):
    user = fetch_user_by_token(data.token, db)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    # Update new password
    hashed_pw = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    update_user(user.userId, {"password": hashed_pw, "resetToken": None, "lastUpdatedAt": datetime.utcnow()}, db)
    return {"message": "Password reset successfully"}