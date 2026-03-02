from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class TimeOffType(str, Enum):
    leave = "leave"
    off = "off"
    sick = "sick"
    other = "other"


class TimeOffStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TimeOffBase(SQLModel):
    user_id: str = Field(foreign_key="users.id", nullable=False)
    start_date: str = Field(nullable=False)
    end_date: str = Field(nullable=False)
    type: TimeOffType = Field(default=TimeOffType.leave)
    status: TimeOffStatus = Field(default=TimeOffStatus.pending)
    justification: Optional[str] = None
    requested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_by: Optional[str] = Field(default=None, foreign_key="users.id")


class TimeOff(TimeOffBase, table=True):
    __tablename__ = "time_off_requests"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "TimeOff.user_id == User.id"}
    )
    approver: Optional["User"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "TimeOff.approved_by == User.id"}
    )
