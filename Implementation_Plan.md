# Implementation Plan - UTeM Student Assistant Bot

## Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation (Steps 1-4) | COMPLETE |
| Phase 2 | AI Integration (Steps 5-8) | COMPLETE |
| Phase 3 | Bot Intelligence (Steps 9-12) | COMPLETE |
| Phase 4 | Notifications (Steps 13-15) | COMPLETE |
| Phase 5 | Polish & Deploy (Steps 16-18) | COMPLETE |

**Progress: 18/18 steps completed (100%)**

---

## Current Implementation Summary

### Bot Commands Available
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and user registration |
| `/setup` | Onboarding flow (calendar + timetable upload) |
| `/help` | Show all available commands |
| `/status` | Overview of pending items |
| `/tomorrow` | Tomorrow's classes |
| `/week` | This week's full schedule |
| `/week_number` | Current semester week (handles mid-semester & inter-semester breaks) |
| `/offday` | Next upcoming holiday |
| `/assignments` | List pending assignments (blocked during inter-semester break) |
| `/tasks` | List upcoming tasks |
| `/todos` | List pending TODOs |
| `/done <type> <id>` | Mark item as complete |
| `/setdate <YYYY-MM-DD>` | Set test date for debugging (resets on bot restart) |
| `/resetdate` | Reset to real system date |

### Natural Language Support
- "What class tomorrow?" → Shows tomorrow's schedule
- "What week is this?" → Shows current semester week
- "Assignment report for BITP1113 due Friday 5pm" → Adds assignment
- "Meet Dr Intan tomorrow 10am" → Adds task
- "Take wife at Satria at 3pm" → Adds TODO
- "Done with BITP report" → Marks matching item complete

### Image Recognition
- **Academic Calendar**: Auto-extracts holidays, breaks, exam periods
- **Class Timetable**: Auto-extracts schedule with rooms and lecturers
- **Assignment Sheets**: Auto-extracts title, subject, due date

### Notification System
| Time | Notification |
|------|--------------|
| 10:00 PM | Tomorrow's classes briefing |
| 8:00 PM | Off-day alert (if applicable) |
| 8:30 PM | Semester starting alert (1 week before inter-semester break ends) |
| 12:00 AM | Midnight TODO review |
| Every 30 min | Assignment/Task/TODO reminder checks |

### Break Handling
- **Mid-semester break**: Detected by name containing "Pertengahan" or "Mid"
- **Inter-semester break**: Detected by name containing "Antara" or "Inter"
- `/week_number` returns break name when in break period
- `/assignments` blocked during inter-semester break with friendly message
- Notification sent 1 week before inter-semester break ends

### Assignment Reminder Escalation
3 days → 2 days → 1 day → 8 hours → 3 hours → 1 hour → Due now

---

### Completed Files
| File | Description | Lines |
|------|-------------|-------|
| `src/config.py` | Configuration and env loading | ~54 |
| `src/database/models.py` | SQLite schema (6 tables) | ~80 |
| `src/database/operations.py` | Full CRUD + lookup methods | ~575 |
| `src/main.py` | Bot entry point with scheduler | ~70 |
| `src/bot/handlers.py` | All commands + message routing + debug commands | ~560 |
| `src/bot/conversations.py` | Onboarding + formatters | ~455 |
| `src/ai/gemini_client.py` | Gemini API with retry logic | ~145 |
| `src/ai/image_parser.py` | Calendar/timetable/assignment parsing | ~355 |
| `src/ai/intent_parser.py` | NL intent classification (15+ intents) | ~370 |
| `src/utils/semester_logic.py` | Week calculation + break handling + date utilities | ~380 |
| `src/utils/logging_config.py` | File logging with rotation | ~65 |
| `src/utils/error_handlers.py` | Error handling utilities | ~115 |
| `src/scheduler/notifications.py` | APScheduler + all reminders + semester alert | ~580 |
| `tests/test_semester_logic.py` | Week calculation tests | ~245 |
| `tests/test_database.py` | CRUD operation tests | ~250 |
| `tests/test_image_parser.py` | AI parsing tests (mocked) | ~185 |
| `deploy/utem-bot.service` | Systemd service file | ~25 |
| `deploy/backup.sh` | Database backup script | ~40 |
| `deploy/install.sh` | Installation script | ~90 |
| `README.md` | Project documentation | ~200 |

**Total: ~4,850+ lines of code**
---

