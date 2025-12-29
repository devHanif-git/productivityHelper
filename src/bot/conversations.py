"""Multi-step conversation flows for bot interactions."""

import logging
from datetime import date, datetime, timedelta
from enum import Enum, auto
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from ..config import config
from ..database.operations import DatabaseOperations
from ..ai.image_parser import (
    parse_academic_calendar,
    parse_timetable,
    parse_assignment_image,
    detect_image_type,
    AcademicEvent,
    ScheduleSlot,
    AssignmentDetails,
)
from ..utils.semester_logic import format_date, format_time, DAY_NAMES

logger = logging.getLogger(__name__)

# Initialize database
db = DatabaseOperations(config.DATABASE_PATH)


# Conversation states
class OnboardingState(Enum):
    WAITING_CALENDAR = auto()
    CONFIRM_CALENDAR = auto()
    WAITING_TIMETABLE = auto()
    CONFIRM_TIMETABLE = auto()
    SET_PREFERENCES = auto()


class AssignmentUploadState(Enum):
    WAITING_IMAGE = auto()
    CONFIRM_DETAILS = auto()
    EDIT_DETAILS = auto()


class ItemConfirmState(Enum):
    CONFIRM_ADD = auto()


# ==================== Onboarding Flow ====================

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the onboarding flow - ask for calendar image."""
    await update.message.reply_text(
        "Let's set up your academic calendar!\n\n"
        "Please send me a photo/screenshot of your academic calendar.\n"
        "This should show semester dates, holidays, exam periods, etc.\n\n"
        "You can send /skip if you want to skip this step."
    )
    return OnboardingState.WAITING_CALENDAR.value


async def receive_calendar_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and parse calendar image."""
    if not update.message.photo:
        await update.message.reply_text(
            "Please send an image of your academic calendar.\n"
            "Use /skip to skip this step."
        )
        return OnboardingState.WAITING_CALENDAR.value

    # Get the largest photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("Analyzing calendar image... Please wait.")

    # Parse the calendar
    events = await parse_academic_calendar(bytes(image_bytes))

    if not events:
        await update.message.reply_text(
            "I couldn't extract any events from that image.\n"
            "Please try again with a clearer image, or /skip this step."
        )
        return OnboardingState.WAITING_CALENDAR.value

    # Store events temporarily for confirmation
    context.user_data["pending_events"] = events

    # Format events for display
    events_text = _format_events_for_confirmation(events)

    await update.message.reply_text(
        f"I found {len(events)} events:\n\n{events_text}\n\n"
        "Reply 'yes' to save these events, or 'no' to try again."
    )
    return OnboardingState.CONFIRM_CALENDAR.value


async def confirm_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and save calendar events."""
    response = update.message.text.lower().strip()

    if response in ("yes", "y", "ok", "confirm"):
        events = context.user_data.get("pending_events", [])

        # Clear existing events and save new ones
        db.clear_events()
        saved_count = 0

        for event in events:
            db.add_event(
                event_type=event.event_type,
                name=event.name,
                name_en=event.name_en,
                start_date=event.start_date,
                end_date=event.end_date,
                affects_classes=event.affects_classes
            )
            saved_count += 1

        # Try to detect semester start from lecture_period events
        for event in events:
            if event.event_type == "lecture_period":
                chat_id = update.effective_chat.id
                db.update_user_config(chat_id, semester_start_date=event.start_date)
                break

        await update.message.reply_text(
            f"Saved {saved_count} events!\n\n"
            "Now please send me your class timetable image.\n"
            "Use /skip if you want to skip this step."
        )
        context.user_data.pop("pending_events", None)
        return OnboardingState.WAITING_TIMETABLE.value

    elif response in ("no", "n", "cancel"):
        context.user_data.pop("pending_events", None)
        await update.message.reply_text(
            "Okay, please send another calendar image.\n"
            "Use /skip to skip this step."
        )
        return OnboardingState.WAITING_CALENDAR.value

    else:
        await update.message.reply_text(
            "Please reply 'yes' to confirm or 'no' to try again."
        )
        return OnboardingState.CONFIRM_CALENDAR.value


async def receive_timetable_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and parse timetable image."""
    if not update.message.photo:
        await update.message.reply_text(
            "Please send an image of your class timetable.\n"
            "Use /skip to skip this step."
        )
        return OnboardingState.WAITING_TIMETABLE.value

    # Get the largest photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("Analyzing timetable image... Please wait.")

    # Parse the timetable
    slots = await parse_timetable(bytes(image_bytes))

    if not slots:
        await update.message.reply_text(
            "I couldn't extract any class slots from that image.\n"
            "Please try again with a clearer image, or /skip this step."
        )
        return OnboardingState.WAITING_TIMETABLE.value

    # Store slots temporarily for confirmation
    context.user_data["pending_schedule"] = slots

    # Format schedule for display
    schedule_text = _format_schedule_for_confirmation(slots)

    await update.message.reply_text(
        f"I found {len(slots)} class slots:\n\n{schedule_text}\n\n"
        "Reply 'yes' to save this schedule, or 'no' to try again."
    )
    return OnboardingState.CONFIRM_TIMETABLE.value


