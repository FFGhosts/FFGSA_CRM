"""
Schedule Utilities for Phase 5: Advanced Scheduling & Calendar
Provides conflict detection, schedule resolution, and calendar generation
"""
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import and_, or_
from models import Schedule, ScheduleException, Device, DeviceGroup, db


class ScheduleConflict:
    """Represents a scheduling conflict between two schedules"""
    
    def __init__(self, schedule1: Schedule, schedule2: Schedule, conflict_type: str, details: str):
        self.schedule1 = schedule1
        self.schedule2 = schedule2
        self.conflict_type = conflict_type  # 'time_overlap', 'device_conflict', 'priority_conflict'
        self.details = details
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'schedule1_id': self.schedule1.id,
            'schedule1_name': self.schedule1.name,
            'schedule2_id': self.schedule2.id,
            'schedule2_name': self.schedule2.name,
            'conflict_type': self.conflict_type,
            'details': self.details
        }


def check_time_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
    """
    Check if two time ranges overlap
    Handles overnight schedules (e.g., 22:00 - 02:00)
    """
    def time_to_minutes(t: time) -> int:
        return t.hour * 60 + t.minute
    
    s1 = time_to_minutes(start1)
    e1 = time_to_minutes(end1)
    s2 = time_to_minutes(start2)
    e2 = time_to_minutes(end2)
    
    # Handle overnight schedules
    if e1 < s1:  # Schedule 1 crosses midnight
        e1 += 24 * 60
    if e2 < s2:  # Schedule 2 crosses midnight
        e2 += 24 * 60
    
    # Check for overlap
    return not (e1 <= s2 or e2 <= s1)


def get_schedule_conflicts(schedule: Schedule, check_date: Optional[date] = None) -> List[ScheduleConflict]:
    """
    Find all schedules that conflict with the given schedule
    
    Args:
        schedule: The schedule to check
        check_date: Optional specific date to check (default: today)
    
    Returns:
        List of ScheduleConflict objects
    """
    if check_date is None:
        check_date = date.today()
    
    conflicts = []
    
    # Build query for potentially conflicting schedules
    query = Schedule.query.filter(
        Schedule.id != schedule.id,
        Schedule.is_active == True
    )
    
    # Filter by date range
    query = query.filter(
        or_(
            Schedule.start_date == None,
            Schedule.start_date <= check_date
        ),
        or_(
            Schedule.end_date == None,
            Schedule.end_date >= check_date
        )
    )
    
    # Get all potentially conflicting schedules
    other_schedules = query.all()
    
    for other in other_schedules:
        # Check if schedules target the same device(s)
        targets_overlap = False
        
        if schedule.device_id and other.device_id:
            # Both target specific devices
            if schedule.device_id == other.device_id:
                targets_overlap = True
        elif schedule.device_group_id and other.device_group_id:
            # Both target specific groups
            if schedule.device_group_id == other.device_group_id:
                targets_overlap = True
        elif schedule.device_id and other.device_group_id:
            # Check if device is in the group
            device = Device.query.get(schedule.device_id)
            if device and device.group_id == other.device_group_id:
                targets_overlap = True
        elif schedule.device_group_id and other.device_id:
            # Check if device is in the group
            device = Device.query.get(other.device_id)
            if device and device.group_id == schedule.device_group_id:
                targets_overlap = True
        elif not schedule.device_id and not schedule.device_group_id:
            # Schedule applies to all devices
            targets_overlap = True
        elif not other.device_id and not other.device_group_id:
            # Other schedule applies to all devices
            targets_overlap = True
        
        if not targets_overlap:
            continue
        
        # Check if schedules are active on the same day of week
        if schedule.days_of_week and other.days_of_week:
            schedule_days = set(schedule.days_list)
            other_days = set(other.days_list)
            if not schedule_days.intersection(other_days):
                continue
        
        # Check for time overlap
        if check_time_overlap(schedule.start_time, schedule.end_time, 
                            other.start_time, other.end_time):
            conflict_type = 'time_overlap'
            details = f"Time ranges overlap: {schedule.start_time}-{schedule.end_time} vs {other.start_time}-{other.end_time}"
            
            if schedule.priority == other.priority:
                conflict_type = 'priority_conflict'
                details += f" (same priority: {schedule.priority})"
            
            conflicts.append(ScheduleConflict(schedule, other, conflict_type, details))
    
    return conflicts


