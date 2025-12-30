# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UTeM Student Assistant Bot - A Telegram bot helping UTeM students manage academic schedules, assignments, tasks, and TODOs with AI-powered features including image recognition, voice transcription, and smart suggestions (Google Gemini).

## Common Commands

```bash
# Run the bot
python -m src.main

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_semester_logic.py -v

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Entry Points
- `src/main.py` - Main entry point; initializes database, registers handlers, starts scheduler
- `src/config.py` - Settings & environment loading

### Core Components

**Bot Layer** (`src/bot/`)
- `handlers.py` - Telegram command handlers and message routing by intent. Handles text, photos, and voice. Debug commands: `/setdate`, `/settime`, `/trigger`
- `conversations.py` - Multi-step conversation flows (onboarding, assignment confirmation) and response formatters
- `keyboards.py` - Inline keyboard layouts (main menu, settings, voice options). Settings keyboard shows date/time override status

**AI Layer** (`src/ai/`)
- `gemini_client.py` - Google Gemini API wrapper (singleton via `get_gemini_client()`)
- `intent_parser.py` - NLP intent classification with `Intent` enum. Regex patterns checked first (lab tests, week queries, class queries), then Gemini for complex messages
- `image_parser.py` - Detects image types (calendar, timetable, assignment) and extracts structured data

**Database Layer** (`src/database/`)
- `models.py` - SQLite schema (user_config, events, schedule, assignments, tasks, todos, voice_notes, etc.)
- `operations.py` - `DatabaseOperations` class with CRUD methods. `get_subject_aliases()` builds name→code mappings from schedule

**Scheduler** (`src/scheduler/`)
- `notifications.py` - APScheduler-based. Notification schedule:
  - 10:00 PM: Tomorrow's classes briefing
  - 8:00 PM: Off-day alert
  - 12:00 AM: Midnight TODO review
  - Every 30 min: Assignment/Task/TODO/Exam reminder checks

**Utils** (`src/utils/`)
- `semester_logic.py` - Week calculation (14-week semester with mid-break), `get_today()`, `get_now()`
- `translations.py` - Multi-language support (English/Malay) via `get_text(key, lang)`

### Key Patterns
- **Timezone**: All times use `Asia/Kuala_Lumpur` (MY_TZ)
- **Authorization**: All handlers wrapped with `authorized()` decorator in `register_handlers()`. Uses `ALLOWED_USER_ID` from config
- **Test Overrides**: `get_today()` and `get_now()` support `_test_date_override` / `_test_time_override`. Settings menu shows override status with reset buttons
- **Semester Structure**: 14 weeks (Week 1-6, mid-break, Week 7-14, inter-semester break)
- **Subject Aliases**: `get_subject_aliases()` maps subject names/abbreviations to codes (e.g., "os" → "BITI1213", "sp" → "Statistics and Probability"). Skips filler words (and, or, of) when building abbreviations
- **Lab Test/Exam**: When adding exams via NLP, system looks up schedule to find actual day/time for the subject's class type (LAB/LEC)
- **Callback Handling**: All inline button callbacks go through `callback_query_handler()` in handlers.py

### Reminder Systems
All reminders are checked every 30 minutes. Each level triggers only once per item.

**Assignment Reminders** (7 levels):
| Level | Hours Before | Message |
|-------|--------------|---------|
| 1 | 72h (3 days) | "due in 3 days" |
| 2 | 48h (2 days) | "due in 2 days" |
| 3 | 24h (1 day) | "due TOMORROW" |
| 4 | 8h | "8 hours left" |
| 5 | 3h | "3 hours left" |
| 6 | 1h | "1 hour remaining" |
| 7 | 0h | "NOW DUE" |

**Exam Reminders** (4 levels):
| Level | Hours Before | Message |
|-------|--------------|---------|
| 1 | 168h (1 week) | "Exam in 1 WEEK" |
| 2 | 72h (3 days) | "Exam in 3 DAYS" |
| 3 | 24h (1 day) | "Exam TOMORROW" |
| 4 | 3h | "Exam in 3 HOURS" |

**Task Reminders** (2 levels):
- 1 day before (at 8 PM): "Task Tomorrow"
- 2 hours before (if time set): "Task in 2 hours"

**TODO Reminders** (1 level):
- 1 hour before (if time set): "TODO Reminder"

### Voice Notes Flow
1. User sends voice message → `handle_voice_message()` transcribes via Gemini
2. User selects processing type (summary, minutes, tasks, study notes, transcript)
3. Processed content saved to `voice_notes` table
4. `/notes` command lists and manages saved notes

## Environment Variables

```
TELEGRAM_TOKEN=<bot token from @BotFather>
GEMINI_API_KEY=<Google Gemini API key>
DATABASE_PATH=data/bot.db  (optional, defaults to data/bot.db)
ALLOWED_USER_ID=561393547  (optional, restricts bot to single user)
```

## Debug Commands

- `/setdate YYYY-MM-DD` - Override current date
- `/settime HH:MM` - Override current time
- `/trigger <type>` - Trigger notifications: briefing, offday, midnight, assignments, tasks, todos, exams, semester
- Settings menu shows current date/time with override warnings and reset buttons

## Adding Features

1. Database: Add table/columns in `models.py`, CRUD in `operations.py`
2. Bot: Add handler in `handlers.py`, wrap with `authorized()` in `register_handlers()`
3. UI: Add callbacks in `callback_query_handler()`, keyboards in `keyboards.py`
4. NLP: Add regex patterns in `intent_parser.py` (before Gemini fallback for common patterns)
5. i18n: Add translations in `translations.py`

## Production Deployment

Use `productivity-bot.service` for systemd deployment:
```bash
# Edit service file with your username
sed -i 's/your_username/'"$USER"'/g' productivity-bot.service

# Install and start
sudo cp productivity-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable productivity-bot
sudo systemctl start productivity-bot

# View logs
sudo journalctl -u productivity-bot -f
```
