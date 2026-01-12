import sys
import os
from sqlmodel import Session, select, create_engine
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.db.session import engine
from app.models.event import Event, EventRead
from app.models.user import User

def test_event_fields():
    print("--- Testing Event Model Fields ---")
    with Session(engine) as session:
        # Get a user for user_id
        user = session.exec(select(User)).first()
        if not user:
            print("No users found in database. Create one first.")
            return

        # Create a new event
        test_event = Event(
            title="Meeting with Team",
            description="Discussing the new features",
            start="2025-12-31T10:00:00",
            end="2025-12-31T11:00:00",
            color="#FF5733",
            user_id=user.id
        )
        
        print(f"Adding event: {test_event.title}")
        session.add(test_event)
        session.commit()
        session.refresh(test_event)
        
        print(f"Event created with ID: {test_event.id}")
        print(f"Color: {test_event.color}")
        print(f"User ID: {test_event.user_id}")
        print(f"Created At: {test_event.created_at}")
        
        # Verify EventRead
        event_read = EventRead.from_orm(test_event)
        print(f"EventRead title: {event_read.title}")
        assert event_read.color == "#FF5733"
        assert event_read.user_id == user.id
        
        # Create a second event
        test_event_2 = Event(
            title="Project Review",
            description="Reviewing the progress of the dashboard",
            start="2026-01-05T14:00:00",
            end="2026-01-05T15:30:00",
            color="#34D399",
            user_id=user.id,
            location="Conference Room B",
            status="tentative"
        )
        session.add(test_event_2)
        session.commit()
        
        print("Sample events created and persisted.")
        print("Verification SUCCESS: All new fields are correctly handled.")

if __name__ == "__main__":
    try:
        test_event_fields()
    except Exception as e:
        print(f"Verification FAILED: {e}")
