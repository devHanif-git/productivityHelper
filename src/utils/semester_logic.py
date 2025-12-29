"""Semester week calculation and academic calendar logic."""

from datetime import date, datetime, timedelta
from typing import Optional, Union, Tuple

# Day name mappings for display
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_NAMES_MALAY = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"]

# Break type constants
BREAK_MID_SEMESTER = "mid_semester"
BREAK_INTER_SEMESTER = "inter_semester"


def classify_break_event(event: dict) -> str:
    """
    Classify a break event as mid-semester or inter-semester.

    Args:
        event: The event dict with 'name' and 'name_en' fields.

    Returns:
        'mid_semester' or 'inter_semester' based on event name.
    """
    name = (event.get("name") or "").lower()
    name_en = (event.get("name_en") or "").lower()

    # Check for mid-semester break keywords
    if "pertengahan" in name or "mid" in name_en:
        return BREAK_MID_SEMESTER

    # Check for inter-semester break keywords
    if "antara" in name or "inter" in name_en or "semester break" in name_en:
        return BREAK_INTER_SEMESTER

    # Default: assume inter-semester if it comes after mid-semester
    return BREAK_INTER_SEMESTER


def get_all_breaks(events: list[dict]) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Get mid-semester and inter-semester break events.

    Args:
        events: List of academic events.

    Returns:
        Tuple of (mid_semester_break, inter_semester_break) event dicts.
    """
    mid_break = None
    inter_break = None

    for event in events:
        if event.get("event_type") == "break":
            break_type = classify_break_event(event)
            if break_type == BREAK_MID_SEMESTER and mid_break is None:
                mid_break = event
            elif break_type == BREAK_INTER_SEMESTER and inter_break is None:
                inter_break = event

    return mid_break, inter_break


def get_current_break(today: date, events: list[dict]) -> Optional[dict]:
    """
    Get the current break event if today is in a break period.

    Args:
        today: The current date.
        events: List of academic events.

    Returns:
        The break event dict if in a break, None otherwise.
    """
    for event in events:
        if event.get("event_type") == "break":
            event_start = parse_date(event.get("start_date"))
            event_end = parse_date(event.get("end_date")) or event_start

            if event_start and event_start <= today <= event_end:
                return event

    return None


def is_semester_active(today: date, semester_start: date, events: list[dict]) -> bool:
    """
    Check if the semester is currently active (lectures happening).

    Args:
        today: The current date.
        semester_start: The start date of the semester.
        events: List of academic events.

    Returns:
        True if lectures should be happening, False if in break/before/after semester.
    """
    week = get_current_week(today, semester_start, events)
    return isinstance(week, int) and 1 <= week <= 14


def parse_date(date_str: str) -> Optional[date]:
    """Parse ISO date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None


