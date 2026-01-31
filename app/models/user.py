"""
User Model Module

This module defines the User model and UserRole enumeration for authentication
and authorization throughout the application.
"""
from enum import Enum
from typing import List, Optional
from sqlmodel import SQLModel, Field, JSON, Column, Relationship
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from app.models.note_share import NoteShare

if TYPE_CHECKING:
    from app.models.note import Note


class UserRole(str, Enum):
    """
    Enumeration of user roles defining permission levels in the system.
    
    Role hierarchy (from least to most privileged):
    - USER: Basic user with minimal permissions
    - CLIENT: External client user with limited access
    - STAFF: Internal staff member with standard access (default role)
    - MANAGER: Project manager with elevated permissions
    - ADMIN: Administrator with full access to most resources
    - SUPER_ADMIN: Super administrator with complete system access
    
    Permission checks throughout the API use these roles to control access to
    resources and operations.
    """
    USER = "user"
    CLIENT = "client"
    STAFF = "staff"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(SQLModel, table=True):
    """
    User model representing authenticated users in the system.
    
    Users are identified by UUID and authenticated via email/password. The roles
    field determines their permission level throughout the application.
    
    Attributes:
        id: Unique identifier (UUID) automatically generated for each user
        email: User's email address, used for authentication (required, unique, indexed)
        emailVerified: Timestamp in milliseconds when email was verified (None if unverified)
        image: URL or path to user's profile image (deprecated, use avatar_url instead)
        password: Hashed password (bcrypt) for authentication
        roles: List of UserRole values assigned to this user (default: [STAFF])
        full_name: User's full display name
        avatar_url: URL to user's avatar image
        created_at: ISO timestamp when the user account was created
    """
    __tablename__ = "users"
    
    # Primary key - auto-generated UUID for global uniqueness
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Authentication fields
    email: str = Field(unique=True, index=True, nullable=False)
    password: Optional[str] = None  # Hashed password (bcrypt)
    
    # Email verification - timestamp in milliseconds (None = not verified)
    # Note: Field name uses camelCase for compatibility with existing schema
    emailVerified: Optional[int] = None
    
    # Profile information
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    image: Optional[str] = None  # Deprecated field, kept for backward compatibility
    
    # Authorization - stored as JSON array in database
    # Default role is STAFF for new users
    roles: List[UserRole] = Field(default=[UserRole.STAFF], sa_column=Column(JSON))
    
    # Audit timestamp
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Relationship to notes shared with this user
    shared_notes: List["Note"] = Relationship(back_populates="shared_with", link_model=NoteShare)

    @property
    def is_privileged(self) -> bool:
        """Helper to check if user has admin-level roles."""
        return UserRole.ADMIN in self.roles or UserRole.SUPER_ADMIN in self.roles
    
    # Note: The emailVerified field uses camelCase naming convention which differs
    # from Python's snake_case convention, but is maintained for compatibility with
    # the existing database schema
