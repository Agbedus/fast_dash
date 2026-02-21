import sys
import os
import asyncio
from sqlmodel import Session, select, delete
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import engine
from app.models.user import User, UserRole
from app.models.notification import Notification
from app.services.notifications import NotificationService

async def test_notification_filtering():
    """
    Tests notification filtering logic:
    1. Users should not receive notifications where they are the sender (Self-notification).
    2. Role-based broadcasts (e.g., to Managers) should include Super Admins unless they are the sender.
    """
    with Session(engine) as session:
        # 1. Setup - Create test users
        timestamp = datetime.utcnow().timestamp()
        admin_email = f"admin_{timestamp}@example.com"
        user_email = f"user_{timestamp}@example.com"
        
        super_admin = User(email=admin_email, full_name="Admin", roles=[UserRole.SUPER_ADMIN])
        test_user = User(email=user_email, full_name="User", roles=[UserRole.USER])
        
        session.add(super_admin)
        session.add(test_user)
        session.commit()
        session.refresh(super_admin)
        session.refresh(test_user)

        # 2. Test Case 1: Self-notification (should be skipped)
        initial_count = len(session.exec(select(Notification)).all())
        
        await NotificationService.send_notification(
            session,
            recipient_id=test_user.id,
            title="Self Test",
            message="This should NOT be saved",
            sender_id=test_user.id
        )
        session.commit()
        
        new_count = len(session.exec(select(Notification)).all())
        assert new_count == initial_count, "Self-notification was not skipped."

        # 3. Test Case 2: Role-based broadcast (Super Admin should receive)
        # We'll notify all SUPER_ADMINS (excluding sender if admin)
        # Actually, let's notify MANAGERS and see if Super Admin gets it
        initial_admin_notifs = len(session.exec(select(Notification).where(Notification.recipient_id == super_admin.id)).all())
        
        await NotificationService.notify_roles(
            session,
            roles=[UserRole.MANAGER],
            title="Broadcast Test",
            message="Message for managers",
            sender_id=test_user.id
        )
        session.commit()
        
        # Check if Super Admin received it (NotificationService logic should include admins in broadcasts)
        final_admin_notifs = len(session.exec(select(Notification).where(Notification.recipient_id == super_admin.id)).all())
        assert final_admin_notifs > initial_admin_notifs, "Super Admin did not receive role-based broadcast."

        # Cleanup - Delete notifications first (both sender and recipient) to avoid FK constraints
        session.exec(delete(Notification).where(
            (Notification.recipient_id == super_admin.id) | 
            (Notification.recipient_id == test_user.id) |
            (Notification.sender_id == super_admin.id) | 
            (Notification.sender_id == test_user.id)
        ))
        session.commit()
        
        session.delete(super_admin)
        session.delete(test_user)
        session.commit()

if __name__ == "__main__":
    # If run directly
    try:
        asyncio.run(test_notification_filtering())
        print("Notification tests PASSED")
    except Exception as e:
        print(f"Notification tests FAILED: {e}")
        sys.exit(1)
