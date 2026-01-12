"""
Event and Decision Models Module

This module defines two models:
1. Event: Calendar events for scheduling and time management
2. Decision: Decision tracking items with ownership
"""
from enum import Enum
from typing import Optional, Any, Union, List
from sqlmodel import SQLModel, Field, AutoString
from datetime import datetime
from pydantic import field_validator, ValidationInfo
import json


class EventStatus(str, Enum):
    tentative = "tentative"
    confirmed = "confirmed"
    cancelled = "cancelled"


class EventPrivacy(str, Enum):
    public = "public"
    private = "private"
    confidential = "confidential"


class EventRecurrence(str, Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class EventReminder(SQLModel):
    """Structured reminder configuration."""
    days: int = 0
    hours: int = 0
    minutes: int = 0


class EventBase(SQLModel):
    """
    Base properties for an Event.
    """
    # Basic event information
    title: str = Field(nullable=False)
    description: Optional[str] = None
    
    # Time range - both required, stored as ISO 8601 strings
    start: str = Field(nullable=False)
    end: str = Field(nullable=False)
    
    # All-day flag - use integer for MySQL compatibility
    all_day: int = 0  # 0 = time-specific event, 1 = all-day event
    
    # Location and participants
    location: Optional[str] = None
    organizer: Optional[str] = None
    attendees: Optional[str] = None  # JSON array: ["email1@example.com", "email2@example.com"]
    
    # Event status
    status: Optional[EventStatus] = Field(default=EventStatus.tentative, sa_type=AutoString)
    
    # Privacy level
    privacy: Optional[EventPrivacy] = Field(default=EventPrivacy.public, sa_type=AutoString)
    
    # Recurrence and reminders
    recurrence: Optional[EventRecurrence] = Field(default=EventRecurrence.none, sa_type=AutoString)
    reminders: Optional[str] = None   # JSON array of EventReminder objects
    
    # Customization and metadata
    color: Optional[str] = None  # Event color for calendar display
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Ownership
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")


class Event(EventBase, table=True):
    """
    Event table model.
    """
    __tablename__ = "events"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)


class EventRead(EventBase):
    """Schema for reading an event."""
    id: int
    attendees: Optional[List[str]] = None
    reminders: Optional[List[EventReminder]] = None

    @field_validator("attendees", mode="before")
    @classmethod
    def parse_attendees(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v] if v else []
        return v

    @field_validator("reminders", mode="before")
    @classmethod
    def parse_reminders(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    @field_validator("status", "privacy", "recurrence", mode="before")
    @classmethod
    def map_legacy_enums(cls, v, info: ValidationInfo):
        field_name = info.field_name
        if v is None:
            if field_name == "status": return EventStatus.tentative
            if field_name == "privacy": return EventPrivacy.public
            if field_name == "recurrence": return EventRecurrence.none
            return v
        
        if isinstance(v, str):
            v_lower = v.lower()
            # Handle legacy 'recurring' value specifically
            if field_name == "recurrence" and v_lower == "recurring":
                return EventRecurrence.weekly # Map legacy 'recurring' to weekly as a safe guess
            
            # Check if it's a valid enum value
            if field_name == "status":
                try: return EventStatus(v_lower)
                except ValueError: return EventStatus.tentative
            if field_name == "privacy":
                try: return EventPrivacy(v_lower)
                except ValueError: return EventPrivacy.public
            if field_name == "recurrence":
                try: return EventRecurrence(v_lower)
                except ValueError: return EventRecurrence.none
        return v


class EventCreate(EventBase):
    """Schema for creating an event."""
    attendees: Optional[List[str]] = None
    reminders: Optional[List[EventReminder]] = None
    all_day: Optional[Union[int, bool]] = 0

    @field_validator("status", "privacy", "recurrence", mode="before")
    @classmethod
    def to_lowercase(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class EventUpdate(SQLModel):
    """Schema for updating an event."""
    title: Optional[str] = None
    description: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    all_day: Optional[Union[int, bool]] = None
    location: Optional[str] = None
    organizer: Optional[str] = None
    attendees: Optional[List[str]] = None
    status: Optional[EventStatus] = None
    privacy: Optional[EventPrivacy] = None
    recurrence: Optional[EventRecurrence] = None
    reminders: Optional[List[EventReminder]] = None
    color: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("status", "privacy", "recurrence", mode="before")
    @classmethod
    def to_lowercase(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class Decision(SQLModel, table=True):
    """
    Decision model for tracking decisions that need to be made.
    
    Attributes:
        id: Auto-incrementing primary key
        name: Decision title/description (required)
        due_date: Deadline for making the decision in ISO format
        user_id: Foreign key to the user who owns/created this decision
    """
    __tablename__ = "decisions"
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Decision information
    name: str = Field(nullable=False)
    due_date: Optional[str] = None  # ISO format date string
    
    # Ownership
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
