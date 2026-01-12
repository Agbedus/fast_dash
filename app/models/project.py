"""
Project Model Module

This module defines the Project model for managing project entities with comprehensive
tracking of status, budget, timeline, and relationships to clients and users.
"""
from typing import Optional
from sqlmodel import SQLModel, Field

from datetime import datetime


class Project(SQLModel, table=True):
    """
    Project model representing a work project with budget, timeline, and tracking.
    
    Projects have ownership and permission controls:
    - Admins and super_admins can see and modify all projects
    - Regular users can only see and modify projects they own (owner_id matches their user ID)
    
    Attributes:
        id: Auto-incrementing primary key
        name: Project name/title (required)
        key: Unique project identifier/code (e.g., "PROJ-001")
        description: Detailed project description
        status: Current project status - one of: "planning", "in_progress", "completed", "on_hold"
        priority: Project priority level - one of: "low", "medium", "high"
        tags: JSON-encoded array of string tags for categorization
        owner_id: Foreign key to the User who owns this project
        client_id: Foreign key to the Client this project is for
        start_date: Project start date in ISO format (YYYY-MM-DD)
        end_date: Project end date in ISO format (YYYY-MM-DD)
        budget: Total project budget in the smallest currency unit (e.g., cents)
        spent: Amount already spent from the budget
        currency: Currency code (default: "USD")
        billing_type: Billing model - typically "billable" or "non_billable"
        is_archived: Whether the project is archived (0 = active, 1 = archived)
        created_at: ISO timestamp when the project was created
        updated_at: ISO timestamp when the project was last modified
    """
    __tablename__ = "projects"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Basic project information
    name: str = Field(nullable=False)
    key: Optional[str] = Field(default=None, unique=True)  # Unique project code/identifier
    description: Optional[str] = None
    
    # Status tracking - valid values: "planning", "in_progress", "completed", "on_hold"
    status: str = Field(default="planning")
    
    # Priority level - valid values: "low", "medium", "high"
    priority: str = Field(default="medium")
    
    # Tags stored as JSON string array for flexible categorization
    tags: Optional[str] = None
    
    # Relationships
    owner_id: Optional[str] = Field(default=None, foreign_key="users.id")
    client_id: Optional[str] = Field(default=None, foreign_key="clients.id")
    # Note: manager_id was removed from the database schema
    # manager_id: Optional[str] = Field(default=None, foreign_key="users.id")
    
    # Timeline - dates stored as ISO format strings (YYYY-MM-DD)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # Budget tracking - amounts in smallest currency unit (e.g., cents for USD)
    budget: Optional[int] = None
    spent: int = 0
    currency: str = "USD"
    
    # Billing configuration
    billing_type: str = "non_billable"  # "billable" or "non_billable"
    
    # Archive flag - use integer for MySQL compatibility (0 = active, 1 = archived)
    is_archived: int = 0
    
    # Audit timestamps - automatically managed
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
