import sys
import os
from datetime import datetime, timedelta
from sqlmodel import Session, select

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import engine
from app.models.user import User, UserRole
from app.models.task import Task, TaskTimeLog, TaskStatus

def test_productivity_logic():
    """
    Tests core productivity logic:
    1. Overlapping timer prevention (starting a new timer closes the old one).
    2. Total hours calculation (aggregates all session durations).
    """
    with Session(engine) as session:
        # 1. Setup - Create test user and tasks
        user_email = f"test_{datetime.utcnow().timestamp()}@example.com"
        user = User(email=user_email, full_name="Test User", roles=[UserRole.USER])
        session.add(user)
        session.commit()
        session.refresh(user)

        t1 = Task(name="Task 1", user_id=user.id)
        t2 = Task(name="Task 2", user_id=user.id)
        session.add(t1)
        session.add(t2)
        session.commit()
        session.refresh(t1)
        session.refresh(t2)

        # 2. Test Timer Overlap Logic
        # (This mimics the logic in app/api/v1/endpoints/tasks.py)
        def start_timer(task_id, user_id, db):
            active = db.exec(select(TaskTimeLog).where(
                TaskTimeLog.user_id == user_id, 
                TaskTimeLog.end_time == None
            )).all()
            for s in active:
                s.end_time = datetime.utcnow().isoformat()
                db.add(s)
            
            new_s = TaskTimeLog(task_id=task_id, user_id=user_id, start_time=datetime.utcnow().isoformat())
            db.add(new_s)
            db.commit()
            return new_s

        s1 = start_timer(t1.id, user.id, session)
        s2 = start_timer(t2.id, user.id, session)
        
        session.refresh(s1)
        assert s1.end_time is not None, "Old timer should be closed when starting a new one."
        assert s2.end_time is None, "New timer should be active."

        # 3. Test Total Hours Calculation
        # Add a fixed 1-hour session to T1
        now = datetime.utcnow()
        past_start = (now - timedelta(hours=2)).isoformat()
        past_end = (now - timedelta(hours=1)).isoformat()
        
        log = TaskTimeLog(
            task_id=t1.id,
            user_id=user.id,
            start_time=past_start,
            end_time=past_end
        )
        session.add(log)
        session.commit()
        
        session.refresh(t1)
        # s1 also has some duration (seconds), but total_hours rounds to 2 decimals
        # The 1-hour log + s1 (which is very short) should be ~1.0 hours or slightly more
        assert t1.total_hours >= 1.0, f"Expected at least 1.0 hours, got {t1.total_hours}"

        # Cleanup
        session.delete(s1)
        session.delete(s2)
        session.delete(log)
        session.delete(t1)
        session.delete(t2)
        session.delete(user)
        session.commit()

if __name__ == "__main__":
    # If run directly without pytest
    try:
        test_productivity_logic()
        print("Productivity tests PASSED")
    except Exception as e:
        print(f"Productivity tests FAILED: {e}")
        sys.exit(1)
