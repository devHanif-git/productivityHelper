# AI module - Gemini integration
from .gemini_client import get_gemini_client, GeminiClient
from .image_parser import (
    parse_academic_calendar,
    parse_timetable,
    parse_assignment_image,
    detect_image_type,
    AcademicEvent,
    ScheduleSlot,
    AssignmentDetails,
)
