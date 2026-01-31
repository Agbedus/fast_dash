"""
Task Endpoints Module

This module provides CRUD endpoints for managing tasks with multi-user assignment support.
Tasks use a many-to-many relationship with users through the TaskAssignee junction table.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, text
from app.db.session import get_db, engine
from app.models.task import Task, TaskAssignee, TaskReadWithAssignees
from app.models.user import User
from app.api import deps

router = APIRouter()


@router.get("", response_model=List[TaskReadWithAssignees])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a paginated list of tasks.
    
    Admins see all tasks. Regular users see tasks they are assigned to
    OR tasks in projects they own.
    """
    from app.models.project import Project
    from app.models.task import TaskAssignee

    if current_user.is_privileged:
        statement = select(Task)
    else:
        # Complex filter:
        # 1. Tasks in projects owned by the user
        # 2. Tasks assigned to the user
        owned_project_ids_subquery = select(Project.id).where(Project.owner_id == current_user.id)
        assigned_task_ids_subquery = select(TaskAssignee.task_id).where(TaskAssignee.user_id == current_user.id)
        
        statement = select(Task).where(
            (Task.project_id.in_(owned_project_ids_subquery)) | 
            (Task.id.in_(assigned_task_ids_subquery))
        )
    
    # Filter by project if specified
    if project_id:
        statement = statement.where(Task.project_id == project_id)
    
    statement = statement.offset(skip).limit(limit)
    tasks = db.exec(statement).all()
    return tasks


@router.get("/{task_id}", response_model=TaskReadWithAssignees)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific task by ID.
    
    Admins see all tasks. Regular users see tasks they are assigned to
    OR tasks in projects they own.
    """
    from app.models.project import Project
    from app.models.task import TaskAssignee

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not current_user.is_privileged:
        # Check project ownership
        project_owned = False
        if task.project_id:
            project = db.get(Project, task.project_id)
            if project and project.owner_id == current_user.id:
                project_owned = True
        
        # Check task assignment
        assigned = db.exec(
            select(TaskAssignee).where(
                TaskAssignee.task_id == task_id, 
                TaskAssignee.user_id == current_user.id
            )
        ).first()
        
        if not project_owned and not assigned:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")
    
    return task


@router.post("", response_model=TaskReadWithAssignees)
def create_task(
    task_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new task with optional assignees.
    
    The task_data can include an "assignees" field containing a list of user IDs
    to assign to the task. These are stored in the task_assignees junction table.
    
    Args:
        task_data: Dictionary of task fields, may include "assignees" array
        db: Database session
        current_user: Currently authenticated user
    
    Returns:
        Task: The newly created task object
    """
    # Extract assignees list from task data (if provided)
    assignee_ids = task_data.pop("assignees", [])
    
    # Create the task
    task = Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create task assignments in the junction table
    # Using raw SQL because junction table doesn't have a SQLModel representation for direct inserts
    if assignee_ids and isinstance(assignee_ids, list):
        with engine.connect() as connection:
            for user_id in assignee_ids:
                # Insert into task_assignees junction table
                assign_query = text("INSERT INTO `task_assignees` (`task_id`, `user_id`) VALUES (:task_id, :user_id)")
                connection.execute(assign_query, {"task_id": task.id, "user_id": user_id})
            connection.commit()
    
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskReadWithAssignees)
def update_task(
    task_id: int,
    task_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing task.
    
    Only project owners or admins can update tasks.
    """
    from app.models.project import Project

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if not current_user.is_privileged:
        project_owned = False
        if task.project_id:
            project = db.get(Project, task.project_id)
            if project and project.owner_id == current_user.id:
                project_owned = True
        
        if not project_owned:
            raise HTTPException(status_code=403, detail="Not authorized to update this task")

    # Extract assignees if provided (None means don't update, [] means clear all)
    assignee_ids = task_update.pop("assignees", None)
    
    # Update task fields
    for key, value in task_update.items():
        setattr(task, key, value)
    
    db.add(task)
    db.commit()
    
    # Update assignees if explicitly provided
    if assignee_ids is not None:
        with engine.connect() as connection:
            # Remove all existing assignees for this task
            connection.execute(text("DELETE FROM `task_assignees` WHERE `task_id` = :task_id"), {"task_id": task_id})
            
            # Add new assignees
            if isinstance(assignee_ids, list):
                for user_id in assignee_ids:
                    assign_query = text("INSERT INTO `task_assignees` (`task_id`, `user_id`) VALUES (:task_id, :user_id)")
                    connection.execute(assign_query, {"task_id": task_id, "user_id": user_id})
            
            connection.commit()
    
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a task and all its assignments.
    
    Only project owners or admins can delete tasks.
    """
    from app.models.project import Project

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if not current_user.is_privileged:
        project_owned = False
        if task.project_id:
            project = db.get(Project, task.project_id)
            if project and project.owner_id == current_user.id:
                project_owned = True
        
        if not project_owned:
            raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    # Delete task assignees first (foreign key constraint)
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM `task_assignees` WHERE `task_id` = :task_id"), {"task_id": task_id})
        connection.commit()
    
    # Now safe to delete the task
    db.delete(task)
    db.commit()
    return {"status": "success", "detail": "Task deleted"}
