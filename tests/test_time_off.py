import pytest
from sqlmodel import Session, SQLModel, create_engine
from app.models.time_off import TimeOff, TimeOffType, TimeOffStatus
from app.models.user import User, UserRole
from app.services.time_off_service import TimeOffService
from app.schemas.time_off import TimeOffCreate
from datetime import datetime, timedelta

# Setup in-memory SQLite for testing
sqlite_url = "sqlite://"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

def test_calculate_total_leave_days(session: Session):
    # Create a user
    user = User(id="user1", email="test@example.com", roles=[UserRole.STAFF])
    session.add(user)
    session.commit()
    
    # Create approved leave requests
    today = datetime.utcnow().date()
    req1 = TimeOff(
        user_id="user1",
        start_date=today.isoformat(),
        end_date=(today + timedelta(days=2)).isoformat(),
        type=TimeOffType.leave,
        status=TimeOffStatus.approved
    )
    req2 = TimeOff(
        user_id="user1",
        start_date=(today + timedelta(days=10)).isoformat(),
        end_date=(today + timedelta(days=11)).isoformat(),
        type=TimeOffType.leave,
        status=TimeOffStatus.approved
    )
    session.add(req1)
    session.add(req2)
    session.commit()
    
    total = TimeOffService.calculate_total_leave_days(session, "user1")
    assert total == 5 # 3 days (0,1,2) + 2 days (10,11)

def test_leave_limit_exceeded(session: Session):
    user = User(id="user1", email="test@example.com", roles=[UserRole.STAFF])
    session.add(user)
    session.commit()
    
    # Request more than 15 days at once
    today = datetime.utcnow().date()
    request_data = TimeOffCreate(
        start_date=today.isoformat(),
        end_date=(today + timedelta(days=16)).isoformat(),
        type=TimeOffType.leave
    )
    
    with pytest.raises(Exception) as excinfo:
        TimeOffService.create_request(session, "user1", request_data)
    assert "Cannot request more than 15 days" in str(excinfo.value)

def test_justification_required(session: Session):
    user = User(id="user1", email="test@example.com", roles=[UserRole.STAFF])
    session.add(user)
    session.commit()
    
    today = datetime.utcnow().date()
    request_data = TimeOffCreate(
        start_date=today.isoformat(),
        end_date=today.isoformat(),
        type=TimeOffType.sick
    )
    
    with pytest.raises(Exception) as excinfo:
        TimeOffService.create_request(session, "user1", request_data)
    assert "Justification is required" in str(excinfo.value)

def test_approve_request_creates_event(session: Session):
    user = User(id="user1", email="test@example.com", full_name="Test User", roles=[UserRole.STAFF])
    session.add(user)
    session.commit()
    
    today = datetime.utcnow().date()
    request_data = TimeOffCreate(
        start_date=today.isoformat(),
        end_date=today.isoformat(),
        type=TimeOffType.leave
    )
    req = TimeOffService.create_request(session, "user1", request_data)
    
    # Approve
    TimeOffService.approve_request(session, req.id, "admin1")
    
    # Check status
    session.refresh(req)
    assert req.status == TimeOffStatus.approved
    
    # Check Event creation
    from app.models.event import Event
    event = session.exec(select(Event).where(Event.user_id == "user1")).first()
    assert event is not None
    assert "Leave: Test User" in event.title
    assert event.all_day == 1

def test_user_availability(session: Session):
    user = User(id="user1", email="test@example.com", roles=[UserRole.STAFF])
    session.add(user)
    session.commit()
    
    today = datetime.utcnow().date()
    start_date = today.isoformat()
    end_date = (today + timedelta(days=2)).isoformat()
    
    # Initial availability
    assert TimeOffService.is_user_available(session, "user1", start_date, start_date) is True
    
    # Create approved leave
    req = TimeOff(
        user_id="user1",
        start_date=start_date,
        end_date=end_date,
        type=TimeOffType.leave,
        status=TimeOffStatus.approved
    )
    session.add(req)
    session.commit()
    
    # Check availability during leave
    assert TimeOffService.is_user_available(session, "user1", start_date, start_date) is False
    assert TimeOffService.is_user_available(session, "user1", (today + timedelta(days=1)).isoformat(), (today + timedelta(days=1)).isoformat()) is False
    # Check availability after leave
    assert TimeOffService.is_user_available(session, "user1", (today + timedelta(days=3)).isoformat(), (today + timedelta(days=3)).isoformat()) is True
