from sqlalchemy import create_engine, Column, String, Integer, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Local PostgreSQL database URL   

DATABASE_URL = "postgresql://postgres:123123@localhost:5432/myoral"

# SQLAlchemy setup for ORM (sync only)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define User model for PostgreSQL
class User(Base):
    __tablename__ = "0611Users"
    userId = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # Should be hashed in production
    gender = Column(String, nullable=True)
    ageGroup = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    lastUpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    token = Column(String, nullable=True)

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
    return db.query(User).filter(User.token == token).first()

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