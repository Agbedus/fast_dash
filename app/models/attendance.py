from enum import Enum
from typing import Optional, List
from datetime import datetime, time, date
from sqlmodel import SQLModel, Field

class PresenceState(str, Enum):
    IN_OFFICE = "IN_OFFICE"
    TEMPORARILY_OUT = "TEMPORARILY_OUT"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"

class AttendanceState(str, Enum):
    NOT_CLOCKED_IN = "NOT_CLOCKED_IN"
    CLOCKED_IN = "CLOCKED_IN"
    CLOCKED_OUT = "CLOCKED_OUT"

class OfficeLocation(SQLModel, table=True):
    __tablename__ = "office_locations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    latitude: float
    longitude: float
    in_office_radius_meters: int = Field(default=5)
    temporarily_out_radius_meters: int = Field(default=15)
    out_of_office_radius_meters: int = Field(default=15)
    is_active: bool = Field(default=True)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AttendancePolicy(SQLModel, table=True):
    __tablename__ = "attendance_policies"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    office_location_id: int = Field(foreign_key="office_locations.id")
    check_in_open_time: time = Field(default=time(7, 30))
    check_in_close_time: time = Field(default=time(10, 0))
    work_start_time: time = Field(default=time(8, 30))
    work_end_time: time = Field(default=time(18, 0))
    auto_clock_out_time: time = Field(default=time(18, 0))
    temporarily_out_grace_minutes: int = Field(default=5)
    out_of_office_grace_minutes: int = Field(default=10)
    return_to_office_confirmation_minutes: int = Field(default=2)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class LocationLog(SQLModel, table=True):
    __tablename__ = "location_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    office_location_id: int = Field(foreign_key="office_locations.id")
    latitude: float
    longitude: float
    accuracy_meters: float
    distance_from_office_meters: float
    derived_zone: PresenceState
    recorded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AttendanceRecord(SQLModel, table=True):
    __tablename__ = "attendance_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    office_location_id: int = Field(foreign_key="office_locations.id")
    work_date: date = Field(index=True)
    attendance_state: AttendanceState = Field(default=AttendanceState.NOT_CLOCKED_IN)
    clock_in_at: Optional[str] = None
    clock_out_at: Optional[str] = None
    first_seen_in_office_at: Optional[str] = None
    last_seen_in_office_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class PresenceStateHistory(SQLModel, table=True):
    __tablename__ = "presence_state_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    office_location_id: int = Field(foreign_key="office_locations.id")
    from_state: Optional[PresenceState] = None
    to_state: PresenceState
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ended_at: Optional[str] = None
    trigger_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AttendanceOverride(SQLModel, table=True):
    __tablename__ = "attendance_overrides"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    attendance_record_id: int = Field(foreign_key="attendance_records.id", index=True)
    changed_by_user_id: str = Field(foreign_key="users.id")
    old_clock_in_at: Optional[str] = None
    new_clock_in_at: Optional[str] = None
    old_clock_out_at: Optional[str] = None
    new_clock_out_at: Optional[str] = None
    reason: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