## Overview
Telegram bot that ingests academic calendar/timetable images, manages assignments/tasks/todos via natural language, and sends proactive notifications with escalating reminders.

**Platform**: Telegram (free, reliable push notifications, easy bot API)
**Hosting**: DigitalOcean Droplet (~$4-6/mo) or local machine for development

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.10+ |
| Bot Framework | `python-telegram-bot` (async) |
| AI | Google Gemini API (`gemini-2.0-flash`) |
| Database | SQLite3 |
| Scheduler | APScheduler |
| Config | python-dotenv |

---

## Project Structure

```
productivity/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Settings & env loading
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLite schema
│   │   └── operations.py       # CRUD functions
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── gemini_client.py    # API wrapper
│   │   ├── image_parser.py     # Calendar/timetable/assignment extraction
│   │   └── intent_parser.py    # NL command classification
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py         # Telegram command handlers
│   │   └── conversations.py    # Multi-step flows (onboarding)
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── notifications.py    # Daily briefing, reminders
│   └── utils/
│       ├── __init__.py
│       ├── semester_logic.py   # Week calculation
│       ├── logging_config.py   # File logging setup
│       └── error_handlers.py   # Error handling utilities
├── tests/
│   ├── __init__.py
│   ├── test_semester_logic.py
│   ├── test_image_parser.py
│   └── test_database.py
├── deploy/
│   ├── utem-bot.service        # Systemd service file
│   ├── backup.sh               # Database backup script
│   └── install.sh              # Installation script
├── data/
│   └── bot.db                  # SQLite file (gitignored)
├── logs/                       # Log files (gitignored)
├── backups/                    # Database backups (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Database Schema

```sql
-- User configuration
CREATE TABLE user_config (
    id INTEGER PRIMARY KEY,
    telegram_chat_id INTEGER UNIQUE NOT NULL,
    semester_start_date TEXT,
    daily_class_alert_time TEXT DEFAULT '22:00',  -- 10PM for tomorrow's classes
    offday_alert_time TEXT DEFAULT '20:00',       -- 8PM for off-day alerts
    midnight_todo_review INTEGER DEFAULT 1,        -- Enable 12AM TODO list
    timezone TEXT DEFAULT 'Asia/Kuala_Lumpur',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Academic events (holidays, breaks, exam periods)
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,        -- 'holiday', 'break', 'exam', 'lecture_period', 'registration', 'pdp_online'
    name TEXT,
    name_en TEXT,                    -- English translation if available
    start_date TEXT NOT NULL,
    end_date TEXT,
    affects_classes INTEGER DEFAULT 1, -- Does this cancel regular classes?
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Weekly timetable slots
CREATE TABLE schedule (
    id INTEGER PRIMARY KEY,
    day_of_week INTEGER NOT NULL,    -- 0=Monday, 6=Sunday
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    subject_code TEXT NOT NULL,
    subject_name TEXT,
    class_type TEXT DEFAULT 'LEC',   -- 'LEC' or 'LAB'
    room TEXT,
    lecturer_name TEXT,              -- Dr Zahriah, Dr Najwan, etc.
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Assignments (formal academic work with escalating reminders)
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    subject_code TEXT,
    description TEXT,
    due_date TEXT NOT NULL,          -- ISO datetime with time
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    last_reminder_level INTEGER DEFAULT 0, -- 0=none, 1=3d, 2=2d, 3=1d, 4=8h, 5=3h, 6=1h, 7=due
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Tasks/Meetings (scheduled appointments)
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,             -- "Meet Dr Intan"
    description TEXT,                -- "for FYP discussion"
    scheduled_date TEXT NOT NULL,
    scheduled_time TEXT,             -- Can be NULL
    location TEXT,
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    reminded_1day INTEGER DEFAULT 0,
    reminded_2hours INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- TODOs (quick personal tasks)
CREATE TABLE todos (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,             -- "Take wife at Satria"
    scheduled_date TEXT,             -- Can be NULL (floating todo)
    scheduled_time TEXT,             -- Can be NULL (no specific time)
    is_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    reminded INTEGER DEFAULT 0,      -- For time-specific todos
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## Notification Schedule

### Assignment Reminders (7-Level Escalation)

| Level | Trigger | Message Example |
|-------|---------|-----------------|
| 1 | 3 days before | "Assignment 'Report BITP1113' due in 3 days (Friday 5PM)" |
| 2 | 2 days before | "Assignment 'Report BITP1113' due in 2 days" |
| 3 | 1 day before | "Assignment 'Report BITP1113' due TOMORROW at 5PM" |
| 4 | 8 hours before | "8 hours left for 'Report BITP1113'!" |
| 5 | 3 hours before | "Only 3 hours left!" |
| 6 | 1 hour before | "URGENT: 1 hour remaining!" |
| 7 | Due time | "Assignment 'Report BITP1113' is NOW DUE" |

### Task/Meeting Reminders

| Trigger | Time |
|---------|------|
| 1 day before | 8PM or 10PM (configurable) |
| 2 hours before | Dynamic based on scheduled_time |

### TODO Reminders

| Type | Trigger |
|------|---------|
| With specific time | 1 hour before |
| Without time | Listed at 12:00 AM midnight |

### Daily Briefings

| Time | Content |
|------|---------|
| 10PM | Tomorrow's classes: times, rooms, lecturers, class type |
| 8PM | Off-day alert (if applicable): "No class tomorrow - [Holiday]" with affected subjects |
| 12AM | Midnight TODO review: List all incomplete TODOs without specific time |

---

## Intent Types

```python
class Intent(Enum):
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
    QUERY_TOMORROW_CLASSES = "query_tomorrow"
    QUERY_WEEK_CLASSES = "query_week"
    QUERY_SUBJECT_SCHEDULE = "query_subject"

    # Academic Calendar Queries
    QUERY_CURRENT_WEEK = "query_current_week"
    QUERY_NEXT_WEEK = "query_next_week"
    QUERY_NEXT_OFFDAY = "query_next_offday"
    QUERY_SEMESTER_DATES = "query_semester"

    # Image Upload
    UPLOAD_ASSIGNMENT_IMAGE = "upload_assignment"

    # General
    GENERAL_CHAT = "general_chat"
```

---

## Academic Calendar Parsing

### Include (Sarjana Muda relevant):
- Kuliah Semester (Lecture periods - Bahagian Pertama, Kedua)
- Public holidays (Deepavali, Hari Krismas, Tahun Baharu, CNY, etc.)
- Cuti Pertengahan Semester (Mid-sem break)
- Cuti Antara Semester (Semester break)
- Ujian Pertengahan Semester (Mid-sem test)
- PDP Dalam Talian (Online learning days)
- Peperiksaan Akhir (Final exam)
- Cuti Ulang Kaji (Study leave)
- Pendaftaran Kursus (Course registration)

### Exclude (Staff/Admin - ignore these):
- Mesyuarat Senat
- Mesyuarat Jawatankuasa Tetap Senat
- Latihan Industri Pelajar (unless user specifies)
- Pendaftaran Lewat Berdenda Pelajar Kanan
- Keputusan Peperiksaan administrative items

---

## Implementation Phases

### Phase 1: Foundation (Steps 1-4) - COMPLETE

#### Step 1: Project Scaffold [DONE]
- Create folder structure as shown above
- Initialize git repo with `.gitignore`
- Create `requirements.txt`:
  ```
  python-telegram-bot>=20.0
  google-generativeai>=0.3.0
  APScheduler>=3.10.0
  python-dotenv>=1.0.0
  pytz>=2024.1
  ```
- Create `.env.example`:
  ```
  TELEGRAM_TOKEN=your_bot_token_here
  GEMINI_API_KEY=your_gemini_key_here
  DATABASE_PATH=data/bot.db
  ```

#### Step 2: Configuration Module [DONE]
- `src/config.py`: Load env vars, validate required keys
- Settings: `TELEGRAM_TOKEN`, `GEMINI_API_KEY`, `DATABASE_PATH`

#### Step 3: Database Setup [DONE]
- `src/database/models.py`: Schema creation function (all 6 tables)
- `src/database/operations.py`:
  - `init_db()` - create tables if not exist
  - CRUD for each table type

#### Step 4: Basic Telegram Bot [DONE]
- `src/main.py`: Bot initialization, run loop
- `src/bot/handlers.py`:
  - `/start` - Welcome message
  - `/help` - Command list
  - `/status` - Current week + pending counts

---

### Phase 2: AI Integration (Steps 5-8) - COMPLETE

#### Step 5: Gemini Client [DONE]
- `src/ai/gemini_client.py`:
  - Initialize Gemini with API key
  - `send_text(prompt)` - text completion
  - `send_image(image_bytes, prompt)` - vision analysis

#### Step 6: Calendar Image Parser [DONE]
- `src/ai/image_parser.py`:
  - `parse_academic_calendar(image_bytes) -> List[AcademicEvent]`
  - Prompt: "Extract only items relevant to undergraduate (Sarjana Muda) students"
  - Filter out Mesyuarat, Latihan Industri, etc.
  - Set `affects_classes` flag appropriately
  - Expected output:
    ```json
    [
      {"type": "lecture_period", "name": "Kuliah Semester I Bahagian Pertama", "start": "2025-10-06", "end": "2025-11-14"},
      {"type": "holiday", "name": "Hari Deepavali", "date": "2025-10-20", "affects_classes": true}
    ]
    ```

#### Step 7: Timetable Image Parser [DONE]
- Same file (`src/ai/image_parser.py`), added:
  - `parse_timetable(image_bytes) -> List[ScheduleSlot]`
  - Extract: day, time range, subject code, subject name, room, **lecturer name**, **class type (LEC/LAB)**
  - Expected output:
    ```json
    [
      {"day": "Monday", "start": "11:00", "end": "13:00", "subject_code": "BITP 1113", "class_type": "LEC", "room": "BK13", "lecturer": "DR ZAHRIAH"}
    ]
    ```

#### Step 7.5: Assignment Image Parser [DONE]
- `parse_assignment_image(image_bytes) -> AssignmentDetails`
- `detect_image_type(image_bytes) -> str` - Auto-detect calendar/timetable/assignment
- Extract: title, subject, due date, requirements from assignment sheet photo
- Return for user confirmation before saving

#### Step 8: Semester Logic [DONE]
- `src/utils/semester_logic.py`:
  - `get_current_week(today, semester_start, events) -> int | str`
  - Returns week number (1-14) or break name ("Cuti Pertengahan Semester", "Cuti Antara Semester", etc.)
  - Handles both mid-semester and inter-semester breaks
  - `get_next_week(today, ...) -> int | str`
  - `is_class_day(date, events) -> bool`
  - `get_event_on_date(date, events) -> Optional[dict]`
  - `get_affected_classes(date, schedule, events) -> List[dict]` - which subjects are off
  - `get_next_offday(today, events, days_ahead) -> Optional[dict]`
  - `classify_break_event(event) -> str` - Returns "mid_semester" or "inter_semester"
  - `get_all_breaks(events) -> Tuple[mid_break, inter_break]` - Get both break types
  - `get_current_break(today, events) -> Optional[dict]` - Get break if currently in one
  - `is_semester_active(today, semester_start, events) -> bool` - Check if lectures happening
  - `format_date(date, include_day) -> str` - Format for display
  - `format_time(time_str) -> str` - Convert 24h to 12h format
  - `days_until(target_date, from_date) -> int`
  - `hours_until(target_datetime, from_datetime) -> float`

---

### Phase 3: Bot Intelligence (Steps 9-12) - COMPLETE

#### Step 9: Intent Parser [DONE]
- `src/ai/intent_parser.py`:
  - `classify_message(text) -> ClassificationResult` with Intent and ParsedEntities
  - All 15+ intents from the Intent enum (assignments, tasks, todos, schedule queries, etc.)
  - Entity extraction: dates, times, subjects, names, descriptions
  - Quick pattern matching for common queries + Gemini fallback for complex messages
  - `extract_completion_target()` for matching "done with X" to pending items
  - Helper builders: `build_assignment_from_entities()`, `build_task_from_entities()`, `build_todo_from_entities()`

#### Step 10: Data Operations (Split by Type) [DONE]
- `src/database/operations.py`: Expanded with lookup methods
  - **Assignments**: `add_assignment()`, `get_pending_assignments()`, `complete_assignment()`, `get_assignments_due_soon(hours)`, `get_assignment_by_id()`, `find_assignment_by_title()`
  - **Tasks**: `add_task()`, `get_upcoming_tasks()`, `get_tasks_for_date()`, `complete_task()`, `get_task_by_id()`, `find_task_by_title()`
  - **TODOs**: `add_todo()`, `get_pending_todos()`, `get_todos_without_time()`, `get_todos_for_date()`, `complete_todo()`, `get_todo_by_id()`, `find_todo_by_title()`
  - **Events**: `get_all_events()` for semester logic

#### Step 11: Conversation Handlers [DONE]
- `src/bot/conversations.py`:
  - **Onboarding flow** (`/setup` command):
    1. Ask for calendar image → parse with `parse_academic_calendar()`
    2. Show extracted events for confirmation (yes/no)
    3. Ask for timetable image → parse with `parse_timetable()`
    4. Show schedule for confirmation → save to database
    5. Auto-detect semester start from lecture_period events
  - **Assignment image upload flow**: Detect → Parse → Show details → Confirm → Save
  - **Query response formatters**: `format_tomorrow_classes()`, `format_week_schedule()`, `format_pending_assignments()`, `format_pending_tasks()`, `format_pending_todos()`, `format_current_week()`, `format_next_offday()`

#### Step 12: Message Router [DONE]
- `src/bot/handlers.py`: Full message routing system
  - **Commands**: `/tomorrow`, `/week`, `/week_number`, `/offday`, `/assignments`, `/tasks`, `/todos`, `/done`
  - **Debug commands**: `/setdate <YYYY-MM-DD>`, `/resetdate` - for testing different dates
  - **Text handler**: Intent classification → route to appropriate action (add/query/complete)
  - **Photo handler**: Auto-detect type (calendar/timetable/assignment) → parse accordingly
  - **Confirmation flow**: Assignment images require user confirmation before saving
  - **Natural language processing**: "What class tomorrow?", "Done with BITP report", etc.
  - **Break handling**: `/assignments` blocked during inter-semester break with friendly message

---

### Phase 4: Notifications (Steps 13-15) - COMPLETE

#### Step 13: Scheduler Setup [DONE]
- `src/scheduler/notifications.py`:
  - `NotificationScheduler` class with APScheduler (`AsyncIOScheduler`)
  - Malaysia timezone (`Asia/Kuala_Lumpur`) configured via pytz
  - Integrated with `main.py` via `post_init` and `post_shutdown` hooks
  - Jobs registered:
    - `send_class_briefing` - CronTrigger at 22:00
    - `send_offday_alert` - CronTrigger at 20:00
    - `send_midnight_todo_review` - CronTrigger at 00:00
    - `check_semester_starting` - CronTrigger at 20:30 (1 week before inter-semester break ends)
    - `check_assignment_reminders` - IntervalTrigger every 30 minutes
    - `check_task_reminders` - IntervalTrigger every 30 minutes
    - `check_todo_reminders` - IntervalTrigger every 30 minutes

#### Step 14: Daily Briefings (4 Types) [DONE]

**10PM Class Briefing** (`send_class_briefing`):
- Checks if tomorrow has classes using `is_class_day()`
- Gets schedule for tomorrow's day_of_week
- Formats with subject, time, class type, room, lecturer
- Example: "📚 Classes Tomorrow (Tuesday, 15 Jan): • BITM1113 8AM-10AM (LEC) 📍 BPA DK7 👨‍🏫 Dr Mahfuzah"

**8PM Off-day Alert** (`send_offday_alert`):
- Checks if tomorrow is holiday/break using `get_event_on_date()`
- Lists affected classes that would have been cancelled
- Example: "🎉 No Classes Tomorrow! Tomorrow is: 📅 Hari Deepavali. Classes cancelled: • BITP1113 at 8AM"

**8:30PM Semester Starting Alert** (`check_semester_starting`):
- Checks if inter-semester break ends in exactly 7 days
- Uses `get_all_breaks()` to find inter-semester break
- Example: "📚 Heads Up! The inter-semester break ends in 1 week! New semester starts: Monday, 20 Jan 2026. That will be Week 1 of the new semester. Time to prepare for classes!"

**12AM Midnight TODO Review** (`send_midnight_todo_review`):
- Gets all TODOs without specific time using `get_todos_without_time()`
- Respects user's `midnight_todo_review` preference
- Example: "📝 Midnight TODO Review. You have 3 pending TODO(s): 1. Take wife at Satria..."

#### Step 15: Escalating Reminders [DONE]

**Assignment Reminders (7 levels)** (`check_assignment_reminders`):
- Level thresholds: 72h (3d), 48h (2d), 24h (1d), 8h, 3h, 1h, 0h (due now)
- Calculates `hours_until()` due date
- Sends appropriate message based on urgency level
- Updates `last_reminder_level` in database after sending
- Skips completed assignments

**Task Reminders (2 levels)** (`check_task_reminders`):
- 1 day before: Sends at 8PM if task is tomorrow
- 2 hours before: Sends when <= 2 hours remaining (only for tasks with specific time)
- Tracks with `reminded_1day`, `reminded_2hours` flags

**TODO Reminders (1 level)** (`check_todo_reminders`):
- 1 hour before for TODOs with specific time
- Tracks with `reminded` flag

---

### Phase 5: Polish & Deploy (Steps 16-18) - COMPLETE

#### Step 16: Error Handling [DONE]
- `src/utils/logging_config.py`: Rotating file logging (5MB max, 3 backups)
- `src/utils/error_handlers.py`: Error wrapper decorators and global error handler
- `src/main.py`: Updated with logging config and global error handler
- Graceful fallbacks with user-friendly messages
- Noise reduction for third-party loggers (httpx, telegram, apscheduler)

#### Step 17: Testing [DONE]
- `tests/test_semester_logic.py`: Week calculation, date parsing, formatting tests
- `tests/test_database.py`: Full CRUD operations for all 6 tables
- `tests/test_image_parser.py`: Mocked Gemini responses for AI parsing
- pytest + pytest-asyncio added to requirements.txt

#### Step 18: Deployment [DONE]
- `deploy/utem-bot.service`: Systemd unit file with security hardening
- `deploy/backup.sh`: SQLite backup script with 7-day retention
- `deploy/install.sh`: Full installation script for Ubuntu
- `README.md`: Comprehensive project documentation
- Server setup instructions included

---

## Query Response Examples

| User Says | Bot Response |
|-----------|--------------|
| "What week is this?" | "This is Week 5 of Semester 1 (2025/2026)" |
| "What week is this?" (during mid-break) | "This is Cuti Pertengahan Semester" |
| "What week is this?" (during inter-break) | "This is Cuti Antara Semester" |
| "What week next week?" | "Next week is Week 6" |
| "When is next off day?" | "Next off day: Hari Deepavali on 20 Oct 2025 (Monday)" |
| "What class tomorrow?" | "Tomorrow (Tuesday): BITM1113 8-10AM (LEC, BPA DK7, Dr Mahfuzah), BITI1213 10-11AM (LEC, DK5 BPA, Dr Yogan)..." |
| "What assignments pending?" | "3 pending: 1) Report BITP1113 (due Fri 5PM), 2) Quiz BITI1213 (due Mon)..." |
| `/assignments` (during inter-break) | "It's Cuti Antara Semester! No assignments to worry about during the break. Enjoy your holiday!" |
| "What todos left?" | "5 TODOs: 1) Take wife at Satria, 2) Buy groceries..." |
| "I finished the BITP report" | "Marked 'Report BITP1113' as completed. No more reminders for this." |

---

## Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Gemini API timeout | Retry once after 5 seconds, then apologize & ask to try again |
| Image parse failure | Show what was extracted (even partial), ask user to confirm/correct |
| Invalid date in task | Ask for clarification: "When exactly is that due?" |
| DB write failure | Log error, notify user, preserve their input in message |
| Scheduler miss | On startup, check if daily briefing was missed today, send if so |
| Ambiguous intent | Ask for clarification with suggested options |

---

## Files to Create (in order)

| Order | Files | Notes |
|-------|-------|-------|
| 1 | `.gitignore`, `.env.example`, `requirements.txt` | Project setup |
| 2 | `src/config.py` | Environment loading |
| 3 | `src/database/models.py`, `src/database/operations.py` | 6 tables, type-specific CRUD |
| 4 | `src/main.py`, `src/bot/handlers.py` | Basic bot skeleton |
| 5 | `src/ai/gemini_client.py` | AI wrapper |
| 6 | `src/ai/image_parser.py` | Calendar + timetable + assignment parsing |
| 7 | `src/utils/semester_logic.py` | Week calculation |
| 8 | `src/ai/intent_parser.py` | 15+ intents |
| 9 | `src/bot/conversations.py` | Onboarding, confirmations |
| 10 | `src/scheduler/notifications.py` | 3 briefings + escalating reminders |
| 11 | `tests/*` | Unit tests |
| 12 | `README.md` | Documentation |

---

## Verification Plan

### Automated Tests
- **Parsing Test**: Feed sample images, assert JSON output matches expected structure
- **Week Calculation Test**: Mock dates (mid-semester, break period, exam week) and verify correct output
- **Reminder Level Test**: Verify escalation logic (3d→2d→1d→8h→3h→1h→due)

### Manual Verification
- **Simulate Notifications**: Set alert time to 1 minute from now, verify Telegram message arrives
- **Chat Test**:
  - "I have assignment report for BITP1113 due Friday 5pm" → Confirm parsing & saving
  - "What week is this?" → Verify correct week number
  - "Done with BITP report" → Verify completion stops reminders
- **Image Upload Test**: Send assignment sheet photo, verify extraction
