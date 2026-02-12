"""
Event Endpoints Module

This module provides CRUD endpoints for managing calendar events.
Events are shared resources that all authenticated users can view,
but only administrators can modify.
"""
import json
from datetime import datetime
from typing import List, Union, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.event import Event, EventRead, EventCreate, EventUpdate
from app.models.user import User, UserRole
from app.api import deps
from app.services.notifications import NotificationService
import asyncio

router = APIRouter()


@router.get("", response_model=List[EventRead])
def list_events(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a paginated list of events.
    
    All authenticated users can view all events. Events are treated as shared
    calendar resources without ownership restrictions.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        List[Event]: List of event objects
    """
    # SUPER_ADMIN and MANAGER can see all events
    if current_user.is_privileged or UserRole.MANAGER in current_user.roles:
        statement = select(Event).offset(skip).limit(limit)
    else:
        # Others see only their own events
        statement = select(Event).where(Event.user_id == current_user.id).offset(skip).limit(limit)
    
    events = db.exec(statement).all()
    return events


@router.get("/{event_id}", response_model=EventRead)
def read_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific event by ID.
    
    All authenticated users can view any event.
    
    Args:
        event_id: ID of the event to retrieve
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Event: The requested event object
    
    Raises:
        HTTPException 404: If the event doesn't exist
    """
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # SUPER_ADMIN and MANAGER can view any event
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        if event.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return event


@router.post("", response_model=EventRead)
async def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new event.
    
    Available to all authenticated users. Since there's no user_id field in the
    Event model, created events are visible to all users.
    
    Args:
        event: Event data to create (must include title, start, and end)
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Event: The newly created event object
    """
    # Create the event data dict
    event_data = event_in.dict()
    
    # Serialize list fields to JSON strings for database storage
    for key in ["attendees", "reminders"]:
        if key in event_data and isinstance(event_data[key], list):
            event_data[key] = json.dumps(event_data[key])
            
    # Handle all_day conversion (bool to int)
    if "all_day" in event_data:
        event_data["all_day"] = 1 if event_data["all_day"] else 0
            
    # Create the event instance
    db_event = Event(**event_data)
    
    # Set current user as creator if not specified
    if not db_event.user_id:
        db_event.user_id = current_user.id
        
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="New Event Created", 
        message=f"Event '{db_event.title}' was created by {current_user.full_name or current_user.email}",
        sender_id=current_user.id,
        resource_type="event",
        resource_id=db_event.id
    )
    
    return db_event


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing event.
    
    Only administrators can update events.
    
    Args:
        event_id: ID of the event to update
        event_update: Dictionary of fields to update
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Event: The updated event object
    
    Raises:
        HTTPException 404: If the event doesn't exist
        HTTPException 403: If the user is not an administrator
    """
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Only SUPER_ADMIN and MANAGER can update events
    # Staff cannot edit/update
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to update events")
    
    # Update timestamp
    event.updated_at = datetime.utcnow().isoformat()
    
    # Apply updates to the event
    update_data = event_in.dict(exclude_unset=True)
    
    # Serialize list fields to JSON strings for database storage
    for key in ["attendees", "reminders"]:
        if key in update_data and isinstance(update_data[key], list):
            update_data[key] = json.dumps(update_data[key])
            
    # Handle all_day conversion (bool to int)
    if "all_day" in update_data:
        update_data["all_day"] = 1 if update_data["all_day"] else 0
            
    for key, value in update_data.items():
        setattr(event, key, value)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Event Updated", 
        message=f"Event '{event.title}' was updated by {current_user.full_name or current_user.email}",
        sender_id=current_user.id,
        resource_type="event",
        resource_id=event.id
    )
    
    return event


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Delete an event.
    
    Only administrators can delete events.
    
    Args:
        event_id: ID of the event to delete
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If the event doesn't exist
        HTTPException 403: If the user is not an administrator
    """
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Only SUPER_ADMIN can delete (enforced by get_current_active_superuser)
    
    db.delete(event)
    db.commit()
    return {"status": "success", "detail": "Event deleted"}
