from typing import Dict, List, Optional
from fastapi import WebSocket
from sqlmodel import Session, select
from app.models.notification import Notification
from datetime import datetime, timedelta
import asyncio
from sqlmodel import Session, select, delete

class ConnectionManager:
    """
    Manages active WebSocket connections for real-time notifications.
    """
    def __init__(self):
        # Maps user_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """Sends a JSON message to all active connections for a specific user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

# Global instance of the connection manager
manager = ConnectionManager()

class NotificationService:
    """
    Service for managing notifications in the database and triggering real-time pushes.
    """
    @staticmethod
    def create_notification(
        db: Session,
        recipient_id: str,
        title: str,
        message: str,
        type: str = "info",
        sender_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> Notification:
        # Deduplication logic: Check if a similar notification exists within the last hour
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        existing = db.exec(
            select(Notification).where(
                Notification.recipient_id == recipient_id,
                Notification.title == title,
                Notification.message == message,
                Notification.resource_type == resource_type,
                Notification.resource_id == resource_id,
                Notification.created_at >= one_hour_ago
            )
        ).first()

        if existing:
            # Update timestamp and mark as unread if it was already read
            existing.created_at = datetime.utcnow().isoformat()
            existing.is_read = False
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        db_notification = Notification(
            recipient_id=recipient_id,
            sender_id=sender_id,
            title=title,
            message=message,
            type=type,
            resource_type=resource_type,
            resource_id=resource_id
        )
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        return db_notification

    @staticmethod
    def cleanup_old_notifications(db: Session):
        """
        Deletes old notifications to prevent database bloat.
        - Read notifications older than 7 days.
        - All notifications older than 30 days.
        """
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()

        # Delete read notifications older than 7 days
        stmt1 = delete(Notification).where(
            Notification.is_read == True,
            Notification.created_at < seven_days_ago
        )
        db.exec(stmt1)

        # Delete all notifications older than 30 days
        stmt2 = delete(Notification).where(
            Notification.created_at < thirty_days_ago
        )
        db.exec(stmt2)
        
        db.commit()

    @staticmethod
    async def send_notification(
        db: Session,
        recipient_id: str,
        title: str,
        message: str,
        type: str = "info",
        sender_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        """
        Creates a notification in the DB and pushes it via WebSocket if user is online.
        Skips if sender is the recipient.
        """
        if sender_id and recipient_id == sender_id:
            return None

        notification = NotificationService.create_notification(
            db, recipient_id, title, message, type, sender_id, resource_type, resource_id
        )
        
        payload = {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "resource_type": notification.resource_type,
            "resource_id": notification.resource_id,
            "created_at": notification.created_at,
            "is_read": notification.is_read
        }
        
        await manager.send_personal_message(payload, recipient_id)
        return notification

    @staticmethod
    async def notify_roles(
        db: Session,
        roles: List[str],
        title: str,
        message: str,
        type: str = "info",
        sender_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        """
        Broadcasts a notification to all users with specific roles efficiently.
        """
        from app.models.user import User, UserRole
        
        # 1. Fetch target users
        # We include explicitly requested roles AND Super Admins
        target_roles = set(roles) | {UserRole.SUPER_ADMIN}
        
        all_users = db.exec(select(User)).all()
        target_users = [
            u for u in all_users 
            if any(role in u.roles for role in target_roles) and (not sender_id or u.id != sender_id)
        ]
        
        if not target_users:
            return

        # 2. Create all notification objects and add them to session
        notifications = []
        for user in target_users:
            db_notification = Notification(
                recipient_id=user.id,
                sender_id=sender_id,
                title=title,
                message=message,
                type=type,
                resource_type=resource_type,
                resource_id=resource_id
            )
            db.add(db_notification)
            notifications.append((user.id, db_notification))
        
        # 3. Commit once for all notifications
        db.commit()
        
        # 4. Gather all WebSocket send tasks to run in parallel
        send_tasks = []
        for recipient_id, notification in notifications:
            # We refresh or just use the data we have
            payload = {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "type": notification.type,
                "resource_type": notification.resource_type,
                "resource_id": notification.resource_id,
                "created_at": notification.created_at,
                "is_read": notification.is_read
            }
            send_tasks.append(manager.send_personal_message(payload, recipient_id))
        
        if send_tasks:
            await asyncio.gather(*send_tasks)

    @staticmethod
    async def notify_super_admins(
        db: Session,
        title: str,
        message: str,
        type: str = "info",
        sender_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        from app.models.user import UserRole
        await NotificationService.notify_roles(
            db, [UserRole.SUPER_ADMIN], title, message, type, sender_id, resource_type, resource_id
        )

    @staticmethod
    async def notify_managers(
        db: Session,
        title: str,
        message: str,
        type: str = "info",
        sender_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        from app.models.user import UserRole
        await NotificationService.notify_roles(
            db, [UserRole.MANAGER, UserRole.SUPER_ADMIN], title, message, type, sender_id, resource_type, resource_id
        )
