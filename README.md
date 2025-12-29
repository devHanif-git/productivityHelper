# UTeM Student Assistant Bot

A Telegram bot that helps UTeM students manage their academic schedule, assignments, tasks, and TODOs with AI-powered image recognition and proactive notifications.

## Features

### Schedule Management
- **Image Recognition**: Upload your academic calendar and class timetable images for automatic extraction
- **Smart Queries**: Ask natural questions like "What class tomorrow?" or "What week is this?"
- **Holiday Detection**: Automatic detection of holidays and off-days

### Task Tracking
- **Assignments**: Track assignments with 7-level escalating reminders (3 days → 2 days → 1 day → 8 hours → 3 hours → 1 hour → due)
- **Tasks/Meetings**: Schedule meetings with 1-day and 2-hour reminders
- **TODOs**: Quick personal tasks with optional time-based reminders

### Proactive Notifications
| Time | Notification |
|------|--------------|
| 10:00 PM | Tomorrow's classes briefing |
| 8:00 PM | Off-day alert (if applicable) |
| 12:00 AM | Midnight TODO review |
| Every 30 min | Assignment/Task/TODO reminder checks |

### Natural Language Processing
- "Assignment report for BITP1113 due Friday 5pm" → Adds assignment
- "Meet Dr Intan tomorrow 10am" → Adds task
- "Take wife at Satria at 3pm" → Adds TODO
- "Done with BITP report" → Marks matching item complete

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and user registration |
| `/setup` | Onboarding flow (calendar + timetable upload) |
| `/help` | Show all available commands |
| `/status` | Overview of pending items |
| `/tomorrow` | Tomorrow's classes |
| `/week` | This week's full schedule |
| `/week_number` | Current semester week |
| `/offday` | Next upcoming holiday |
| `/assignments` | List pending assignments |
| `/tasks` | List upcoming tasks |
| `/todos` | List pending TODOs |
| `/done <type> <id>` | Mark item as complete |

### Debug/Testing Commands

| Command | Description |
|---------|-------------|
| `/setdate YYYY-MM-DD` | Set test date override |
| `/resetdate` | Reset to real system date |
| `/settime HH:MM` | Set test time override (24-hour format) |
| `/resettime` | Reset to real system time |
| `/trigger <type>` | Manually trigger a notification |

**Available trigger types:**
- `briefing` - 10PM class briefing
- `offday` - 8PM off-day alert
- `midnight` - 12AM TODO review
- `assignments` - Assignment reminder check
- `tasks` - Task reminder check
- `todos` - TODO reminder check
- `semester` - Semester starting notification

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.10+ |
| Bot Framework | python-telegram-bot (async) |
| AI | Google Gemini API |
| Database | SQLite3 |
| Scheduler | APScheduler |
| Config | python-dotenv |

## Installation

### Prerequisites
- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Gemini API Key

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/utem-bot.git
cd utem-bot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the bot:
```bash
python -m src.main
```

### Production Deployment (Ubuntu)

1. Run the installation script:
```bash
sudo bash deploy/install.sh
```

2. Configure your API keys:
```bash
sudo nano /opt/utem-bot/.env
```

3. Start the service:
```bash
sudo systemctl start utem-bot
sudo systemctl status utem-bot
```

4. View logs:
```bash
journalctl -u utem-bot -f
```

## Configuration

Create a `.env` file with the following variables:

```env
TELEGRAM_TOKEN=your_bot_token_here
GEMINI_API_KEY=your_gemini_key_here
DATABASE_PATH=data/bot.db
```

## Project Structure

```
productivity/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Settings & env loading
│   ├── database/
│   │   ├── models.py           # SQLite schema
│   │   └── operations.py       # CRUD functions
│   ├── ai/
│   │   ├── gemini_client.py    # API wrapper
│   │   ├── image_parser.py     # Calendar/timetable extraction
│   │   └── intent_parser.py    # NL command classification
│   ├── bot/
│   │   ├── handlers.py         # Telegram command handlers
│   │   └── conversations.py    # Multi-step flows
│   ├── scheduler/
│   │   └── notifications.py    # Daily briefing, reminders
│   └── utils/
│       ├── semester_logic.py   # Week calculation
│       ├── logging_config.py   # Logging setup
│       └── error_handlers.py   # Error handling
├── tests/
│   ├── test_semester_logic.py
│   ├── test_database.py
│   └── test_image_parser.py
├── deploy/
│   ├── utem-bot.service        # Systemd service
│   ├── backup.sh               # Database backup script
│   └── install.sh              # Installation script
├── data/                       # SQLite database (gitignored)
├── logs/                       # Log files (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_semester_logic.py -v
```

## Database Backup

Automatic backups run daily at 2 AM via cron. Manual backup:
```bash
/opt/utem-bot/deploy/backup.sh
```

Backups are stored in `/opt/utem-bot/backups/` with 7-day retention.

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.
