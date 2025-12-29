"""Database CRUD operations for all tables."""

import sqlite3
from datetime import datetime
from typing import Optional
from .models import get_connection


class DatabaseOperations:
    """Database operations wrapper."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # ==================== User Config ====================

    def get_user_config(self, chat_id: int) -> Optional[dict]:
        """Get user configuration by Telegram chat ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM user_config WHERE telegram_chat_id = ?",
                (chat_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_user_config(self, chat_id: int) -> int:
        """Create a new user config. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO user_config (telegram_chat_id) VALUES (?)",
                (chat_id,)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_user_config(self, chat_id: int, **kwargs) -> bool:
        """Update user configuration fields."""
        if not kwargs:
            return False

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [chat_id]

        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE user_config SET {fields} WHERE telegram_chat_id = ?",
                values
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== Events ====================

    def add_event(
        self,
        event_type: str,
        start_date: str,
        name: str = None,
        name_en: str = None,
        end_date: str = None,
        affects_classes: bool = True
    ) -> int:
        """Add an academic event. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO events
                   (event_type, name, name_en, start_date, end_date, affects_classes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event_type, name, name_en, start_date, end_date, int(affects_classes))
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_events_in_range(self, start: str, end: str) -> list[dict]:
        """Get events within a date range."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE start_date <= ? AND (end_date >= ? OR end_date IS NULL)
                   ORDER BY start_date""",
                (end, start)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_event_on_date(self, date: str) -> Optional[dict]:
        """Get event affecting a specific date."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE start_date <= ? AND (end_date >= ? OR (end_date IS NULL AND start_date = ?))
                   AND affects_classes = 1
                   LIMIT 1""",
                (date, date, date)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def clear_events(self) -> int:
        """Clear all events. Returns number deleted."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM events")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ==================== Schedule ====================

    def add_schedule_slot(
        self,
        day_of_week: int,
        start_time: str,
        end_time: str,
        subject_code: str,
        subject_name: str = None,
        class_type: str = "LEC",
        room: str = None,
        lecturer_name: str = None
    ) -> int:
        """Add a schedule slot. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO schedule
                   (day_of_week, start_time, end_time, subject_code, subject_name,
                    class_type, room, lecturer_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (day_of_week, start_time, end_time, subject_code, subject_name,
                 class_type, room, lecturer_name)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_schedule_for_day(self, day_of_week: int) -> list[dict]:
        """Get all schedule slots for a day (0=Monday, 6=Sunday)."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM schedule
                   WHERE day_of_week = ?
                   ORDER BY start_time""",
                (day_of_week,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_schedule(self) -> list[dict]:
        """Get entire weekly schedule."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM schedule ORDER BY day_of_week, start_time"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def clear_schedule(self) -> int:
        """Clear all schedule slots. Returns number deleted."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM schedule")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ==================== Assignments ====================

    def add_assignment(
        self,
        title: str,
        due_date: str,
        subject_code: str = None,
        description: str = None
    ) -> int:
        """Add an assignment. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO assignments
                   (title, subject_code, description, due_date)
                   VALUES (?, ?, ?, ?)""",
                (title, subject_code, description, due_date)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_pending_assignments(self) -> list[dict]:
        """Get all incomplete assignments ordered by due date."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM assignments
                   WHERE is_completed = 0
                   ORDER BY due_date"""
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_assignments_due_soon(self, hours: int) -> list[dict]:
        """Get assignments due within specified hours."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """SELECT * FROM assignments
                   WHERE is_completed = 0
                   AND due_date <= datetime(?, '+' || ? || ' hours')
                   AND due_date >= ?
                   ORDER BY due_date""",
                (now, hours, now)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def complete_assignment(self, assignment_id: int) -> bool:
        """Mark an assignment as completed."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE assignments
                   SET is_completed = 1, completed_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), assignment_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_assignment_reminder_level(self, assignment_id: int, level: int) -> bool:
        """Update the last reminder level for an assignment."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE assignments SET last_reminder_level = ? WHERE id = ?",
                (level, assignment_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== Tasks ====================

    def add_task(
        self,
        title: str,
        scheduled_date: str,
        description: str = None,
        scheduled_time: str = None,
        location: str = None
    ) -> int:
        """Add a task/meeting. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO tasks
                   (title, description, scheduled_date, scheduled_time, location)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, description, scheduled_date, scheduled_time, location)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_upcoming_tasks(self, days: int = 7) -> list[dict]:
        """Get tasks scheduled within the next N days."""
        conn = self._get_conn()
        try:
            today = datetime.now().date().isoformat()
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE is_completed = 0
                   AND scheduled_date >= ?
                   AND scheduled_date <= date(?, '+' || ? || ' days')
                   ORDER BY scheduled_date, scheduled_time""",
                (today, today, days)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_tasks_for_date(self, date: str) -> list[dict]:
        """Get all tasks for a specific date."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE scheduled_date = ? AND is_completed = 0
                   ORDER BY scheduled_time""",
                (date,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE tasks
                   SET is_completed = 1, completed_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), task_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_task_reminder(self, task_id: int, reminder_type: str) -> bool:
        """Update task reminder flag (1day or 2hours)."""
        field = "reminded_1day" if reminder_type == "1day" else "reminded_2hours"
        conn = self._get_conn()
        try:
            conn.execute(f"UPDATE tasks SET {field} = 1 WHERE id = ?", (task_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== TODOs ====================

    def add_todo(
        self,
        title: str,
        scheduled_date: str = None,
        scheduled_time: str = None
    ) -> int:
        """Add a TODO item. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO todos
                   (title, scheduled_date, scheduled_time)
                   VALUES (?, ?, ?)""",
                (title, scheduled_date, scheduled_time)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_pending_todos(self) -> list[dict]:
        """Get all incomplete TODOs."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE is_completed = 0
                   ORDER BY scheduled_date, scheduled_time, created_at"""
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_todos_without_time(self) -> list[dict]:
        """Get TODOs without specific scheduled time (for midnight review)."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE is_completed = 0 AND scheduled_time IS NULL
                   ORDER BY scheduled_date, created_at"""
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_todos_for_date(self, date: str) -> list[dict]:
        """Get TODOs for a specific date."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE scheduled_date = ? AND is_completed = 0
                   ORDER BY scheduled_time, created_at""",
                (date,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def complete_todo(self, todo_id: int) -> bool:
        """Mark a TODO as completed."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE todos
                   SET is_completed = 1, completed_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), todo_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_todo_reminder(self, todo_id: int) -> bool:
        """Mark a TODO as reminded."""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE todos SET reminded = 1 WHERE id = ?", (todo_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== Lookup Methods ====================

    def get_assignment_by_id(self, assignment_id: int) -> Optional[dict]:
        """Get a specific assignment by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM assignments WHERE id = ?",
                (assignment_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_task_by_id(self, task_id: int) -> Optional[dict]:
        """Get a specific task by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_todo_by_id(self, todo_id: int) -> Optional[dict]:
        """Get a specific TODO by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM todos WHERE id = ?",
                (todo_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_events(self) -> list[dict]:
        """Get all academic events."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY start_date"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_assignment_by_title(self, search: str) -> Optional[dict]:
        """Find assignment by partial title or subject code match."""
        conn = self._get_conn()
        try:
            search_pattern = f"%{search}%"
            cursor = conn.execute(
                """SELECT * FROM assignments
                   WHERE is_completed = 0
                   AND (title LIKE ? OR subject_code LIKE ?)
                   ORDER BY due_date
                   LIMIT 1""",
                (search_pattern, search_pattern)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def find_task_by_title(self, search: str) -> Optional[dict]:
        """Find task by partial title match."""
        conn = self._get_conn()
        try:
            search_pattern = f"%{search}%"
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE is_completed = 0
                   AND title LIKE ?
                   ORDER BY scheduled_date
                   LIMIT 1""",
                (search_pattern,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def find_todo_by_title(self, search: str) -> Optional[dict]:
        """Find TODO by partial title match."""
        conn = self._get_conn()
        try:
            search_pattern = f"%{search}%"
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE is_completed = 0
                   AND title LIKE ?
                   ORDER BY created_at
                   LIMIT 1""",
                (search_pattern,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ==================== Stats ====================

    def get_pending_counts(self) -> dict:
        """Get counts of pending items for status display."""
        conn = self._get_conn()
        try:
            counts = {}

            cursor = conn.execute(
                "SELECT COUNT(*) FROM assignments WHERE is_completed = 0"
            )
            counts["assignments"] = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE is_completed = 0"
            )
            counts["tasks"] = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE is_completed = 0"
            )
            counts["todos"] = cursor.fetchone()[0]

            return counts
        finally:
            conn.close()
