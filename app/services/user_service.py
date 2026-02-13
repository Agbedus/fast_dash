from sqlmodel import Session, select, text
from app.models import User, Notification, TaskAssignee, NoteShare, Account, UserSession, Project, Task, Event, Decision, Note

class UserService:
    @staticmethod
    def safe_delete_user(db: Session, user: User) -> None:
        """
        Safely deletes a user by detaching or deleting all related resources
        to satisfy foreign key constraints and maintain data integrity.
        """
        user_id = user.id
        
        # 1. Junction Tables (Delete associations)
        shared_notes = db.exec(select(NoteShare).where(NoteShare.user_id == user_id)).all()
        for share in shared_notes:
            db.delete(share)
        
        task_links = db.exec(select(TaskAssignee).where(TaskAssignee.user_id == user_id)).all()
        for link in task_links:
            db.delete(link)
        
        # 2. Identity & Session Tables
        accounts = db.exec(select(Account).where(Account.userId == user_id)).all()
        for acc in accounts:
            db.delete(acc)
            
        sessions = db.exec(select(UserSession).where(UserSession.userId == user_id)).all()
        for s in sessions:
            db.delete(s)
        
        # 3. Notifications (Delete as recipient, orphan as sender)
        notifications = db.exec(select(Notification).where(Notification.recipient_id == user_id)).all()
        for n in notifications:
            db.delete(n)
            
        db.execute(text("UPDATE notifications SET sender_id = NULL WHERE sender_id = :user_id"), {"user_id": user_id})
        
        # 4. Owned Resources (Orphan instead of cascade delete for history/integrity)
        db.execute(text("UPDATE projects SET owner_id = NULL WHERE owner_id = :user_id"), {"user_id": user_id})
        db.execute(text("UPDATE tasks SET user_id = NULL WHERE user_id = :user_id"), {"user_id": user_id})
        db.execute(text("UPDATE events SET user_id = NULL WHERE user_id = :user_id"), {"user_id": user_id})
        db.execute(text("UPDATE decisions SET user_id = NULL WHERE user_id = :user_id"), {"user_id": user_id})
        db.execute(text("UPDATE notes SET user_id = NULL WHERE user_id = :user_id"), {"user_id": user_id})
        
        # Ensure all detach/delete operations are flushed to DB before final user deletion
        db.flush()
        
        # Final User Deletion
        db.delete(user)
        db.commit()