async def confirm_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and save timetable schedule."""
    response = update.message.text.lower().strip()

    if response in ("yes", "y", "ok", "confirm"):
        slots = context.user_data.get("pending_schedule", [])

        # Clear existing schedule and save new ones
        db.clear_schedule()
        saved_count = 0

        for slot in slots:
            db.add_schedule_slot(
                day_of_week=slot.day_of_week,
                start_time=slot.start_time,
                end_time=slot.end_time,
                subject_code=slot.subject_code,
                subject_name=slot.subject_name,
                class_type=slot.class_type,
                room=slot.room,
                lecturer_name=slot.lecturer_name
            )
            saved_count += 1

        await update.message.reply_text(
            f"Saved {saved_count} class slots!\n\n"
            "Setup complete! You're all set.\n\n"
            "You can now:\n"
            "- Ask me about your classes\n"
            "- Add assignments, tasks, and TODOs\n"
            "- Send me assignment images to add them\n\n"
            "Use /help to see all available commands."
        )
        context.user_data.pop("pending_schedule", None)
        return ConversationHandler.END

    elif response in ("no", "n", "cancel"):
        context.user_data.pop("pending_schedule", None)
        await update.message.reply_text(
            "Okay, please send another timetable image.\n"
            "Use /skip to skip this step."
        )
        return OnboardingState.WAITING_TIMETABLE.value

    else:
        await update.message.reply_text(
            "Please reply 'yes' to confirm or 'no' to try again."
        )
        return OnboardingState.CONFIRM_TIMETABLE.value


async def skip_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip the current step in onboarding."""
    current_state = context.user_data.get("state")

    if current_state == OnboardingState.WAITING_CALENDAR.value:
        await update.message.reply_text(
            "Skipping calendar setup.\n\n"
            "Now please send me your class timetable image.\n"
            "Use /skip to skip this step too."
        )
        return OnboardingState.WAITING_TIMETABLE.value

    elif current_state in (OnboardingState.WAITING_TIMETABLE.value,
                           OnboardingState.CONFIRM_TIMETABLE.value):
        await update.message.reply_text(
            "Skipping timetable setup.\n\n"
            "Setup complete! You can add calendar and timetable later using /setup.\n"
            "Use /help to see all available commands."
        )
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "Setup complete! Use /help to see available commands."
        )
        return ConversationHandler.END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the onboarding flow."""
    context.user_data.clear()
    await update.message.reply_text(
        "Setup cancelled. You can restart anytime with /setup.\n"
        "Use /help to see available commands."
    )
    return ConversationHandler.END


# ==================== Assignment Upload Flow ====================

async def handle_assignment_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_bytes: bytes
) -> str:
    """Handle an assignment image upload."""
    await update.message.reply_text("Analyzing assignment... Please wait.")

    details = await parse_assignment_image(image_bytes)

    if not details:
        return (
            "I couldn't extract assignment details from that image.\n"
            "You can add assignments manually:\n"
            "\"Assignment [title] for [subject] due [date time]\""
        )

    # Store for potential confirmation
    context.user_data["pending_assignment"] = details

    # Format for display
    details_text = _format_assignment_for_confirmation(details)

    return (
        f"I found this assignment:\n\n{details_text}\n\n"
        "Reply 'yes' to save, or 'no' to cancel.\n"
        "You can also edit details by sending corrections."
    )


async def confirm_assignment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> Optional[str]:
    """Confirm and save an assignment from image."""
    details = context.user_data.get("pending_assignment")
    if not details:
        return None

    response = update.message.text.lower().strip()

    if response in ("yes", "y", "ok", "confirm", "save"):
        assignment_id = db.add_assignment(
            title=details.title,
            due_date=details.due_date or datetime.now().isoformat(),
            subject_code=details.subject_code,
            description=details.description
        )
        context.user_data.pop("pending_assignment", None)

        return f"Assignment '{details.title}' saved! (ID: {assignment_id})"

    elif response in ("no", "n", "cancel"):
        context.user_data.pop("pending_assignment", None)
        return "Assignment cancelled."

    return None


# ==================== Query Response Formatters ====================

def format_tomorrow_classes(schedule: list[dict], events: list[dict], today: date = None) -> str:
    """Format tomorrow's classes for display."""
    if today is None:
        today = date.today()
    tomorrow = today + timedelta(days=1)
    day_of_week = tomorrow.weekday()

    # Check for events affecting tomorrow
    tomorrow_iso = tomorrow.isoformat()
    for event in events:
        start = event.get("start_date", "")
        end = event.get("end_date") or start
        if start <= tomorrow_iso <= end and event.get("affects_classes"):
            event_name = event.get("name_en") or event.get("name", "")
            return f"Tomorrow is {event_name} - No classes!"

    # Filter classes for tomorrow
    tomorrow_classes = [s for s in schedule if s.get("day_of_week") == day_of_week]

    if not tomorrow_classes:
        return f"No classes tomorrow ({DAY_NAMES[day_of_week]})!"

    # Sort by start time
    tomorrow_classes.sort(key=lambda x: x.get("start_time", ""))

    lines = [f"Tomorrow ({DAY_NAMES[day_of_week]}):"]
    for cls in tomorrow_classes:
        start = format_time(cls.get("start_time", ""))
        end = format_time(cls.get("end_time", ""))
        subject = cls.get("subject_code", "")
        class_type = cls.get("class_type", "LEC")
        room = cls.get("room", "")
        lecturer = cls.get("lecturer_name", "")

        line = f"- {subject} {start}-{end} ({class_type}"
        if room:
            line += f", {room}"
        if lecturer:
            line += f", {lecturer}"
        line += ")"
        lines.append(line)

    return "\n".join(lines)