def resolve_schedule_for_device(device_id: int, check_datetime: Optional[datetime] = None) -> Optional[Schedule]:
    """
    Determine which schedule should be active for a device at a given time
    Handles priority, exceptions, and conflict resolution
    
    Args:
        device_id: Device ID to check
        check_datetime: DateTime to check (default: now)
    
    Returns:
        Active Schedule object or None if no schedule is active
    """
    if check_datetime is None:
        check_datetime = datetime.now()
    
    check_date = check_datetime.date()
    check_time = check_datetime.time()
    
    device = Device.query.get(device_id)
    if not device:
        return None
    
    # Find all schedules that could apply to this device
    query = Schedule.query.filter(Schedule.is_active == True)
    
    # Filter by date range
    query = query.filter(
        or_(
            Schedule.start_date == None,
            Schedule.start_date <= check_date
        ),
        or_(
            Schedule.end_date == None,
            Schedule.end_date >= check_date
        )
    )
    
    # Filter by recurrence end date
    query = query.filter(
        or_(
            Schedule.recurrence_end_date == None,
            Schedule.recurrence_end_date >= check_date
        )
    )
    
    # Filter by device/group targeting
    query = query.filter(
        or_(
            Schedule.device_id == device_id,
            Schedule.device_group_id == device.group_id,
            and_(Schedule.device_id == None, Schedule.device_group_id == None)
        )
    )
    
    schedules = query.all()
    
    # Filter by day of week and time
    active_schedules = []
    for schedule in schedules:
        # Check if schedule is active on this date
        if not schedule.is_active_on_date(check_date):
            continue
        
        # Check for exceptions
        exception = ScheduleException.query.filter_by(
            schedule_id=schedule.id,
            exception_date=check_date
        ).first()
        
        if exception:
            if exception.exception_type == 'blackout':
                # Schedule is disabled on this date
                continue
            # Override handled later
        
        # Check if schedule is active at this time
        if schedule.is_all_day or schedule.is_active_at_time(check_time):
            active_schedules.append(schedule)
    
    if not active_schedules:
        return None
    
    # Sort by priority (highest first), then by ID for consistency
    active_schedules.sort(key=lambda s: (-s.priority, s.id))
    
    return active_schedules[0]


