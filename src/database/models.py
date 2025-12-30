"""Database schema and initialization."""

import sqlite3
from pathlib import Path


SCHEMA = """
-- User configuration
CREATE TABLE IF NOT EXISTS user_config (
    id INTEGER PRIMARY KEY,
    telegram_chat_id INTEGER UNIQUE NOT NULL,
    semester_start_date TEXT,
    daily_class_alert_time TEXT DEFAULT '22:00',
    offday_alert_time TEXT DEFAULT '20:00',
    midnight_todo_review INTEGER DEFAULT 1,
    timezone TEXT DEFAULT 'Asia/Kuala_Lumpur',
    language TEXT DEFAULT 'en',
    muted_until TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Academic events (holidays, breaks, exam periods)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    name TEXT,
    name_en TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    affects_classes INTEGER DEFAULT 1,
    subject_code TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Action history for undo functionality
CREATE TABLE IF NOT EXISTS action_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    table_name TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    old_data TEXT,
    new_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Notification settings
CREATE TABLE IF NOT EXISTS notification_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, setting_key)
);

-- Weekly timetable slots
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY,
    day_of_week INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    subject_code TEXT NOT NULL,
    subject_name TEXT,
    class_type TEXT DEFAULT 'LEC',
    room TEXT,
    lecturer_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Assignments (formal academic work with escalating reminders)
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    subject_code TEXT,
    description TEXT,
    due_date TEXT NOT NULL,
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    last_reminder_level INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Tasks/Meetings (scheduled appointments)
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_date TEXT NOT NULL,
    scheduled_time TEXT,
    location TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    reminded_1day INTEGER DEFAULT 0,
    reminded_2hours INTEGER DEFAULT 0,
    recurrence TEXT,
    recurrence_end TEXT,
    parent_task_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- TODOs (quick personal tasks)
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    scheduled_date TEXT,
    scheduled_time TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    reminded INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Online class overrides (per-class or global online settings by week/date)
CREATE TABLE IF NOT EXISTS online_overrides (
    id INTEGER PRIMARY KEY,
    subject_code TEXT,
    week_number INTEGER,
    specific_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Initialize the database with all required tables."""
    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
