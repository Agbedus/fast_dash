"""
Note Model Module

This module defines the Note model and NoteShare junction table for implementing
note sharing functionality. Notes can be owned by a user and shared with multiple
other users.
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

from app.models.note_share import NoteShare


class NoteBase(SQLModel):
    """
    Base properties for a Note.
    """
    # Basic note content
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    
    # Note type - common values: "note", "checklist", "todo", "journal"
    type: str = Field(default="note")
    
    # Tags stored as JSON string array for flexible categorization
    tags: Optional[str] = None  # e.g., '["work", "important", "project-x"]'
    
    # Boolean flags stored as integers for MySQL compatibility
    is_pinned: int = 0      # Pin important notes to the top
    is_archived: int = 0    # Archive old/completed notes
    is_favorite: int = 0    # Mark frequently accessed notes
    
    # Visual customization
    cover_image: Optional[str] = None  # URL or file path
    
    # Audit timestamps
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Ownership and associations
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    task_id: Optional[int] = Field(default=None, foreign_key="tasks.id")


class Note(NoteBase, table=True):
    """
    Note table model.
    """
    __tablename__ = "notes"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationship to access users this note is shared with via NoteShare junction table
    shared_with: List["User"] = Relationship(back_populates="shared_notes", link_model=NoteShare)


class NoteRead(NoteBase):
    """Basic schema for reading a note."""
    id: int


from app.schemas.user import UserRead


class NoteReadWithShared(NoteRead):
    """Extended schema for reading a note with its shared users."""
    shared_with: List[UserRead] = []
