"""
Project Endpoints Module

This module provides CRUD endpoints for managing projects. Projects have ownership
controls - users can only see and modify their own projects unless they are administrators.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.api import deps

router = APIRouter()


@router.get("", response_model=List[Project])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a paginated list of projects.
    
    Admins see all projects, regular users see only projects they own.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        List[Project]: List of project objects
    """
    # Admins can see all projects
    if "super_admin" in current_user.roles or "admin" in current_user.roles:
        statement = select(Project).offset(skip).limit(limit)
    else:
        # Regular users only see projects they own
        statement = select(Project).where(
            Project.owner_id == current_user.id
        ).offset(skip).limit(limit)
    
    projects = db.exec(statement).all()
    return projects


@router.get("/{project_id}", response_model=Project)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific project by ID.
    
    Users can only view projects they own unless they are administrators.
    
    Args:
        project_id: ID of the project to retrieve
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Project: The requested project object
    
    Raises:
        HTTPException 404: If the project doesn't exist
        HTTPException 403: If the user doesn't own the project and is not an admin
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership permissions
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return project


@router.post("", response_model=Project)
def create_project(
    project: Project,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new project.
    
    If owner_id is not specified, it defaults to the current user.
    
    Args:
        project: Project data to create
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Project: The newly created project object
    """
    # Default owner to current user if not provided
    if not project.owner_id:
        project.owner_id = current_user.id
    
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=Project)
def update_project(
    project_id: int,
    project_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing project.
    
    Users can only update projects they own unless they are administrators.
    
    Args:
        project_id: ID of the project to update
        project_update: Dictionary of fields to update
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Project: The updated project object
    
    Raises:
        HTTPException 404: If the project doesn't exist
        HTTPException 403: If the user doesn't own the project and is not an admin
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership permissions
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    # Apply updates to the project
    for key, value in project_update.items():
        setattr(project, key, value)
    
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a project.
    
    Users can only delete projects they own unless they are administrators.
    
    Args:
        project_id: ID of the project to delete
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException 404: If the project doesn't exist
        HTTPException 403: If the user doesn't own the project and is not an admin
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership permissions  
    if "super_admin" not in current_user.roles and "admin" not in current_user.roles:
        if project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(project)
    db.commit()
    return {"status": "success", "detail": "Project deleted"}
