from typing import Optional
from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime

class Notification(SQLModel, table=True):
    """
    Notification model for storing user alerts and system messages.
    """
    __tablename__ = "notifications"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    recipient_id: str = Field(index=True, foreign_key="users.id")
    sender_id: Optional[str] = Field(default=None, foreign_key="users.id")
    
    title: str = Field(nullable=False)
    message: str = Field(nullable=False)
    type: str = Field(default="info")  # info, success, warning, error
    
    is_read: bool = Field(default=False)
    
    # Metadata for contextual navigation
    resource_type: Optional[str] = Field(default=None)  # e.g., "task", "project", "note"
    resource_id: Optional[str] = Field(default=None)    # The ID of the related object
    
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
