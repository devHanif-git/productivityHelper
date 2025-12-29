"""Natural language intent classification and entity extraction."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Optional

from .gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class Intent(Enum):
    """All supported user intents."""

    # Assignments
    ADD_ASSIGNMENT = "add_assignment"
    QUERY_ASSIGNMENTS = "query_assignments"
    COMPLETE_ASSIGNMENT = "complete_assignment"

    # Tasks/Meetings
    ADD_TASK = "add_task"
    QUERY_TASKS = "query_tasks"
    COMPLETE_TASK = "complete_task"

    # TODOs
    ADD_TODO = "add_todo"
    QUERY_TODOS = "query_todos"
    COMPLETE_TODO = "complete_todo"

    # Schedule Queries
    QUERY_TODAY_CLASSES = "query_today"
    QUERY_TOMORROW_CLASSES = "query_tomorrow"
    QUERY_WEEK_CLASSES = "query_week"
    QUERY_SUBJECT_SCHEDULE = "query_subject"

    # Academic Calendar Queries
    QUERY_CURRENT_WEEK = "query_current_week"
    QUERY_NEXT_WEEK = "query_next_week"
    QUERY_NEXT_OFFDAY = "query_next_offday"
    QUERY_MIDTERM_BREAK = "query_midterm_break"
    QUERY_FINAL_EXAM = "query_final_exam"
    QUERY_MIDTERM_EXAM = "query_midterm_exam"
    QUERY_SEMESTER_DATES = "query_semester"

    # Editing
    EDIT_SCHEDULE = "edit_schedule"
    EDIT_ASSIGNMENT = "edit_assignment"

    # Online Mode
    SET_ONLINE = "set_online"
    QUERY_ONLINE = "query_online"

    # Image Upload
    UPLOAD_ASSIGNMENT_IMAGE = "upload_assignment"

    # General
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"


@dataclass
class ParsedEntities:
    """Extracted entities from user message."""

    # Common entities
    title: Optional[str] = None
    description: Optional[str] = None

    # Date/Time entities
    date: Optional[str] = None  # YYYY-MM-DD format
    time: Optional[str] = None  # HH:MM format
    due_date: Optional[str] = None  # ISO datetime for assignments

    # Academic entities
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None

    # Location/Person entities
    location: Optional[str] = None
    person_name: Optional[str] = None

    # Identifiers
    item_id: Optional[int] = None
    item_type: Optional[str] = None  # 'assignment', 'task', 'todo'

    # Raw extracted data
    raw: dict = field(default_factory=dict)


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    intent: Intent
    entities: ParsedEntities
    confidence: float = 0.0


def _clean_json_response(response: str) -> str:
    """Remove markdown code blocks and clean JSON response."""
    if not response:
        return ""
    response = re.sub(r"```json\s*", "", response)
    response = re.sub(r"```\s*", "", response)
    return response.strip()


def _parse_relative_date(date_str: str) -> Optional[str]:
    """Parse relative date expressions to ISO format."""
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    today = date.today()

    # Direct mappings
    if date_str in ("today", "hari ini"):
        return today.isoformat()
    elif date_str in ("tomorrow", "esok"):
        return (today + timedelta(days=1)).isoformat()
    elif date_str in ("day after tomorrow", "lusa"):
        return (today + timedelta(days=2)).isoformat()

    # This Friday, next Monday, etc.
    day_names = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
        "isnin": 0, "selasa": 1, "rabu": 2, "khamis": 3,
        "jumaat": 4, "sabtu": 5, "ahad": 6
    }

    for day_name, day_num in day_names.items():
        if day_name in date_str:
            days_ahead = day_num - today.weekday()
            if "next" in date_str or days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).isoformat()

    # Try ISO format
    try:
        return datetime.fromisoformat(date_str).date().isoformat()
    except ValueError:
        pass

    # Try common date formats
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue

    return date_str  # Return as-is if can't parse


def _parse_time(time_str: str) -> Optional[str]:
    """Parse time string to HH:MM format."""
    if not time_str:
        return None

    time_str = time_str.lower().strip()

    # Handle 12-hour format with AM/PM
    am_pm_pattern = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
    match = re.search(am_pm_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    # Handle 24-hour format
    time_pattern = r"(\d{1,2}):(\d{2})"
    match = re.search(time_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return f"{hour:02d}:{minute:02d}"

    return None


INTENT_CLASSIFICATION_PROMPT = """Analyze this user message and classify the intent.

