from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, BackgroundTasks
from sqlmodel import Session, select
from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead, NotificationUpdate
from app.services.notifications import manager, NotificationService

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time notifications.
    Note: In a production app, you would authenticate the user here using a token 
    passed in the query string or subprotocol.
    """
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep the connection alive and wait for client to close or send data
            data = await websocket.receive_text()
            # For now we just echo or ignore client messages
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

@router.get("", response_model=List[NotificationRead])
def read_notifications(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve current user's notifications and trigger cleanup.
    """
    background_tasks.add_task(NotificationService.cleanup_old_notifications, db)
    notifications = db.exec(
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return notifications

@router.put("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    *,
    db: Session = Depends(get_db),
    notification_id: str,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Mark a notification as read.
    """
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification.is_read = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
