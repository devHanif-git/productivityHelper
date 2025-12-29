"""Image parsing for academic calendars, timetables, and assignments."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


@dataclass
class AcademicEvent:
    """Represents an academic calendar event."""
    event_type: str  # 'holiday', 'break', 'exam', 'lecture_period', 'registration', 'pdp_online'
    name: str
    name_en: Optional[str]
    start_date: str  # ISO format YYYY-MM-DD
    end_date: Optional[str]  # ISO format YYYY-MM-DD
    affects_classes: bool


@dataclass
class ScheduleSlot:
    """Represents a class slot in the weekly timetable."""
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    subject_code: str
    subject_name: Optional[str]
    class_type: str  # 'LEC' or 'LAB'
    room: Optional[str]
    lecturer_name: Optional[str]


@dataclass
class AssignmentDetails:
    """Represents extracted assignment information."""
    title: str
    subject_code: Optional[str]
    description: Optional[str]
    due_date: Optional[str]  # ISO datetime format
    requirements: Optional[str]


def _clean_json_response(response: str) -> str:
    """Remove markdown code blocks and clean JSON response."""
    if not response:
        return ""

    # Remove markdown code blocks
    response = re.sub(r"```json\s*", "", response)
    response = re.sub(r"```\s*", "", response)
    response = response.strip()

    return response


def _parse_json_safely(response: str) -> Optional[list | dict]:
    """Safely parse JSON from Gemini response."""
    try:
        cleaned = _clean_json_response(response)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Raw response: {response}")
        return None


DAY_NAME_TO_NUMBER = {
    "monday": 0, "mon": 0, "isnin": 0,
    "tuesday": 1, "tue": 1, "selasa": 1,
    "wednesday": 2, "wed": 2, "rabu": 2,
    "thursday": 3, "thu": 3, "khamis": 3,
    "friday": 4, "fri": 4, "jumaat": 4,
    "saturday": 5, "sat": 5, "sabtu": 5,
    "sunday": 6, "sun": 6, "ahad": 6,
}


async def parse_academic_calendar(image_bytes: bytes) -> list[AcademicEvent]:
    """
    Parse an academic calendar image to extract events.

    Filters for Sarjana Muda (undergraduate) relevant items only.
    Excludes: Mesyuarat Senat, Mesyuarat Jawatankuasa, Latihan Industri, etc.

    Args:
        image_bytes: Raw bytes of the calendar image.

    Returns:
        List of AcademicEvent objects.
    """
    prompt = """Analyze this academic calendar image and extract all events relevant to undergraduate (Sarjana Muda) students.

INCLUDE these event types:
- Kuliah Semester / Lecture periods (Bahagian Pertama, Bahagian Kedua)
- Public holidays (Deepavali, Hari Krismas, Tahun Baharu, CNY, Hari Raya, etc.)
- Cuti Pertengahan Semester (Mid-semester break)
- Cuti Antara Semester (Semester break)
- Ujian Pertengahan Semester (Mid-semester test/exam)
- PDP Dalam Talian (Online learning days)
- Peperiksaan Akhir (Final examination)
- Cuti Ulang Kaji (Study leave/revision week)
- Pendaftaran Kursus (Course registration)

EXCLUDE these (staff/admin items, irrelevant to continuing students):
- Mesyuarat Senat
- Mesyuarat Jawatankuasa Tetap Senat
- Latihan Industri Pelajar
- Pendaftaran Lewat Berdenda Pelajar Kanan
- Keputusan Peperiksaan administrative items
- Any meeting or committee items
- Pendaftaran Pelajar Baharu (new student registration)
- Pendaftaran Kursus Pelajar Baharu (new student course registration)
- Minggu Harian Siswa (student activity week)
- Any items with "Pelajar Baharu" (new students only)

Return as JSON array with this structure:
[
  {
    "event_type": "holiday|break|exam|lecture_period|registration|pdp_online|study_leave",
    "name": "Original name in Malay",
    "name_en": "English translation if obvious, null otherwise",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD or null if single day",
    "affects_classes": true/false (does this cancel regular classes?)
  }
]