def generate_calendar_events(start_date: date, end_date: date, 
                            device_id: Optional[int] = None,
                            device_group_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Generate calendar events for FullCalendar.js
    
    Args:
        start_date: Start of date range
        end_date: End of date range
        device_id: Optional filter by device
        device_group_id: Optional filter by device group
    
    Returns:
        List of event dictionaries for FullCalendar
    """
    query = Schedule.query.filter(Schedule.is_active == True)
    
    # Filter by date range
    query = query.filter(
        or_(
            Schedule.start_date == None,
            Schedule.start_date <= end_date
        ),
        or_(
            Schedule.end_date == None,
            Schedule.end_date >= start_date
        )
    )
    
    # Filter by device/group if specified
    if device_id:
        query = query.filter(
            or_(
                Schedule.device_id == device_id,
                and_(Schedule.device_id == None, Schedule.device_group_id == None)
            )
        )
    elif device_group_id:
        query = query.filter(
            or_(
                Schedule.device_group_id == device_group_id,
                and_(Schedule.device_id == None, Schedule.device_group_id == None)
            )
        )
    
    schedules = query.all()
    events = []
    
    # Generate events for each schedule
    for schedule in schedules:
        # For recurring schedules, generate instances within date range
        if schedule.is_recurring and schedule.recurrence_type != 'none':
            events.extend(_generate_recurring_events(schedule, start_date, end_date))
        else:
            # One-time schedule
            event = _create_calendar_event(schedule, start_date)
            if event:
                events.append(event)
    
    return events


def _generate_recurring_events(schedule: Schedule, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """Generate calendar events for a recurring schedule"""
    events = []
    
    # Determine the actual start date for generation
    gen_start = schedule.start_date if schedule.start_date else start_date
    gen_start = max(gen_start, start_date)
    
    # Determine the end date for generation
    gen_end = end_date
    if schedule.end_date:
        gen_end = min(gen_end, schedule.end_date)
    if schedule.recurrence_end_date:
        gen_end = min(gen_end, schedule.recurrence_end_date)
    
    current = gen_start
    
    if schedule.recurrence_type == 'daily':
        # Generate daily events
        while current <= gen_end:
            if schedule.is_active_on_date(current):
                event = _create_calendar_event(schedule, current)
                if event:
                    events.append(event)
            current += timedelta(days=schedule.recurrence_interval)
    
    elif schedule.recurrence_type == 'weekly':
        # Generate weekly events based on days_of_week
        days_to_generate = schedule.days_list if schedule.days_of_week else list(range(7))
        
        # Start from the first occurrence
        while current <= gen_end:
            if current.weekday() in days_to_generate:
                event = _create_calendar_event(schedule, current)
                if event:
                    events.append(event)
            
            current += timedelta(days=1)
            
            # Jump to next week if we've passed Sunday
            if current.weekday() == 0 and schedule.recurrence_interval > 1:
                current += timedelta(weeks=schedule.recurrence_interval - 1)
    
    elif schedule.recurrence_type == 'monthly':
        # Generate monthly events on the same day of month
        target_day = gen_start.day
        
        while current <= gen_end:
            try:
                # Try to create date with same day of month
                check_date = date(current.year, current.month, target_day)
                if start_date <= check_date <= gen_end and schedule.is_active_on_date(check_date):
                    event = _create_calendar_event(schedule, check_date)
                    if event:
                        events.append(event)
            except ValueError:
                # Day doesn't exist in this month (e.g., Feb 30)
                pass
            
            # Move to next month
            month = current.month + schedule.recurrence_interval
            year = current.year
            while month > 12:
                month -= 12
                year += 1
            current = date(year, month, 1)
    
    elif schedule.recurrence_type == 'yearly':
        # Generate yearly events
        while current <= gen_end:
            if schedule.is_active_on_date(current):
                event = _create_calendar_event(schedule, current)
                if event:
                    events.append(event)
            
            # Move to next year
            try:
                current = date(current.year + schedule.recurrence_interval, current.month, current.day)
            except ValueError:
                # Handle leap year edge case (Feb 29)
                current = date(current.year + schedule.recurrence_interval, current.month, 28)
    
    return events


def _create_calendar_event(schedule: Schedule, event_date: date) -> Optional[Dict[str, Any]]:
    """Create a single calendar event dictionary"""
    
    # Check for exceptions
    exception = ScheduleException.query.filter_by(
        schedule_id=schedule.id,
        exception_date=event_date
    ).first()
    
    if exception and exception.exception_type == 'blackout':
        return None  # Don't show blackout dates
    
    # Create event
    if schedule.is_all_day:
        event = {
            'id': f"schedule_{schedule.id}_{event_date}",
            'title': schedule.name,
            'start': event_date.isoformat(),
            'allDay': True,
            'backgroundColor': schedule.color,
            'borderColor': schedule.color,
            'extendedProps': {
                'scheduleId': schedule.id,
                'contentType': schedule.content_type,
                'contentName': schedule.content_name,
                'target': schedule.target_description,
                'priority': schedule.priority,
                'hasException': exception is not None
            }
        }
    else:
        start_datetime = datetime.combine(event_date, schedule.start_time)
        end_datetime = datetime.combine(event_date, schedule.end_time)
        
        # Handle overnight schedules
        if schedule.end_time < schedule.start_time:
            end_datetime += timedelta(days=1)
        
        event = {
            'id': f"schedule_{schedule.id}_{event_date}",
            'title': schedule.name,
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'backgroundColor': schedule.color,
            'borderColor': schedule.color,
            'extendedProps': {
                'scheduleId': schedule.id,
                'contentType': schedule.content_type,
                'contentName': schedule.content_name,
                'target': schedule.target_description,
                'priority': schedule.priority,
                'hasException': exception is not None
            }
        }
    
    # Override title if there's an exception
    if exception and exception.exception_type == 'override':
        event['title'] = f"{schedule.name} (Override)"
        event['backgroundColor'] = '#ff9800'  # Orange for overrides
        event['borderColor'] = '#ff9800'
    
    return event


def get_schedule_preview(device_id: int, preview_date: date) -> List[Dict[str, Any]]:
    """
    Get a timeline preview of what will play on a device for a given date
    
    Args:
        device_id: Device ID
        preview_date: Date to preview
    
    Returns:
        List of time slots with schedule information
    """
    timeline = []
    
    # Create time slots for the day (every hour)
    for hour in range(24):
        check_time = time(hour, 0)
        check_datetime = datetime.combine(preview_date, check_time)
        
        active_schedule = resolve_schedule_for_device(device_id, check_datetime)
        
        slot = {
            'time': check_time.strftime('%H:%M'),
            'hour': hour,
            'schedule': None
        }
        
        if active_schedule:
            slot['schedule'] = {
                'id': active_schedule.id,
                'name': active_schedule.name,
                'content_type': active_schedule.content_type,
                'content_name': active_schedule.content_name,
                'priority': active_schedule.priority,
                'color': active_schedule.color
            }
        
        timeline.append(slot)
    
    return timeline
