"""
Task Model Module

This module defines the Task model and TaskAssignee junction table for many-to-many
task assignment relationships. Tasks can have multiple assignees, and users can be
assigned to multiple tasks.
"""
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.note import Note
    from app.models.user import User


class TaskStatus(str, Enum):
    """
    Enum for task status workflow.
    """
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    QA = "QA"
    REVIEW = "REVIEW"
    DONE = "DONE"


class TaskAssignee(SQLModel, table=True):
    """
    Junction table for many-to-many relationship between Tasks and Users.
    """
    __tablename__ = "task_assignees"
    
    task_id: int = Field(foreign_key="tasks.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)


class TaskTimeLog(SQLModel, table=True):
    """
    Model for tracking time spent on tasks via sessions.
    """
    __tablename__ = "task_time_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id")
    user_id: str = Field(foreign_key="users.id")
    
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    
    is_break: bool = Field(default=False)
    
    # Relationship to task
    task: "Task" = Relationship(back_populates="time_logs")


class TaskBase(SQLModel):
    """
    Base Task model containing common fields.
    """
    # Basic task information
    name: str = Field(nullable=False)
    description: Optional[str] = None
    
    # Due date stored as ISO format string
    due_date: Optional[str] = None
    
    # Priority and status
    priority: str = Field(default="medium")  # e.g., "low", "medium", "high"
    status: TaskStatus = Field(default=TaskStatus.TODO)
    
    # Validation flags
    qa_required: bool = Field(default=False)
    review_required: bool = Field(default=False)
    
    # Dependency management
    depends_on_id: Optional[int] = Field(default=None, foreign_key="tasks.id")
    
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

    # Ownership
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    
    # Relationships
    project: Optional["Project"] = Relationship(back_populates="tasks")
    creator: Optional["User"] = Relationship(back_populates="tasks")
    
    # Relationship to access assignees through the junction table
    task_assignees: List["TaskAssignee"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    
    # Relationship to notes
    notes: List["Note"] = Relationship(back_populates="task")
    
    # Relationship to time logs
    time_logs: List["TaskTimeLog"] = Relationship(back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    
    # Self-referencing relationship for dependencies
    # dependency: Optional["Task"] = Relationship(
    #     sa_relationship_kwargs={"remote_side": "Task.id"}
    # )

    @property
    def total_hours(self) -> float:
        """Calculates total hours spent on task excluding breaks."""
        if not self.time_logs:
            return 0.0
        total_seconds = 0
        for log in self.time_logs:
            if not log.is_break and log.start_time and log.end_time:
                try:
                    start = datetime.fromisoformat(log.start_time)
                    end = datetime.fromisoformat(log.end_time)
                    total_seconds += (end - start).total_seconds()
                except (ValueError, TypeError):
                    continue
        return round(total_seconds / 3600, 2)


class TaskRead(TaskBase):
    """Schema for reading basic task data."""
    id: int
    user_id: Optional[str] = None


class TaskReadWithAssignees(TaskRead):
    """Schema for reading task data with its assignees."""
    task_assignees: List[TaskAssignee] = []


class TaskReadWithTimeLogs(TaskReadWithAssignees):
    """Schema for reading task data with its time logs."""
    time_logs: List["TaskTimeLog"] = []
    total_hours: float = 0.0
