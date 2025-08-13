from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ElderlyUser(BaseModel):
    userId: str
    username: str
    email: str
    fullName: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[str] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True

class ElderlyListResponse(BaseModel):
    elderly: List[ElderlyUser]
    total: int
    page: int
    limit: int

class CreateElderlyRequest(BaseModel):
    username: Optional[str] = None  # Will auto-generate if not provided
    email: str
    fullName: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[str] = None
    phoneNumber: str

class AdminActionResponse(BaseModel):
    message: str
    elderly_id: str
    action: str

class AdminLoginResponse(BaseModel):
    userId: str
    token: str
    message: str
    isAdmin: bool = True
