"""
User Management Endpoints Module

This module provides CRUD endpoints for user management. All endpoints require
administrative privileges except for the /me endpoints which allow users to
manage their own profile.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api import deps
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.core.security import get_password_hash

router = APIRouter()

@router.get("", response_model=List[UserRead])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve a paginated list of all users.
    
    Only administrators can access this endpoint.
    
    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        current_user: Must be an admin (enforced by dependency)
    
    Returns:
        List[UserRead]: List of user objects (passwords excluded)
    """
    users = db.exec(select(User).offset(skip).limit(limit)).all()
    return users

@router.post("", response_model=UserRead)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create a new user.
    
    Only administrators can create users. Passwords are automatically hashed.
    
    Args:
        db: Database session
        user_in: User data to create (includes email, password, roles, etc.)
        current_user: Must be an admin (enforced by dependency)
    
    Returns:
        UserRead: The newly created user object (password excluded)
    
    Raises:
        HTTPException 400: If a user with this email already exists
    """
    # Check for existing user with same email
    user = db.exec(select(User).where(User.email == user_in.email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    # Create new user with hashed password and specified roles
    db_user = User(
        email=user_in.email,
        password=get_password_hash(user_in.password),  # Hash password using bcrypt
        full_name=user_in.full_name,
        roles=user_in.roles or [UserRole.USER],  # Default to USER role if not specified
        image=user_in.image,
        avatar_url=user_in.avatar_url
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserRead)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the current authenticated user's profile.
    
    This endpoint allows any authenticated user to retrieve their own profile data.
    
    Args:
        current_user: The authenticated user
    
    Returns:
        UserRead: The current user's profile (password excluded)
    """
    return current_user

@router.put("/me", response_model=UserRead)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update the current user's own profile.
    
    Allows users to update their own profile information including password,
    name, email, and avatar.
    
    Args:
        db: Database session
        user_in: Updated user data (only provided fields are updated)
        current_user: The authenticated user
    
    Returns:
        UserRead: The updated user profile (password excluded)
    """
    # Update password if provided (will be hashed)
    if user_in.password is not None:
        current_user.password = get_password_hash(user_in.password)
    
    # Update other fields if provided
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.email is not None:
        current_user.email = user_in.email
    if user_in.avatar_url is not None:
        current_user.avatar_url = user_in.avatar_url
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/{user_id}", response_model=UserRead)
def read_user_by_id(
    user_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific user by ID.
    
    Users can retrieve their own profile. Only administrators can retrieve
    other users' profiles.
    
    Args:
        user_id: UUID of the user to retrieve
        current_user: The authenticated user
        db: Database session
    
    Returns:
        UserRead: The requested user's profile (password excluded)
    
    Raises:
        HTTPException 400: If user doesn't have permission to view this profile
    """
    user = db.get(User, user_id)
    
    # Users can view their own profile
    if user == current_user:
        return user
    
    # Only admins can view other users' profiles
    if not current_user.is_privileged:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return user

@router.put("/{user_id}", response_model=UserRead)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update any user's profile.
    
    Only administrators can update other users' profiles. This endpoint allows
    updating any field including roles and password.
    
    Args:
        db: Database session
        user_id: UUID of the user to update
        user_in: Updated user data (only provided fields are updated)
        current_user: Must be an admin (enforced by dependency)
    
    Returns:
        UserRead: The updated user profile (password excluded)
    
    Raises:
        HTTPException 404: If the user doesn't exist
    """
    db_user = db.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    
    # Get update data, excluding unset fields
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Hash password if it's being updated
    if "password" in update_data:
        update_data["password"] = get_password_hash(update_data["password"])
    
    # Apply all updates to the user
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", response_model=UserRead)
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete a user.
    
    Only administrators can delete users. Users cannot delete themselves.
    
    Args:
        db: Database session
        user_id: UUID of the user to delete
        current_user: Must be an admin (enforced by dependency)
    
    Returns:
        UserRead: The deleted user's profile (for confirmation)
    
    Raises:
        HTTPException 404: If the user doesn't exist
        HTTPException 400: If trying to delete yourself
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user == current_user:
        raise HTTPException(
            status_code=400, detail="Users cannot delete themselves"
        )
    
    db.delete(user)
    db.commit()
    return user
