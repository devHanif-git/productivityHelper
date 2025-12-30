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
- `run.py` - Alternative run script (simpler, without scheduler lifecycle hooks)

### Core Components

**Bot Layer** (`src/bot/`)
- `handlers.py` - Telegram command handlers and message routing by intent. Handles text, photos, and voice messages. Contains debug commands (`/setdate`, `/settime`, `/trigger`) for testing.
- `conversations.py` - Multi-step conversation flows (onboarding, assignment confirmation) and response formatters
- `keyboards.py` - Telegram inline keyboard layouts (main menu, settings, voice processing options, note actions)

**AI Layer** (`src/ai/`)
- `gemini_client.py` - Google Gemini API wrapper (singleton via `get_gemini_client()`). Supports:
  - Text prompts (`send_text`)
  - Image analysis (`send_image`, `send_image_with_json`)
  - Audio transcription (`transcribe_audio`, `process_audio_content`)
  - AI suggestions (`get_ai_suggestions`)
- `intent_parser.py` - NLP intent classification with `Intent` enum. Uses regex for common queries, Gemini for complex messages.
- `image_parser.py` - Detects image types (calendar, timetable, assignment) and extracts structured data

**Database Layer** (`src/database/`)
- `models.py` - SQLite schema. Tables: user_config, events, schedule, assignments, tasks, todos, online_overrides, voice_notes, action_history, notification_settings
- `operations.py` - `DatabaseOperations` class with CRUD methods for all tables

**Scheduler** (`src/scheduler/`)
- `notifications.py` - `NotificationScheduler` class using APScheduler. Daily briefings include AI-powered suggestions when pending items exist.

**Utils** (`src/utils/`)
- `semester_logic.py` - Week calculation (14-week semester with mid-break), break classification, date helpers
- `translations.py` - Multi-language support (English/Malay) via `get_text(key, lang)`

### Data Flow
1. User sends message/image/voice to Telegram
2. `handlers.py` receives via python-telegram-bot
3. For text: `intent_parser.py` classifies intent using regex or Gemini
4. For images: `image_parser.py` detects type and extracts data
5. For voice: `gemini_client.py` transcribes, then user selects processing type
6. Handler executes action (database CRUD via `operations.py`)
7. Response includes inline keyboard for menu persistence

### Key Patterns
- **Timezone**: All times use `Asia/Kuala_Lumpur` (MY_TZ)
- **Test Overrides**: `get_today()` and `get_now()` support `_test_date_override` / `_test_time_override`
- **Semester Structure**: 14 weeks (Week 1-6, mid-break, Week 7-14, inter-semester break)
- **Menu Persistence**: Inline keyboards remain visible after button presses via `get_content_with_menu_keyboard()`
- **Callback Handling**: All inline button callbacks go through `callback_query_handler()` in handlers.py

## Environment Variables

```
TELEGRAM_TOKEN=<bot token from @BotFather>
GEMINI_API_KEY=<Google Gemini API key>
DATABASE_PATH=data/bot.db  (optional, defaults to data/bot.db)
```

## Testing Debug Commands

- `/setdate YYYY-MM-DD` - Override current date
- `/settime HH:MM` - Override current time
- `/trigger <type>` - Manually trigger notifications (briefing, offday, midnight, assignments, tasks, todos, semester)

## Adding New Features

When adding features:
1. Add database table/columns in `models.py` if needed
2. Add CRUD operations in `operations.py`
3. Add command handler in `handlers.py` and register in `register_handlers()`
4. Add callback handlers in `callback_query_handler()` for inline buttons
5. Add keyboard layouts in `keyboards.py` if interactive UI needed
6. Add intent patterns in `intent_parser.py` for natural language support
7. Add translations in `translations.py` for multi-language support
