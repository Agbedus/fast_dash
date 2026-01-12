"""
Task Model Module

This module defines the Task model and TaskAssignee junction table for many-to-many
task assignment relationships. Tasks can have multiple assignees, and users can be
assigned to multiple tasks.
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


class TaskAssignee(SQLModel, table=True):
    """
    Junction table for many-to-many relationship between Tasks and Users.
    
    This table enables a task to be assigned to multiple users, and a user to have
    multiple tasks assigned to them. The table uses a composite primary key of both
    task_id and user_id.
    
    Attributes:
        task_id: Foreign key to the task being assigned
        user_id: Foreign key to the user being assigned the task
    """
    __tablename__ = "task_assignees"
    
    task_id: int = Field(foreign_key="tasks.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)


class TaskBase(SQLModel):
    """
    Base Task model containing common fields.
    """
    # Basic task information
    name: str = Field(nullable=False)
    description: Optional[str] = None
    
    # Due date stored as ISO format string
    due_date: Optional[str] = None
    
    # Priority and status - values can be customized based on workflow
    priority: str = Field(default="medium")  # e.g., "low", "medium", "high"
    status: str = Field(default="task")      # e.g., "task", "in_progress", "completed"
    
    # Project association
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")
    
    # Audit timestamps
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Task(TaskBase, table=True):
    """
    Task table model.
    """
    __tablename__ = "tasks"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationship to access assignees through the junction table
    task_assignees: List["TaskAssignee"] = Relationship()


class TaskRead(TaskBase):
    """Schema for reading basic task data."""
    id: int


class TaskReadWithAssignees(TaskRead):
    """Schema for reading task data with its assignees."""
    task_assignees: List[TaskAssignee] = []