def format_today_classes(schedule: list[dict], events: list[dict], today: date = None) -> str:
    """Format today's classes for display."""
    if today is None:
        today = date.today()
    day_of_week = today.weekday()

    # Check for events affecting today
    today_iso = today.isoformat()
    for event in events:
        start = event.get("start_date", "")
        end = event.get("end_date") or start
        if start <= today_iso <= end and event.get("affects_classes"):
            event_name = event.get("name_en") or event.get("name", "")
            return f"Today is {event_name} - No classes!"

    # Check if weekend
    if day_of_week >= 5:  # Saturday or Sunday
        return f"Today is {DAY_NAMES[day_of_week]} - No classes on weekends!"

    # Filter classes for today
    today_classes = [s for s in schedule if s.get("day_of_week") == day_of_week]

    if not today_classes:
        return f"No classes today ({DAY_NAMES[day_of_week]})!"

    # Sort by start time
    today_classes.sort(key=lambda x: x.get("start_time", ""))

    lines = [f"Today ({DAY_NAMES[day_of_week]}):"]
    for cls in today_classes:
        start = format_time(cls.get("start_time", ""))
        end = format_time(cls.get("end_time", ""))
        subject = cls.get("subject_code", "")
        class_type = cls.get("class_type", "LEC")
        room = cls.get("room", "")
        lecturer = cls.get("lecturer_name", "")

        line = f"- {subject} {start}-{end} ({class_type}"
        if room:
            line += f", {room}"
        if lecturer:
            line += f", {lecturer}"
        line += ")"
        lines.append(line)

    return "\n".join(lines)


def format_week_schedule(schedule: list[dict]) -> str:
    """Format the full week schedule for display."""
    if not schedule:
        return "No classes in your schedule!"

    # Group by day
    by_day = {}
    for slot in schedule:
        day = slot.get("day_of_week", 0)
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(slot)

    lines = ["This week's schedule:"]
    for day in sorted(by_day.keys()):
        day_name = DAY_NAMES[day]
        lines.append(f"\n*{day_name}*")

        day_classes = sorted(by_day[day], key=lambda x: x.get("start_time", ""))
        for cls in day_classes:
            start = format_time(cls.get("start_time", ""))
            end = format_time(cls.get("end_time", ""))
            subject = cls.get("subject_code", "")
            class_type = cls.get("class_type", "LEC")
            room = cls.get("room", "")

            line = f"  {start}-{end}: {subject} ({class_type}"
            if room:
                line += f", {room}"
            line += ")"
            lines.append(line)

    return "\n".join(lines)


def format_pending_assignments(assignments: list[dict]) -> str:
    """Format pending assignments for display."""
    if not assignments:
        return "No pending assignments!"

    lines = [f"{len(assignments)} pending assignment(s):"]
    for a in assignments:
        item_id = a.get("id", "?")
        title = a.get("title", "Untitled")
        subject = a.get("subject_code", "")
        due = a.get("due_date", "")

        # Format due date
        if due:
            try:
                dt = datetime.fromisoformat(due)
                due_str = dt.strftime("%a %d %b, %I:%M%p")
            except ValueError:
                due_str = due
        else:
            due_str = "No due date"

        line = f"[ID:{item_id}] {title}"
        if subject:
            line += f" ({subject})"
        line += f" - due {due_str}"
        lines.append(line)

    return "\n".join(lines)


