"""
Note Endpoints Module

This module provides CRUD endpoints for managing notes with sharing functionality.
Notes have ownership and can be shared with other users through the NoteShare junction table.
"""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, text
from sqlalchemy.orm import selectinload
from app.db.session import get_db, engine
from app.models.note_share import NoteShare
from app.models.note import Note, NoteReadWithShared
from app.models.user import User
from app.api import deps

router = APIRouter()


@router.get("", response_model=List[NoteReadWithShared])
def list_notes(
    skip: int = 0,
    limit: int = 100,
    task_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a paginated list of notes.
    
    Admins see all notes, regular users see only notes they own.
    Optionally filter by task_id.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        task_id: Optional task ID to filter notes
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        List[Note]: List of note objects
    """
    # Privileged users (Admins/Super Admins) can see all notes
    if current_user.is_privileged:
        statement = select(Note)
    else:
        # Regular users only see notes they own
        # TODO: Also include notes shared with the user via NoteShare table
        statement = select(Note).where(Note.user_id == current_user.id)
    
    # Eager load shared_with relationship
    statement = statement.options(selectinload(Note.shared_with))
    
    # Filter by task if specified
    if task_id:
        statement = statement.where(Note.task_id == task_id)
    
    statement = statement.offset(skip).limit(limit)
    notes = db.exec(statement).all()
    return notes


@router.get("/{note_id}", response_model=NoteReadWithShared)
def read_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific note by ID.
    
    Users can only view notes they own unless they are administrators.
    Future enhancement: Allow viewing notes shared via NoteShare.
    
    Args:
        note_id: ID of the note to retrieve
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Note: The requested note object
    
    Raises:
        HTTPException 404: If the note doesn't exist
        HTTPException 403: If the user doesn't own the note and is not an admin
    """
    statement = select(Note).where(Note.id == note_id).options(selectinload(Note.shared_with))
    note = db.exec(statement).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Check ownership permissions
    if not current_user.is_privileged:
        if note.user_id != current_user.id:
            # TODO: Also check if note is shared with current_user via NoteShare
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return note


@router.post("", response_model=NoteReadWithShared)
def create_note(
    note_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new note with optional shared users.
    
    The note_data can include a "shared_with" field containing a list of user IDs
    to share the note with. These are stored in the note_shares junction table.
    
    Args:
        note_data: Dictionary of note fields, may include "shared_with" array
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Note: The newly created note object
    """
    # Extract shared_with list from note data (if provided)
    shared_user_ids = note_data.pop("shared_with", [])
    
    # Default owner to current user if not specified
    if "user_id" not in note_data:
        note_data["user_id"] = current_user.id
    
    # Serialize tags list to JSON string if provided
    if "tags" in note_data and isinstance(note_data["tags"], list):
        note_data["tags"] = json.dumps(note_data["tags"])
    
    # Create the note
    note = Note(**note_data)
    db.add(note)
    db.commit()
    db.refresh(note)
    
    # Create note shares in the junction table
    # Using raw SQL because junction table operations are more efficient this way
    if shared_user_ids and isinstance(shared_user_ids, list):
        with engine.connect() as connection:
            for user_id in shared_user_ids:
                # Insert into note_shares junction table
                share_query = text("INSERT INTO `note_shares` (`note_id`, `user_id`) VALUES (:note_id, :user_id)")
                connection.execute(share_query, {"note_id": note.id, "user_id": user_id})
            connection.commit()
        # Refresh to load the newly added shares
        db.exec(select(Note).where(Note.id == note.id).options(selectinload(Note.shared_with))).first()
        db.refresh(note)
    
    return note


@router.patch("/{note_id}", response_model=NoteReadWithShared)
def update_note(
    note_id: int,
    note_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing note.
    
    Users can only update notes they own unless they are administrators.
    If the note_update includes a "shared_with" field, the note's shares will be
    replaced with the new list.
    
    Args:
        note_id: ID of the note to update
        note_update: Dictionary of fields to update, may include "shared_with" array
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Note: The updated note object
    
    Raises:
        HTTPException 404: If the note doesn't exist
        HTTPException 403: If the user doesn't own the note and is not an admin
    """
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Check ownership permissions
    if not current_user.is_privileged:
        if note.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Extract shared_with if provided (None means don't update, [] means clear all shares)
    shared_user_ids = note_update.pop("shared_with", None)
    
    # Serialize tags list to JSON string if provided
    if "tags" in note_update and isinstance(note_update["tags"], list):
        note_update["tags"] = json.dumps(note_update["tags"])
    
    # Update note fields
    for key, value in note_update.items():
        setattr(note, key, value)
    
    db.add(note)
    db.commit()
    
    # Update shared users if explicitly provided
    if shared_user_ids is not None:
        with engine.connect() as connection:
            # Remove all existing shares for this note
            connection.execute(text("DELETE FROM `note_shares` WHERE `note_id` = :note_id"), {"note_id": note_id})
            
            # Add new shares
            if isinstance(shared_user_ids, list):
                for user_id in shared_user_ids:
                    share_query = text("INSERT INTO `note_shares` (`note_id`, `user_id`) VALUES (:note_id, :user_id)")
                    connection.execute(share_query, {"note_id": note_id, "user_id": user_id})
            
            connection.commit()
        # Refresh to load the newly added shares
        db.exec(select(Note).where(Note.id == note_id).options(selectinload(Note.shared_with))).first()

    db.refresh(note)
    return note


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a note and all its shares.
    
    Users can only delete notes they own unless they are administrators.
    Automatically removes all note share relationships before deleting the note.
    
    Args:
        note_id: ID of the note to delete
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If the note doesn't exist
        HTTPException 403: If the user doesn't own the note and is not an admin
    """
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Check ownership permissions
    if not current_user.is_privileged:
        if note.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete note shares first (foreign key constraint)
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM `note_shares` WHERE `note_id` = :note_id"), {"note_id": note_id})
        connection.commit()
    
    # Now safe to delete the note
    db.delete(note)
    db.commit()
    return {"status": "success", "detail": "Note deleted"}
