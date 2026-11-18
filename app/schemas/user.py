from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Optional[str] = "customer"

class UserCreate(UserBase):
    # bcrypt sirf pehle 72 bytes use karta hai, is liye max 72
    password: str = Field(min_length=8, max_length=72)

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None