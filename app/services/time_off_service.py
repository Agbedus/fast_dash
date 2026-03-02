from sqlmodel import Session, select, func, and_, or_
from app.models.time_off import TimeOff, TimeOffType, TimeOffStatus
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus, EventPrivacy
from app.schemas.time_off import TimeOffCreate, TimeOffUpdate
from datetime import datetime, date
from fastapi import HTTPException, status
from typing import List, Optional


class TimeOffService:
    @staticmethod
    def calculate_total_leave_days(db: Session, user_id: str) -> int:
        """Calculate total 'leave' days taken by a user in the current year."""
        current_year = datetime.utcnow().year
        start_of_year = f"{current_year}-01-01"
        end_of_year = f"{current_year}-12-31"
        
        statement = select(TimeOff).where(
            TimeOff.user_id == user_id,
            TimeOff.type == TimeOffType.leave,
            TimeOff.status == TimeOffStatus.approved,
            TimeOff.start_date >= start_of_year,
            TimeOff.end_date <= end_of_year
        )
        approved_requests = db.exec(statement).all()
        
        total_days = 0
        for req in approved_requests:
            start = datetime.fromisoformat(req.start_date).date()
            end = datetime.fromisoformat(req.end_date).date()
            total_days += (end - start).days + 1
        return total_days

    @staticmethod
    def create_request(db: Session, user_id: str, request_data: TimeOffCreate) -> TimeOff:
        """Create a new time-off request."""
        # Validation for 'leave' type (15 days limit)
        if request_data.type == TimeOffType.leave:
            start = datetime.fromisoformat(request_data.start_date).date()
            end = datetime.fromisoformat(request_data.end_date).date()
            requested_days = (end - start).days + 1
            
            if requested_days > 15:
                raise HTTPException(status_code=400, detail="Cannot request more than 15 days of leave at once.")
                
            total_taken = TimeOffService.calculate_total_leave_days(db, user_id)
            if total_taken + requested_days > 15:
                raise HTTPException(status_code=400, detail=f"Leave limit exceeded. You have {15 - total_taken} days remaining.")

        # Validation for 'off', 'sick', 'other' (Justification required)
        if request_data.type in [TimeOffType.off, TimeOffType.sick, TimeOffType.other] and not request_data.justification:
            raise HTTPException(status_code=400, detail=f"Justification is required for {request_data.type.value} requests.")

        db_request = TimeOff(
            **request_data.model_dump(),
            user_id=user_id,
            status=TimeOffStatus.pending
        )
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        return db_request

    @staticmethod
    def approve_request(db: Session, request_id: int, approver_id: str) -> TimeOff:
        """Approve a time-off request and block calendar."""
        db_request = db.get(TimeOff, request_id)
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if db_request.status != TimeOffStatus.pending:
            raise HTTPException(status_code=400, detail="Only pending requests can be approved")

        db_request.status = TimeOffStatus.approved
        db_request.approved_by = approver_id
        db_request.updated_at = datetime.utcnow().isoformat()
        
        # Block calendar: Create an Event
        new_event = Event(
            title=f"{db_request.type.value.capitalize()}: {db_request.user.full_name or db_request.user.email}",
            description=f"Approved {db_request.type.value} request. Justification: {db_request.justification or 'None'}",
            start=db_request.start_date,
            end=db_request.end_date,
            all_day=1,
            status=EventStatus.confirmed,
            privacy=EventPrivacy.public,
            user_id=db_request.user_id,
            color="#ef4444" # Red color to indicate unavailability
        )
        db.add(new_event)
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        return db_request

    @staticmethod
    def reject_request(db: Session, request_id: int, approver_id: str) -> TimeOff:
        """Reject a time-off request."""
        db_request = db.get(TimeOff, request_id)
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if db_request.status != TimeOffStatus.pending:
            raise HTTPException(status_code=400, detail="Only pending requests can be rejected")

        db_request.status = TimeOffStatus.rejected
        db_request.approved_by = approver_id
        db_request.updated_at = datetime.utcnow().isoformat()
        
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        return db_request

    @staticmethod
    def is_user_available(db: Session, user_id: str, start_date: str, end_date: str) -> bool:
        """Check if a user is available (not on approved leave) for a given range."""
        statement = select(TimeOff).where(
            TimeOff.user_id == user_id,
            TimeOff.status == TimeOffStatus.approved,
            or_(
                and_(TimeOff.start_date <= start_date, TimeOff.end_date >= start_date),
                and_(TimeOff.start_date <= end_date, TimeOff.end_date >= end_date),
                and_(TimeOff.start_date >= start_date, TimeOff.end_date <= end_date)
            )
        )
        result = db.exec(statement).first()
        return result is None
