"""
NoteShare Junction Table Model

This module defines the NoteShare junction table for implementing
note sharing functionality between Notes and Users.
"""
from sqlmodel import SQLModel, Field

class NoteShare(SQLModel, table=True):
    """
    Junction table for many-to-many relationship between Notes and Users for sharing.
    
    This table enables a note to be shared with multiple users. The note owner is
    tracked separately in the Note.user_id field. The table uses a composite primary
    key of both note_id and user_id.
    
    Attributes:
        note_id: Foreign key to the note being shared
        user_id: Foreign key to the user the note is shared with
    """
    __tablename__ = "note_shares"
    
    note_id: int = Field(foreign_key="notes.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)
