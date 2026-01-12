"""
Decision Endpoints Module

This module provides CRUD endpoints for managing decision items.
Decisions have ownership - users can only see and modify their own decisions
unless they are administrators.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.event import Decision
from app.models.user import User
from app.api import deps

router = APIRouter()


@router.get("", response_model=List[Decision])
def list_decisions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a paginated list of decisions.
    
    Admins see all decisions, regular users see only decisions they own.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        List[Decision]: List of decision objects
    """
    # Admins can see all decisions
    if "super_admin" in current_user.roles or "admin" in current_user.roles:
        statement = select(Decision).offset(skip).limit(limit)
    else:
        # Regular users only see decisions they own
        statement = select(Decision).where(Decision.user_id == current_user.id).offset(skip).limit(limit)
    
    decisions = db.exec(statement).all()
    return decisions


@router.get("/{decision_id}", response_model=Decision)
def read_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific decision by ID.
    
    Users can only view decisions they own unless they are administrators.
    
    Args:
        decision_id: ID of the decision to retrieve
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Decision: The requested decision object
    
    Raises:
        HTTPException 404: If the decision doesn't exist
        HTTPException 403: If the user doesn't own the decision and is not an admin
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # Check ownership permissions
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if decision.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return decision


@router.post("", response_model=Decision)
def create_decision(
    decision: Decision,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new decision.
    
    If user_id is not specified, it defaults to the current user.
    
    Args:
        decision: Decision data to create
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Decision: The newly created decision object
    """
    # Default owner to current user if not provided
    if not decision.user_id:
        decision.user_id = current_user.id
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.patch("/{decision_id}", response_model=Decision)
def update_decision(
    decision_id: int,
    decision_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing decision.
    
    Users can only update decisions they own unless they are administrators.
    
    Args:
        decision_id: ID of the decision to update
        decision_update: Dictionary of fields to update
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Decision: The updated decision object
    
    Raises:
        HTTPException 404: If the decision doesn't exist
        HTTPException 403: If the user doesn't own the decision and is not an admin
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # Check ownership permissions
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if decision.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Apply updates to the decision
    for key, value in decision_update.items():
        setattr(decision, key, value)
    
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


@router.delete("/{decision_id}")
def delete_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a decision.
    
    Users can only delete decisions they own unless they are administrators.
    
    Args:
        decision_id: ID of the decision to delete
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If the decision doesn't exist
        HTTPException 403: If the user doesn't own the decision and is not an admin
    """
    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # Check ownership permissions
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if decision.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(decision)
    db.commit()
    return {"status": "success", "detail": "Decision deleted"}
