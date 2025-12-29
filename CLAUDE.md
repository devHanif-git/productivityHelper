# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UTeM Student Assistant Bot - A Telegram bot helping UTeM students manage academic schedules, assignments, tasks, and TODOs with AI-powered image recognition (Google Gemini) and proactive notifications.

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
- `run.py` - Alternative run script (simpler, without scheduler lifecycle hooks)

### Core Components

**Bot Layer** (`src/bot/`)
- `handlers.py` - Telegram command handlers (`/start`, `/help`, `/tomorrow`, `/assignments`, etc.) and message routing by intent. Contains debug commands (`/setdate`, `/settime`, `/trigger`) for testing time-sensitive features.
- `conversations.py` - Multi-step conversation flows (onboarding, assignment confirmation)

**AI Layer** (`src/ai/`)
- `gemini_client.py` - Google Gemini API wrapper (singleton pattern via `get_gemini_client()`). Supports text prompts and vision/image analysis.
- `intent_parser.py` - NLP intent classification with `Intent` enum. Uses regex for common queries, Gemini for complex messages. Returns `ClassificationResult` with intent and `ParsedEntities`.
- `image_parser.py` - Detects image types (calendar, timetable, assignment) and extracts structured data

**Database Layer** (`src/database/`)
- `models.py` - SQLite schema (user_config, events, schedule, assignments, tasks, todos). Uses `row_factory = sqlite3.Row`.
- `operations.py` - `DatabaseOperations` class with CRUD methods for all tables

**Scheduler** (`src/scheduler/`)
- `notifications.py` - `NotificationScheduler` class using APScheduler. Handles:
  - Daily briefings (10PM class briefing, 8PM off-day alert, 12AM TODO review)
  - Escalating assignment reminders (7 levels: 3 days → due)
  - Task reminders (1 day before, 2 hours before)
  - TODO reminders (1 hour before for time-specific)
  - Semester starting notification (1 week before break ends)

**Utils** (`src/utils/`)
- `semester_logic.py` - Week calculation (14-week semester with mid-break), break classification, date helpers
- `logging_config.py` - Logging setup with file output
- `error_handlers.py` - Global error handling

### Data Flow
1. User sends message/image to Telegram
2. `handlers.py` receives via python-telegram-bot
3. For text: `intent_parser.py` classifies intent using regex or Gemini
4. For images: `image_parser.py` detects type and extracts data
5. Handler executes action (database CRUD via `operations.py`)
6. Background: `NotificationScheduler` runs scheduled jobs every 30 min / at specific times

### Key Patterns
- **Timezone**: All times use `Asia/Kuala_Lumpur` (MY_TZ)
- **Test Overrides**: `get_today()` and `get_now()` in handlers.py support `_test_date_override` / `_test_time_override` for debugging
- **Semester Structure**: 14 weeks (Week 1-6, mid-break, Week 7-14, inter-semester break)

## Environment Variables

```
TELEGRAM_TOKEN=<bot token from @BotFather>
GEMINI_API_KEY=<Google Gemini API key>
DATABASE_PATH=data/bot.db  (optional, defaults to data/bot.db)
```

## Testing Debug Commands

The bot includes debug commands for testing time-sensitive notifications:
- `/setdate YYYY-MM-DD` - Override current date
- `/settime HH:MM` - Override current time
- `/trigger <type>` - Manually trigger notifications (briefing, offday, midnight, assignments, tasks, todos, semester)
