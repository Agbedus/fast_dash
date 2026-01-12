from pydantic import BaseModel, EmailStr
from typing import List, Optional
from app.models.user import UserRole
import uuid

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: Optional[List[UserRole]] = None
    image: Optional[str] = None
    avatar_url: Optional[str] = None
    emailVerified: Optional[int] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

# Internal properties stored in DB
class UserInDBBase(UserBase):
    id: str
    email: EmailStr
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

# Properties to return to client
class UserRead(UserInDBBase):
    pass

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    password: str
