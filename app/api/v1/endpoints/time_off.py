from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.time_off import TimeOff, TimeOffStatus
from app.models.user import User, UserRole
from app.schemas.time_off import TimeOffCreate, TimeOffRead, TimeOffUpdate
from app.api.deps import get_current_user
from app.services.time_off_service import TimeOffService
from app.services.notifications import NotificationService
from typing import List, Optional

router = APIRouter()


@router.post("/", response_model=TimeOffRead)
async def create_time_off_request(
    *,
    db: Session = Depends(get_db),
    request_in: TimeOffCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new time-off request.
    """
    # Permission check: STAFF and above can request
    if UserRole.STAFF not in current_user.roles and \
       UserRole.MANAGER not in current_user.roles and \
       UserRole.SUPER_ADMIN not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted"
        )
    
    time_off = TimeOffService.create_request(db, current_user.id, request_in)
    
    await NotificationService.notify_managers(
        db, 
        title="Time Off Request", 
        message=f"{current_user.full_name or current_user.email} requested time off from {time_off.start_date} to {time_off.end_date}",
        sender_id=current_user.id,
        resource_type="time_off",
        resource_id=str(time_off.id)
    )
    
    return time_off


@router.get("/", response_model=List[TimeOffRead])
def read_time_off_requests(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve time-off requests.
    Managers and Super Admins see all. Staff see their own.
    """
    if UserRole.SUPER_ADMIN in current_user.roles or UserRole.MANAGER in current_user.roles:
        statement = select(TimeOff).offset(skip).limit(limit)
    else:
        statement = select(TimeOff).where(TimeOff.user_id == current_user.id).offset(skip).limit(limit)
    
    return db.exec(statement).all()


@router.get("/{request_id}", response_model=TimeOffRead)
def read_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific time-off request.
    """
    db_request = db.get(TimeOff, request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if UserRole.SUPER_ADMIN not in current_user.roles and \
       UserRole.MANAGER not in current_user.roles and \
       db_request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Operation not permitted")
        
    return db_request


@router.post("/{request_id}/approve", response_model=TimeOffRead)
async def approve_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a time-off request. Only Super Admins for now as per requirements.
    """
    if UserRole.SUPER_ADMIN not in current_user.roles:
        raise HTTPException(status_code=403, detail="Only super admins can approve requests")
    
    time_off = TimeOffService.approve_request(db, request_id, current_user.id)
    
    await NotificationService.send_notification(
        db, 
        recipient_id=time_off.user_id,
        title="Time Off Request Approved",
        message=f"Your time off request from {time_off.start_date} to {time_off.end_date} has been approved",
        type="success",
        sender_id=current_user.id,
        resource_type="time_off",
        resource_id=str(time_off.id)
    )
    
    return time_off


@router.post("/{request_id}/reject", response_model=TimeOffRead)
async def reject_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a time-off request. Only Super Admins for now.
    """
    if UserRole.SUPER_ADMIN not in current_user.roles:
        raise HTTPException(status_code=403, detail="Only super admins can reject requests")
    
    time_off = TimeOffService.reject_request(db, request_id, current_user.id)
    
    await NotificationService.send_notification(
        db, 
        recipient_id=time_off.user_id,
        title="Time Off Request Rejected",
        message=f"Your time off request from {time_off.start_date} to {time_off.end_date} has been rejected",
        type="info",
        sender_id=current_user.id,
        resource_type="time_off",
        resource_id=str(time_off.id)
    )
    
    return time_off


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_off_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a time-off request.
    Only the owner can delete their pending request.
    """
    db_request = db.get(TimeOff, request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if db_request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")
    
    if db_request.status != TimeOffStatus.pending:
        raise HTTPException(status_code=400, detail="Cannot delete a non-pending request")
        
    db.delete(db_request)
    db.commit()
    return None