For affects_classes:
- holidays, breaks = true (no classes)
- lecture_period = false (classes happen during this)
- exam period = true (no regular lectures)
- pdp_online = true (online replaces physical classes)
- registration = false (doesn't affect classes)"""

    client = get_gemini_client()
    response = await client.send_image_with_json(image_bytes, prompt)
    if not response:
        logger.error("Failed to get response from Gemini for calendar parsing")
        return []

    data = _parse_json_safely(response)
    if not data or not isinstance(data, list):
        logger.error("Invalid calendar parsing response format")
        return []

    # Blocklist for events we don't want (filter at code level as backup)
    EVENT_BLOCKLIST = [
        "pelajar baharu",
        "harian siswa",
        "minggu harian",
        "pendaftaran pelajar baharu",
        "pendaftaran kursus pelajar baharu",
    ]

    events = []
    for item in data:
        # Check if event should be filtered out
        event_name = (item.get("name", "") + " " + (item.get("name_en") or "")).lower()
        if any(blocked in event_name for blocked in EVENT_BLOCKLIST):
            logger.info(f"Filtering out event: {item.get('name', 'Unknown')}")
            continue
        try:
            event = AcademicEvent(
                event_type=item.get("event_type", "unknown"),
                name=item.get("name", "Unknown Event"),
                name_en=item.get("name_en"),
                start_date=item.get("start_date", ""),
                end_date=item.get("end_date"),
                affects_classes=item.get("affects_classes", True)
            )
            events.append(event)
        except Exception as e:
            logger.warning(f"Failed to parse calendar event: {e}")
            continue

    logger.info(f"Parsed {len(events)} academic events from calendar image")
    return events


async def parse_timetable(image_bytes: bytes) -> list[ScheduleSlot]:
    """
    Parse a class timetable image to extract schedule slots.

    Args:
        image_bytes: Raw bytes of the timetable image.

    Returns:
        List of ScheduleSlot objects.
    """
    prompt = """Analyze this class timetable image and extract all class slots.

Extract for each class:
- Day of week (Monday-Sunday)
- Start time (HH:MM format, 24-hour)
- End time (HH:MM format, 24-hour)
- Subject code (e.g., BITP 1113, BITM1123)
- Subject name (if visible)
- Class type: LEC (lecture) or LAB (lab/tutorial/practical)
- Room/Location (e.g., BK13, BPA DK7)
- Lecturer name (e.g., Dr Zahriah, Dr Najwan)

Return as JSON array:
[
  {
    "day": "Monday",
    "start_time": "08:00",
    "end_time": "10:00",
    "subject_code": "BITP 1113",
    "subject_name": "Programming Fundamentals",
    "class_type": "LEC",
    "room": "BK13",
    "lecturer": "DR ZAHRIAH"
  }
]

Notes:
- Convert all times to 24-hour format
- Keep subject codes as shown (with or without space)
- For class_type: lectures are LEC, labs/tutorials/practicals are LAB
- If lecturer name not visible, use null
- If room not visible, use null"""

    client = get_gemini_client()
    response = await client.send_image_with_json(image_bytes, prompt)
    if not response:
        logger.error("Failed to get response from Gemini for timetable parsing")
        return []

    data = _parse_json_safely(response)
    if not data or not isinstance(data, list):
        logger.error("Invalid timetable parsing response format")
        return []

    slots = []
    for item in data:
        try:
            # Convert day name to number
            day_name = item.get("day", "").lower()
            day_of_week = DAY_NAME_TO_NUMBER.get(day_name, -1)
            if day_of_week == -1:
                logger.warning(f"Unknown day name: {day_name}")
                continue

            slot = ScheduleSlot(
                day_of_week=day_of_week,
                start_time=item.get("start_time", "00:00"),
                end_time=item.get("end_time", "00:00"),
                subject_code=item.get("subject_code", "UNKNOWN"),
                subject_name=item.get("subject_name"),
                class_type=item.get("class_type", "LEC").upper(),
                room=item.get("room"),
                lecturer_name=item.get("lecturer")
            )
            slots.append(slot)
        except Exception as e:
            logger.warning(f"Failed to parse timetable slot: {e}")
            continue

    logger.info(f"Parsed {len(slots)} schedule slots from timetable image")
    return slots


async def parse_assignment_image(image_bytes: bytes) -> Optional[AssignmentDetails]:
    """
    Parse an assignment sheet/photo to extract assignment details.

    Args:
        image_bytes: Raw bytes of the assignment image.

    Returns:
        AssignmentDetails object, or None if parsing failed.
    """
    prompt = """Analyze this assignment sheet/document image and extract the assignment details.

Extract:
- Title: The assignment/task title or name
- Subject code: Course/subject code if visible (e.g., BITP1113)
- Description: Brief description of what needs to be done
- Due date: Deadline in YYYY-MM-DD HH:MM format (use 23:59 if only date given)
- Requirements: Any specific requirements, submission format, etc.

Return as JSON object:
{
  "title": "Assignment title",
  "subject_code": "BITP1113 or null if not visible",
  "description": "Brief description of the task",
  "due_date": "2025-02-15 17:00 or null if not clear",
  "requirements": "Any specific requirements or null"
}

If the image is not an assignment document, return:
{"error": "Not an assignment document"}"""

    client = get_gemini_client()
    response = await client.send_image_with_json(image_bytes, prompt)
    if not response:
        logger.error("Failed to get response from Gemini for assignment parsing")
        return None

    data = _parse_json_safely(response)
    if not data or not isinstance(data, dict):
        logger.error("Invalid assignment parsing response format")
        return None

    if "error" in data:
        logger.info(f"Assignment parsing: {data['error']}")
        return None

    try:
        # Parse due_date to proper ISO format if present
        due_date = data.get("due_date")
        if due_date:
            # Try to normalize the date format
            try:
                dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                due_date = dt.isoformat()
            except ValueError:
                try:
                    dt = datetime.strptime(due_date, "%Y-%m-%d")
                    due_date = dt.replace(hour=23, minute=59).isoformat()
                except ValueError:
                    pass  # Keep as-is

        return AssignmentDetails(
            title=data.get("title", "Untitled Assignment"),
            subject_code=data.get("subject_code"),
            description=data.get("description"),
            due_date=due_date,
            requirements=data.get("requirements")
        )
    except Exception as e:
        logger.error(f"Failed to create AssignmentDetails: {e}")
        return None


async def detect_image_type(image_bytes: bytes) -> str:
    """
    Detect the type of academic image.

    Args:
        image_bytes: Raw bytes of the image.

    Returns:
        One of: 'calendar', 'timetable', 'assignment', 'unknown'
    """
    prompt = """Analyze this image and determine what type of academic document it is.

Types:
- "calendar": An academic calendar showing semester dates, holidays, exam periods
- "timetable": A class schedule/timetable showing weekly classes with times and rooms
- "assignment": An assignment sheet, homework, or task document with due date
- "unknown": Cannot determine or not an academic document

Return ONLY one word: calendar, timetable, assignment, or unknown"""

    client = get_gemini_client()
    response = await client.send_image(image_bytes, prompt)
    if not response:
        return "unknown"

    result = response.strip().lower()
    if result in ["calendar", "timetable", "assignment"]:
        return result
    return "unknown"