Message: "{message}"

Available intents:
- add_assignment: User wants to add/create an academic assignment with a due date
- query_assignments: User asks about pending assignments
- complete_assignment: User marks an assignment as done/completed

- add_task: User wants to add a meeting or scheduled appointment
- query_tasks: User asks about upcoming tasks/meetings
- complete_task: User marks a task/meeting as done

- add_todo: User wants to add a quick personal task/reminder
- query_todos: User asks about pending TODOs
- complete_todo: User marks a TODO as done

- query_tomorrow: User asks about tomorrow's classes
- query_week: User asks about this week's schedule
- query_subject: User asks about a specific subject's schedule

- query_current_week: User asks what week of semester it is
- query_next_week: User asks about next week
- query_next_offday: User asks about next holiday/off day
- query_semester: User asks about semester dates

- general_chat: General conversation, greetings, thanks, etc.
- unknown: Cannot determine intent

Return ONLY a JSON object with this structure:
{{
  "intent": "the_intent_name",
  "confidence": 0.0-1.0,
  "entities": {{
    "title": "extracted title/name if any",
    "description": "extracted description if any",
    "date": "extracted date (YYYY-MM-DD or relative like 'tomorrow', 'Friday')",
    "time": "extracted time if any (HH:MM or '5pm')",
    "due_date": "for assignments, the full due date with time",
    "subject_code": "extracted subject code like BITP1113",
    "location": "extracted location/room if any",
    "person_name": "extracted person name if any (like 'Dr Intan')",
    "item_id": null,
    "item_type": null
  }}
}}