def get_current_week(
    today: date,
    semester_start: date,
    events: list[dict]
) -> Union[int, str]:
    """
    Calculate the current week number of the semester.

    Semester structure:
    - Part 1: Week 1-6 (6 weeks from semester_start)
    - Mid-semester break: 1 week (not counted)
    - Part 2: Week 7-14 (8 weeks after break)
    - Inter-semester break: after Week 14

    Args:
        today: The current date.
        semester_start: The start date of the semester (first day of Week 1).
        events: List of academic events (breaks, holidays, etc.).

    Returns:
        Week number (1-14) or a string describing the current period
        (e.g., "Cuti Pertengahan Semester", "Cuti Antara Semester").
    """
    if today < semester_start:
        return "Before semester starts"

    # Calculate calendar week from semester start (1-indexed)
    days_elapsed = (today - semester_start).days
    calendar_week = (days_elapsed // 7) + 1

    # Get both types of breaks
    mid_break, inter_break = get_all_breaks(events)

    # Check if currently in inter-semester break
    if inter_break:
        inter_start = parse_date(inter_break.get("start_date"))
        inter_end = parse_date(inter_break.get("end_date")) or inter_start
        if inter_start and inter_start <= today <= inter_end:
            return inter_break.get("name_en") or inter_break.get("name") or "Inter-semester Break"

    # Check if currently in mid-semester break
    if mid_break:
        mid_start = parse_date(mid_break.get("start_date"))
        mid_end = parse_date(mid_break.get("end_date")) or mid_start
        if mid_start and mid_start <= today <= mid_end:
            return mid_break.get("name_en") or mid_break.get("name") or "Mid Semester Break"

    # Calculate lecture week
    # If we're past the mid-semester break, subtract 1 from calendar week
    lecture_week = calendar_week
    if mid_break:
        mid_end = parse_date(mid_break.get("end_date"))
        if mid_end and today > mid_end:
            lecture_week = calendar_week - 1

    # Check if past Week 14 (semester ended / inter-semester break)
    if lecture_week > 14:
        if inter_break:
            return inter_break.get("name_en") or inter_break.get("name") or "Inter-semester Break"
        return "Semester ended"

    return max(lecture_week, 1)


def get_next_week(
    today: date,
    semester_start: date,
    events: list[dict]
) -> Union[int, str]:
    """
    Get next week's number or period name.

    Args:
        today: The current date.
        semester_start: The start date of the semester.
        events: List of academic events.

    Returns:
        Next week number or period name.
    """
    next_week_date = today + timedelta(days=7)
    return get_current_week(next_week_date, semester_start, events)


def is_class_day(check_date: date, events: list[dict]) -> bool:
    """
    Check if a date has regular classes (not affected by holiday/break).

    Args:
        check_date: The date to check.
        events: List of academic events.

    Returns:
        True if regular classes happen, False if it's a holiday/off day.
    """
    # Saturday and Sunday are off by default (adjust if needed)
    if check_date.weekday() >= 5:
        return False

    for event in events:
        event_start = parse_date(event.get("start_date"))
        event_end = parse_date(event.get("end_date")) or event_start
        affects_classes = event.get("affects_classes", True)

        if event_start and affects_classes:
            if event_start <= check_date <= event_end:
                return False

    return True


def get_event_on_date(check_date: date, events: list[dict]) -> Optional[dict]:
    """
    Get the event affecting a specific date (if any).

    Args:
        check_date: The date to check.
        events: List of academic events.

    Returns:
        Event dict if found, None otherwise.
    """
    for event in events:
        event_start = parse_date(event.get("start_date"))
        event_end = parse_date(event.get("end_date")) or event_start
        affects_classes = event.get("affects_classes", True)

        if event_start and affects_classes:
            if event_start <= check_date <= event_end:
                return event

    return None


def get_affected_classes(
    check_date: date,
    schedule: list[dict],
    events: list[dict]
) -> list[dict]:
    """
    Get classes that would be affected (cancelled) on a given date.

    Args:
        check_date: The date to check.
        schedule: List of weekly schedule slots.
        events: List of academic events.

    Returns:
        List of schedule slots that would normally happen but are cancelled.
    """
    # First check if there's an event affecting classes
    event = get_event_on_date(check_date, events)
    if not event:
        return []

    # Get classes for this day of week
    day_of_week = check_date.weekday()
    affected = [
        slot for slot in schedule
        if slot.get("day_of_week") == day_of_week
    ]

    return affected


def get_next_offday(
    today: date,
    events: list[dict],
    days_ahead: int = 90
) -> Optional[dict]:
    """
    Find the next upcoming off day (holiday/break).

    Args:
        today: The current date.
        events: List of academic events.
        days_ahead: How many days ahead to search.

    Returns:
        Dict with 'date' and 'event' keys, or None if no off day found.
    """
    # Filter events that affect classes and are in the future
    future_events = []
    for event in events:
        event_start = parse_date(event.get("start_date"))
        affects_classes = event.get("affects_classes", True)

        if event_start and affects_classes and event_start > today:
            if (event_start - today).days <= days_ahead:
                future_events.append(event)

    if not future_events:
        return None

    # Sort by start date and return the nearest one
    future_events.sort(key=lambda e: e.get("start_date", ""))

    nearest = future_events[0]
    return {
        "date": parse_date(nearest.get("start_date")),
        "event": nearest
    }


def format_date(d: date, include_day: bool = True) -> str:
    """
    Format a date for display.

    Args:
        d: The date to format.
        include_day: Whether to include day name.

    Returns:
        Formatted date string like "Monday, 20 Oct 2025".
    """
    if include_day:
        day_name = DAY_NAMES[d.weekday()]
        return f"{day_name}, {d.strftime('%d %b %Y')}"
    return d.strftime("%d %b %Y")


def format_time(time_str: str) -> str:
    """
    Format a time string for display (convert 24h to 12h if needed).

    Args:
        time_str: Time in HH:MM format.

    Returns:
        Formatted time like "8:00AM" or "2:30PM".
    """
    try:
        hour, minute = map(int, time_str.split(":"))
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        if minute == 0:
            return f"{display_hour}{period}"
        return f"{display_hour}:{minute:02d}{period}"
    except (ValueError, AttributeError):
        return time_str


def get_tomorrow(today: date) -> date:
    """Get tomorrow's date."""
    return today + timedelta(days=1)


def days_until(target_date: date, from_date: Optional[date] = None) -> int:
    """
    Calculate days until a target date.

    Args:
        target_date: The target date.
        from_date: The date to calculate from (default: today).

    Returns:
        Number of days until target (negative if in past).
    """
    if from_date is None:
        from_date = date.today()
    return (target_date - from_date).days


def hours_until(target_datetime: datetime, from_datetime: Optional[datetime] = None) -> float:
    """
    Calculate hours until a target datetime.

    Args:
        target_datetime: The target datetime.
        from_datetime: The datetime to calculate from (default: now).

    Returns:
        Number of hours until target (negative if in past).
    """
    if from_datetime is None:
        from_datetime = datetime.now()
    delta = target_datetime - from_datetime
    return delta.total_seconds() / 3600
