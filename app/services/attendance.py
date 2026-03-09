import math
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import User, UserRole
from app.models.attendance import (
    OfficeLocation, AttendancePolicy, LocationLog,
    AttendanceRecord, PresenceStateHistory, AttendanceOverride,
    PresenceState, AttendanceState
)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class LocationService:
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_distance(lat1, lon1, lat2, lon2)

    @staticmethod
    def derive_raw_zone(distance: float, office: OfficeLocation) -> PresenceState:
        if distance <= office.in_office_radius_meters:
            return PresenceState.IN_OFFICE
        elif distance <= office.temporarily_out_radius_meters:
            return PresenceState.TEMPORARILY_OUT
        else:
            return PresenceState.OUT_OF_OFFICE

    @staticmethod
    def save_raw_log(db: Session, user_id: str, office_id: int, lat: float, lon: float, accuracy: float, distance: float, zone: PresenceState) -> LocationLog:
        now = datetime.utcnow()
        log = LocationLog(
            user_id=user_id,
            office_location_id=office_id,
            latitude=lat,
            longitude=lon,
            accuracy_meters=accuracy,
            distance_from_office_meters=distance,
            derived_zone=zone,
            recorded_at=now.isoformat()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log


class PresenceService:
    @staticmethod
    def get_current_confirmed_state(db: Session, user_id: str, office_id: int) -> Optional[PresenceState]:
        stmt = select(PresenceStateHistory).where(
            PresenceStateHistory.user_id == user_id,
            PresenceStateHistory.office_location_id == office_id,
            PresenceStateHistory.ended_at == None
        ).order_by(PresenceStateHistory.started_at.desc())
        history = db.exec(stmt).first()
        return history.to_state if history else None

    @staticmethod
    def evaluate_presence(db: Session, user_id: str, office: OfficeLocation, policy: AttendancePolicy, current_zone: PresenceState, accuracy: float) -> PresenceState:
        # If accuracy is very poor, don't use it to end presence, just log it. 
        if accuracy > 30 and current_zone != PresenceState.IN_OFFICE:
            current_state = PresenceService.get_current_confirmed_state(db, user_id, office.id)
            return current_state or PresenceState.OUT_OF_OFFICE

        # Fetch recent logs
        now = datetime.utcnow()
        check_window = max(policy.out_of_office_grace_minutes, policy.temporarily_out_grace_minutes, policy.return_to_office_confirmation_minutes)
        window_start = now - timedelta(minutes=check_window + 5) # look back a bit further
        
        logs_stmt = select(LocationLog).where(
            LocationLog.user_id == user_id,
            LocationLog.office_location_id == office.id,
            LocationLog.recorded_at >= window_start.isoformat()
        ).order_by(LocationLog.recorded_at.desc())
        recent_logs = db.exec(logs_stmt).all()

        current_state = PresenceService.get_current_confirmed_state(db, user_id, office.id)
        if not current_state:
            new_state = current_zone if current_zone == PresenceState.IN_OFFICE else PresenceState.OUT_OF_OFFICE
            PresenceService.update_state(db, user_id, office.id, None, new_state, "Initial State")
            return new_state

        if current_state == current_zone:
            return current_state

        # Check grace periods for transitioning
        # This is a simplified rolling window evaluation
        def has_been_in_zone_for(zone: PresenceState, minutes: int) -> bool:
            cutoff = now - timedelta(minutes=minutes)
            relevant_logs = [l for l in recent_logs if datetime.fromisoformat(l.recorded_at) >= cutoff]
            if not relevant_logs:
                return False
            # Check if consistently in this zone or worse
            for l in relevant_logs:
                # If we're looking for IN_OFFICE, all must be IN_OFFICE
                if zone == PresenceState.IN_OFFICE and l.derived_zone != PresenceState.IN_OFFICE:
                    return False
                # If looking for OUT_OF_OFFICE, all must be OUT_OF_OFFICE
                if zone == PresenceState.OUT_OF_OFFICE and l.derived_zone != PresenceState.OUT_OF_OFFICE:
                    return False
                # If looking for TEMPORARILY_OUT, all must be TEMP_OUT or OUT_OF_OFFICE
                if zone == PresenceState.TEMPORARILY_OUT and l.derived_zone == PresenceState.IN_OFFICE:
                    return False
            # Ensure the earliest log in the window is approximately `minutes` ago
            if (now - datetime.fromisoformat(relevant_logs[-1].recorded_at)).total_seconds() < (minutes * 60) - 30: # 30s buffer
                return False
            return True

        new_state = current_state

        if current_zone == PresenceState.OUT_OF_OFFICE:
            if current_state == PresenceState.IN_OFFICE and has_been_in_zone_for(PresenceState.OUT_OF_OFFICE, policy.out_of_office_grace_minutes):
                new_state = PresenceState.OUT_OF_OFFICE
            elif current_state == PresenceState.TEMPORARILY_OUT and has_been_in_zone_for(PresenceState.OUT_OF_OFFICE, policy.out_of_office_grace_minutes - policy.temporarily_out_grace_minutes):
                 new_state = PresenceState.OUT_OF_OFFICE

        elif current_zone == PresenceState.TEMPORARILY_OUT:
            if current_state == PresenceState.IN_OFFICE and has_been_in_zone_for(PresenceState.TEMPORARILY_OUT, policy.temporarily_out_grace_minutes):
                new_state = PresenceState.TEMPORARILY_OUT

        elif current_zone == PresenceState.IN_OFFICE:
            if current_state != PresenceState.IN_OFFICE and has_been_in_zone_for(PresenceState.IN_OFFICE, policy.return_to_office_confirmation_minutes):
                new_state = PresenceState.IN_OFFICE

        if new_state != current_state:
            PresenceService.update_state(db, user_id, office.id, current_state, new_state, "Grace period met")

        return new_state

    @staticmethod
    def update_state(db: Session, user_id: str, office_id: int, old_state: Optional[PresenceState], new_state: PresenceState, reason: str):
        now = datetime.utcnow().isoformat()
        if old_state:
            old_history_stmt = select(PresenceStateHistory).where(
                PresenceStateHistory.user_id == user_id,
                PresenceStateHistory.office_location_id == office_id,
                PresenceStateHistory.ended_at == None
            )
            old_history = db.exec(old_history_stmt).first()
            if old_history:
                old_history.ended_at = now
                db.add(old_history)
        
        new_history = PresenceStateHistory(
            user_id=user_id,
            office_location_id=office_id,
            from_state=old_state,
            to_state=new_state,
            started_at=now,
            trigger_reason=reason
        )
        db.add(new_history)
        db.commit()


class AttendanceService:
    @staticmethod
    def evaluate_attendance(db: Session, user: User, office: OfficeLocation, policy: AttendancePolicy, confirmed_state: PresenceState) -> Tuple[AttendanceState, AttendanceRecord]:
        now = datetime.utcnow()
        today = now.date()
        current_time = now.time()
        
        stmt = select(AttendanceRecord).where(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.office_location_id == office.id,
            AttendanceRecord.work_date == today
        )
        record = db.exec(stmt).first()
        
        if not record:
            record = AttendanceRecord(
                user_id=user.id,
                office_location_id=office.id,
                work_date=today,
                attendance_state=AttendanceState.NOT_CLOCKED_IN
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        if record.attendance_state == AttendanceState.CLOCKED_OUT:
             return record.attendance_state, record

        if confirmed_state == PresenceState.IN_OFFICE:
            if not record.first_seen_in_office_at:
                record.first_seen_in_office_at = now.isoformat()
            record.last_seen_in_office_at = now.isoformat()

            if record.attendance_state == AttendanceState.NOT_CLOCKED_IN:
                if policy.check_in_open_time <= current_time <= policy.check_in_close_time:
                    record.attendance_state = AttendanceState.CLOCKED_IN
                    record.clock_in_at = now.isoformat()

        if record.attendance_state == AttendanceState.CLOCKED_IN:
            if current_time >= policy.auto_clock_out_time:
                record.attendance_state = AttendanceState.CLOCKED_OUT
                out_datetime = datetime.combine(today, policy.auto_clock_out_time)
                record.clock_out_at = out_datetime.isoformat()

        record.updated_at = now.isoformat()
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return record.attendance_state, record


class OverrideService:
    @staticmethod
    def apply_override(db: Session, record_id: int, manager: User, new_in: Optional[str], new_out: Optional[str], reason: str) -> AttendanceRecord:
        if UserRole.MANAGER not in manager.roles and UserRole.SUPER_ADMIN not in manager.roles:
            raise HTTPException(status_code=403, detail="Not authorized to override attendance")
            
        record = db.get(AttendanceRecord, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Attendance record not found")

        override = AttendanceOverride(
            attendance_record_id=record.id,
            changed_by_user_id=manager.id,
            old_clock_in_at=record.clock_in_at,
            new_clock_in_at=new_in,
            old_clock_out_at=record.clock_out_at,
            new_clock_out_at=new_out,
            reason=reason
        )
        db.add(override)
        
        record.clock_in_at = new_in
        record.clock_out_at = new_out
        
        if new_in and not new_out:
            record.attendance_state = AttendanceState.CLOCKED_IN
        elif new_in and new_out:
            record.attendance_state = AttendanceState.CLOCKED_OUT
        elif not new_in and not new_out:
             record.attendance_state = AttendanceState.NOT_CLOCKED_IN
             
        record.updated_at = datetime.utcnow().isoformat()
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return record
