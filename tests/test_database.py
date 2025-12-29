"""Tests for database CRUD operations."""

import pytest
import os
import tempfile
from datetime import datetime, date

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.models import init_db, get_connection
from database.operations import DatabaseOperations


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize database schema
    init_db(path)

    # Create operations instance
    db = DatabaseOperations(path)

    yield db

    # Cleanup
    os.unlink(path)


class TestUserConfig:
    """Tests for user configuration operations."""

    def test_create_user_config(self, test_db):
        """Create new user config."""
        chat_id = 12345
        user_id = test_db.create_user_config(chat_id)
        assert user_id > 0

    def test_get_user_config(self, test_db):
        """Retrieve user config."""
        chat_id = 12345
        test_db.create_user_config(chat_id)

        config = test_db.get_user_config(chat_id)
        assert config is not None
        assert config["telegram_chat_id"] == chat_id

    def test_get_nonexistent_user(self, test_db):
        """Get nonexistent user returns None."""
        config = test_db.get_user_config(99999)
        assert config is None

    def test_update_user_config(self, test_db):
        """Update user config fields."""
        chat_id = 12345
        test_db.create_user_config(chat_id)

        test_db.update_user_config(chat_id, semester_start_date="2025-10-06")

        config = test_db.get_user_config(chat_id)
        assert config["semester_start_date"] == "2025-10-06"


class TestEvents:
    """Tests for academic events operations."""

    def test_add_event(self, test_db):
        """Add academic event."""
        event_id = test_db.add_event(
            event_type="holiday",
            name="Hari Deepavali",
            start_date="2025-10-20",
            affects_classes=True
        )
        assert event_id > 0

    def test_get_all_events(self, test_db):
        """Get all events."""
        test_db.add_event("holiday", "2025-10-20", name="Deepavali")
        test_db.add_event("break", "2025-11-15", name="Mid-sem Break", end_date="2025-11-23")

        events = test_db.get_all_events()
        assert len(events) == 2

    def test_get_event_on_date(self, test_db):
        """Get event affecting specific date."""
        test_db.add_event(
            event_type="holiday",
            name="Deepavali",
            start_date="2025-10-20",
            affects_classes=True
        )

        event = test_db.get_event_on_date("2025-10-20")
        assert event is not None
        assert event["name"] == "Deepavali"

    def test_clear_events(self, test_db):
        """Clear all events."""
        test_db.add_event("holiday", "2025-10-20")
        test_db.add_event("holiday", "2025-12-25")

        count = test_db.clear_events()
        assert count == 2

        events = test_db.get_all_events()
        assert len(events) == 0


class TestSchedule:
    """Tests for schedule operations."""

    def test_add_schedule_slot(self, test_db):
        """Add schedule slot."""
        slot_id = test_db.add_schedule_slot(
            day_of_week=0,  # Monday
            start_time="08:00",
            end_time="10:00",
            subject_code="BITP1113",
            subject_name="Programming",
            class_type="LEC",
            room="BK13",
            lecturer_name="Dr Zahriah"
        )
        assert slot_id > 0

    def test_get_schedule_for_day(self, test_db):
        """Get schedule for specific day."""
        test_db.add_schedule_slot(0, "08:00", "10:00", "BITP1113")
        test_db.add_schedule_slot(0, "10:00", "12:00", "BITI1213")
        test_db.add_schedule_slot(1, "14:00", "16:00", "BITM1113")

        monday_schedule = test_db.get_schedule_for_day(0)
        assert len(monday_schedule) == 2

        tuesday_schedule = test_db.get_schedule_for_day(1)
        assert len(tuesday_schedule) == 1

    def test_get_all_schedule(self, test_db):
        """Get entire weekly schedule."""
        test_db.add_schedule_slot(0, "08:00", "10:00", "BITP1113")
        test_db.add_schedule_slot(1, "14:00", "16:00", "BITM1113")

        schedule = test_db.get_all_schedule()
        assert len(schedule) == 2

    def test_clear_schedule(self, test_db):
        """Clear all schedule slots."""
        test_db.add_schedule_slot(0, "08:00", "10:00", "BITP1113")
        test_db.add_schedule_slot(1, "14:00", "16:00", "BITM1113")

        count = test_db.clear_schedule()
        assert count == 2


class TestAssignments:
    """Tests for assignment operations."""

    def test_add_assignment(self, test_db):
        """Add assignment."""
        assignment_id = test_db.add_assignment(
            title="Report BITP1113",
            due_date="2025-10-25T17:00:00",
            subject_code="BITP1113"
        )
        assert assignment_id > 0

    def test_get_pending_assignments(self, test_db):
        """Get incomplete assignments."""
        test_db.add_assignment("Report 1", "2025-10-25T17:00:00")
        test_db.add_assignment("Report 2", "2025-10-28T17:00:00")

        pending = test_db.get_pending_assignments()
        assert len(pending) == 2

    def test_complete_assignment(self, test_db):
        """Mark assignment as complete."""
        assignment_id = test_db.add_assignment("Report", "2025-10-25T17:00:00")

        test_db.complete_assignment(assignment_id)

        pending = test_db.get_pending_assignments()
        assert len(pending) == 0

    def test_get_assignment_by_id(self, test_db):
        """Get assignment by ID."""
        assignment_id = test_db.add_assignment("Report", "2025-10-25T17:00:00")

        assignment = test_db.get_assignment_by_id(assignment_id)
        assert assignment is not None
        assert assignment["title"] == "Report"

    def test_find_assignment_by_title(self, test_db):
        """Find assignment by partial title match."""
        test_db.add_assignment("Report BITP1113", "2025-10-25T17:00:00", subject_code="BITP1113")

        # Search by title
        result = test_db.find_assignment_by_title("BITP")
        assert result is not None
        assert "BITP" in result["title"]

    def test_update_reminder_level(self, test_db):
        """Update assignment reminder level."""
        assignment_id = test_db.add_assignment("Report", "2025-10-25T17:00:00")

        test_db.update_assignment_reminder_level(assignment_id, 3)

        assignment = test_db.get_assignment_by_id(assignment_id)
        assert assignment["last_reminder_level"] == 3


