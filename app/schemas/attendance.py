from typing import Optional
from datetime import datetime, time
from pydantic import BaseModel
from app.models.attendance import PresenceState, AttendanceState

class LocationUpdateRequest(BaseModel):
    office_location_id: int
    latitude: float
    longitude: float
    accuracy_meters: float
    recorded_at: str

class LocationUpdateResponse(BaseModel):
    distance_from_office_meters: float
    derived_zone: PresenceState
    presence_state: PresenceState
    attendance_state: AttendanceState
    clock_in_at: Optional[str] = None
    clock_out_at: Optional[str] = None

class AttendanceOverrideRequest(BaseModel):
    new_clock_in_at: Optional[str] = None
    new_clock_out_at: Optional[str] = None
    reason: str

class OfficeLocationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    in_office_radius_meters: Optional[int] = 5
    temporarily_out_radius_meters: Optional[int] = 15
    out_of_office_radius_meters: Optional[int] = 15
    is_active: Optional[bool] = True

class OfficeLocationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    in_office_radius_meters: Optional[int] = None
    temporarily_out_radius_meters: Optional[int] = None
    out_of_office_radius_meters: Optional[int] = None
    is_active: Optional[bool] = None

class AttendancePolicyUpdate(BaseModel):
    check_in_open_time: Optional[time] = None
    check_in_close_time: Optional[time] = None
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    auto_clock_out_time: Optional[time] = None
    temporarily_out_grace_minutes: Optional[int] = None
    out_of_office_grace_minutes: Optional[int] = None
    return_to_office_confirmation_minutes: Optional[int] = None