def format_pending_tasks(tasks: list[dict]) -> str:
    """Format upcoming tasks for display."""
    if not tasks:
        return "No upcoming tasks!"

    lines = [f"{len(tasks)} upcoming task(s):"]
    for t in tasks:
        item_id = t.get("id", "?")
        title = t.get("title", "Untitled")
        date_str = t.get("scheduled_date", "")
        time_str = t.get("scheduled_time", "")
        location = t.get("location", "")

        line = f"[ID:{item_id}] {title}"
        if date_str:
            try:
                d = datetime.fromisoformat(date_str).date()
                line += f" - {format_date(d, include_day=True)}"
            except ValueError:
                line += f" - {date_str}"
        if time_str:
            line += f" at {format_time(time_str)}"
        if location:
            line += f" ({location})"
        lines.append(line)

    return "\n".join(lines)


def format_pending_todos(todos: list[dict]) -> str:
    """Format pending TODOs for display."""
    if not todos:
        return "No pending TODOs!"

    lines = [f"{len(todos)} pending TODO(s):"]
    for t in todos:
        item_id = t.get("id", "?")
        title = t.get("title", "Untitled")
        date_str = t.get("scheduled_date", "")
        time_str = t.get("scheduled_time", "")

        line = f"[ID:{item_id}] {title}"
        if date_str:
            line += f" ({date_str})"
        if time_str:
            line += f" at {format_time(time_str)}"
        lines.append(line)

    return "\n".join(lines)


def format_current_week(week: int | str, semester_start: Optional[str]) -> str:
    """Format current week information."""
    if isinstance(week, str):
        return f"Currently: {week}"

    if semester_start:
        return f"This is Week {week} of the semester"

    return f"Week {week} (semester start date not set)"


def format_next_offday(result: Optional[dict]) -> str:
    """Format next off day information."""
    if not result:
        return "No upcoming off days found in the next 3 months."

    event = result.get("event", {})
    off_date = result.get("date")

    name = event.get("name_en") or event.get("name", "Off Day")

    if off_date:
        return f"Next off day: {name} on {format_date(off_date, include_day=True)}"

    return f"Next off day: {name}"


# ==================== Helper Functions ====================

def _format_events_for_confirmation(events: list[AcademicEvent]) -> str:
    """Format events list for user confirmation."""
    lines = []
    for event in events[:15]:  # Limit to first 15 to avoid message too long
        date_str = event.start_date
        if event.end_date and event.end_date != event.start_date:
            date_str += f" to {event.end_date}"

        name = event.name_en if event.name_en else event.name
        lines.append(f"- [{event.event_type}] {name}: {date_str}")

    if len(events) > 15:
        lines.append(f"... and {len(events) - 15} more events")

    return "\n".join(lines)


def _format_schedule_for_confirmation(slots: list[ScheduleSlot]) -> str:
    """Format schedule slots for user confirmation."""
    # Group by day
    by_day = {}
    for slot in slots:
        if slot.day_of_week not in by_day:
            by_day[slot.day_of_week] = []
        by_day[slot.day_of_week].append(slot)

    lines = []
    for day in sorted(by_day.keys()):
        day_name = DAY_NAMES[day]
        lines.append(f"\n{day_name}:")

        day_slots = sorted(by_day[day], key=lambda x: x.start_time)
        for slot in day_slots:
            time_str = f"{format_time(slot.start_time)}-{format_time(slot.end_time)}"
            lines.append(
                f"  {time_str}: {slot.subject_code} ({slot.class_type})"
                f"{' - ' + slot.room if slot.room else ''}"
            )

    return "\n".join(lines)


def _format_assignment_for_confirmation(details: AssignmentDetails) -> str:
    """Format assignment details for user confirmation."""
    lines = [f"Title: {details.title}"]

    if details.subject_code:
        lines.append(f"Subject: {details.subject_code}")

    if details.due_date:
        try:
            dt = datetime.fromisoformat(details.due_date)
            lines.append(f"Due: {dt.strftime('%A, %d %b %Y at %I:%M%p')}")
        except ValueError:
            lines.append(f"Due: {details.due_date}")

    if details.description:
        lines.append(f"Description: {details.description}")

    if details.requirements:
        lines.append(f"Requirements: {details.requirements}")

    return "\n".join(lines)


# ==================== Conversation Handler Builders ====================

def get_onboarding_handler() -> ConversationHandler:
    """Build the onboarding conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("setup", start_onboarding)],
        states={
            OnboardingState.WAITING_CALENDAR.value: [
                MessageHandler(filters.PHOTO, receive_calendar_image),
                CommandHandler("skip", skip_step),
            ],
            OnboardingState.CONFIRM_CALENDAR.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_calendar),
            ],
            OnboardingState.WAITING_TIMETABLE.value: [
                MessageHandler(filters.PHOTO, receive_timetable_image),
                CommandHandler("skip", skip_step),
            ],
            OnboardingState.CONFIRM_TIMETABLE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_timetable),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)],
        name="onboarding",
        persistent=False,
    )