Examples:
- "I have assignment report for BITP1113 due Friday 5pm" → add_assignment, title="report", subject_code="BITP1113", date="Friday", time="5pm"
- "What assignments pending?" → query_assignments
- "Done with BITP report" → complete_assignment, title="BITP report"
- "Meet Dr Intan tomorrow 10am" → add_task, person_name="Dr Intan", date="tomorrow", time="10am"
- "What class tomorrow?" → query_tomorrow
- "What week is this?" → query_current_week
- "Take wife at Satria at 3pm" → add_todo, title="Take wife at Satria", time="3pm"
- "Thanks!" → general_chat
"""


async def classify_message(message: str) -> ClassificationResult:
    """
    Classify user message intent and extract entities.

    Args:
        message: The user's text message.

    Returns:
        ClassificationResult with intent and extracted entities.
    """
    # Quick pattern matching for common queries
    message_lower = message.lower().strip()

    # Week queries
    if re.search(r"(what|which)\s+week\s+(is\s+)?(this|now)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_CURRENT_WEEK,
            entities=ParsedEntities(),
            confidence=0.95
        )

    if re.search(r"(what|which)\s+week\s+(is\s+)?next", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_NEXT_WEEK,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Class queries - Tomorrow
    if re.search(r"(what|any)\s+(class|classes)\s+tomorrow", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TOMORROW_CLASSES,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Class queries - Today (English and Malay)
    if re.search(r"(what|any)\s+(class|classes|is\s+my\s+schedule)\s+today", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TODAY_CLASSES,
            entities=ParsedEntities(),
            confidence=0.95
        )
    if re.search(r"(do\s+i\s+have|ada)\s+(class|classes|kelas)\s+today", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TODAY_CLASSES,
            entities=ParsedEntities(),
            confidence=0.95
        )
    if re.search(r"kelas\s+(hari\s+)?ini", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TODAY_CLASSES,
            entities=ParsedEntities(),
            confidence=0.95
        )
    if re.search(r"jadual\s+hari\s+ini", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TODAY_CLASSES,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Midterm break query (English and Malay)
    if re.search(r"(when|bila).*(mid\s*term\s*break|cuti\s*pertengahan|mid\s*semester\s*break)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_MIDTERM_BREAK,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Final exam query (English and Malay)
    if re.search(r"(when|bila).*(final\s*exam|peperiksaan\s*akhir|final\s*test)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_FINAL_EXAM,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Midterm exam query (English and Malay)
    if re.search(r"(when|bila).*(mid\s*term\s*exam|ujian\s*pertengahan|mid\s*semester\s*exam|mid\s*term\s*test)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_MIDTERM_EXAM,
            entities=ParsedEntities(),
            confidence=0.95
        )

    # Edit schedule patterns (e.g., "change BITP1113 room to BK12", "update class room")
    edit_schedule_match = re.search(
        r"(change|update|edit|tukar)\s+(\w+)\s*(class|kelas)?\s*(room|bilik|lecturer|pensyarah)\s+(to|ke|kepada)\s+(.+)",
        message_lower
    )
    if edit_schedule_match:
        subject = edit_schedule_match.group(2).upper()
        field = edit_schedule_match.group(4)
        new_value = edit_schedule_match.group(6).strip()
        return ClassificationResult(
            intent=Intent.EDIT_SCHEDULE,
            entities=ParsedEntities(subject_code=subject, title=new_value),
            confidence=0.90
        )

    # Edit assignment patterns (e.g., "update assignment 1 due to Friday")
    edit_assignment_match = re.search(
        r"(change|update|edit|tukar)\s+assignment\s+(\d+)\s+(due|title|tajuk)\s+(to|ke|kepada)\s+(.+)",
        message_lower
    )
    if edit_assignment_match:
        item_id = int(edit_assignment_match.group(2))
        field = edit_assignment_match.group(3)
        new_value = edit_assignment_match.group(5).strip()
        return ClassificationResult(
            intent=Intent.EDIT_ASSIGNMENT,
            entities=ParsedEntities(item_id=item_id, title=new_value),
            confidence=0.90
        )

    # Set online patterns (e.g., "set class BITP1113 online on week 12")
    set_online_match = re.search(
        r"set\s+(class\s+)?(\w+|all)\s+online\s+(on\s+|for\s+)?(week\s*\d+|tomorrow|today|\d{4}-\d{2}-\d{2})",
        message_lower
    )
    if set_online_match:
        subject = set_online_match.group(2).upper()
        time_part = set_online_match.group(4)
        return ClassificationResult(
            intent=Intent.SET_ONLINE,
            entities=ParsedEntities(subject_code=subject, title=time_part),
            confidence=0.90
        )

    # Query online patterns
    if re.search(r"(what|which|show).*(online|dalam\s*talian)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_ONLINE,
            entities=ParsedEntities(),
            confidence=0.90
        )

    # Assignment queries
    if re.search(r"(what|show|list).*(assignment|assignments)\s*(pending|due)?", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_ASSIGNMENTS,
            entities=ParsedEntities(),
            confidence=0.90
        )

    # TODO queries
    if re.search(r"(what|show|list).*(todo|todos|to-do)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TODOS,
            entities=ParsedEntities(),
            confidence=0.90
        )

    # Task queries
    if re.search(r"(what|show|list).*(task|tasks|meeting)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_TASKS,
            entities=ParsedEntities(),
            confidence=0.90
        )

    # Off day query
    if re.search(r"(when|next).*(off\s*day|holiday|cuti)", message_lower):
        return ClassificationResult(
            intent=Intent.QUERY_NEXT_OFFDAY,
            entities=ParsedEntities(),
            confidence=0.90
        )

    # For complex messages, use Gemini
    client = get_gemini_client()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)

    response = await client.send_text(prompt)
    if not response:
        logger.warning("Failed to get intent classification from Gemini")
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            entities=ParsedEntities(),
            confidence=0.0
        )

    try:
        cleaned = _clean_json_response(response)
        data = json.loads(cleaned)

        # Parse intent
        intent_str = data.get("intent", "unknown")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        # Parse entities
        entities_data = data.get("entities", {})
        entities = ParsedEntities(
            title=entities_data.get("title"),
            description=entities_data.get("description"),
            date=_parse_relative_date(entities_data.get("date")),
            time=_parse_time(entities_data.get("time")),
            due_date=entities_data.get("due_date"),
            subject_code=entities_data.get("subject_code"),
            location=entities_data.get("location"),
            person_name=entities_data.get("person_name"),
            item_id=entities_data.get("item_id"),
            item_type=entities_data.get("item_type"),
            raw=entities_data
        )

        confidence = data.get("confidence", 0.5)

        return ClassificationResult(
            intent=intent,
            entities=entities,
            confidence=confidence
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse intent classification response: {e}")
        return ClassificationResult(
            intent=Intent.UNKNOWN,
            entities=ParsedEntities(),
            confidence=0.0
        )


async def extract_completion_target(
    message: str,
    pending_items: dict[str, list[dict]]
) -> Optional[tuple[str, dict]]:
    """
    Extract which item the user wants to mark as complete.

    Args:
        message: The user's message (e.g., "Done with BITP report")
        pending_items: Dict with 'assignments', 'tasks', 'todos' lists

    Returns:
        Tuple of (item_type, item_dict) or None if no match found.
    """
    message_lower = message.lower()

    # Build context of pending items for Gemini
    items_context = []

    for assignment in pending_items.get("assignments", []):
        items_context.append(
            f"assignment:{assignment['id']}:{assignment['title']} ({assignment.get('subject_code', 'no code')})"
        )

    for task in pending_items.get("tasks", []):
        items_context.append(
            f"task:{task['id']}:{task['title']}"
        )

    for todo in pending_items.get("todos", []):
        items_context.append(
            f"todo:{todo['id']}:{todo['title']}"
        )

    if not items_context:
        return None

    prompt = f"""The user said: "{message}"

