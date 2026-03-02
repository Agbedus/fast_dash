from typing import Optional, List
from sqlmodel import SQLModel
from app.models.time_off import TimeOffType, TimeOffStatus


class TimeOffBase(SQLModel):
    start_date: str
    end_date: str
    type: TimeOffType = TimeOffType.leave
    justification: Optional[str] = None


class TimeOffCreate(TimeOffBase):
    pass


class TimeOffRead(TimeOffBase):
    id: int
    user_id: str
    status: TimeOffStatus
    requested_at: str
    updated_at: str
    approved_by: Optional[str] = None


class TimeOffUpdate(SQLModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    type: Optional[TimeOffType] = None
    status: Optional[TimeOffStatus] = None
    justification: Optional[str] = None
    approved_by: Optional[str] = None
