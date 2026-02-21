from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.task import Task, TaskTimeLog, TaskTimeLogCreate, TaskTimeLogUpdate, TaskTimeLogRead
from app.models.user import User, UserRole
from app.api import deps
from datetime import datetime

router = APIRouter()


@router.get("", response_model=List[TaskTimeLogRead])
def list_timelogs(
    skip: int = 0,
    limit: int = 100,
    task_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve a list of time logs for the current user.
    Admins can see all logs. Others see only their own.
    """
    if current_user.is_privileged or UserRole.MANAGER in current_user.roles:
        statement = select(TaskTimeLog)
    else:
        statement = select(TaskTimeLog).where(TaskTimeLog.user_id == current_user.id)
    
    if task_id:
        statement = statement.where(TaskTimeLog.task_id == task_id)
        
    timelogs = db.exec(statement.offset(skip).limit(limit)).all()
    return timelogs


@router.get("/{log_id}", response_model=TaskTimeLogRead)
def read_timelog(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get a specific time log by ID.
    """
    timelog = db.get(TaskTimeLog, log_id)
    if not timelog:
        raise HTTPException(status_code=404, detail="Time log not found")
    
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        if timelog.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this time log")
            
    return timelog


@router.post("", response_model=TaskTimeLogRead)
def create_timelog(
    log_in: TaskTimeLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Create a new manual time log entry.
    """
    task = db.get(Task, log_in.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    timelog = TaskTimeLog(
        **log_in.dict(),
        user_id=current_user.id
    )
    db.add(timelog)
    db.commit()
    db.refresh(timelog)
    return timelog


@router.patch("/{log_id}", response_model=TaskTimeLogRead)
def update_timelog(
    log_id: int,
    log_update: TaskTimeLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update an existing time log entry.
    """
    timelog = db.get(TaskTimeLog, log_id)
    if not timelog:
        raise HTTPException(status_code=404, detail="Time log not found")
        
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        if timelog.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this time log")
    
    log_data = log_update.dict(exclude_unset=True)
    for key, value in log_data.items():
        setattr(timelog, key, value)
        
    db.add(timelog)
    db.commit()
    db.refresh(timelog)
    return timelog


@router.delete("/{log_id}")
def delete_timelog(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a time log entry.
    """
    timelog = db.get(TaskTimeLog, log_id)
    if not timelog:
        raise HTTPException(status_code=404, detail="Time log not found")
        
    if not (current_user.is_privileged or UserRole.MANAGER in current_user.roles):
        if timelog.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this time log")
            
    db.delete(timelog)
    db.commit()
    return {"status": "success", "detail": "Time log deleted"}
