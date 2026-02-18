"""
Task Endpoints Module

This module provides CRUD endpoints for managing tasks with multi-user assignment support.
Tasks use a many-to-many relationship with users through the TaskAssignee junction table.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, text
from app.db.session import get_db, engine
from app.models.task import Task, TaskAssignee, TaskReadWithAssignees, TaskStatus, TaskTimeLog, TaskReadWithTimeLogs
from app.models.user import User, UserRole
from app.api import deps
from app.services.notifications import NotificationService
from datetime import datetime
import asyncio

router = APIRouter()


@router.get("", response_model=List[TaskReadWithTimeLogs])
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

    # SUPER_ADMIN and MANAGER can see all tasks
    if current_user.is_privileged or UserRole.MANAGER in current_user.roles:
        statement = select(Task)
    else:
        # Complex filter:
        # 1. Tasks in projects owned by the user
        # 2. Tasks assigned to the user
        # 3. Tasks created by the user
        owned_project_ids_subquery = select(Project.id).where(Project.owner_id == current_user.id)
        assigned_task_ids_subquery = select(TaskAssignee.task_id).where(TaskAssignee.user_id == current_user.id)
        
        statement = select(Task).where(
            (Task.project_id.in_(owned_project_ids_subquery)) | 
            (Task.id.in_(assigned_task_ids_subquery)) |
            (Task.user_id == current_user.id)
        )
    
    # Filter by project if specified
    if project_id:
        statement = statement.where(Task.project_id == project_id)
    
    statement = statement.offset(skip).limit(limit)
    tasks = db.exec(statement).all()
    return tasks


@router.get("/{task_id}", response_model=TaskReadWithTimeLogs)
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
    
    # SUPER_ADMIN and MANAGER can see all tasks
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
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
        
        if not project_owned and not assigned and task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")
    
    return task


@router.post("", response_model=TaskReadWithTimeLogs)
async def create_task(
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
    task.user_id = current_user.id # Set the creator
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
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="New Task Created", 
        message=f"Task '{task.name}' was created by {current_user.full_name or current_user.email}",
        sender_id=current_user.id,
        resource_type="task",
        resource_id=task.id
    )
    
    # Notify Assignees
    if assignee_ids:
        for user_id in assignee_ids:
            await NotificationService.send_notification(
                db, 
                recipient_id=user_id,
                title="New Task Assigned",
                message=f"You have been assigned to task: '{task.name}'",
                type="info",
                sender_id=current_user.id,
                resource_type="task",
                resource_id=task.id
            )
            
    return task


@router.patch("/{task_id}", response_model=TaskReadWithTimeLogs)
async def update_task(
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
    # Only SUPER_ADMIN and MANAGER can update tasks
    # Staff cannot edit/update tasks
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        raise HTTPException(status_code=403, detail="Not authorized to update tasks")

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
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Task Updated", 
        message=f"Task '{task.name}' was updated by {current_user.full_name or current_user.email}",
        sender_id=current_user.id,
        resource_type="task",
        resource_id=task.id
    )
    
    # Notify New Assignees if updated
    if assignee_ids is not None:
        for user_id in assignee_ids:
            await NotificationService.send_notification(
                db, 
                recipient_id=user_id,
                title="Task Assignment Updated",
                message=f"You are assigned to task: '{task.name}'",
                type="info",
                sender_id=current_user.id,
                resource_type="task",
                resource_id=task.id
            )

    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Delete a task and all its assignments.
    
    Only project owners or admins can delete tasks.
    """
    from app.models.project import Project

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only SUPER_ADMIN can delete (enforced by get_current_active_superuser)

    # Unlink notes and delete task assignees (foreign key constraints)
    # Using db.execute ensures we stay in the same transaction
    db.execute(text("UPDATE notes SET task_id = NULL WHERE task_id = :task_id"), {"task_id": task_id})
    db.execute(text("DELETE FROM task_assignees WHERE task_id = :task_id"), {"task_id": task_id})
    
    # Commit the unlink/cleanup operations first to ensure DB state satisfies constraints
    db.commit()
    
    # Now safe to delete the task
    db.delete(task)
    db.commit()
    return {"status": "success", "detail": "Task deleted"}


@router.post("/{task_id}/timer/start")
async def start_task_timer(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Starts a new time tracking session for a task.
    Automatically pauses any other active sessions for the user.
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 1. Close any other active sessions for this user (across all tasks)
    active_sessions = db.exec(
        select(TaskTimeLog).where(
            TaskTimeLog.user_id == current_user.id,
            TaskTimeLog.end_time == None
        )
    ).all()
    
    for session in active_sessions:
        session.end_time = datetime.utcnow().isoformat()
        db.add(session)
    
    # 2. Create new session for this task
    new_session = TaskTimeLog(
        task_id=task_id,
        user_id=current_user.id,
        start_time=datetime.utcnow().isoformat()
    )
    
    # Automatically move task to IN_PROGRESS if it's in TODO
    if task.status == TaskStatus.TODO:
        task.status = TaskStatus.IN_PROGRESS
        db.add(task)
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session


@router.post("/{task_id}/timer/pause")
async def pause_task_timer(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Pauses (ends) the current active session.
    """
    active_session = db.exec(
        select(TaskTimeLog).where(
            TaskTimeLog.task_id == task_id,
            TaskTimeLog.user_id == current_user.id,
            TaskTimeLog.end_time == None
        )
    ).first()
    
    if not active_session:
        raise HTTPException(status_code=400, detail="No active session found for this task")
    
    active_session.end_time = datetime.utcnow().isoformat()
    # Note: We don't mark as is_break here. Pausing simply ends the work session.
    
    db.add(active_session)
    db.commit()
    db.refresh(active_session)
    
    return active_session


@router.post("/{task_id}/timer/stop")
async def stop_task_timer(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Stops (ends) the current active session.
    """
    active_session = db.exec(
        select(TaskTimeLog).where(
            TaskTimeLog.task_id == task_id,
            TaskTimeLog.user_id == current_user.id,
            TaskTimeLog.end_time == None
        )
    ).first()
    
    if not active_session:
        # Check if there was any recent session
        last_session = db.exec(
            select(TaskTimeLog).where(
                TaskTimeLog.task_id == task_id,
                TaskTimeLog.user_id == current_user.id
            ).order_by(text("start_time DESC"))
        ).first()
        
        if not last_session:
            raise HTTPException(status_code=400, detail="No session found for this task")
        
        return last_session
    
    active_session.end_time = datetime.utcnow().isoformat()
    
    db.add(active_session)
    db.commit()
    db.refresh(active_session)
    
    return active_session
