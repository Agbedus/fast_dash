"""
API Dependencies Module

This module provides FastAPI dependency functions for authentication and authorization.
It implements a dual authentication strategy supporting both bearer tokens (for API clients)
and HTTP-only cookies (for browser clients).
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenData
from fastapi import Request

# Configure OAuth2 scheme to use the login endpoint
# auto_error=False allows us to check cookies as a fallback
tokenUrl = f"{settings.API_V1_STR}/auth/login" if hasattr(settings, "API_V1_STR") else "/api/v1/auth/login"

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=tokenUrl,
    auto_error=False  # Don't raise error immediately if Authorization header is missing
)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(reusable_oauth2)
) -> User:
    """
    Dependency that retrieves and validates the current authenticated user.
    
    Supports dual authentication methods:
    1. Bearer token in Authorization header (for API clients)
    2. HTTP-only cookie (for browser clients)
    
    The function first checks for a bearer token in the Authorization header.
    If not found, it falls back to checking the access_token cookie.
    
    Args:
        request: FastAPI request object (used to access cookies)
        db: Database session
        token: Optional bearer token from Authorization header
    
    Returns:
        User: The authenticated user object
    
    Raises:
        HTTPException 401: If no valid authentication token is provided
        HTTPException 403: If the token is invalid or expired
        HTTPException 404: If the user referenced in the token doesn't exist
    """
    # Try Authorization header first, then fall back to cookie
    if not token:
        token = request.cookies.get("access_token")
        # Cookie format is "Bearer <token>", so we need to extract the token
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
    
    # Require authentication
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate the JWT token
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(email=payload.get("sub"))  # Extract email from token
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # Look up the user in the database
    user = db.exec(select(User).where(User.email == token_data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires the current user to be an administrator.
    
    Validates that the authenticated user has admin or super_admin role.
    Use this dependency on endpoints that require administrative privileges.
    
    Args:
        current_user: The currently authenticated user
    
    Returns:
        User: The authenticated admin user
    
    Raises:
        HTTPException 400: If the user doesn't have admin privileges
    """
    from app.models.user import UserRole
    
    # Check if user has admin or super_admin role
    if UserRole.ADMIN not in current_user.roles and UserRole.SUPER_ADMIN not in current_user.roles:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires any authenticated user.
    
    This is a convenience wrapper around get_current_user that can be extended
    to add additional checks like email verification or account status.
    Currently it just ensures the user is authenticated.
    
    Args:
        current_user: The currently authenticated user
    
    Returns:
        User: The authenticated user
    
    Note: Future enhancements could include:
        - Checking if email is verified (emailVerified field)
        - Checking if account is active/enabled
        - Checking if account is suspended
    """
    # Could add additional checks here (e.g., is_active, email_verified)
    return current_user