class TestTasks:
    """Tests for task operations."""

    def test_add_task(self, test_db):
        """Add task/meeting."""
        task_id = test_db.add_task(
            title="Meet Dr Intan",
            scheduled_date="2025-10-22",
            scheduled_time="10:00",
            location="FTK Office"
        )
        assert task_id > 0

    def test_get_upcoming_tasks(self, test_db):
        """Get tasks within date range."""
        today = datetime.now().date().isoformat()
        tomorrow = (datetime.now().date() + __import__('datetime').timedelta(days=1)).isoformat()

        test_db.add_task("Task 1", today)
        test_db.add_task("Task 2", tomorrow)

        tasks = test_db.get_upcoming_tasks(days=7)
        assert len(tasks) == 2

    def test_complete_task(self, test_db):
        """Mark task as complete."""
        task_id = test_db.add_task("Meeting", "2025-10-22")

        test_db.complete_task(task_id)

        task = test_db.get_task_by_id(task_id)
        assert task["is_completed"] == 1

    def test_get_task_by_id(self, test_db):
        """Get task by ID."""
        task_id = test_db.add_task("Meeting", "2025-10-22")

        task = test_db.get_task_by_id(task_id)
        assert task is not None
        assert task["title"] == "Meeting"

    def test_update_task_reminder(self, test_db):
        """Update task reminder flags."""
        task_id = test_db.add_task("Meeting", "2025-10-22")

        test_db.update_task_reminder(task_id, "1day")

        task = test_db.get_task_by_id(task_id)
        assert task["reminded_1day"] == 1


class TestTodos:
    """Tests for TODO operations."""

    def test_add_todo(self, test_db):
        """Add TODO item."""
        todo_id = test_db.add_todo("Buy groceries")
        assert todo_id > 0

    def test_add_todo_with_time(self, test_db):
        """Add TODO with scheduled time."""
        todo_id = test_db.add_todo(
            title="Pick up wife",
            scheduled_date="2025-10-22",
            scheduled_time="15:00"
        )

        todo = test_db.get_todo_by_id(todo_id)
        assert todo["scheduled_time"] == "15:00"

    def test_get_pending_todos(self, test_db):
        """Get incomplete TODOs."""
        test_db.add_todo("Task 1")
        test_db.add_todo("Task 2")

        todos = test_db.get_pending_todos()
        assert len(todos) == 2

    def test_get_todos_without_time(self, test_db):
        """Get TODOs without specific time."""
        test_db.add_todo("Floating task")
        test_db.add_todo("Timed task", scheduled_time="15:00")

        floating = test_db.get_todos_without_time()
        assert len(floating) == 1
        assert floating[0]["title"] == "Floating task"

    def test_complete_todo(self, test_db):
        """Mark TODO as complete."""
        todo_id = test_db.add_todo("Task")

        test_db.complete_todo(todo_id)

        pending = test_db.get_pending_todos()
        assert len(pending) == 0

    def test_get_todo_by_id(self, test_db):
        """Get TODO by ID."""
        todo_id = test_db.add_todo("Task")

        todo = test_db.get_todo_by_id(todo_id)
        assert todo is not None
        assert todo["title"] == "Task"

    def test_update_todo_reminder(self, test_db):
        """Mark TODO as reminded."""
        todo_id = test_db.add_todo("Task", scheduled_time="15:00")

        test_db.update_todo_reminder(todo_id)

        todo = test_db.get_todo_by_id(todo_id)
        assert todo["reminded"] == 1


class TestPendingCounts:
    """Tests for pending counts summary."""

    def test_get_pending_counts(self, test_db):
        """Get summary of all pending items."""
        # Add test data
        test_db.add_assignment("Assignment 1", "2025-10-25T17:00:00")
        test_db.add_assignment("Assignment 2", "2025-10-28T17:00:00")
        test_db.add_task("Task 1", "2025-10-22")
        test_db.add_todo("TODO 1")
        test_db.add_todo("TODO 2")
        test_db.add_todo("TODO 3")

        counts = test_db.get_pending_counts()
        assert counts["assignments"] == 2
        assert counts["tasks"] == 1
        assert counts["todos"] == 3

    def test_counts_exclude_completed(self, test_db):
        """Completed items not counted."""
        assignment_id = test_db.add_assignment("Assignment", "2025-10-25T17:00:00")
        test_db.complete_assignment(assignment_id)

        counts = test_db.get_pending_counts()
        assert counts["assignments"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
