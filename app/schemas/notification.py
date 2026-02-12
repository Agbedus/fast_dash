from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class NotificationRead(NotificationBase):
    id: str
    recipient_id: str
    sender_id: Optional[str] = None
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True
