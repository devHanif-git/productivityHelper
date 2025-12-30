"""Database CRUD operations for all tables."""

import json
import sqlite3
from datetime import datetime, timedelta
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

    def get_schedule_by_id(self, slot_id: int) -> Optional[dict]:
        """Get a specific schedule slot by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM schedule WHERE id = ?",
                (slot_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_schedule_by_subject(self, search: str) -> list[dict]:
        """
        Find schedule slots by subject code OR subject name (fuzzy match).
        Returns all matching slots (could be multiple for same subject on different days).
        """
        conn = self._get_conn()
        try:
            search_upper = search.upper()
            search_pattern = f"%{search}%"
            cursor = conn.execute(
                """SELECT * FROM schedule
                   WHERE subject_code LIKE ? OR subject_name LIKE ?
                   ORDER BY day_of_week, start_time""",
                (search_pattern, search_pattern)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_subject_aliases(self) -> dict:
        """
        Build a mapping of subject name aliases to subject codes.
        Returns dict like {"database design": "BITI1113", "programming": "BITP1113"}
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT DISTINCT subject_code, subject_name FROM schedule"
            )
            aliases = {}
            for row in cursor.fetchall():
                code = row["subject_code"]
                name = row["subject_name"]
                if code:
                    aliases[code.lower()] = code
                if name:
                    # Add full name and common abbreviations
                    aliases[name.lower()] = code
                    # Add first letters as alias (e.g., "dbd" for "Database Design")
                    words = name.split()
                    if len(words) > 1:
                        abbrev = "".join(w[0].lower() for w in words if w)
                        aliases[abbrev] = code
            return aliases
        finally:
            conn.close()

    def update_schedule_slot(
        self,
        slot_id: int,
        room: str = None,
        lecturer_name: str = None,
        subject_name: str = None
    ) -> bool:
        """Update a schedule slot. Only updates non-None fields."""
        conn = self._get_conn()
        try:
            updates = []
            params = []
            if room is not None:
                updates.append("room = ?")
                params.append(room)
            if lecturer_name is not None:
                updates.append("lecturer_name = ?")
                params.append(lecturer_name)
            if subject_name is not None:
                updates.append("subject_name = ?")
                params.append(subject_name)

            if not updates:
                return False

            params.append(slot_id)
            query = f"UPDATE schedule SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, tuple(params))
            conn.commit()
            return True
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

    def update_assignment(
        self,
        assignment_id: int,
        title: str = None,
        due_date: str = None,
        subject_code: str = None,
        description: str = None
    ) -> bool:
        """Update an assignment. Only updates non-None fields."""
        conn = self._get_conn()
        try:
            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if due_date is not None:
                updates.append("due_date = ?")
                params.append(due_date)
            if subject_code is not None:
                updates.append("subject_code = ?")
                params.append(subject_code)
            if description is not None:
                updates.append("description = ?")
                params.append(description)

            if not updates:
                return False

            params.append(assignment_id)
            query = f"UPDATE assignments SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, tuple(params))
            conn.commit()
            return True
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

    # ==================== Online Overrides ====================

    def add_online_override(
        self,
        subject_code: str = None,
        week_number: int = None,
        specific_date: str = None
    ) -> int:
        """
        Add an online override. Returns the new ID.
        - subject_code=None means ALL classes
        - Either week_number OR specific_date should be set
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO online_overrides
                   (subject_code, week_number, specific_date)
                   VALUES (?, ?, ?)""",
                (subject_code, week_number, specific_date)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_online_overrides(self) -> list[dict]:
        """Get all online overrides."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM online_overrides ORDER BY week_number, specific_date"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def is_class_online(
        self,
        subject_code: str,
        check_date: str = None,
        week_number: int = None
    ) -> bool:
        """Check if a class is online for a given date or week."""
        conn = self._get_conn()
        try:
            # Check subject-specific overrides
            if check_date:
                cursor = conn.execute(
                    """SELECT COUNT(*) FROM online_overrides
                       WHERE (subject_code = ? OR subject_code IS NULL)
                       AND specific_date = ?""",
                    (subject_code, check_date)
                )
                if cursor.fetchone()[0] > 0:
                    return True

            if week_number:
                cursor = conn.execute(
                    """SELECT COUNT(*) FROM online_overrides
                       WHERE (subject_code = ? OR subject_code IS NULL)
                       AND week_number = ?""",
                    (subject_code, week_number)
                )
                if cursor.fetchone()[0] > 0:
                    return True

            return False
        finally:
            conn.close()

    def get_next_online_week(self) -> Optional[dict]:
        """Get the next online override (week-based)."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM online_overrides
                   WHERE week_number IS NOT NULL
                   ORDER BY week_number
                   LIMIT 1"""
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_online_override(self, override_id: int) -> bool:
        """Delete an online override."""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM online_overrides WHERE id = ?",
                (override_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== Exam Events ====================

    def add_exam(
        self,
        subject_code: str,
        exam_type: str,
        exam_date: str,
        exam_time: str = None,
        name: str = None
    ) -> int:
        """Add an exam event for a subject. Returns the new ID."""
        event_type = "exam"
        name = name or f"{exam_type.title()} Exam - {subject_code}"
        name_en = name

        conn = self._get_conn()
        try:
            # Store time in name_en if provided
            if exam_time:
                name_en = f"{name} at {exam_time}"

            cursor = conn.execute(
                """INSERT INTO events
                   (event_type, name, name_en, start_date, subject_code, affects_classes)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (event_type, name, name_en, exam_date, subject_code)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_upcoming_exams(self, from_date: str = None) -> list[dict]:
        """Get all upcoming exams."""
        conn = self._get_conn()
        try:
            if from_date is None:
                from_date = datetime.now().date().isoformat()

            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE event_type = 'exam'
                   AND start_date >= ?
                   ORDER BY start_date""",
                (from_date,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_exams_for_subject(self, subject_code: str) -> list[dict]:
        """Get all exams for a specific subject."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE event_type = 'exam'
                   AND subject_code = ?
                   ORDER BY start_date""",
                (subject_code,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== Delete Operations ====================

    def delete_assignment(self, assignment_id: int) -> Optional[dict]:
        """Delete an assignment. Returns the deleted item or None."""
        conn = self._get_conn()
        try:
            # Get the item first for undo support
            cursor = conn.execute(
                "SELECT * FROM assignments WHERE id = ?",
                (assignment_id,)
            )
            item = cursor.fetchone()
            if not item:
                return None

            item_dict = dict(item)
            conn.execute(
                "DELETE FROM assignments WHERE id = ?",
                (assignment_id,)
            )
            conn.commit()
            return item_dict
        finally:
            conn.close()

    def delete_task(self, task_id: int) -> Optional[dict]:
        """Delete a task. Returns the deleted item or None."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            )
            item = cursor.fetchone()
            if not item:
                return None

            item_dict = dict(item)
            conn.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,)
            )
            conn.commit()
            return item_dict
        finally:
            conn.close()

    def delete_todo(self, todo_id: int) -> Optional[dict]:
        """Delete a TODO. Returns the deleted item or None."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM todos WHERE id = ?",
                (todo_id,)
            )
            item = cursor.fetchone()
            if not item:
                return None

            item_dict = dict(item)
            conn.execute(
                "DELETE FROM todos WHERE id = ?",
                (todo_id,)
            )
            conn.commit()
            return item_dict
        finally:
            conn.close()

    def delete_event(self, event_id: int) -> Optional[dict]:
        """Delete an event. Returns the deleted item or None."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,)
            )
            item = cursor.fetchone()
            if not item:
                return None

            item_dict = dict(item)
            conn.execute(
                "DELETE FROM events WHERE id = ?",
                (event_id,)
            )
            conn.commit()
            return item_dict
        finally:
            conn.close()

    # ==================== Action History (Undo) ====================

    def add_action_history(
        self,
        action_type: str,
        table_name: str,
        item_id: int,
        old_data: str = None,
        new_data: str = None
    ) -> int:
        """Record an action for undo functionality."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO action_history
                   (action_type, table_name, item_id, old_data, new_data)
                   VALUES (?, ?, ?, ?, ?)""",
                (action_type, table_name, item_id, old_data, new_data)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_last_action(self, chat_id: int = None) -> Optional[dict]:
        """Get the most recent action for undo."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM action_history
                   ORDER BY id DESC
                   LIMIT 1"""
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_action_history(self, action_id: int) -> bool:
        """Delete an action from history after undo."""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM action_history WHERE id = ?",
                (action_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== Notification Settings ====================

    def set_notification_setting(
        self,
        chat_id: int,
        setting_key: str,
        setting_value: str
    ) -> bool:
        """Set a notification setting for a user."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO notification_settings
                   (chat_id, setting_key, setting_value)
                   VALUES (?, ?, ?)""",
                (chat_id, setting_key, setting_value)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_notification_setting(
        self,
        chat_id: int,
        setting_key: str
    ) -> Optional[str]:
        """Get a notification setting for a user."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT setting_value FROM notification_settings
                   WHERE chat_id = ? AND setting_key = ?""",
                (chat_id, setting_key)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_all_notification_settings(self, chat_id: int) -> dict:
        """Get all notification settings for a user."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT setting_key, setting_value FROM notification_settings
                   WHERE chat_id = ?""",
                (chat_id,)
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

    def set_mute_until(self, chat_id: int, muted_until: str) -> bool:
        """Set mute until datetime for a user."""
        return self.update_user_config(chat_id, muted_until=muted_until)

    def is_muted(self, chat_id: int) -> bool:
        """Check if notifications are muted for a user."""
        user_config = self.get_user_config(chat_id)
        if not user_config:
            return False

        muted_until = user_config.get("muted_until")
        if not muted_until:
            return False

        try:
            mute_end = datetime.fromisoformat(muted_until)
            return datetime.now() < mute_end
        except ValueError:
            return False

    # ==================== Statistics ====================

    def get_completion_stats(self, days: int = 7) -> dict:
        """Get completion statistics for the past N days."""
        conn = self._get_conn()
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            stats = {}

            # Assignments stats
            cursor = conn.execute(
                """SELECT COUNT(*) FROM assignments
                   WHERE is_completed = 1
                   AND completed_at >= ?""",
                (cutoff,)
            )
            completed_assignments = cursor.fetchone()[0]

            cursor = conn.execute(
                """SELECT COUNT(*) FROM assignments
                   WHERE created_at >= ?""",
                (cutoff,)
            )
            total_assignments = cursor.fetchone()[0]

            stats["assignments"] = {
                "completed": completed_assignments,
                "total": total_assignments
            }

            # Tasks stats
            cursor = conn.execute(
                """SELECT COUNT(*) FROM tasks
                   WHERE is_completed = 1
                   AND completed_at >= ?""",
                (cutoff,)
            )
            completed_tasks = cursor.fetchone()[0]

            cursor = conn.execute(
                """SELECT COUNT(*) FROM tasks
                   WHERE created_at >= ?""",
                (cutoff,)
            )
            total_tasks = cursor.fetchone()[0]

            stats["tasks"] = {
                "completed": completed_tasks,
                "total": total_tasks
            }

            # TODOs stats
            cursor = conn.execute(
                """SELECT COUNT(*) FROM todos
                   WHERE is_completed = 1
                   AND completed_at >= ?""",
                (cutoff,)
            )
            completed_todos = cursor.fetchone()[0]

            cursor = conn.execute(
                """SELECT COUNT(*) FROM todos
                   WHERE created_at >= ?""",
                (cutoff,)
            )
            total_todos = cursor.fetchone()[0]

            stats["todos"] = {
                "completed": completed_todos,
                "total": total_todos
            }

            return stats
        finally:
            conn.close()

    # ==================== Global Search ====================

    def search_all(self, query: str) -> dict:
        """Search across all tables for a query string."""
        conn = self._get_conn()
        try:
            results = {
                "assignments": [],
                "tasks": [],
                "todos": [],
                "schedule": [],
                "events": []
            }

            search_pattern = f"%{query}%"

            # Search assignments
            cursor = conn.execute(
                """SELECT * FROM assignments
                   WHERE title LIKE ? OR description LIKE ? OR subject_code LIKE ?
                   ORDER BY due_date""",
                (search_pattern, search_pattern, search_pattern)
            )
            results["assignments"] = [dict(row) for row in cursor.fetchall()]

            # Search tasks
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
                   ORDER BY scheduled_date""",
                (search_pattern, search_pattern, search_pattern)
            )
            results["tasks"] = [dict(row) for row in cursor.fetchall()]

            # Search todos
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE title LIKE ?
                   ORDER BY created_at""",
                (search_pattern,)
            )
            results["todos"] = [dict(row) for row in cursor.fetchall()]

            # Search schedule
            cursor = conn.execute(
                """SELECT * FROM schedule
                   WHERE subject_code LIKE ? OR subject_name LIKE ? OR room LIKE ?
                   ORDER BY day_of_week, start_time""",
                (search_pattern, search_pattern, search_pattern)
            )
            results["schedule"] = [dict(row) for row in cursor.fetchall()]

            # Search events
            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE name LIKE ? OR name_en LIKE ?
                   ORDER BY start_date""",
                (search_pattern, search_pattern)
            )
            results["events"] = [dict(row) for row in cursor.fetchall()]

            return results
        finally:
            conn.close()

    # ==================== Recurring Tasks ====================

    def add_recurring_task(
        self,
        title: str,
        scheduled_date: str,
        recurrence: str,
        description: str = None,
        scheduled_time: str = None,
        location: str = None,
        recurrence_end: str = None
    ) -> int:
        """Add a recurring task. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO tasks
                   (title, description, scheduled_date, scheduled_time, location,
                    recurrence, recurrence_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, description, scheduled_date, scheduled_time, location,
                 recurrence, recurrence_end)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_recurring_tasks(self) -> list[dict]:
        """Get all recurring tasks (master records)."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE recurrence IS NOT NULL
                   AND parent_task_id IS NULL
                   ORDER BY scheduled_date"""
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def create_recurring_instance(
        self,
        parent_task_id: int,
        scheduled_date: str
    ) -> int:
        """Create an instance of a recurring task for a specific date."""
        conn = self._get_conn()
        try:
            # Get parent task
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (parent_task_id,)
            )
            parent = cursor.fetchone()
            if not parent:
                return -1

            parent_dict = dict(parent)

            cursor = conn.execute(
                """INSERT INTO tasks
                   (title, description, scheduled_date, scheduled_time, location,
                    parent_task_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (parent_dict["title"], parent_dict.get("description"),
                 scheduled_date, parent_dict.get("scheduled_time"),
                 parent_dict.get("location"), parent_task_id)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    # ==================== Language Settings ====================

    def set_language(self, chat_id: int, language: str) -> bool:
        """Set user language preference."""
        return self.update_user_config(chat_id, language=language)

    def get_language(self, chat_id: int) -> str:
        """Get user language preference. Defaults to 'en'."""
        user_config = self.get_user_config(chat_id)
        if not user_config:
            return "en"
        return user_config.get("language", "en")

    # ==================== Pending Counts ====================

    def get_pending_counts(self) -> dict:
        """Get counts of pending items."""
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

    # ==================== Get Item By ID ====================

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

    def get_schedule_by_subject(self, subject: str) -> list[dict]:
        """Get schedule slots for a subject by code or name."""
        conn = self._get_conn()
        try:
            search_pattern = f"%{subject}%"
            cursor = conn.execute(
                """SELECT * FROM schedule
                   WHERE subject_code LIKE ? OR subject_name LIKE ?
                   ORDER BY day_of_week, start_time""",
                (search_pattern, search_pattern)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== Voice Notes ====================

    def add_voice_note(
        self,
        chat_id: int,
        original_transcript: str,
        processed_content: str,
        processing_type: str,
        duration_seconds: int = None,
        title: str = None,
        tags: str = None
    ) -> int:
        """Add a voice note. Returns the new ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO voice_notes
                   (chat_id, original_transcript, processed_content, processing_type,
                    duration_seconds, title, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (chat_id, original_transcript, processed_content, processing_type,
                 duration_seconds, title, tags)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_voice_notes(self, chat_id: int, limit: int = 20) -> list[dict]:
        """Get voice notes for a user."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT * FROM voice_notes
                   WHERE chat_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (chat_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_voice_note_by_id(self, note_id: int) -> Optional[dict]:
        """Get a specific voice note by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM voice_notes WHERE id = ?",
                (note_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def search_voice_notes(self, chat_id: int, query: str) -> list[dict]:
        """Search voice notes by content or title."""
        conn = self._get_conn()
        try:
            search_pattern = f"%{query}%"
            cursor = conn.execute(
                """SELECT * FROM voice_notes
                   WHERE chat_id = ?
                   AND (title LIKE ? OR original_transcript LIKE ? OR processed_content LIKE ? OR tags LIKE ?)
                   ORDER BY created_at DESC""",
                (chat_id, search_pattern, search_pattern, search_pattern, search_pattern)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def delete_voice_note(self, note_id: int) -> Optional[dict]:
        """Delete a voice note. Returns the deleted item or None."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM voice_notes WHERE id = ?",
                (note_id,)
            )
            item = cursor.fetchone()
            if not item:
                return None

            item_dict = dict(item)
            conn.execute(
                "DELETE FROM voice_notes WHERE id = ?",
                (note_id,)
            )
            conn.commit()
            return item_dict
        finally:
            conn.close()

    def update_voice_note_title(self, note_id: int, title: str) -> bool:
        """Update a voice note's title."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE voice_notes SET title = ? WHERE id = ?",
                (title, note_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== AI Suggestions Data ====================

    def get_data_for_suggestions(self) -> dict:
        """Get all relevant data for AI suggestions."""
        conn = self._get_conn()
        try:
            data = {}

            # Pending assignments with due dates
            cursor = conn.execute(
                """SELECT * FROM assignments
                   WHERE is_completed = 0
                   ORDER BY due_date"""
            )
            data["assignments"] = [dict(row) for row in cursor.fetchall()]

            # Upcoming tasks
            today = datetime.now().date().isoformat()
            cursor = conn.execute(
                """SELECT * FROM tasks
                   WHERE is_completed = 0
                   AND scheduled_date >= ?
                   ORDER BY scheduled_date, scheduled_time""",
                (today,)
            )
            data["tasks"] = [dict(row) for row in cursor.fetchall()]

            # Pending todos
            cursor = conn.execute(
                """SELECT * FROM todos
                   WHERE is_completed = 0
                   ORDER BY scheduled_date, created_at"""
            )
            data["todos"] = [dict(row) for row in cursor.fetchall()]

            # Weekly schedule
            cursor = conn.execute(
                "SELECT * FROM schedule ORDER BY day_of_week, start_time"
            )
            data["schedule"] = [dict(row) for row in cursor.fetchall()]

            # Upcoming exams
            cursor = conn.execute(
                """SELECT * FROM events
                   WHERE event_type = 'exam'
                   AND start_date >= ?
                   ORDER BY start_date""",
                (today,)
            )
            data["exams"] = [dict(row) for row in cursor.fetchall()]

            return data
        finally:
            conn.close()
