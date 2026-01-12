"""
Application Configuration Module

This module defines all configuration settings for the FastAPI application.
Settings are loaded from environment variables (via .env file) using Pydantic.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    
    All settings can be overridden via environment variables.
    The .env file is automatically loaded if present.
    """
    # === Application Metadata ===
    PROJECT_NAME: str = "Fast Dash API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"  # API version prefix for all routes

    # === Database Configuration ===
    # Option 1: Direct connection via DATABASE_URL
    DATABASE_URL: Optional[str] = None  # e.g., "mysql+pymysql://user:pass@host/dbname"
    
    # Option 2: Individual database connection parameters
    DB_HOST: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # === SSH Tunnel Configuration ===
    # Used for connecting to remote MySQL databases (e.g., PythonAnywhere)
    USE_SSH: bool = False  # Set to True to enable SSH tunneling
    SSH_HOST: Optional[str] = "ssh.pythonanywhere.com"
    SSH_USER: Optional[str] = None
    SSH_PASSWORD: Optional[str] = None

    # === Security Configuration ===
    # IMPORTANT: Change SECRET_KEY in production to a strong random value
    SECRET_KEY: str = "your-super-secret-key-change-me"  # Used for JWT token signing
    ALGORITHM: str = "HS256"  # JWT encoding algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # Token validity: 7 days

    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=".env",        # Load environment variables from .env file
        case_sensitive=True,    # Environment variable names must match case
        extra="ignore"          # Ignore extra environment variables not defined here
    )

# Create a single global settings instance
# This is imported throughout the application for configuration access
settings = Settings()
