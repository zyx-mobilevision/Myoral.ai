from sqlalchemy import create_engine, Column, String, Integer, DateTime, LargeBinary, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import jwt
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables from .env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
# Database URL (replace with your PostgreSQL credentials)
#using NeonDB as an example
#need another database
DATABASE_URL = "postgresql://neondb_owner:npg_VhGXzeoJca62@ep-still-brook-a1o2ku0m-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# SQLAlchemy setup for ORM (sync only)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define User model for PostgreSQL
class User(Base):
    __tablename__ = "Users"
    userId = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phoneNumber = Column(String, nullable=False)
    fullName = Column(String, nullable=False)
    birthdate = Column(String, nullable=False)  # Store as ISO format string
    password = Column(String, nullable=False)  # Stores hashed password
    gender = Column(String, nullable=True)
    ageGroup = Column(String, nullable=True)
    appointDate = Column(String, nullable=True)  # 精确到小时的预约时间（如：2024-06-10 15:00）
    createdAt = Column(DateTime, default=datetime.utcnow)
    lastUpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    token = Column(String, nullable=True)
    confirmed = Column(Boolean, default=False)  # 新增：邮箱是否已确认
    confirmed_at = Column(DateTime, nullable=True)  # 新增：邮箱确认时间
    register_method = Column(String, nullable=True)  # 新增：注册方式（email/sms）


class Photo(Base):
    __tablename__ = 'photos_path'
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    image_type = Column(String)  # 'front', 'left', 'right'
    image_data = Column(String)  # Store image as binary
    timestamp = Column(String)


# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get sync database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- User CRUD operations for sync PostgreSQL access ---

def insert_user(user_data: dict, db):
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

#next step: try to combine the functions below?
def fetch_user_by_name(name: str, db):
    return db.query(User).filter(User.username == name).first()

def fetch_user_by_id(user_id: str, db):
    return db.query(User).filter(User.userId == user_id).first()

def fetch_user_by_token(token: str, db):
    """
    解码JWT token,获取userId,再查找用户。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("userId")
        if not user_id:
            return None
        return db.query(User).filter(User.userId == user_id).first()
    except Exception:
        return None

def fetch_user_by_email(email: str, db):
    return db.query(User).filter(User.email == email).first()

def update_user(user_id: str, update_data: dict, db):
    user = db.query(User).filter(User.userId == user_id).first()
    if user:
        for k, v in update_data.items():
            setattr(user, k, v)
        db.commit()
        db.refresh(user)
    return user

def delete_user(user_id: str, db):
    user = db.query(User).filter(User.userId == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return user

def send_email(to_email, subject, body):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = smtp_user
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))
    print(f"[DEBUG] Try send email to {to_email} via {smtp_server}:{smtp_port} as {smtp_user}")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        print(f"[DEBUG] Email sent to {to_email} successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")