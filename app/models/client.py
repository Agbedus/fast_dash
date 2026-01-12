"""
Client Model Module

This module defines the Client model representing client/company entities in the system.
Clients are shared resources accessible to all authenticated users, but only admins
can modify or delete them.
"""
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

from datetime import datetime


class Client(SQLModel, table=True):
    """
    Client model representing a client/company entity.
    
    Clients are organizations or companies that projects can be associated with.
    This is a shared resource - all users can view clients, but only administrators
    can create, update, or delete them.
    
    Attributes:
        id: Unique identifier (UUID) automatically generated for each client
        company_name: Official company/organization name (required)
        contact_person_name: Primary contact person at the client organization
        contact_email: Email address for the primary contact
        website_url: Client's website URL
        created_at: ISO timestamp of when the client record was created
    """
    __tablename__ = "clients"
    
    # Primary key - auto-generated UUID for global uniqueness
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Required company information
    company_name: str = Field(nullable=False)
    
    # Optional contact details
    contact_person_name: Optional[str] = None
    contact_email: Optional[str] = None
    website_url: Optional[str] = None
    
    # Audit timestamp - automatically set to current UTC time on creation
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Note: user_id field was removed from the database schema as clients are
    # treated as shared resources rather than user-owned entities
    # user_id: Optional[str] = Field(default=None, foreign_key="users.id")
