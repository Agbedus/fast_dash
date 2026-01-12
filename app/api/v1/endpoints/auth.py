"""
Authentication Endpoints Module

This module provides authentication endpoints for user registration, login, and logout.
The system supports both JWT bearer token authentication and HTTP-only cookie-based
authentication for browser clients.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.schemas.auth import Token, UserRegister

router = APIRouter()

@router.post("/register", response_model=User)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Creates a new user with the provided email and password. The password is
    automatically hashed before storage. New users are assigned the USER role by default.
    
    Returns:
        User: The newly created user object (password hash is excluded from response)
    
    Raises:
        HTTPException 400: If a user with this email already exists
    """
    # Check if email is already registered
    user = db.exec(select(User).where(User.email == user_in.email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists."
        )
    
    # Create new user with hashed password
    db_user = User(
        email=user_in.email,
        password=get_password_hash(user_in.password),  # Hash password using bcrypt
        full_name=user_in.full_name,
        roles=[UserRole.USER]  # Default role for new registrations
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(response: Response, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate a user and issue an access token.
    
    Validates the user's credentials and returns a JWT access token. The token is also
    set as an HTTP-only cookie for browser clients. This dual approach supports both
    API clients (using the bearer token) and browser clients (using the cookie).
    
    Note: OAuth2PasswordRequestForm uses 'username' field, but we treat it as email.
    
    Returns:
        Token: Object containing the access_token and token_type
    
    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Look up user by email (form_data.username contains the email)
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate JWT access token with configurable expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    
    # Set HTTP-only cookie for browser-based authentication
    # httponly=True prevents JavaScript access to the cookie (XSS protection)
    # samesite="lax" provides CSRF protection while allowing normal navigation
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,  # Cannot be accessed via JavaScript
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
        samesite="lax"  # CSRF protection
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/logout")
def logout(response: Response):
    """
    Log out the current user by clearing their authentication cookie.
    
    Deletes the access_token cookie and redirects to the login page. This endpoint
    is primarily for browser-based clients. API clients can simply discard their token.
    
    Returns:
        RedirectResponse: Redirects to the /login page
    """
    # Clear the authentication cookie
    response.delete_cookie("access_token")
    
    # Redirect to login page (useful for web interface)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")
