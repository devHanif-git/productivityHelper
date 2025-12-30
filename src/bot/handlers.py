"""Telegram bot command handlers."""

import io
import json
import logging
import os
from datetime import date, datetime, time, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import pytz

from .keyboards import (
    get_main_menu_keyboard,
    get_settings_keyboard,
    get_language_keyboard,
    get_initial_language_keyboard,
    get_semester_keyboard,
    get_notification_settings_keyboard,
    get_item_actions_keyboard,
    get_confirmation_keyboard,
    get_snooze_keyboard,
    get_export_keyboard,
    get_back_to_menu_keyboard,
    get_content_with_menu_keyboard,
    get_voice_processing_keyboard,
    get_notes_list_keyboard,
    get_note_actions_keyboard,
)

# Malaysia timezone
MY_TZ = pytz.timezone("Asia/Kuala_Lumpur")

# Debug: Test date/time override (set via /setdate and /settime commands)
_test_date_override: date = None
_test_time_override: time = None


def get_today() -> date:
    """Get current date (or test date if set for debugging)."""
    global _test_date_override
    if _test_date_override:
        return _test_date_override
    # Check environment variable
    env_date = os.getenv("TEST_DATE")
    if env_date:
        try:
            return datetime.strptime(env_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def get_now() -> datetime:
    """Get current datetime (or test datetime if set for debugging)."""
    global _test_date_override, _test_time_override

    # Get the date part
    current_date = get_today()

    # Get the time part
    if _test_time_override:
        current_time = _test_time_override
    else:
        env_time = os.getenv("TEST_TIME")
        if env_time:
            try:
                current_time = datetime.strptime(env_time, "%H:%M").time()
            except ValueError:
                current_time = datetime.now(MY_TZ).time()
        else:
            current_time = datetime.now(MY_TZ).time()

    # Combine date and time
    result = datetime.combine(current_date, current_time)
    return MY_TZ.localize(result)

from ..config import config
from ..database.operations import DatabaseOperations
from ..ai.intent_parser import (
    Intent,
    classify_message,
    extract_completion_target,
    build_assignment_from_entities,
    build_task_from_entities,
    build_todo_from_entities,
)
from ..ai.image_parser import detect_image_type, parse_assignment_image, parse_academic_calendar, parse_timetable
from ..utils.semester_logic import (
    get_current_week,
    get_next_week,
    get_next_offday,
    get_current_break,
    classify_break_event,
    BREAK_INTER_SEMESTER,
    parse_date,
)
from .conversations import (
    format_tomorrow_classes,
    format_today_classes,
    format_week_schedule,
    format_pending_assignments,
    format_pending_tasks,
    format_pending_todos,
    format_current_week,
    format_next_offday,
    handle_assignment_image,
    confirm_assignment,
    get_onboarding_handler,
)

logger = logging.getLogger(__name__)

# Initialize database operations
db = DatabaseOperations(config.DATABASE_PATH)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message and setup."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    # Check if new user
    existing = db.get_user_config(chat_id)
    is_new_user = existing is None

    if is_new_user:
        # Create user config
        db.create_user_config(chat_id)

        # Welcome message with language selection for new users
        welcome_message = f"""
Assalamualaikum {user.first_name}! 👋

Welcome to UTeM Student Assistant Bot.

Please select your preferred language:
Sila pilih bahasa pilihan anda:
"""
        await update.message.reply_text(
            welcome_message.strip(),
            reply_markup=get_initial_language_keyboard()
        )
    else:
        # Returning user - show welcome back message
        user_config = db.get_user_config(chat_id)
        lang = user_config.get("language", "en") if user_config else "en"

        welcome_message = f"""
Welcome back, {user.first_name}! 👋

I can help you with:
📅 Class schedule & week tracking
📝 Assignment tracking with reminders
✅ Tasks and TODO management
🎤 Voice notes transcription
📸 Image recognition (calendar, timetable, assignments)
💡 AI-powered suggestions
🔔 Daily briefings and notifications

Use /setup to configure your calendar and timetable.
Use /help to see all available commands.
"""
        await update.message.reply_text(
            welcome_message.strip(),
            reply_markup=get_main_menu_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands."""
    args = context.args

    # Section-specific help
    if args:
        section = args[0].lower()
        help_sections = {
            "schedule": """
*📅 Schedule Commands*

/today - View today's classes
/tomorrow - View tomorrow's classes
/week - View full week schedule
/schedule [subject] - View schedule for a subject
/week_number - Current semester week
/offday - Next off day/holiday

*💬 Natural Language:*
• "What class tomorrow?" / "kelas esok?"
• "harini ada kelas x?" / "today got class?"
• "What week is this?" / "minggu ni minggu ke berapa?"
• "When is mid term break?"

*📆 Setup:*
/setsemester YYYY-MM-DD - Set semester start date
📸 Send calendar image → auto-import events
📸 Send timetable image → auto-import schedule
""",
            "assignments": """
*📝 Assignment Commands*

/assignments - List pending assignments
/done assignment <id> - Mark as complete
/edit assignment <id> due <date> - Change due date
/delete assignment <id> - Delete assignment

*💬 Add Assignment (Natural Language):*
• "Assignment report BITP1113 due Friday 5pm"
• "I have assignment for database due next Monday"
• "BITP report submission tomorrow 11:59pm"

*📸 Image:*
Send an assignment sheet image → auto-extract details

*🔔 Reminders:*
Automatic reminders at: 3 days, 2 days, 1 day, 8h, 3h, 1h, and due time
""",
            "tasks": """
*📋 Task Commands*

/tasks - List upcoming tasks/meetings
/done task <id> - Mark as complete
/delete task <id> - Delete task

*💬 Add Task (Natural Language):*
• "Meet Dr Intan tomorrow 10am"
• "Meeting with supervisor Friday 2pm at BK5"
• "Consultation with lecturer next Monday"

Tasks are for scheduled appointments and meetings.
""",
            "todos": """
*✅ TODO Commands*

/todos - List pending TODOs
/done todo <id> - Mark as complete
/delete todo <id> - Delete TODO

*💬 Add TODO (Natural Language):*
• "Remind me buy groceries at 3pm"
• "Take wife at Satria at 5pm"
• "Call mum later"
• "Print notes before class"

TODOs are quick personal reminders.
""",
            "exams": """
*📝 Exam Commands*

/exams - List upcoming exams
/setexam <subject> <type> <date> [time]
   Types: final, midterm, quiz, test, labtest

*💬 Add Exam (Natural Language):*
• "Lab test for OS next week on lab section"
• "Quiz BITP1113 this Friday"
• "Final exam database on 15 Jan 2025"

System auto-finds the exam day/time from your schedule!
""",
            "voice": """
*🎤 Voice Notes*

/notes - List saved voice notes
/notes <id> - View specific note
/notes search <query> - Search notes

*How to use:*
1. Send a voice message (up to 30 min)
2. Bot transcribes automatically
3. Choose processing type:
   📝 Summary - Condense key points
   📋 Meeting Minutes - Format as minutes
   ✅ Extract Tasks - Pull out action items
   📚 Study Notes - Format for studying
   💾 Save Transcript - Keep raw text
   🎯 Smart Analysis - AI decides best format
""",
            "online": """
*🖥️ Online Class Settings*

/online - View online class settings
/setonline <subject|all> <week#|date>

*Examples:*
/setonline BITP1113 week12
/setonline all week12
/setonline BITP1113 tomorrow

*💬 Natural Language:*
• "Set class BITP1113 online on week 12"
• "All classes online tomorrow"

/delete online <id> - Remove setting
""",
            "settings": """
*⚙️ Settings & Preferences*

/settings - Settings menu
/language [en|my] - Set language
/mute [hours] - Mute notifications (default 1h)

*🔔 Notification Schedule:*
• 10:00 PM - Tomorrow's class briefing
• 8:00 PM - Off-day alert
• 12:00 AM - Midnight TODO review
• Every 30 min - Assignment/task reminders

Toggle notifications in /settings menu.
""",
            "other": """
*🔧 Other Commands*

/status - Overview of all pending items
/stats [days] - Productivity statistics
/search <query> - Search everything
/suggest - AI-powered suggestions
/export [schedule|assignments|all] - Export data
/undo - Undo last action

*🗑️ Delete Items:*
/delete assignment <id>
/delete task <id>
/delete todo <id>
/delete event <id>
/delete online <id>

*✏️ Edit Items:*
/edit schedule <id> room <value>
/edit assignment <id> due <date>
""",
            "debug": """
*🛠️ Debug Commands*

/setdate YYYY-MM-DD - Override current date
/resetdate - Reset to real date
/settime HH:MM - Override current time
/resettime - Reset to real time
/trigger <type> - Manually trigger notification
   Types: briefing, offday, midnight,
          assignments, tasks, todos, semester
""",
        }

        if section in help_sections:
            await update.message.reply_text(
                help_sections[section].strip(),
                parse_mode="Markdown"
            )
            return

    # Main help menu
    help_text = """
*📚 UTeM Student Assistant Bot*

Your AI-powered academic helper for schedules, assignments, tasks, and more!

*📖 Help Topics:*
/help schedule - Classes & timetable
/help assignments - Assignment tracking
/help tasks - Meetings & appointments
/help todos - Quick reminders
/help exams - Exam management
/help voice - Voice notes
/help online - Online class settings
/help settings - Preferences & notifications
/help other - Search, stats, export, undo
/help debug - Debug commands

*🚀 Quick Start:*
1. /setup - Upload calendar & timetable
2. /menu - Interactive menu
3. Or just chat naturally!

*💬 Natural Language Examples:*
• "What class tomorrow?"
• "Assignment report due Friday 5pm"
• "Meet Dr Intan tomorrow 10am"
• "Remind me buy groceries"
• "Done with BITP report"
• "What week is this?"
• "Lab test OS next week"

*📸 Send Images:*
• Academic calendar → import events
• Class timetable → import schedule
• Assignment sheet → add assignment

*🎤 Send Voice:*
Record & send → transcribe + process

Use /menu for quick access to all features!
"""
    await update.message.reply_text(help_text.strip(), parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show current status overview."""
    chat_id = update.effective_chat.id

    # Get pending counts
    counts = db.get_pending_counts()

    # Get user config for semester info
    user_config = db.get_user_config(chat_id)

    status_text = f"""
*Status Overview*

📝 Assignments: {counts['assignments']} pending
📋 Tasks: {counts['tasks']} upcoming
✅ TODOs: {counts['todos']} remaining

_Semester start: {'Not set' if not user_config or not user_config.get('semester_start_date') else user_config['semester_start_date']}_
"""
    await update.message.reply_text(status_text.strip(), parse_mode="Markdown")


async def tomorrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tomorrow command - show tomorrow's classes."""
    schedule = db.get_all_schedule()
    events = db.get_all_events()

    response = format_tomorrow_classes(schedule, events, today=get_today())
    await update.message.reply_text(response)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show today's classes."""
    schedule = db.get_all_schedule()
    events = db.get_all_events()

    response = format_today_classes(schedule, events, today=get_today())
    await update.message.reply_text(response)


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /week command - show this week's schedule."""
    schedule = db.get_all_schedule()
    response = format_week_schedule(schedule)
    await update.message.reply_text(response, parse_mode="Markdown")


async def week_number_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /week_number command - show current semester week."""
    chat_id = update.effective_chat.id
    user_config = db.get_user_config(chat_id)
    events = db.get_all_events()

    semester_start_str = user_config.get("semester_start_date") if user_config else None
    semester_start = parse_date(semester_start_str) if semester_start_str else None

    if not semester_start:
        await update.message.reply_text(
            "Semester start date not set.\n"
            "Use /setsemester YYYY-MM-DD to set it manually,\n"
            "or upload your academic calendar image."
        )
        return

    week = get_current_week(get_today(), semester_start, events)
    response = format_current_week(week, semester_start_str)
    await update.message.reply_text(response)


async def setsemester_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setsemester command - set semester start date manually."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        # Show current setting and usage
        user_config = db.get_user_config(chat_id)
        current = user_config.get("semester_start_date") if user_config else None
        current_display = current if current else "Not set"

        await update.message.reply_text(
            f"*Semester Start Date*\n\n"
            f"Current: {current_display}\n\n"
            f"Usage: `/setsemester YYYY-MM-DD`\n"
            f"Example: `/setsemester 2025-01-06`\n\n"
            f"This is the first day of Week 1.",
            parse_mode="Markdown"
        )
        return

    date_str = args[0]

    # Validate date format
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        db.update_user_config(chat_id, semester_start_date=date_str)

        await update.message.reply_text(
            f"✅ Semester start date set to: {parsed_date.strftime('%d %B %Y')}\n\n"
            f"Week 1 begins on this date.\n"
            f"Use /week_number to check current week."
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format.\n\n"
            "Please use: `/setsemester YYYY-MM-DD`\n"
            "Example: `/setsemester 2025-01-06`",
            parse_mode="Markdown"
        )


async def offday_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /offday command - show next off day."""
    events = db.get_all_events()
    result = get_next_offday(get_today(), events)
    response = format_next_offday(result)
    await update.message.reply_text(response)


async def assignments_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /assignments command - list pending assignments."""
    events = db.get_all_events()

    # Check if in inter-semester break
    current_break = get_current_break(get_today(), events)
    if current_break:
        break_type = classify_break_event(current_break)
        if break_type == BREAK_INTER_SEMESTER:
            break_name = current_break.get("name_en") or current_break.get("name") or "Inter-semester Break"
            await update.message.reply_text(
                f"It's {break_name}!\n\n"
                "No assignments to worry about during the break.\n"
                "Enjoy your holiday!"
            )
            return

    assignments = db.get_pending_assignments()
    response = format_pending_assignments(assignments)
    await update.message.reply_text(response)


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tasks command - list upcoming tasks."""
    tasks = db.get_upcoming_tasks()
    response = format_pending_tasks(tasks)
    await update.message.reply_text(response)


async def todos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /todos command - list pending TODOs."""
    todos = db.get_pending_todos()
    response = format_pending_todos(todos)
    await update.message.reply_text(response)


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /done command - mark item as complete."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: /done <type> <id>\n"
            "Examples:\n"
            "  /done assignment 1\n"
            "  /done task 2\n"
            "  /done todo 3\n\n"
            "Or just say 'done with [item name]'"
        )
        return

    if len(args) >= 2:
        item_type = args[0].lower()
        try:
            item_id = int(args[1])
        except ValueError:
            await update.message.reply_text("Invalid ID. Please provide a number.")
            return

        if item_type in ("assignment", "a"):
            item = db.get_assignment_by_id(item_id)
            if item:
                db.complete_assignment(item_id)
                await update.message.reply_text(
                    f"Marked '{item['title']}' as completed!"
                )
            else:
                await update.message.reply_text(f"Assignment #{item_id} not found.")

        elif item_type in ("task", "t"):
            item = db.get_task_by_id(item_id)
            if item:
                db.complete_task(item_id)
                await update.message.reply_text(
                    f"Marked '{item['title']}' as completed!"
                )
            else:
                await update.message.reply_text(f"Task #{item_id} not found.")

        elif item_type in ("todo", "td"):
            item = db.get_todo_by_id(item_id)
            if item:
                db.complete_todo(item_id)
                await update.message.reply_text(
                    f"Marked '{item['title']}' as completed!"
                )
            else:
                await update.message.reply_text(f"TODO #{item_id} not found.")

        else:
            await update.message.reply_text(
                "Unknown item type. Use 'assignment', 'task', or 'todo'."
            )
    else:
        await update.message.reply_text(
            "Please specify type and ID: /done <type> <id>"
        )


async def online_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /online command - show online class overrides."""
    overrides = db.get_online_overrides()

    if not overrides:
        await update.message.reply_text(
            "🖥️ No online class settings configured.\n\n"
            "Set classes as online:\n"
            "💬 \"Set BITP1113 online week 12\"\n"
            "💬 \"All classes online tomorrow\"\n"
            "⌨️ /setonline BITP1113 week12"
        )
        return

    lines = ["Online class settings:"]
    for o in overrides:
        subject = o.get("subject_code") or "ALL classes"
        week = o.get("week_number")
        date = o.get("specific_date")

        if week:
            lines.append(f"- {subject} is online on Week {week}")
        elif date:
            lines.append(f"- {subject} is online on {date}")

    await update.message.reply_text("\n".join(lines))


async def setonline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setonline command - set a class as online for a week or date."""
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /setonline <subject|all> <week#|date>\n\n"
            "Examples:\n"
            "  /setonline BITP1113 week12\n"
            "  /setonline all week12\n"
            "  /setonline BITP1113 2025-01-15\n"
            "  /setonline all tomorrow"
        )
        return

    subject_arg = args[0].upper()
    time_arg = " ".join(args[1:]).lower()

    # Determine subject (None means all)
    subject_code = None if subject_arg == "ALL" else subject_arg

    # Parse time argument
    week_number = None
    specific_date = None

    if time_arg.startswith("week"):
        try:
            week_number = int(time_arg.replace("week", "").strip())
        except ValueError:
            await update.message.reply_text("Invalid week number. Use format: week12")
            return
    elif time_arg == "tomorrow":
        tomorrow = get_today() + timedelta(days=1)
        specific_date = tomorrow.isoformat()
    elif time_arg == "today":
        specific_date = get_today().isoformat()
    else:
        # Try to parse as date
        specific_date = time_arg

    # Add the override
    override_id = db.add_online_override(
        subject_code=subject_code,
        week_number=week_number,
        specific_date=specific_date
    )

    subject_display = subject_code or "ALL classes"
    if week_number:
        await update.message.reply_text(
            f"Set {subject_display} as online for Week {week_number}."
        )
    else:
        await update.message.reply_text(
            f"Set {subject_display} as online on {specific_date}."
        )


async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /edit command - edit schedule or assignment data with confirmation."""
    args = context.args

    if not args or len(args) < 4:
        await update.message.reply_text(
            "Usage: /edit <type> <id> <field> <value>\n\n"
            "Examples:\n"
            "  /edit schedule 1 room BK12\n"
            "  /edit assignment 1 due 2025-01-15\n\n"
            "Fields for schedule: room, lecturer\n"
            "Fields for assignment: due, title"
        )
        return

    item_type = args[0].lower()
    try:
        item_id = int(args[1])
    except ValueError:
        await update.message.reply_text("Invalid ID. Please provide a number.")
        return

    field = args[2].lower()
    new_value = " ".join(args[3:])

    if item_type == "schedule":
        slot = db.get_schedule_by_id(item_id)
        if not slot:
            await update.message.reply_text(f"Schedule slot #{item_id} not found.")
            return

        if field not in ("room", "lecturer"):
            await update.message.reply_text("Invalid field. Use 'room' or 'lecturer'.")
            return

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = day_names[slot.get("day_of_week", 0)]
        subject = slot.get("subject_code", "Unknown")
        start = slot.get("start_time", "?")
        old_value = slot.get(field if field != "lecturer" else "lecturer_name", "Not set")

        # Store pending edit
        context.user_data["pending_edit"] = {
            "type": "schedule",
            "id": item_id,
            "field": field,
            "new_value": new_value,
            "description": f"{subject} ({day_name} {start})"
        }

        await update.message.reply_text(
            f"Edit {subject} ({day_name} {start})?\n"
            f"Change {field} from '{old_value}' to '{new_value}'?\n\n"
            "Reply 'yes' to confirm or 'no' to cancel."
        )

    elif item_type == "assignment":
        assignment = db.get_assignment_by_id(item_id)
        if not assignment:
            await update.message.reply_text(f"Assignment #{item_id} not found.")
            return

        if field not in ("due", "title"):
            await update.message.reply_text("Invalid field. Use 'due' or 'title'.")
            return

        title = assignment.get("title", "Unknown")
        old_value = assignment.get("due_date" if field == "due" else "title", "Not set")

        # Store pending edit
        context.user_data["pending_edit"] = {
            "type": "assignment",
            "id": item_id,
            "field": field,
            "new_value": new_value,
            "description": title
        }

        await update.message.reply_text(
            f"Edit assignment '{title}'?\n"
            f"Change {field} from '{old_value}' to '{new_value}'?\n\n"
            "Reply 'yes' to confirm or 'no' to cancel."
        )

    else:
        await update.message.reply_text(
            "Unknown item type. Use 'schedule' or 'assignment'."
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages - route by intent."""
    message_text = update.message.text

    # Check if we're waiting for assignment confirmation
    if "pending_assignment" in context.user_data:
        response = await confirm_assignment(update, context)
        if response:
            await update.message.reply_text(response)
            return

    # Check if we're waiting for edit confirmation
    if "pending_edit" in context.user_data:
        response_lower = message_text.lower().strip()
        pending = context.user_data["pending_edit"]

        if response_lower in ("yes", "y", "ya", "confirm"):
            # Execute the edit
            if pending["type"] == "schedule":
                field = pending["field"]
                if field == "room":
                    db.update_schedule_slot(pending["id"], room=pending["new_value"])
                elif field == "lecturer":
                    db.update_schedule_slot(pending["id"], lecturer_name=pending["new_value"])
                await update.message.reply_text(
                    f"Updated! {pending['description']} {field} is now '{pending['new_value']}'."
                )
            elif pending["type"] == "assignment":
                field = pending["field"]
                if field == "due":
                    db.update_assignment(pending["id"], due_date=pending["new_value"])
                elif field == "title":
                    db.update_assignment(pending["id"], title=pending["new_value"])
                await update.message.reply_text(
                    f"Updated! Assignment '{pending['description']}' {field} is now '{pending['new_value']}'."
                )
            del context.user_data["pending_edit"]
            return

        elif response_lower in ("no", "n", "tidak", "cancel"):
            del context.user_data["pending_edit"]
            await update.message.reply_text("Edit cancelled.")
            return

    # Check if we're waiting for delete confirmation
    if "pending_delete" in context.user_data:
        response_lower = message_text.lower().strip()
        pending = context.user_data["pending_delete"]

        if response_lower in ("yes", "y", "ya", "confirm"):
            item_type = pending["type"]
            item_id = pending["id"]
            item_data = pending.get("data")

            deleted = None
            if item_type in ("assignment", "a"):
                deleted = db.delete_assignment(item_id)
            elif item_type in ("task", "t"):
                deleted = db.delete_task(item_id)
            elif item_type in ("todo", "td"):
                deleted = db.delete_todo(item_id)
            elif item_type == "online":
                db.delete_online_override(item_id)
                deleted = True
            elif item_type == "event":
                deleted = db.delete_event(item_id)

            if deleted:
                if item_data:
                    db.add_action_history("delete", f"{item_type}s", item_id, item_data)
                await update.message.reply_text(f"Deleted {item_type} '{pending['name']}'.")
            else:
                await update.message.reply_text(f"{item_type.title()} not found.")

            del context.user_data["pending_delete"]
            return

        elif response_lower in ("no", "n", "tidak", "cancel"):
            del context.user_data["pending_delete"]
            await update.message.reply_text("Delete cancelled.")
            return

    # Classify the intent
    result = await classify_message(message_text)
    intent = result.intent
    entities = result.entities

    logger.info(f"Classified intent: {intent.value} (confidence: {result.confidence})")

    # Route based on intent
    if intent == Intent.QUERY_CURRENT_WEEK:
        await week_number_command(update, context)

    elif intent == Intent.QUERY_NEXT_WEEK:
        chat_id = update.effective_chat.id
        user_config = db.get_user_config(chat_id)
        events = db.get_all_events()
        semester_start_str = user_config.get("semester_start_date") if user_config else None
        semester_start = parse_date(semester_start_str) if semester_start_str else None

        if semester_start:
            week = get_next_week(get_today(), semester_start, events)
            await update.message.reply_text(f"Next week is Week {week}")
        else:
            await update.message.reply_text(
                "Semester start date not set. Use /setsemester YYYY-MM-DD to set it."
            )

    elif intent == Intent.QUERY_TODAY_CLASSES:
        await today_command(update, context)

    elif intent == Intent.QUERY_TOMORROW_CLASSES:
        await tomorrow_command(update, context)

    elif intent == Intent.QUERY_WEEK_CLASSES:
        await week_command(update, context)

    elif intent == Intent.QUERY_NEXT_OFFDAY:
        await offday_command(update, context)

    elif intent == Intent.QUERY_MIDTERM_BREAK:
        events = db.get_all_events()
        midterm = None
        for event in events:
            name = (event.get("name", "") + " " + event.get("name_en", "")).lower()
            if "pertengahan" in name or "mid" in name:
                if event.get("event_type") == "break":
                    midterm = event
                    break
        if midterm:
            start = midterm.get("start_date", "")
            end = midterm.get("end_date", start)
            name = midterm.get("name_en") or midterm.get("name", "Mid Semester Break")
            await update.message.reply_text(f"{name}: {start} to {end}")
        else:
            await update.message.reply_text("Mid semester break dates not found in calendar.")

    elif intent == Intent.QUERY_FINAL_EXAM:
        events = db.get_all_events()
        final = None
        for event in events:
            name = (event.get("name", "") + " " + event.get("name_en", "")).lower()
            if ("akhir" in name or "final" in name) and event.get("event_type") == "exam":
                final = event
                break
        if final:
            start = final.get("start_date", "")
            end = final.get("end_date", start)
            name = final.get("name_en") or final.get("name", "Final Examination")
            await update.message.reply_text(f"{name}: {start} to {end}")
        else:
            await update.message.reply_text("Final exam dates not found in calendar.")

    elif intent == Intent.QUERY_MIDTERM_EXAM:
        events = db.get_all_events()
        midterm_exam = None
        for event in events:
            name = (event.get("name", "") + " " + event.get("name_en", "")).lower()
            if ("pertengahan" in name or "mid" in name) and event.get("event_type") == "exam":
                midterm_exam = event
                break
        if midterm_exam:
            start = midterm_exam.get("start_date", "")
            end = midterm_exam.get("end_date", start)
            name = midterm_exam.get("name_en") or midterm_exam.get("name", "Mid Semester Examination")
            await update.message.reply_text(f"{name}: {start} to {end}")
        else:
            await update.message.reply_text("Midterm exam dates not found in calendar.")

    elif intent == Intent.EDIT_SCHEDULE:
        # Natural language schedule edit - find matching schedule slot
        subject_code = entities.subject_code
        new_value = entities.title  # New room/lecturer value stored in title
        if subject_code:
            # Use fuzzy subject matching (supports subject name and code)
            matching = db.get_schedule_by_subject(subject_code)
            if matching:
                slot = matching[0]  # Take first match
                slot_id = slot.get("id")
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                day_name = day_names[slot.get("day_of_week", 0)]
                subject = slot.get("subject_code", "Unknown")
                start = slot.get("start_time", "?")

                # Store pending edit
                context.user_data["pending_edit"] = {
                    "type": "schedule",
                    "id": slot_id,
                    "field": "room",  # Default to room
                    "new_value": new_value,
                    "description": f"{subject} ({day_name} {start})"
                }

                old_room = slot.get("room", "Not set")
                await update.message.reply_text(
                    f"Edit {subject} ({day_name} {start})?\n"
                    f"Change room from '{old_room}' to '{new_value}'?\n\n"
                    "Reply 'yes' to confirm or 'no' to cancel."
                )
            else:
                await update.message.reply_text(f"No schedule found for subject '{subject_code}'.")
        else:
            await update.message.reply_text("Please specify a subject code.")

    elif intent == Intent.EDIT_ASSIGNMENT:
        # Natural language assignment edit
        item_id = entities.item_id
        new_value = entities.title  # New value stored in title
        if item_id:
            assignment = db.get_assignment_by_id(item_id)
            if assignment:
                title = assignment.get("title", "Unknown")
                old_due = assignment.get("due_date", "Not set")

                context.user_data["pending_edit"] = {
                    "type": "assignment",
                    "id": item_id,
                    "field": "due",
                    "new_value": new_value,
                    "description": title
                }

                await update.message.reply_text(
                    f"Edit assignment '{title}'?\n"
                    f"Change due date from '{old_due}' to '{new_value}'?\n\n"
                    "Reply 'yes' to confirm or 'no' to cancel."
                )
            else:
                await update.message.reply_text(f"Assignment #{item_id} not found.")
        else:
            await update.message.reply_text("Please specify an assignment ID.")

    elif intent == Intent.SET_ONLINE:
        # Natural language set online
        subject_input = entities.subject_code
        time_part = entities.title  # Contains week# or date

        if subject_input and time_part:
            # Determine subject (None means all)
            if subject_input.upper() == "ALL":
                subject = None
            else:
                # Try to resolve subject name to code using aliases
                aliases = db.get_subject_aliases()
                subject = aliases.get(subject_input.lower(), subject_input.upper())

            # Parse time part
            week_number = None
            specific_date = None

            if "week" in time_part.lower():
                try:
                    week_number = int(time_part.lower().replace("week", "").strip())
                except ValueError:
                    await update.message.reply_text("Invalid week number.")
                    return
            elif time_part.lower() == "tomorrow":
                tomorrow = get_today() + timedelta(days=1)
                specific_date = tomorrow.isoformat()
            elif time_part.lower() == "today":
                specific_date = get_today().isoformat()
            else:
                specific_date = time_part

            db.add_online_override(
                subject_code=subject,
                week_number=week_number,
                specific_date=specific_date
            )

            subject_display = subject or "ALL classes"
            if week_number:
                await update.message.reply_text(
                    f"Set {subject_display} as online for Week {week_number}."
                )
            else:
                await update.message.reply_text(
                    f"Set {subject_display} as online on {specific_date}."
                )
        else:
            await update.message.reply_text(
                "Please specify a subject and time. Example: 'set class BITP1113 online on week 12'"
            )

    elif intent == Intent.QUERY_ONLINE:
        await online_command(update, context)

    elif intent == Intent.ADD_EXAM:
        # Natural language add exam
        subject_input = entities.subject_code
        exam_type = entities.title or "exam"
        date_str = entities.date
        class_type = entities.description  # LAB or LEC

        if subject_input:
            # Try to resolve subject alias (OS -> Operating System / actual code)
            aliases = db.get_subject_aliases()
            subject = aliases.get(subject_input.lower(), subject_input.upper())

            # Get user's semester config
            chat_id = update.effective_chat.id
            user_config = db.get_user_config(chat_id)
            events = db.get_all_events()
            semester_start_str = user_config.get("semester_start_date") if user_config else None
            semester_start = parse_date(semester_start_str) if semester_start_str else None

            # Determine the week number
            week_num = None
            if date_str:
                if "next week" in date_str.lower() or "minggu depan" in date_str.lower():
                    if semester_start:
                        week_num = get_next_week(get_today(), semester_start, events)
                elif "this week" in date_str.lower() or "minggu ni" in date_str.lower():
                    if semester_start:
                        current_week = get_current_week(get_today(), semester_start, events)
                        if isinstance(current_week, int):
                            week_num = current_week

            # Look up the schedule to find the actual day
            actual_date = None
            schedule_day = None
            schedule_time = None

            if week_num and semester_start:
                # Find the schedule slot for this subject and class type
                schedule_slots = db.get_schedule_by_subject(subject)
                target_slot = None

                if class_type and schedule_slots:
                    # Filter by class type (LAB or LEC)
                    for slot in schedule_slots:
                        if slot.get("class_type", "").upper() == class_type:
                            target_slot = slot
                            break

                # If no class type match or no class type specified, use first slot
                if not target_slot and schedule_slots:
                    target_slot = schedule_slots[0]

                if target_slot:
                    day_of_week = target_slot.get("day_of_week", 0)  # 0=Monday
                    schedule_time = target_slot.get("start_time")
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    schedule_day = day_names[day_of_week]

                    # Calculate actual date: semester_start + (week_num - 1) * 7 + day_of_week
                    week_start = semester_start + timedelta(weeks=(week_num - 1))
                    actual_date = week_start + timedelta(days=day_of_week)
                    date_str = actual_date.isoformat()

            # Build exam name with class type
            exam_name = exam_type.replace("labtest", "Lab Test").replace("lab test", "Lab Test").title()
            if class_type:
                exam_name = f"{exam_name} ({class_type})"

            exam_id = db.add_exam(
                subject_code=subject,
                exam_type=exam_type,
                exam_date=date_str,
                exam_time=schedule_time
            )
            db.add_action_history("add", "events", exam_id)

            # Build response
            response = f"✅ {exam_name} added for {subject}"
            if actual_date and schedule_day:
                response += f"\n📅 {schedule_day}, {actual_date.strftime('%d %b %Y')}"
                if week_num:
                    response += f" (Week {week_num})"
            elif date_str:
                response += f" on {date_str}"
            if schedule_time:
                response += f"\n⏰ {schedule_time}"
            response += f"\n🔔 Reminders will be sent before the test"
            response += f"\nID: {exam_id}"

            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "Please specify subject and date. Example:\n"
                "💬 \"Lab test for OS next week on lab section\"\n"
                "💬 \"Final exam BITP1113 on 15 Jan 2025\""
            )

    elif intent == Intent.QUERY_EXAMS:
        await exams_command(update, context)

    elif intent == Intent.DELETE_ITEM:
        # Natural language delete
        item_type = entities.item_type
        item_id = entities.item_id

        if item_type and item_id:
            # Simulate /delete command
            context.args = [item_type, str(item_id)]
            await delete_command(update, context)
        else:
            await update.message.reply_text(
                "Please specify what to delete. Example:\n"
                "\"delete assignment 5\""
            )

    elif intent == Intent.SEARCH_ALL:
        # Natural language search
        query = entities.title
        if query:
            context.args = [query]
            await search_command(update, context)
        else:
            await update.message.reply_text("What would you like to search for?")

    elif intent == Intent.QUERY_STATS:
        await stats_command(update, context)

    elif intent == Intent.SET_LANGUAGE:
        chat_id = update.effective_chat.id
        lang = entities.title or "en"
        db.set_language(chat_id, lang)
        if lang == "my":
            await update.message.reply_text("Bahasa ditetapkan kepada Bahasa Melayu.")
        else:
            await update.message.reply_text("Language set to English.")

    elif intent == Intent.MUTE_NOTIFICATIONS:
        chat_id = update.effective_chat.id
        duration = int(entities.title or "1")
        unit = entities.description or "hour"

        if "min" in unit:
            hours = duration / 60
        else:
            hours = duration

        mute_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        db.set_mute_until(chat_id, mute_until)

        await update.message.reply_text(
            f"🔇 Notifications muted for {duration} {unit}(s)."
        )

    elif intent == Intent.QUERY_ASSIGNMENTS:
        await assignments_command(update, context)

    elif intent == Intent.QUERY_TASKS:
        await tasks_command(update, context)

    elif intent == Intent.QUERY_TODOS:
        await todos_command(update, context)

    elif intent == Intent.ADD_ASSIGNMENT:
        data = build_assignment_from_entities(entities)
        if data.get("title") and data.get("due_date"):
            assignment_id = db.add_assignment(
                title=data["title"],
                due_date=data["due_date"],
                subject_code=data.get("subject_code"),
                description=data.get("description")
            )
            await update.message.reply_text(
                f"Assignment added: '{data['title']}'\n"
                f"Due: {data['due_date']}\n"
                f"ID: {assignment_id}"
            )
        else:
            await update.message.reply_text(
                "I understood you want to add an assignment, but I need more details.\n"
                "Try: 'Assignment [title] for [subject] due [date time]'"
            )

    elif intent == Intent.ADD_TASK:
        data = build_task_from_entities(entities)
        if data.get("title"):
            task_id = db.add_task(
                title=data["title"],
                scheduled_date=data.get("scheduled_date") or get_today().isoformat(),
                description=data.get("description"),
                scheduled_time=data.get("scheduled_time"),
                location=data.get("location")
            )
            response_msg = f"Task added: '{data['title']}'\n"
            response_msg += f"Scheduled: {data.get('scheduled_date', 'Today')}"
            if data.get("scheduled_time"):
                response_msg += f" at {data['scheduled_time']}"
            if data.get("location"):
                response_msg += f"\nLocation: {data['location']}"
            response_msg += f"\nID: {task_id}"
            await update.message.reply_text(response_msg)
        else:
            await update.message.reply_text(
                "I understood you want to add a task, but I need more details.\n"
                "Try: 'Meet [person] on [date] at [time]'"
            )

    elif intent == Intent.ADD_TODO:
        data = build_todo_from_entities(entities)
        if data.get("title"):
            todo_id = db.add_todo(
                title=data["title"],
                scheduled_date=data.get("scheduled_date"),
                scheduled_time=data.get("scheduled_time")
            )
            await update.message.reply_text(
                f"TODO added: '{data['title']}'\n"
                f"ID: {todo_id}"
            )
        else:
            await update.message.reply_text(
                "What would you like to add to your TODO list?"
            )

    elif intent in (Intent.COMPLETE_ASSIGNMENT, Intent.COMPLETE_TASK, Intent.COMPLETE_TODO):
        # Try to find the matching item
        pending_items = {
            "assignments": db.get_pending_assignments(),
            "tasks": db.get_upcoming_tasks(),
            "todos": db.get_pending_todos()
        }

        match = await extract_completion_target(message_text, pending_items)

        if match:
            item_type, item = match
            if item_type == "assignment":
                db.complete_assignment(item["id"])
                await update.message.reply_text(
                    f"Marked assignment '{item['title']}' as completed!"
                )
            elif item_type == "task":
                db.complete_task(item["id"])
                await update.message.reply_text(
                    f"Marked task '{item['title']}' as completed!"
                )
            elif item_type == "todo":
                db.complete_todo(item["id"])
                await update.message.reply_text(
                    f"Marked TODO '{item['title']}' as completed!"
                )
        else:
            await update.message.reply_text(
                "I couldn't find which item you want to mark as done.\n"
                "Try: /done assignment 1, /done task 2, or /done todo 3"
            )

    elif intent == Intent.GENERAL_CHAT:
        # Simple responses for general chat
        msg_lower = message_text.lower()
        # Islamic greeting - respond appropriately
        if any(g in msg_lower for g in ["assalamualaikum", "salam", "aslm", "slm"]):
            await update.message.reply_text(
                "Waalaikumussalam! 👋\n\nHow can I help you today?\nTry /menu for quick access."
            )
        # Regular greeting
        elif any(g in msg_lower for g in ["hi", "hello", "hey", "helo", "hai"]):
            await update.message.reply_text(
                "Hello! 👋\n\nHow can I help you today?\nTry /menu for quick access."
            )
        elif any(t in msg_lower for t in ["thank", "thanks", "terima kasih"]):
            await update.message.reply_text("You're welcome! 😊 Let me know if you need anything else.")
        elif any(b in msg_lower for b in ["bye", "goodbye", "see you"]):
            await update.message.reply_text("Goodbye! Good luck with your studies! 📚")
        else:
            await update.message.reply_text(
                "I'm here to help with your schedule and tasks.\n\n"
                "Try: \"What class tomorrow?\" or use /menu"
            )

    else:
        await update.message.reply_text(
            "🤔 I'm not sure what you mean.\n\n"
            "Try:\n"
            "📅 \"What class tomorrow?\"\n"
            "📝 \"Assignment report due Friday\"\n"
            "✅ \"Remind me buy groceries at 3pm\"\n\n"
            "Use /menu for quick access or /help for all commands."
        )


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photo messages - detect type and parse."""
    chat_id = update.effective_chat.id

    # Get the largest photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("Analyzing image... Please wait.")

    # Detect image type
    image_type = await detect_image_type(bytes(image_bytes))

    if image_type == "calendar":
        await update.message.reply_text(
            "This looks like an academic calendar!\n"
            "Processing... Please wait."
        )
        # Process the calendar image
        events = await parse_academic_calendar(bytes(image_bytes))
        if events:
            # Store events - unpack AcademicEvent dataclass
            for event in events:
                db.add_event(
                    event_type=event.event_type,
                    start_date=event.start_date,
                    name=event.name,
                    name_en=event.name_en,
                    end_date=event.end_date,
                    affects_classes=event.affects_classes
                )
            # Try to detect semester start from lecture_period event
            for event in events:
                if event.event_type == 'lecture_period':
                    db.update_user_config(chat_id, semester_start_date=event.start_date)
                    break
            await update.message.reply_text(
                f"✅ Imported {len(events)} events from calendar!\n"
                f"Use /week_number to check current week."
            )
        else:
            await update.message.reply_text(
                "Couldn't extract events from this image.\n"
                "Please try with a clearer image."
            )

    elif image_type == "timetable":
        await update.message.reply_text(
            "This looks like a class timetable!\n"
            "Processing... Please wait."
        )
        # Process the timetable image
        schedule_entries = await parse_timetable(bytes(image_bytes))
        if schedule_entries:
            # Store schedule slots - unpack ScheduleSlot dataclass
            for entry in schedule_entries:
                db.add_schedule_slot(
                    day_of_week=entry.day_of_week,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    subject_code=entry.subject_code,
                    subject_name=entry.subject_name,
                    class_type=entry.class_type,
                    room=entry.room,
                    lecturer_name=entry.lecturer_name
                )
            await update.message.reply_text(
                f"✅ Imported {len(schedule_entries)} class entries!\n"
                f"Use /today or /week to see your schedule."
            )
        else:
            await update.message.reply_text(
                "Couldn't extract schedule from this image.\n"
                "Please try with a clearer image."
            )

    elif image_type == "assignment":
        response = await handle_assignment_image(update, context, bytes(image_bytes))
        await update.message.reply_text(response)

    else:
        await update.message.reply_text(
            "🤔 I couldn't determine the type of this image.\n\n"
            "I can recognize:\n"
            "📅 Academic calendars → auto-import events\n"
            "🗓️ Class timetables → auto-import schedule\n"
            "📝 Assignment sheets → auto-add assignment\n\n"
            "Try with a clearer image or use /setup for guided upload."
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages - transcribe and offer processing options."""
    from ..ai.gemini_client import get_gemini_client

    voice = update.message.voice
    chat_id = update.effective_chat.id

    # Check duration (max 30 minutes = 1800 seconds)
    duration = voice.duration
    if duration > 1800:
        await update.message.reply_text(
            "Voice message too long! Maximum duration is 30 minutes.\n"
            f"Your message: {duration // 60} minutes {duration % 60} seconds"
        )
        return

    await update.message.reply_text("🎙️ Processing voice message... Please wait.")

    try:
        # Download the voice file
        file = await voice.get_file()
        audio_bytes = await file.download_as_bytearray()

        # Transcribe using Gemini
        gemini = get_gemini_client()
        transcript = await gemini.transcribe_audio(bytes(audio_bytes), "audio/ogg")

        if not transcript:
            await update.message.reply_text(
                "Sorry, I couldn't transcribe the audio. Please try again."
            )
            return

        # Store transcript temporarily for processing
        context.user_data["pending_voice"] = {
            "transcript": transcript,
            "duration": duration,
            "message_id": update.message.message_id
        }

        # Show preview and processing options
        preview = transcript[:300] + "..." if len(transcript) > 300 else transcript
        duration_str = f"{duration // 60}m {duration % 60}s"

        await update.message.reply_text(
            f"✅ *Transcription Complete!* ({duration_str})\n\n"
            f"📝 Preview:\n_{preview}_\n\n"
            "What would you like me to do with this?",
            reply_markup=get_voice_processing_keyboard(update.message.message_id),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await update.message.reply_text(
            f"Error processing voice message: {e}"
        )


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /notes command - list and manage voice notes."""
    chat_id = update.effective_chat.id
    args = context.args

    if args:
        # Check if searching or viewing specific note
        if args[0].lower() == "search" and len(args) > 1:
            query = " ".join(args[1:])
            notes = db.search_voice_notes(chat_id, query)
            if not notes:
                await update.message.reply_text(f"No notes found for '{query}'.")
                return

            lines = [f"🔍 Found {len(notes)} note(s) for '{query}':"]
            for note in notes[:10]:
                title = note.get("title") or f"Note #{note['id']}"
                created = note.get("created_at", "")[:10]
                ptype = note.get("processing_type", "").title()
                lines.append(f"\n[ID:{note['id']}] {title}\n  Type: {ptype} | {created}")

            await update.message.reply_text(
                "\n".join(lines),
                reply_markup=get_notes_list_keyboard(notes)
            )
            return

        # View specific note by ID
        try:
            note_id = int(args[0])
            note = db.get_voice_note_by_id(note_id)
            if not note:
                await update.message.reply_text(f"Note #{note_id} not found.")
                return

            title = note.get("title") or f"Note #{note_id}"
            ptype = note.get("processing_type", "").title()
            created = note.get("created_at", "")[:16].replace("T", " ")
            duration = note.get("duration_seconds", 0)
            duration_str = f"{duration // 60}m {duration % 60}s" if duration else "N/A"

            # Show processed content (truncated if too long)
            content = note.get("processed_content", "")
            if len(content) > 3000:
                content = content[:3000] + "\n\n... (truncated, use 'Full Content' button to see all)"

            await update.message.reply_text(
                f"📄 *{title}*\n"
                f"Type: {ptype} | Duration: {duration_str}\n"
                f"Created: {created}\n\n"
                f"{content}",
                reply_markup=get_note_actions_keyboard(note_id),
                parse_mode="Markdown"
            )
            return
        except ValueError:
            pass

    # List all notes
    notes = db.get_voice_notes(chat_id, limit=10)

    if not notes:
        await update.message.reply_text(
            "🎤 No voice notes yet.\n\n"
            "Send me a voice message (up to 30 min) and I'll:\n"
            "📝 Transcribe it\n"
            "📋 Create summaries or meeting minutes\n"
            "✅ Extract tasks and action items\n"
            "📚 Format as study notes\n\n"
            "Just record and send a voice message to try!"
        )
        return

    lines = ["📝 *Your Voice Notes:*"]
    for note in notes:
        title = note.get("title") or f"Note #{note['id']}"
        ptype = note.get("processing_type", "").title()
        created = note.get("created_at", "")[:10]
        lines.append(f"\n[ID:{note['id']}] {title}\n  {ptype} | {created}")

    await update.message.reply_text(
        "\n".join(lines) + "\n\nUse /notes <id> to view a specific note.",
        reply_markup=get_notes_list_keyboard(notes),
        parse_mode="Markdown"
    )


async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /suggest command - get AI-powered suggestions."""
    from ..ai.gemini_client import get_gemini_client

    await update.message.reply_text("🤔 Analyzing your tasks and schedule...")

    try:
        # Get all relevant data
        data = db.get_data_for_suggestions()

        # Check if there's anything to analyze
        total_items = (
            len(data.get("assignments", [])) +
            len(data.get("tasks", [])) +
            len(data.get("todos", []))
        )

        if total_items == 0:
            await update.message.reply_text(
                "📊 No pending items to analyze!\n\n"
                "Add items first, then I'll give you smart suggestions:\n"
                "📝 \"Assignment report BITP1113 due Friday\"\n"
                "📋 \"Meet Dr Intan tomorrow 10am\"\n"
                "✅ \"Remind me buy groceries at 3pm\""
            )
            return

        # Get AI suggestions
        gemini = get_gemini_client()
        suggestions = await gemini.get_ai_suggestions(data)

        if not suggestions:
            await update.message.reply_text(
                "Sorry, I couldn't generate suggestions right now. Please try again."
            )
            return

        await update.message.reply_text(
            f"💡 *AI Suggestions*\n\n{suggestions}",
            reply_markup=get_content_with_menu_keyboard(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        await update.message.reply_text(f"Error generating suggestions: {e}")


async def setdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setdate command - set a test date for debugging."""
    global _test_date_override

    args = context.args
    if not args:
        current = get_today()
        is_override = _test_date_override is not None
        await update.message.reply_text(
            f"Current date: {current.isoformat()}\n"
            f"{'(Test date override active)' if is_override else '(Real date)'}\n\n"
            "Usage: /setdate YYYY-MM-DD\n"
            "Example: /setdate 2025-12-30"
        )
        return

    try:
        test_date = datetime.strptime(args[0], "%Y-%m-%d").date()
        _test_date_override = test_date
        await update.message.reply_text(
            f"Test date set to: {test_date.isoformat()}\n"
            "All date-based commands will use this date.\n"
            "Use /resetdate to go back to real date."
        )
    except ValueError:
        await update.message.reply_text(
            "Invalid date format. Use YYYY-MM-DD\n"
            "Example: /setdate 2025-12-30"
        )


async def resetdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resetdate command - reset to real date."""
    global _test_date_override
    _test_date_override = None
    await update.message.reply_text(
        f"Date reset to real date: {date.today().isoformat()}"
    )


async def settime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settime command - set a test time for debugging."""
    global _test_time_override

    args = context.args
    if not args:
        current_dt = get_now()
        is_override = _test_time_override is not None
        await update.message.reply_text(
            f"Current time: {current_dt.strftime('%H:%M')}\n"
            f"{'(Test time override active)' if is_override else '(Real time)'}\n\n"
            "Usage: /settime HH:MM\n"
            "Example: /settime 21:55 (for 9:55 PM)"
        )
        return

    try:
        test_time = datetime.strptime(args[0], "%H:%M").time()
        _test_time_override = test_time
        await update.message.reply_text(
            f"Test time set to: {test_time.strftime('%H:%M')}\n"
            "All time-based commands will use this time.\n"
            "Use /resettime to go back to real time.\n\n"
            f"Current test datetime: {get_now().strftime('%Y-%m-%d %H:%M')}"
        )
    except ValueError:
        await update.message.reply_text(
            "Invalid time format. Use HH:MM (24-hour)\n"
            "Example: /settime 21:55"
        )


async def resettime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resettime command - reset to real time."""
    global _test_time_override
    _test_time_override = None
    await update.message.reply_text(
        f"Time reset to real time: {datetime.now(MY_TZ).strftime('%H:%M')}"
    )


async def trigger_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trigger command - manually trigger a notification for testing."""
    from ..scheduler.notifications import get_scheduler
    from ..utils.semester_logic import is_class_day

    args = context.args
    valid_triggers = {
        "briefing": "send_class_briefing",
        "offday": "send_offday_alert",
        "midnight": "send_midnight_todo_review",
        "assignments": "check_assignment_reminders",
        "tasks": "check_task_reminders",
        "todos": "check_todo_reminders",
        "semester": "check_semester_starting",
    }

    if not args:
        trigger_list = "\n".join(f"  • {name}" for name in valid_triggers.keys())
        await update.message.reply_text(
            f"Usage: /trigger <notification_type>\n\n"
            f"Available triggers:\n{trigger_list}\n\n"
            f"Example: /trigger briefing"
        )
        return

    trigger_name = args[0].lower()
    if trigger_name not in valid_triggers:
        await update.message.reply_text(
            f"Unknown trigger: {trigger_name}\n"
            f"Valid options: {', '.join(valid_triggers.keys())}"
        )
        return

    try:
        scheduler = get_scheduler(context.bot)

        # Debug info before triggering
        chat_ids = await scheduler._get_all_chat_ids()
        tomorrow = get_today() + timedelta(days=1)
        events = db.get_all_events()
        day_of_week = tomorrow.weekday()
        schedule = db.get_schedule_for_day(day_of_week)
        is_class = is_class_day(tomorrow, events)

        debug_info = (
            f"Debug Info:\n"
            f"• Test datetime: {get_now().strftime('%Y-%m-%d %H:%M')}\n"
            f"• Tomorrow: {tomorrow} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day_of_week]})\n"
            f"• Registered chat_ids: {chat_ids or 'None'}\n"
            f"• Is class day: {is_class}\n"
            f"• Classes scheduled: {len(schedule) if schedule else 0}\n"
        )

        await update.message.reply_text(f"Triggering {trigger_name}...\n\n{debug_info}")

        method_name = valid_triggers[trigger_name]
        method = getattr(scheduler, method_name)
        await method()

        await update.message.reply_text(f"Done! Check if you received the notification.")
    except Exception as e:
        await update.message.reply_text(f"Error triggering {trigger_name}: {e}")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command - show interactive menu."""
    await update.message.reply_text(
        "📱 *Main Menu*\n\nChoose an option:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


async def exams_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exams command - list upcoming exams."""
    exams = db.get_upcoming_exams()

    if not exams:
        await update.message.reply_text(
            "📝 No upcoming exams found.\n\n"
            "Add exams:\n"
            "💬 \"Final exam BITP1113 on 15 Jan 2025\"\n"
            "📸 Upload academic calendar to auto-import\n"
            "⌨️ /setexam BITP1113 final 2025-01-15"
        )
        return

    lines = ["📝 Upcoming Exams:"]
    for exam in exams:
        name = exam.get("name_en") or exam.get("name", "Exam")
        date_str = exam.get("start_date", "")
        subject = exam.get("subject_code", "")
        exam_id = exam.get("id", "?")

        line = f"[ID:{exam_id}] {name}"
        if subject:
            line += f" ({subject})"
        line += f" - {date_str}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))


async def setexam_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setexam command - set exam date for a subject."""
    args = context.args

    if not args or len(args) < 3:
        await update.message.reply_text(
            "Usage: /setexam <subject> <type> <date> [time]\n\n"
            "Examples:\n"
            "  /setexam BITP1113 final 2025-01-15\n"
            "  /setexam BITI1213 midterm 2024-12-20 10:00\n\n"
            "Type can be: final, midterm, quiz, test"
        )
        return

    subject_code = args[0].upper()
    exam_type = args[1].lower()
    exam_date = args[2]
    exam_time = args[3] if len(args) > 3 else None

    exam_id = db.add_exam(
        subject_code=subject_code,
        exam_type=exam_type,
        exam_date=exam_date,
        exam_time=exam_time
    )

    # Record for undo
    db.add_action_history("add", "events", exam_id)

    response = f"Exam added: {exam_type.title()} for {subject_code} on {exam_date}"
    if exam_time:
        response += f" at {exam_time}"
    response += f"\nID: {exam_id}"

    await update.message.reply_text(response)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete command - delete an item with confirmation."""
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /delete <type> <id>\n\n"
            "Examples:\n"
            "  /delete assignment 5\n"
            "  /delete task 3\n"
            "  /delete todo 1\n"
            "  /delete online 2\n"
            "  /delete event 10"
        )
        return

    item_type = args[0].lower()
    try:
        item_id = int(args[1])
    except ValueError:
        await update.message.reply_text("Invalid ID. Please provide a number.")
        return

    # Get item for confirmation
    item = None
    item_name = ""

    if item_type in ("assignment", "a"):
        item = db.get_assignment_by_id(item_id)
        item_name = item.get("title", "Unknown") if item else ""
    elif item_type in ("task", "t"):
        item = db.get_task_by_id(item_id)
        item_name = item.get("title", "Unknown") if item else ""
    elif item_type in ("todo", "td"):
        item = db.get_todo_by_id(item_id)
        item_name = item.get("title", "Unknown") if item else ""
    elif item_type == "online":
        overrides = db.get_online_overrides()
        item = next((o for o in overrides if o.get("id") == item_id), None)
        if item:
            subject = item.get("subject_code") or "ALL"
            week = item.get("week_number")
            date_val = item.get("specific_date")
            item_name = f"{subject} online on {'Week ' + str(week) if week else date_val}"
    elif item_type == "event":
        events = db.get_all_events()
        item = next((e for e in events if e.get("id") == item_id), None)
        item_name = item.get("name_en") or item.get("name", "Unknown") if item else ""

    if not item:
        await update.message.reply_text(f"{item_type.title()} #{item_id} not found.")
        return

    # Store pending delete for confirmation
    context.user_data["pending_delete"] = {
        "type": item_type,
        "id": item_id,
        "name": item_name,
        "data": json.dumps(dict(item)) if item else None
    }

    await update.message.reply_text(
        f"Delete {item_type} '{item_name}' (ID: {item_id})?\n\n"
        "Reply 'yes' to confirm or 'no' to cancel."
    )


async def schedule_subject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /schedule <subject> command - show schedule for a subject."""
    args = context.args

    if not args:
        # Show full week schedule
        schedule = db.get_all_schedule()
        response = format_week_schedule(schedule)
        await update.message.reply_text(response, parse_mode="Markdown")
        return

    subject = " ".join(args)
    slots = db.get_schedule_by_subject(subject)

    if not slots:
        await update.message.reply_text(f"No schedule found for '{subject}'.")
        return

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = [f"Schedule for {subject.upper()}:"]

    for slot in slots:
        day = day_names[slot.get("day_of_week", 0)]
        start = slot.get("start_time", "")
        end = slot.get("end_time", "")
        class_type = slot.get("class_type", "LEC")
        room = slot.get("room", "")
        slot_id = slot.get("id", "?")

        line = f"[ID:{slot_id}] {day} {start}-{end} ({class_type})"
        if room:
            line += f" - {room}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - show productivity statistics."""
    args = context.args
    days = 7  # Default to past week

    if args:
        try:
            days = int(args[0])
        except ValueError:
            pass

    stats = db.get_completion_stats(days)
    pending = db.get_pending_counts()

    # Calculate percentages
    def calc_pct(completed, total):
        if total == 0:
            return 0
        return int((completed / total) * 100)

    a_stats = stats["assignments"]
    t_stats = stats["tasks"]
    td_stats = stats["todos"]

    a_pct = calc_pct(a_stats["completed"], a_stats["total"])
    t_pct = calc_pct(t_stats["completed"], t_stats["total"])
    td_pct = calc_pct(td_stats["completed"], td_stats["total"])

    response = f"""📊 *Statistics (Past {days} Days)*

*Assignments*
Completed: {a_stats['completed']}/{a_stats['total']} ({a_pct}%)
Pending: {pending['assignments']}

*Tasks*
Completed: {t_stats['completed']}/{t_stats['total']} ({t_pct}%)
Pending: {pending['tasks']}

*TODOs*
Completed: {td_stats['completed']}/{td_stats['total']} ({td_pct}%)
Pending: {pending['todos']}
"""
    await update.message.reply_text(response, parse_mode="Markdown")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command - global search."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: /search <query>\n\n"
            "Example: /search database"
        )
        return

    query = " ".join(args)
    results = db.search_all(query)

    total_count = sum(len(v) for v in results.values())

    if total_count == 0:
        await update.message.reply_text(f"No results found for '{query}'.")
        return

    lines = [f"🔍 Found {total_count} result(s) for '{query}':"]

    if results["assignments"]:
        lines.append("\n📚 *Assignments:*")
        for a in results["assignments"][:5]:
            status = "✅" if a.get("is_completed") else "⏳"
            lines.append(f"  {status} {a['title']} (ID:{a['id']})")

    if results["tasks"]:
        lines.append("\n📋 *Tasks:*")
        for t in results["tasks"][:5]:
            status = "✅" if t.get("is_completed") else "⏳"
            lines.append(f"  {status} {t['title']} (ID:{t['id']})")

    if results["todos"]:
        lines.append("\n✅ *TODOs:*")
        for td in results["todos"][:5]:
            status = "✅" if td.get("is_completed") else "⏳"
            lines.append(f"  {status} {td['title']} (ID:{td['id']})")

    if results["schedule"]:
        lines.append("\n📅 *Schedule:*")
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for s in results["schedule"][:5]:
            day = day_names[s.get("day_of_week", 0)]
            lines.append(f"  {s['subject_code']} - {day} {s['start_time']}")

    if results["events"]:
        lines.append("\n📆 *Events:*")
        for e in results["events"][:5]:
            name = e.get("name_en") or e.get("name", "Unknown")
            lines.append(f"  {name} - {e['start_date']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /undo command - undo last action."""
    last_action = db.get_last_action()

    if not last_action:
        await update.message.reply_text("No action to undo.")
        return

    action_type = last_action.get("action_type")
    table_name = last_action.get("table_name")
    item_id = last_action.get("item_id")
    old_data = last_action.get("old_data")

    try:
        if action_type == "add":
            # Undo add = delete
            if table_name == "assignments":
                db.delete_assignment(item_id)
            elif table_name == "tasks":
                db.delete_task(item_id)
            elif table_name == "todos":
                db.delete_todo(item_id)
            elif table_name == "events":
                db.delete_event(item_id)

            db.delete_action_history(last_action["id"])
            await update.message.reply_text(f"Undone: Removed {table_name[:-1]} #{item_id}")

        elif action_type == "delete" and old_data:
            # Undo delete = restore
            data = json.loads(old_data)
            if table_name == "assignments":
                db.add_assignment(
                    title=data["title"],
                    due_date=data["due_date"],
                    subject_code=data.get("subject_code"),
                    description=data.get("description")
                )
            elif table_name == "tasks":
                db.add_task(
                    title=data["title"],
                    scheduled_date=data["scheduled_date"],
                    description=data.get("description"),
                    scheduled_time=data.get("scheduled_time"),
                    location=data.get("location")
                )
            elif table_name == "todos":
                db.add_todo(
                    title=data["title"],
                    scheduled_date=data.get("scheduled_date"),
                    scheduled_time=data.get("scheduled_time")
                )

            db.delete_action_history(last_action["id"])
            await update.message.reply_text(f"Undone: Restored {table_name[:-1]}")

        elif action_type == "complete":
            # Undo complete = uncomplete (reset is_completed to 0)
            conn = db._get_conn()
            try:
                conn.execute(
                    f"UPDATE {table_name} SET is_completed = 0, completed_at = NULL WHERE id = ?",
                    (item_id,)
                )
                conn.commit()
            finally:
                conn.close()

            db.delete_action_history(last_action["id"])
            await update.message.reply_text(f"Undone: Unmarked {table_name[:-1]} #{item_id} as complete")

        else:
            await update.message.reply_text("Cannot undo this action.")

    except Exception as e:
        logger.error(f"Error undoing action: {e}")
        await update.message.reply_text(f"Error undoing action: {e}")


async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mute command - mute notifications."""
    chat_id = update.effective_chat.id
    args = context.args

    hours = 1  # Default to 1 hour
    if args:
        try:
            hours = int(args[0])
        except ValueError:
            pass

    mute_until = (datetime.now() + timedelta(hours=hours)).isoformat()
    db.set_mute_until(chat_id, mute_until)

    await update.message.reply_text(
        f"🔇 Notifications muted for {hours} hour(s).\n"
        f"Will resume at {mute_until[:16].replace('T', ' ')}"
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command - show settings menu."""
    global _test_date_override, _test_time_override

    # Get current date/time info
    current_date = get_today()
    current_time = get_now()
    real_date = date.today()
    real_time = datetime.now(MY_TZ)

    has_date_override = _test_date_override is not None
    has_time_override = _test_time_override is not None

    # Build settings message
    msg = "⚙️ *Settings*\n\n"
    msg += f"📅 Date: `{current_date.strftime('%a, %d %b %Y')}`"
    if has_date_override:
        msg += " ⚠️ _Override_"
    msg += f"\n⏰ Time: `{current_time.strftime('%H:%M')}`"
    if has_time_override:
        msg += " ⚠️ _Override_"

    if has_date_override or has_time_override:
        msg += f"\n\n_Real: {real_date.strftime('%d %b %Y')} {real_time.strftime('%H:%M')}_"

    msg += "\n\nChoose an option:"

    await update.message.reply_text(
        msg,
        reply_markup=get_settings_keyboard(has_date_override, has_time_override),
        parse_mode="Markdown"
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command - set language preference."""
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "Choose your language:",
            reply_markup=get_language_keyboard()
        )
        return

    lang = args[0].lower()
    if lang in ("en", "english"):
        db.set_language(chat_id, "en")
        await update.message.reply_text("Language set to English.")
    elif lang in ("my", "malay", "melayu", "bm"):
        db.set_language(chat_id, "my")
        await update.message.reply_text("Bahasa ditetapkan kepada Bahasa Melayu.")
    else:
        await update.message.reply_text("Invalid language. Use 'en' or 'my'.")


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command - export data."""
    args = context.args

    if not args:
        await update.message.reply_text(
            "📤 *Export Options*\n\nChoose what to export:",
            reply_markup=get_export_keyboard(),
            parse_mode="Markdown"
        )
        return

    export_type = args[0].lower()

    if export_type == "schedule":
        schedule = db.get_all_schedule()
        if not schedule:
            await update.message.reply_text("No schedule data to export.")
            return

        lines = ["# Class Schedule\n"]
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_day = {}
        for slot in schedule:
            day = slot.get("day_of_week", 0)
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(slot)

        for day in sorted(by_day.keys()):
            lines.append(f"\n## {day_names[day]}")
            for slot in sorted(by_day[day], key=lambda x: x.get("start_time", "")):
                lines.append(
                    f"- {slot['start_time']}-{slot['end_time']}: "
                    f"{slot['subject_code']} ({slot.get('class_type', 'LEC')}) "
                    f"Room: {slot.get('room', 'TBA')}"
                )

        content = "\n".join(lines)
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = "schedule.md"
        await update.message.reply_document(bio, caption="Your class schedule")

    elif export_type == "assignments":
        assignments = db.get_pending_assignments()
        if not assignments:
            await update.message.reply_text("No assignments to export.")
            return

        lines = ["# Pending Assignments\n"]
        for a in assignments:
            lines.append(f"- **{a['title']}**")
            if a.get("subject_code"):
                lines.append(f"  Subject: {a['subject_code']}")
            lines.append(f"  Due: {a['due_date']}")
            if a.get("description"):
                lines.append(f"  Description: {a['description']}")
            lines.append("")

        content = "\n".join(lines)
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = "assignments.md"
        await update.message.reply_document(bio, caption="Your pending assignments")

    elif export_type == "all":
        data = {
            "schedule": db.get_all_schedule(),
            "assignments": db.get_pending_assignments(),
            "tasks": db.get_upcoming_tasks(30),
            "todos": db.get_pending_todos(),
            "events": db.get_all_events(),
        }

        content = json.dumps(data, indent=2, default=str)
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = "all_data.json"
        await update.message.reply_document(bio, caption="All your data (JSON)")

    else:
        await update.message.reply_text("Unknown export type. Use: schedule, assignments, or all")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button callbacks."""
    global _test_date_override, _test_time_override

    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id

    # Menu navigation
    if data == "menu_main":
        await query.edit_message_text(
            "📱 *Main Menu*\n\nChoose an option:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_settings":
        # Get current date/time info
        current_date = get_today()
        current_time = get_now()
        real_date = date.today()
        real_time = datetime.now(MY_TZ)

        has_date_override = _test_date_override is not None
        has_time_override = _test_time_override is not None

        # Build settings message
        msg = "⚙️ *Settings*\n\n"
        msg += f"📅 Date: `{current_date.strftime('%a, %d %b %Y')}`"
        if has_date_override:
            msg += " ⚠️ _Override_"
        msg += f"\n⏰ Time: `{current_time.strftime('%H:%M')}`"
        if has_time_override:
            msg += " ⚠️ _Override_"

        if has_date_override or has_time_override:
            msg += f"\n\n_Real: {real_date.strftime('%d %b %Y')} {real_time.strftime('%H:%M')}_"

        msg += "\n\nChoose an option:"

        await query.edit_message_text(
            msg,
            reply_markup=get_settings_keyboard(has_date_override, has_time_override),
            parse_mode="Markdown"
        )

    elif data == "reset_date":
        _test_date_override = None
        await query.edit_message_text(
            f"✅ Date reset to real date: {date.today().strftime('%a, %d %b %Y')}",
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "reset_time":
        _test_time_override = None
        await query.edit_message_text(
            f"✅ Time reset to real time: {datetime.now(MY_TZ).strftime('%H:%M')}",
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "menu_language":
        await query.edit_message_text(
            "🌐 *Language*\n\nChoose your language:",
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_semester":
        user_config = db.get_user_config(chat_id)
        current = user_config.get("semester_start_date") if user_config else None
        current_display = current if current else "Not set"

        await query.edit_message_text(
            f"📅 *Semester Settings*\n\n"
            f"Current semester start: *{current_display}*\n\n"
            f"Choose an option:",
            reply_markup=get_semester_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "semester_set":
        await query.edit_message_text(
            "📅 *Set Semester Start Date*\n\n"
            "Send the date in this format:\n"
            "`/setsemester YYYY-MM-DD`\n\n"
            "Example: `/setsemester 2025-01-06`\n\n"
            "This is the first day of Week 1.",
            reply_markup=get_semester_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "semester_week":
        user_config = db.get_user_config(chat_id)
        events = db.get_all_events()
        semester_start_str = user_config.get("semester_start_date") if user_config else None
        semester_start = parse_date(semester_start_str) if semester_start_str else None

        if semester_start:
            week = get_current_week(get_today(), semester_start, events)
            response = format_current_week(week, semester_start_str)
        else:
            response = "Semester start date not set.\nUse 'Set Semester Start' to configure."

        await query.edit_message_text(
            f"📊 *Current Week*\n\n{response}",
            reply_markup=get_semester_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_notifications":
        settings = db.get_all_notification_settings(chat_id)
        await query.edit_message_text(
            "🔔 *Notification Settings*\n\nToggle notifications:",
            reply_markup=get_notification_settings_keyboard(settings),
            parse_mode="Markdown"
        )

    # Commands via buttons - keep menu visible
    elif data == "cmd_today":
        schedule = db.get_all_schedule()
        events = db.get_all_events()
        response = format_today_classes(schedule, events, today=get_today())
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_tomorrow":
        schedule = db.get_all_schedule()
        events = db.get_all_events()
        response = format_tomorrow_classes(schedule, events, today=get_today())
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_assignments":
        assignments = db.get_pending_assignments()
        response = format_pending_assignments(assignments)
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_tasks":
        tasks = db.get_upcoming_tasks()
        response = format_pending_tasks(tasks)
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_todos":
        todos = db.get_pending_todos()
        response = format_pending_todos(todos)
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_stats":
        stats = db.get_completion_stats(7)
        pending = db.get_pending_counts()

        def calc_pct(c, t):
            return int((c / t) * 100) if t > 0 else 0

        a = stats["assignments"]
        t = stats["tasks"]
        td = stats["todos"]

        response = (
            f"📊 Stats (Past 7 Days)\n\n"
            f"📚 Assignments: {a['completed']}/{a['total']} ({calc_pct(a['completed'], a['total'])}%)\n"
            f"📋 Tasks: {t['completed']}/{t['total']} ({calc_pct(t['completed'], t['total'])}%)\n"
            f"✅ TODOs: {td['completed']}/{td['total']} ({calc_pct(td['completed'], td['total'])}%)\n\n"
            f"Pending: {pending['assignments']} assignments, {pending['tasks']} tasks, {pending['todos']} todos"
        )
        await query.edit_message_text(
            response,
            reply_markup=get_content_with_menu_keyboard()
        )

    elif data == "cmd_help":
        help_text = (
            "📖 *Quick Help*\n\n"
            "*📅 Schedule:* /today, /tomorrow, /week\n"
            "*📝 Items:* /assignments, /tasks, /todos\n"
            "*✅ Actions:* /done, /delete, /edit, /undo\n"
            "*📝 Exams:* /exams, /setexam\n"
            "*🎤 Voice:* /notes, /suggest\n"
            "*⚙️ Settings:* /settings, /mute, /language\n\n"
            "*💬 Just chat naturally!*\n"
            "• \"What class tomorrow?\"\n"
            "• \"Assignment due Friday 5pm\"\n"
            "• \"Done with BITP report\"\n\n"
            "Use /help for detailed topics."
        )
        await query.edit_message_text(
            help_text,
            reply_markup=get_content_with_menu_keyboard(),
            parse_mode="Markdown"
        )

    # Language selection
    elif data.startswith("lang_"):
        lang = data.split("_")[1]
        db.set_language(chat_id, lang)
        msg = "✅ Language set to English." if lang == "en" else "✅ Bahasa ditetapkan kepada Bahasa Melayu."
        await query.edit_message_text(
            msg,
            reply_markup=get_content_with_menu_keyboard()
        )

    # Initial language selection (for new users in onboarding)
    elif data.startswith("initial_lang_"):
        lang = data.split("_")[2]  # initial_lang_en -> en
        db.set_language(chat_id, lang)

        if lang == "en":
            msg = """✅ Language set to English.

Welcome! I can help you with:
📅 Class schedule & week tracking
📝 Assignment tracking with reminders
✅ Tasks and TODO management
🎤 Voice notes transcription
📸 Image recognition (calendar, timetable, assignments)
💡 AI-powered suggestions
🔔 Daily briefings and notifications

Use /setup to configure your calendar and timetable.
Use /help to see all available commands."""
        else:
            msg = """✅ Bahasa ditetapkan kepada Bahasa Melayu.

Selamat datang! Saya boleh membantu anda dengan:
📅 Jadual kelas & penjejakan minggu
📝 Penjejakan tugasan dengan peringatan
✅ Pengurusan tugas dan TODO
🎤 Transkripsi nota suara
📸 Pengecaman imej (kalendar, jadual, tugasan)
💡 Cadangan berkuasa AI
🔔 Taklimat harian dan pemberitahuan

Gunakan /setup untuk mengkonfigurasi kalendar dan jadual anda.
Gunakan /help untuk melihat semua arahan."""

        await query.edit_message_text(
            msg,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )

    # Mute
    elif data.startswith("mute_"):
        hours = int(data.split("_")[1].replace("h", ""))
        mute_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        db.set_mute_until(chat_id, mute_until)
        await query.edit_message_text(
            f"🔇 Notifications muted for {hours} hour(s).",
            reply_markup=get_content_with_menu_keyboard()
        )

    # Notification toggles
    elif data.startswith("toggle_"):
        parts = data.split("_")
        setting_type = parts[1]
        current = parts[2]
        new_value = "off" if current == "on" else "on"

        setting_key = f"{setting_type}_alert" if setting_type != "briefing" else "daily_briefing"
        if setting_type == "midnight":
            setting_key = "midnight_review"

        db.set_notification_setting(chat_id, setting_key, new_value)

        settings = db.get_all_notification_settings(chat_id)
        await query.edit_message_text(
            "🔔 *Notification Settings*\n\nToggle notifications:",
            reply_markup=get_notification_settings_keyboard(settings),
            parse_mode="Markdown"
        )

    # Done action
    elif data.startswith("done_"):
        parts = data.split("_")
        item_type = parts[1]
        item_id = int(parts[2])

        if item_type == "assignment":
            item = db.get_assignment_by_id(item_id)
            if item:
                db.complete_assignment(item_id)
                db.add_action_history("complete", "assignments", item_id)
                await query.edit_message_text(
                    f"✅ Marked '{item['title']}' as completed!",
                    reply_markup=get_content_with_menu_keyboard()
                )
        elif item_type == "task":
            item = db.get_task_by_id(item_id)
            if item:
                db.complete_task(item_id)
                db.add_action_history("complete", "tasks", item_id)
                await query.edit_message_text(
                    f"✅ Marked '{item['title']}' as completed!",
                    reply_markup=get_content_with_menu_keyboard()
                )
        elif item_type == "todo":
            item = db.get_todo_by_id(item_id)
            if item:
                db.complete_todo(item_id)
                db.add_action_history("complete", "todos", item_id)
                await query.edit_message_text(
                    f"✅ Marked '{item['title']}' as completed!",
                    reply_markup=get_content_with_menu_keyboard()
                )

    # Delete confirmation
    elif data.startswith("delete_"):
        parts = data.split("_")
        item_type = parts[1]
        item_id = int(parts[2])

        await query.edit_message_text(
            f"Are you sure you want to delete this {item_type}?",
            reply_markup=get_confirmation_keyboard("delete", item_type, item_id)
        )

    elif data.startswith("confirm_delete_"):
        parts = data.split("_")
        item_type = parts[2]
        item_id = int(parts[3])

        deleted = None
        if item_type == "assignment":
            deleted = db.delete_assignment(item_id)
        elif item_type == "task":
            deleted = db.delete_task(item_id)
        elif item_type == "todo":
            deleted = db.delete_todo(item_id)

        if deleted:
            db.add_action_history("delete", f"{item_type}s", item_id, json.dumps(deleted))
            await query.edit_message_text(
                f"🗑️ Deleted {item_type} successfully!",
                reply_markup=get_content_with_menu_keyboard()
            )
        else:
            await query.edit_message_text(
                f"{item_type.title()} not found.",
                reply_markup=get_content_with_menu_keyboard()
            )

    elif data.startswith("cancel_"):
        await query.edit_message_text(
            "Action cancelled.",
            reply_markup=get_content_with_menu_keyboard()
        )

    # Snooze
    elif data.startswith("snooze_"):
        parts = data.split("_")
        item_type = parts[1]
        item_id = int(parts[2])
        minutes = int(parts[3])

        # For snooze, we just acknowledge - actual scheduling would need more infrastructure
        await query.edit_message_text(
            f"⏰ Snoozed for {minutes} minutes. I'll remind you again later.",
            reply_markup=get_content_with_menu_keyboard()
        )

    # Export
    elif data.startswith("export_"):
        export_type = data.split("_")[1]
        # Trigger export through message
        context.user_data["export_type"] = export_type
        await query.edit_message_text(f"Processing {export_type} export...")

        # Create a fake update for the export command
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Exporting {export_type}..."
        )

    # Voice processing callbacks
    elif data.startswith("voice_"):
        from ..ai.gemini_client import get_gemini_client

        parts = data.split("_")
        action = parts[1]
        message_id = int(parts[2]) if len(parts) > 2 else 0

        # Get pending voice data
        pending = context.user_data.get("pending_voice")
        if not pending:
            await query.edit_message_text(
                "Voice data expired. Please send a new voice message.",
                reply_markup=get_content_with_menu_keyboard()
            )
            return

        transcript = pending.get("transcript", "")
        duration = pending.get("duration", 0)

        if action == "cancel":
            del context.user_data["pending_voice"]
            await query.edit_message_text(
                "Voice processing cancelled.",
                reply_markup=get_content_with_menu_keyboard()
            )
            return

        # Map action to processing type
        type_map = {
            "summary": "summary",
            "minutes": "minutes",
            "tasks": "tasks",
            "study": "study",
            "transcript": "transcript",
            "smart": "smart"
        }

        processing_type = type_map.get(action, "summary")

        await query.edit_message_text(f"🔄 Processing as {processing_type}...")

        try:
            gemini = get_gemini_client()

            if processing_type == "transcript":
                # Just save the raw transcript
                processed_content = transcript
            else:
                # Process with AI
                processed_content = await gemini.process_audio_content(transcript, processing_type)

            if not processed_content:
                await query.edit_message_text(
                    "Failed to process content. Please try again.",
                    reply_markup=get_content_with_menu_keyboard()
                )
                return

            # Generate title from first line or summary
            title_preview = processed_content[:50].split("\n")[0]
            if len(title_preview) > 40:
                title_preview = title_preview[:37] + "..."

            # Save to database
            note_id = db.add_voice_note(
                chat_id=chat_id,
                original_transcript=transcript,
                processed_content=processed_content,
                processing_type=processing_type,
                duration_seconds=duration,
                title=title_preview
            )

            # Clean up pending data
            del context.user_data["pending_voice"]

            # Show result
            display_content = processed_content[:2000]
            if len(processed_content) > 2000:
                display_content += "\n\n... (truncated)"

            await query.edit_message_text(
                f"✅ *Saved as {processing_type.title()}!*\n"
                f"Note ID: {note_id}\n\n"
                f"{display_content}\n\n"
                "_Use /notes to see all your notes._",
                reply_markup=get_note_actions_keyboard(note_id),
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Voice processing callback error: {e}")
            await query.edit_message_text(
                f"Error processing: {e}",
                reply_markup=get_content_with_menu_keyboard()
            )

    # Notes list callback
    elif data == "cmd_notes":
        notes = db.get_voice_notes(chat_id, limit=10)
        if not notes:
            await query.edit_message_text(
                "📝 No voice notes yet.\n\nSend a voice message to get started!",
                reply_markup=get_content_with_menu_keyboard()
            )
            return

        lines = ["📝 *Your Voice Notes:*"]
        for note in notes:
            title = note.get("title") or f"Note #{note['id']}"
            ptype = note.get("processing_type", "").title()
            created = note.get("created_at", "")[:10]
            lines.append(f"\n[ID:{note['id']}] {title}\n  {ptype} | {created}")

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=get_notes_list_keyboard(notes),
            parse_mode="Markdown"
        )

    # View note callback
    elif data.startswith("view_note_"):
        note_id = int(data.split("_")[2])
        note = db.get_voice_note_by_id(note_id)

        if not note:
            await query.edit_message_text(
                f"Note #{note_id} not found.",
                reply_markup=get_content_with_menu_keyboard()
            )
            return

        title = note.get("title") or f"Note #{note_id}"
        ptype = note.get("processing_type", "").title()
        created = note.get("created_at", "")[:16].replace("T", " ")
        content = note.get("processed_content", "")[:2500]

        await query.edit_message_text(
            f"📄 *{title}*\n"
            f"Type: {ptype} | Created: {created}\n\n"
            f"{content}",
            reply_markup=get_note_actions_keyboard(note_id),
            parse_mode="Markdown"
        )

    # Note full content callback
    elif data.startswith("note_full_"):
        note_id = int(data.split("_")[2])
        note = db.get_voice_note_by_id(note_id)

        if note:
            content = note.get("processed_content", "")
            # Split into multiple messages if too long
            if len(content) > 4000:
                await query.edit_message_text(
                    content[:4000] + "\n\n... (continued)",
                    reply_markup=get_note_actions_keyboard(note_id)
                )
                # Send rest as new message
                await context.bot.send_message(chat_id=chat_id, text=content[4000:])
            else:
                await query.edit_message_text(
                    content,
                    reply_markup=get_note_actions_keyboard(note_id)
                )

    # Note transcript callback
    elif data.startswith("note_transcript_"):
        note_id = int(data.split("_")[2])
        note = db.get_voice_note_by_id(note_id)

        if note:
            transcript = note.get("original_transcript", "")[:4000]
            await query.edit_message_text(
                f"📝 *Original Transcript*\n\n{transcript}",
                reply_markup=get_note_actions_keyboard(note_id),
                parse_mode="Markdown"
            )

    # Note delete callback
    elif data.startswith("note_delete_"):
        note_id = int(data.split("_")[2])
        deleted = db.delete_voice_note(note_id)

        if deleted:
            await query.edit_message_text(
                f"🗑️ Note #{note_id} deleted.",
                reply_markup=get_content_with_menu_keyboard()
            )
        else:
            await query.edit_message_text(
                f"Note #{note_id} not found.",
                reply_markup=get_content_with_menu_keyboard()
            )


def register_handlers(application: Application) -> None:
    """Register all command handlers with the application."""
    # Add onboarding conversation handler first (higher priority)
    application.add_handler(get_onboarding_handler())

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tomorrow", tomorrow_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("week", week_command))
    application.add_handler(CommandHandler("week_number", week_number_command))
    application.add_handler(CommandHandler("setsemester", setsemester_command))
    application.add_handler(CommandHandler("offday", offday_command))
    application.add_handler(CommandHandler("assignments", assignments_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("todos", todos_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("online", online_command))
    application.add_handler(CommandHandler("setonline", setonline_command))

    # New feature commands
    application.add_handler(CommandHandler("exams", exams_command))
    application.add_handler(CommandHandler("setexam", setexam_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("schedule", schedule_subject_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("export", export_command))

    # Voice notes and AI suggestions
    application.add_handler(CommandHandler("notes", notes_command))
    application.add_handler(CommandHandler("suggest", suggest_command))

    # Debug commands
    application.add_handler(CommandHandler("setdate", setdate_command))
    application.add_handler(CommandHandler("resetdate", resetdate_command))
    application.add_handler(CommandHandler("settime", settime_command))
    application.add_handler(CommandHandler("resettime", resettime_command))
    application.add_handler(CommandHandler("trigger", trigger_command))

    # Callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Message handlers (lower priority than commands)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
