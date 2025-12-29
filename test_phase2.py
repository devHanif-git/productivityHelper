"""Quick test script for Phase 2 components."""

import asyncio
import sys
from datetime import date, datetime

# Test 1: Import all modules
print("=" * 50)
print("TEST 1: Module Imports")
print("=" * 50)

try:
    from src.ai.gemini_client import get_gemini_client, GeminiClient
    print("[OK] gemini_client imported")
except Exception as e:
    print(f"[FAIL] gemini_client: {e}")
    sys.exit(1)

try:
    from src.ai.image_parser import (
        parse_academic_calendar,
        parse_timetable,
        parse_assignment_image,
        detect_image_type,
        AcademicEvent,
        ScheduleSlot,
        AssignmentDetails,
    )
    print("[OK] image_parser imported")
except Exception as e:
    print(f"[FAIL] image_parser: {e}")

try:
    from src.utils.semester_logic import (
        get_current_week,
        get_next_week,
        is_class_day,
        get_next_offday,
        format_date,
        format_time,
        days_until,
        hours_until,
    )
    print("[OK] semester_logic imported")
except Exception as e:
    print(f"[FAIL] semester_logic: {e}")

try:
    from src.config import config
    print("[OK] config imported")
except Exception as e:
    print(f"[FAIL] config: {e}")

try:
    from src.database.models import init_db
    from src.database.operations import DatabaseOperations
    print("[OK] database imported")
except Exception as e:
    print(f"[FAIL] database: {e}")


# Test 2: Semester Logic Functions
print("\n" + "=" * 50)
print("TEST 2: Semester Logic Functions")
print("=" * 50)

# Test format_date
today = date.today()
print(f"[OK] format_date(today): {format_date(today)}")

# Test format_time
print(f"[OK] format_time('08:00'): {format_time('08:00')}")
print(f"[OK] format_time('14:30'): {format_time('14:30')}")
print(f"[OK] format_time('00:00'): {format_time('00:00')}")

# Test days_until
future_date = date(2025, 2, 1)
print(f"[OK] days_until({future_date}): {days_until(future_date)}")

# Test get_current_week with sample data
semester_start = date(2024, 10, 7)  # Example: Oct 7, 2024
events = [
    {
        "event_type": "break",
        "name": "Cuti Pertengahan Semester",
        "start_date": "2024-11-18",
        "end_date": "2024-11-24",
        "affects_classes": True
    }
]
week = get_current_week(today, semester_start, events)
print(f"[OK] get_current_week (semester start {semester_start}): {week}")

# Test is_class_day
print(f"[OK] is_class_day(today, events): {is_class_day(today, events)}")


# Test 3: Gemini Client (requires API key)
print("\n" + "=" * 50)
print("TEST 3: Gemini Client")
print("=" * 50)

if config.GEMINI_API_KEY:
    print("[OK] GEMINI_API_KEY is set")

    async def test_gemini():
        try:
            client = get_gemini_client()
            response = await client.send_text("Say 'Hello, test successful!' in exactly those words.")
            if response:
                print(f"[OK] Gemini response: {response[:100]}...")
            else:
                print("[WARN] Gemini returned None (check API key)")
        except Exception as e:
            print(f"[FAIL] Gemini test: {e}")

    asyncio.run(test_gemini())
else:
    print("[SKIP] GEMINI_API_KEY not set - skipping Gemini test")


# Test 4: Data classes
print("\n" + "=" * 50)
print("TEST 4: Data Classes")
print("=" * 50)

event = AcademicEvent(
    event_type="holiday",
    name="Hari Raya",
    name_en="Eid",
    start_date="2025-03-31",
    end_date=None,
    affects_classes=True
)
print(f"[OK] AcademicEvent: {event}")

slot = ScheduleSlot(
    day_of_week=0,
    start_time="08:00",
    end_time="10:00",
    subject_code="BITP1113",
    subject_name="Programming",
    class_type="LEC",
    room="BK13",
    lecturer_name="Dr Zahriah"
)
print(f"[OK] ScheduleSlot: {slot}")

assignment = AssignmentDetails(
    title="Report 1",
    subject_code="BITP1113",
    description="Write a report",
    due_date="2025-02-15T17:00:00",
    requirements="PDF format"
)
print(f"[OK] AssignmentDetails: {assignment}")


# Test 5: Database
print("\n" + "=" * 50)
print("TEST 5: Database")
print("=" * 50)

try:
    import tempfile
    import os

    # Create a temp database for testing
    temp_db = os.path.join(tempfile.gettempdir(), "test_bot.db")
    init_db(temp_db)
    print(f"[OK] Database initialized at {temp_db}")

    db = DatabaseOperations(temp_db)

    # Test adding a todo
    todo_id = db.add_todo("Test todo item")
    print(f"[OK] Added todo with ID: {todo_id}")

    # Test getting todos
    todos = db.get_pending_todos()
    print(f"[OK] Retrieved {len(todos)} pending todos")

    # Clean up
    os.remove(temp_db)
    print("[OK] Test database cleaned up")
except Exception as e:
    print(f"[FAIL] Database test: {e}")


print("\n" + "=" * 50)
print("ALL TESTS COMPLETED")
print("=" * 50)