They want to mark something as complete. Here are their pending items:
{chr(10).join(items_context)}

Which item are they referring to? Match based on keywords, subject codes, or descriptions.

Return ONLY JSON: {{"type": "assignment|task|todo", "id": 123}} or {{"match": null}} if no clear match."""

    client = get_gemini_client()
    response = await client.send_text(prompt)

    if not response:
        return None

    try:
        cleaned = _clean_json_response(response)
        data = json.loads(cleaned)

        # Check if Gemini found a match (returns type+id) or no match (returns match:null)
        if data.get("match") is None and data.get("type") is None:
            return None

        if data.get("type") is None or data.get("id") is None:
            return None

        item_type = data.get("type")
        item_id = data.get("id")

        # Find the actual item
        if item_type == "assignment":
            for item in pending_items.get("assignments", []):
                if item["id"] == item_id:
                    return ("assignment", item)
        elif item_type == "task":
            for item in pending_items.get("tasks", []):
                if item["id"] == item_id:
                    return ("task", item)
        elif item_type == "todo":
            for item in pending_items.get("todos", []):
                if item["id"] == item_id:
                    return ("todo", item)

        return None

    except (json.JSONDecodeError, KeyError):
        return None


def build_assignment_from_entities(entities: ParsedEntities) -> dict:
    """Build assignment data dict from parsed entities."""
    # Construct due_date from date and time
    due_date = entities.due_date
    if not due_date and entities.date:
        due_date = entities.date
        if entities.time:
            due_date = f"{entities.date}T{entities.time}:00"
        else:
            due_date = f"{entities.date}T23:59:00"

    return {
        "title": entities.title or "Untitled Assignment",
        "subject_code": entities.subject_code,
        "description": entities.description,
        "due_date": due_date
    }


def build_task_from_entities(entities: ParsedEntities) -> dict:
    """Build task data dict from parsed entities."""
    # Construct title from person name if available
    title = entities.title
    if not title and entities.person_name:
        title = f"Meet {entities.person_name}"

    return {
        "title": title or "Untitled Task",
        "description": entities.description,
        "scheduled_date": entities.date,
        "scheduled_time": entities.time,
        "location": entities.location
    }


def build_todo_from_entities(entities: ParsedEntities) -> dict:
    """Build todo data dict from parsed entities."""
    return {
        "title": entities.title or "Untitled TODO",
        "scheduled_date": entities.date,
        "scheduled_time": entities.time
    }
