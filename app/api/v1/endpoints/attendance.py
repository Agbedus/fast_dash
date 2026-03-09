from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db, get_current_user, RoleChecker
from app.models.user import User, UserRole
from app.models.attendance import OfficeLocation, AttendancePolicy, AttendanceRecord, PresenceStateHistory
from app.schemas.attendance import (
    LocationUpdateRequest, LocationUpdateResponse,
    AttendanceOverrideRequest, OfficeLocationCreate,
    OfficeLocationUpdate, AttendancePolicyUpdate
)
from app.services.attendance import LocationService, PresenceService, AttendanceService, OverrideService

router = APIRouter()

@router.post("/location-update", response_model=LocationUpdateResponse)
def location_update(
    req: LocationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.STAFF, UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    office = db.get(OfficeLocation, req.office_location_id)
    if not office or not office.is_active:
        raise HTTPException(status_code=404, detail="Active office location not found")
        
    policy = db.exec(select(AttendancePolicy).where(AttendancePolicy.office_location_id == office.id)).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Attendance policy not found for this office")

    distance = LocationService.calculate_distance(req.latitude, req.longitude, office.latitude, office.longitude)
    raw_zone = LocationService.derive_raw_zone(distance, office)
    
    LocationService.save_raw_log(
        db=db, user_id=current_user.id, office_id=office.id,
        lat=req.latitude, lon=req.longitude, accuracy=req.accuracy_meters,
        distance=distance, zone=raw_zone
    )
    
    confirmed_state = PresenceService.evaluate_presence(
        db=db, user_id=current_user.id, office=office, policy=policy,
        current_zone=raw_zone, accuracy=req.accuracy_meters
    )
    
    attendance_state, record = AttendanceService.evaluate_attendance(
        db=db, user=current_user, office=office, policy=policy, confirmed_state=confirmed_state
    )
    
    return LocationUpdateResponse(
        distance_from_office_meters=distance,
        derived_zone=raw_zone,
        presence_state=confirmed_state,
        attendance_state=attendance_state,
        clock_in_at=record.clock_in_at,
        clock_out_at=record.clock_out_at
    )

@router.get("/me/today", response_model=Optional[AttendanceRecord])
def get_my_attendance_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.STAFF, UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    today = datetime.utcnow().date()
    # If using multiple offices, might need office_location_id
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.user_id == current_user.id,
        AttendanceRecord.work_date == today
    )
    return db.exec(stmt).first()

@router.get("/me/history", response_model=List[AttendanceRecord])
def get_my_attendance_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.STAFF, UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.user_id == current_user.id
    ).order_by(AttendanceRecord.work_date.desc())
    return db.exec(stmt).all()

@router.get("/team/today", response_model=List[AttendanceRecord])
def get_team_attendance_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    today = datetime.utcnow().date()
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.work_date == today
    )
    # Could filter by teams if available, returning all for simplicity
    return db.exec(stmt).all()

@router.get("/{user_id}/history", response_model=List[AttendanceRecord])
def get_user_attendance_history(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    stmt = select(AttendanceRecord).where(
        AttendanceRecord.user_id == user_id
    ).order_by(AttendanceRecord.work_date.desc())
    return db.exec(stmt).all()

@router.post("/{attendance_record_id}/override", response_model=AttendanceRecord)
def override_attendance(
    attendance_record_id: int,
    req: AttendanceOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.MANAGER, UserRole.SUPER_ADMIN]))
):
    try:
        return OverrideService.apply_override(
            db=db, record_id=attendance_record_id, manager=current_user,
            new_in=req.new_clock_in_at, new_out=req.new_clock_out_at, reason=req.reason
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/office-locations", response_model=OfficeLocation)
def create_office_location(
    req: OfficeLocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN]))
):
    office = OfficeLocation(**req.dict())
    db.add(office)
    db.commit()
    db.refresh(office)
    
    # Auto-create default policy
    policy = AttendancePolicy(office_location_id=office.id)
    db.add(policy)
    db.commit()
    
    return office

@router.patch("/office-locations/{id}", response_model=OfficeLocation)
def update_office_location(
    id: int,
    req: OfficeLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN]))
):
    office = db.get(OfficeLocation, id)
    if not office:
        raise HTTPException(status_code=404, detail="Office not found")
        
    update_data = req.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(office, field, value)
        
    db.add(office)
    db.commit()
    db.refresh(office)
    return office

@router.get("-policy/{office_location_id}", response_model=AttendancePolicy)
def get_attendance_policy(
    office_location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN]))
):
    policy = db.exec(select(AttendancePolicy).where(AttendancePolicy.office_location_id == office_location_id)).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.patch("-policy/{office_location_id}", response_model=AttendancePolicy)
def update_attendance_policy(
    office_location_id: int,
    req: AttendancePolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN]))
):
    policy = db.exec(select(AttendancePolicy).where(AttendancePolicy.office_location_id == office_location_id)).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    update_data = req.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
        
    policy.updated_at = datetime.utcnow().isoformat()
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy
