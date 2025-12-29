"""Telegram bot command handlers."""

import logging
import os
from datetime import date, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Debug: Test date override (set via /setdate command or TEST_DATE env var)
_test_date_override: date = None


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
from ..ai.image_parser import detect_image_type, parse_assignment_image
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

    # Create user config if doesn't exist
    existing = db.get_user_config(chat_id)
    if not existing:
        db.create_user_config(chat_id)

    welcome_message = f"""
Assalamualaikum {user.first_name}! 👋

Welcome to UTeM Student Assistant Bot.

I can help you with:
📅 Managing your class schedule
📝 Tracking assignments with reminders
✅ Tasks and TODO lists
🔔 Daily briefings and notifications

To get started:
1. Send me your academic calendar image
2. Send me your class timetable image

Use /help to see all available commands.
"""
    await update.message.reply_text(welcome_message.strip())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands."""
    help_text = """
*Available Commands*

*Setup*
/start - Start the bot and setup

*Schedule*
/tomorrow - Show tomorrow's classes
/week - Show this week's schedule

*Academic*
/week\\_number - Current week of semester
/offday - Next off day / holiday

*Tasks*
/assignments - List pending assignments
/tasks - List upcoming tasks
/todos - List pending TODOs

*Status*
/status - Overview of pending items

*Management*
/done <id> - Mark item as complete
/help - Show this help message

You can also send me natural language messages like:
• "I have assignment report for BITP1113 due Friday 5pm"
• "What class tomorrow?"
• "Done with BITP report"
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
            "Use /setup to upload your academic calendar."
        )
        return

    week = get_current_week(get_today(), semester_start, events)
    response = format_current_week(week, semester_start_str)
    await update.message.reply_text(response)


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


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages - route by intent."""
    message_text = update.message.text

    # Check if we're waiting for assignment confirmation
    if "pending_assignment" in context.user_data:
        response = await confirm_assignment(update, context)
        if response:
            await update.message.reply_text(response)
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
                "Semester start date not set. Use /setup to configure."
            )

    elif intent == Intent.QUERY_TOMORROW_CLASSES:
        await tomorrow_command(update, context)

    elif intent == Intent.QUERY_WEEK_CLASSES:
        await week_command(update, context)

    elif intent == Intent.QUERY_NEXT_OFFDAY:
        await offday_command(update, context)

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
        if any(g in msg_lower for g in ["hi", "hello", "hey", "assalamualaikum"]):
            await update.message.reply_text(
                "Waalaikumussalam! How can I help you today?"
            )
        elif any(t in msg_lower for t in ["thank", "thanks", "terima kasih"]):
            await update.message.reply_text("You're welcome! Let me know if you need anything else.")
        elif any(b in msg_lower for b in ["bye", "goodbye", "see you"]):
            await update.message.reply_text("Goodbye! Good luck with your studies!")
        else:
            await update.message.reply_text(
                "I'm here to help with your schedule and tasks.\n"
                "Use /help to see what I can do!"
            )

    else:
        await update.message.reply_text(
            "I'm not sure what you mean.\n"
            "Try asking about your classes, assignments, or tasks.\n"
            "Use /help to see available commands."
        )


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photo messages - detect type and parse."""
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
            "Use /setup to properly import your calendar with confirmation."
        )

    elif image_type == "timetable":
        await update.message.reply_text(
            "This looks like a class timetable!\n"
            "Use /setup to properly import your timetable with confirmation."
        )

    elif image_type == "assignment":
        response = await handle_assignment_image(update, context, bytes(image_bytes))
        await update.message.reply_text(response)

    else:
        await update.message.reply_text(
            "I couldn't determine the type of this image.\n"
            "I can recognize:\n"
            "- Academic calendars\n"
            "- Class timetables\n"
            "- Assignment sheets\n\n"
            "Please try with a clearer image."
        )


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


def register_handlers(application: Application) -> None:
    """Register all command handlers with the application."""
    # Add onboarding conversation handler first (higher priority)
    application.add_handler(get_onboarding_handler())

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tomorrow", tomorrow_command))
    application.add_handler(CommandHandler("week", week_command))
    application.add_handler(CommandHandler("week_number", week_number_command))
    application.add_handler(CommandHandler("offday", offday_command))
    application.add_handler(CommandHandler("assignments", assignments_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("todos", todos_command))
    application.add_handler(CommandHandler("done", done_command))

    # Debug commands
    application.add_handler(CommandHandler("setdate", setdate_command))
    application.add_handler(CommandHandler("resetdate", resetdate_command))

    # Message handlers (lower priority than commands)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
