"""Notification scheduler for daily briefings and reminders."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot
from telegram.error import TelegramError
import pytz

from ..config import config
from ..database.operations import DatabaseOperations
from ..bot.handlers import get_today, get_now
from ..utils.semester_logic import (
    get_current_week,
    is_class_day,
    get_event_on_date,
    get_all_breaks,
    classify_break_event,
    BREAK_INTER_SEMESTER,
    format_date,
    format_time,
    parse_date,
    hours_until,
    DAY_NAMES,
)

logger = logging.getLogger(__name__)

# Malaysia timezone
MY_TZ = pytz.timezone("Asia/Kuala_Lumpur")

# Initialize database
db = DatabaseOperations(config.DATABASE_PATH)

# Reminder level thresholds (hours before due)
ASSIGNMENT_REMINDER_LEVELS = {
    1: 72,   # 3 days
    2: 48,   # 2 days
    3: 24,   # 1 day
    4: 8,    # 8 hours
    5: 3,    # 3 hours
    6: 1,    # 1 hour
    7: 0,    # Due now
}

ASSIGNMENT_REMINDER_MESSAGES = {
    1: "Assignment '{title}' due in 3 days ({due_date})",
    2: "Assignment '{title}' due in 2 days ({due_date})",
    3: "Assignment '{title}' due TOMORROW at {due_time}!",
    4: "8 hours left for '{title}'!",
    5: "Only 3 hours left for '{title}'!",
    6: "URGENT: 1 hour remaining for '{title}'!",
    7: "Assignment '{title}' is NOW DUE!",
}


class NotificationScheduler:
    """Handles all scheduled notifications for the bot."""

    def __init__(self, bot: Bot):
        """Initialize the scheduler with a Telegram bot instance."""
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=MY_TZ)
        self._setup_jobs()

    def _setup_jobs(self):
        """Configure all scheduled jobs."""
        # Daily briefings
        self.scheduler.add_job(
            self.send_class_briefing,
            CronTrigger(hour=22, minute=0, timezone=MY_TZ),
            id="class_briefing",
            name="10PM Class Briefing",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.send_offday_alert,
            CronTrigger(hour=20, minute=0, timezone=MY_TZ),
            id="offday_alert",
            name="8PM Off-day Alert",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.send_midnight_todo_review,
            CronTrigger(hour=0, minute=0, timezone=MY_TZ),
            id="midnight_todo",
            name="12AM TODO Review",
            replace_existing=True
        )

        # Frequent checks for time-sensitive reminders (every 30 minutes)
        self.scheduler.add_job(
            self.check_assignment_reminders,
            IntervalTrigger(minutes=30, timezone=MY_TZ),
            id="assignment_reminders",
            name="Assignment Reminder Check",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.check_task_reminders,
            IntervalTrigger(minutes=30, timezone=MY_TZ),
            id="task_reminders",
            name="Task Reminder Check",
            replace_existing=True
        )

        self.scheduler.add_job(
            self.check_todo_reminders,
            IntervalTrigger(minutes=30, timezone=MY_TZ),
            id="todo_reminders",
            name="TODO Reminder Check",
            replace_existing=True
        )

        # Check for semester starting (1 week before break ends)
        self.scheduler.add_job(
            self.check_semester_starting,
            CronTrigger(hour=20, minute=30, timezone=MY_TZ),
            id="semester_starting",
            name="8:30PM Semester Starting Check",
            replace_existing=True
        )

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Notification scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Notification scheduler stopped")

    async def _get_all_chat_ids(self) -> list[int]:
        """Get all registered user chat IDs."""
        # For now, we'll get users from the database
        # In a real scenario, you might want to filter by notification preferences
        conn = db._get_conn()
        try:
            cursor = conn.execute("SELECT telegram_chat_id FROM user_config")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    async def _send_notification(self, chat_id: int, message: str, keyboard=None) -> bool:
        """Send a notification to a specific user."""
        # Check if user is muted
        if db.is_muted(chat_id):
            logger.info(f"Skipping notification to {chat_id} - user is muted")
            return False

        try:
            if keyboard:
                await self.bot.send_message(chat_id=chat_id, text=message, reply_markup=keyboard)
            else:
                await self.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Sent notification to {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send notification to {chat_id}: {e}")
            return False

    # ==================== Daily Briefings ====================

    async def send_class_briefing(self):
        """10PM briefing: Tomorrow's classes."""
        logger.info("Running 10PM class briefing")

        chat_ids = await self._get_all_chat_ids()
        if not chat_ids:
            logger.info("No users to notify")
            return

        tomorrow = get_today() + timedelta(days=1)
        events = db.get_all_events()

        # Check if tomorrow has classes
        if not is_class_day(tomorrow, events):
            # Skip if tomorrow is off - the 8PM alert will handle this
            logger.info("Tomorrow is not a class day, skipping briefing")
            return

        # Get schedule for tomorrow
        day_of_week = tomorrow.weekday()
        schedule = db.get_schedule_for_day(day_of_week)

        # Format message (handles both with classes and no classes)
        message = self._format_class_briefing(tomorrow, schedule)

        # Send to all users
        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)

    def _format_class_briefing(self, tomorrow: date, schedule: list[dict]) -> str:
        """Format the class briefing message."""
        day_name = DAY_NAMES[tomorrow.weekday()]

        # Handle no classes scheduled
        if not schedule:
            return (
                f"📚 Tomorrow ({day_name}, {tomorrow.strftime('%d %b')})\n\n"
                f"No classes on your timetable!\n"
                f"Enjoy your free day 🎉"
            )

        lines = [f"📚 Classes Tomorrow ({day_name}, {tomorrow.strftime('%d %b')}):\n"]

        # Sort by start time
        schedule.sort(key=lambda x: x.get("start_time", ""))

        for cls in schedule:
            start = format_time(cls.get("start_time", ""))
            end = format_time(cls.get("end_time", ""))
            subject = cls.get("subject_code", "Unknown")
            class_type = cls.get("class_type", "LEC")
            room = cls.get("room", "")
            lecturer = cls.get("lecturer_name", "")

            line = f"• {subject} {start}-{end} ({class_type})"
            if room:
                line += f"\n  📍 {room}"
            if lecturer:
                line += f"\n  👨‍🏫 {lecturer}"
            lines.append(line)

        return "\n".join(lines)

    async def send_offday_alert(self):
        """8PM alert: If tomorrow is a holiday/off-day."""
        logger.info("Running 8PM off-day check")

        chat_ids = await self._get_all_chat_ids()
        if not chat_ids:
            return

        tomorrow = get_today() + timedelta(days=1)
        events = db.get_all_events()

        # Check if tomorrow is an off day
        event = get_event_on_date(tomorrow, events)
        if not event:
            logger.info("Tomorrow is not an off day")
            return

        # Get classes that would have happened
        day_of_week = tomorrow.weekday()
        affected_classes = db.get_schedule_for_day(day_of_week)

        # Format message
        message = self._format_offday_alert(tomorrow, event, affected_classes)

        # Send to all users
        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)

    def _format_offday_alert(
        self,
        tomorrow: date,
        event: dict,
        affected_classes: list[dict]
    ) -> str:
        """Format the off-day alert message."""
        event_name = event.get("name_en") or event.get("name", "Holiday")
        day_name = DAY_NAMES[tomorrow.weekday()]

        lines = [
            f"🎉 No Classes Tomorrow!",
            f"",
            f"Tomorrow ({day_name}, {tomorrow.strftime('%d %b')}) is:",
            f"📅 {event_name}",
        ]

        if affected_classes:
            lines.append("")
            lines.append("Classes cancelled:")
            for cls in affected_classes:
                subject = cls.get("subject_code", "")
                start = format_time(cls.get("start_time", ""))
                lines.append(f"• {subject} at {start}")

        return "\n".join(lines)

    async def send_midnight_todo_review(self):
        """12AM review: List all pending TODOs without specific time."""
        logger.info("Running midnight TODO review")

        chat_ids = await self._get_all_chat_ids()
        if not chat_ids:
            return

        # Get TODOs without specific time
        todos = db.get_todos_without_time()

        if not todos:
            logger.info("No pending TODOs to review")
            return

        # Format message
        message = self._format_todo_review(todos)

        # Send to all users with midnight review enabled
        for chat_id in chat_ids:
            user_config = db.get_user_config(chat_id)
            if user_config and user_config.get("midnight_todo_review", 1):
                await self._send_notification(chat_id, message)

    def _format_todo_review(self, todos: list[dict]) -> str:
        """Format the midnight TODO review message."""
        lines = [
            f"📝 Midnight TODO Review",
            f"",
            f"You have {len(todos)} pending TODO(s):",
            "",
        ]

        for i, todo in enumerate(todos, 1):
            title = todo.get("title", "Untitled")
            date_str = todo.get("scheduled_date", "")

            line = f"{i}. {title}"
            if date_str:
                line += f" (scheduled: {date_str})"
            lines.append(line)

        lines.append("")
        lines.append("Reply with 'done with [task]' to mark as complete.")

        return "\n".join(lines)

    # ==================== Escalating Reminders ====================

    async def check_assignment_reminders(self):
        """Check and send assignment reminders based on escalation levels."""
        logger.info("Checking assignment reminders")

        assignments = db.get_pending_assignments()
        now = get_now()

        for assignment in assignments:
            due_date_str = assignment.get("due_date")
            if not due_date_str:
                continue

            try:
                # Parse due date
                due_date = datetime.fromisoformat(due_date_str)
                if due_date.tzinfo is None:
                    due_date = MY_TZ.localize(due_date)

                hours_left = hours_until(due_date, now)
                current_level = assignment.get("last_reminder_level", 0)

                # Determine which level should be sent
                next_level = self._get_next_reminder_level(hours_left, current_level)

                if next_level and next_level > current_level:
                    # Send reminder
                    await self._send_assignment_reminder(assignment, next_level, due_date)

                    # Update reminder level
                    db.update_assignment_reminder_level(assignment["id"], next_level)

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid due date for assignment {assignment['id']}: {e}")

    def _get_next_reminder_level(self, hours_left: float, current_level: int) -> Optional[int]:
        """Determine the next reminder level based on hours remaining."""
        for level in range(current_level + 1, 8):
            threshold = ASSIGNMENT_REMINDER_LEVELS.get(level, -1)
            if threshold >= 0 and hours_left <= threshold:
                return level
        return None

    async def _send_assignment_reminder(
        self,
        assignment: dict,
        level: int,
        due_date: datetime
    ):
        """Send an assignment reminder at the specified level."""
        chat_ids = await self._get_all_chat_ids()

        title = assignment.get("title", "Untitled")
        subject = assignment.get("subject_code", "")
        if subject:
            title = f"{title} ({subject})"

        message_template = ASSIGNMENT_REMINDER_MESSAGES.get(level, "Reminder for '{title}'")
        message = "⏰ " + message_template.format(
            title=title,
            due_date=due_date.strftime("%a %d %b"),
            due_time=due_date.strftime("%I:%M%p")
        )

        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)

    async def check_task_reminders(self):
        """Check and send task reminders (1 day before and 2 hours before)."""
        logger.info("Checking task reminders")

        tasks = db.get_upcoming_tasks(days=7)
        now = get_now()
        today = now.date()

        for task in tasks:
            task_date_str = task.get("scheduled_date")
            task_time_str = task.get("scheduled_time")

            if not task_date_str:
                continue

            try:
                task_date = datetime.strptime(task_date_str, "%Y-%m-%d").date()

                # 1-day reminder: Send at 8PM the day before
                if not task.get("reminded_1day"):
                    if task_date == today + timedelta(days=1):
                        if now.hour >= 20:  # After 8PM
                            await self._send_task_reminder(task, "1day")
                            db.update_task_reminder(task["id"], "1day")

                # 2-hour reminder: Only if task has specific time
                if task_time_str and not task.get("reminded_2hours"):
                    task_datetime = datetime.combine(
                        task_date,
                        datetime.strptime(task_time_str, "%H:%M").time()
                    )
                    task_datetime = MY_TZ.localize(task_datetime)

                    hours_left = hours_until(task_datetime, now)
                    if 0 <= hours_left <= 2:
                        await self._send_task_reminder(task, "2hours")
                        db.update_task_reminder(task["id"], "2hours")

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date for task {task['id']}: {e}")

    async def _send_task_reminder(self, task: dict, reminder_type: str):
        """Send a task reminder."""
        chat_ids = await self._get_all_chat_ids()

        title = task.get("title", "Untitled")
        task_date = task.get("scheduled_date", "")
        task_time = task.get("scheduled_time", "")
        location = task.get("location", "")

        if reminder_type == "1day":
            message = f"📋 Task Tomorrow: {title}"
            if task_time:
                message += f" at {format_time(task_time)}"
            if location:
                message += f"\n📍 {location}"
        else:  # 2hours
            message = f"⏰ Task in 2 hours: {title}"
            if task_time:
                message += f" at {format_time(task_time)}"
            if location:
                message += f"\n📍 {location}"

        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)

    async def check_todo_reminders(self):
        """Check and send TODO reminders (1 hour before for time-specific TODOs)."""
        logger.info("Checking TODO reminders")

        todos = db.get_pending_todos()
        now = get_now()
        today = now.date()

        for todo in todos:
            todo_date_str = todo.get("scheduled_date")
            todo_time_str = todo.get("scheduled_time")

            # Only remind for TODOs with specific time that haven't been reminded
            if not todo_time_str or todo.get("reminded"):
                continue

            try:
                # Default to today if no date specified
                if todo_date_str:
                    todo_date = datetime.strptime(todo_date_str, "%Y-%m-%d").date()
                else:
                    todo_date = today

                if todo_date != today:
                    continue

                todo_datetime = datetime.combine(
                    todo_date,
                    datetime.strptime(todo_time_str, "%H:%M").time()
                )
                todo_datetime = MY_TZ.localize(todo_datetime)

                hours_left = hours_until(todo_datetime, now)
                if 0 <= hours_left <= 1:
                    await self._send_todo_reminder(todo)
                    db.update_todo_reminder(todo["id"])

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date/time for todo {todo['id']}: {e}")

    async def _send_todo_reminder(self, todo: dict):
        """Send a TODO reminder."""
        chat_ids = await self._get_all_chat_ids()

        title = todo.get("title", "Untitled")
        todo_time = todo.get("scheduled_time", "")

        message = f"⏰ TODO Reminder: {title}"
        if todo_time:
            message += f" at {format_time(todo_time)}"

        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)

    # ==================== Semester Starting Notification ====================

    async def check_semester_starting(self):
        """Check if inter-semester break is ending in 1 week and notify."""
        logger.info("Checking for semester starting notification")

        events = db.get_all_events()
        today = get_today()

        # Get inter-semester break
        _, inter_break = get_all_breaks(events)

        if not inter_break:
            logger.info("No inter-semester break found")
            return

        # Get break end date
        break_end = parse_date(inter_break.get("end_date"))
        if not break_end:
            logger.info("Inter-semester break has no end date")
            return

        # Check if break ends in exactly 7 days
        days_until_end = (break_end - today).days

        if days_until_end == 7:
            logger.info("Inter-semester break ends in 1 week, sending notification")
            await self._send_semester_starting_notification(break_end)
        else:
            logger.info(f"Inter-semester break ends in {days_until_end} days, not notifying")

    async def _send_semester_starting_notification(self, break_end: date):
        """Send notification that new semester is starting soon."""
        chat_ids = await self._get_all_chat_ids()

        # The new semester starts the day after break ends
        semester_start = break_end + timedelta(days=1)
        day_name = DAY_NAMES[semester_start.weekday()]

        message = (
            "📚 Heads Up!\n\n"
            f"The inter-semester break ends in 1 week!\n\n"
            f"New semester starts: {day_name}, {semester_start.strftime('%d %b %Y')}\n"
            f"That will be Week 1 of the new semester.\n\n"
            "Time to prepare for classes!"
        )

        for chat_id in chat_ids:
            await self._send_notification(chat_id, message)


# Module-level scheduler instance
_scheduler: Optional[NotificationScheduler] = None


def get_scheduler(bot: Bot) -> NotificationScheduler:
    """Get or create the notification scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = NotificationScheduler(bot)
    return _scheduler


def start_scheduler(bot: Bot):
    """Start the notification scheduler."""
    scheduler = get_scheduler(bot)
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the notification scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
