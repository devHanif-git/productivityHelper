"""Multi-language support for bot messages."""

from typing import Optional


TRANSLATIONS = {
    "en": {
        # General
        "welcome": "Welcome to UTeM Student Assistant Bot!",
        "goodbye": "Goodbye! Good luck with your studies!",
        "thanks": "You're welcome! Let me know if you need anything else.",
        "help_prompt": "I'm here to help with your schedule and tasks.\nUse /help to see what I can do!",

        # Schedule
        "today_header": "Today ({day}):",
        "tomorrow_header": "Tomorrow ({day}):",
        "no_classes_today": "No classes today ({day})!",
        "no_classes_tomorrow": "No classes tomorrow ({day})!",
        "weekend": "Today is {day} - No classes on weekends!",
        "holiday": "Today is {event} - No classes!",

        # Assignments
        "pending_assignments": "{count} pending assignment(s):",
        "no_assignments": "No pending assignments!",
        "assignment_added": "Assignment added: '{title}'\nDue: {due_date}\nID: {id}",
        "assignment_completed": "Marked '{title}' as completed!",

        # Tasks
        "pending_tasks": "{count} upcoming task(s):",
        "no_tasks": "No upcoming tasks!",
        "task_added": "Task added: '{title}'\nScheduled: {date}",
        "task_completed": "Marked '{title}' as completed!",

        # TODOs
        "pending_todos": "{count} pending TODO(s):",
        "no_todos": "No pending TODOs!",
        "todo_added": "TODO added: '{title}'\nID: {id}",
        "todo_completed": "Marked '{title}' as completed!",

        # Exams
        "upcoming_exams": "Upcoming Exams:",
        "no_exams": "No upcoming exams found.",
        "exam_added": "Exam added: {type} for {subject} on {date}",

        # Actions
        "deleted": "Deleted {type} '{name}'.",
        "delete_confirm": "Delete {type} '{name}' (ID: {id})?\n\nReply 'yes' to confirm or 'no' to cancel.",
        "cancelled": "Action cancelled.",
        "not_found": "{type} #{id} not found.",

        # Stats
        "stats_header": "Statistics (Past {days} Days)",
        "completed": "Completed: {completed}/{total} ({percent}%)",
        "pending": "Pending: {count}",

        # Notifications
        "muted": "Notifications muted for {duration} hour(s).",
        "unmuted": "Notifications resumed.",

        # Errors
        "error_generic": "Something went wrong. Please try again.",
        "invalid_id": "Invalid ID. Please provide a number.",
        "unknown_type": "Unknown item type.",
    },

    "my": {
        # General
        "welcome": "Selamat datang ke Bot Pembantu Pelajar UTeM!",
        "goodbye": "Selamat tinggal! Semoga berjaya dalam pelajaran anda!",
        "thanks": "Sama-sama! Beritahu saya jika anda perlukan apa-apa lagi.",
        "help_prompt": "Saya di sini untuk membantu dengan jadual dan tugasan anda.\nGuna /help untuk melihat apa yang saya boleh lakukan!",

        # Schedule
        "today_header": "Hari ini ({day}):",
        "tomorrow_header": "Esok ({day}):",
        "no_classes_today": "Tiada kelas hari ini ({day})!",
        "no_classes_tomorrow": "Tiada kelas esok ({day})!",
        "weekend": "Hari ini adalah {day} - Tiada kelas pada hujung minggu!",
        "holiday": "Hari ini adalah {event} - Tiada kelas!",

        # Assignments
        "pending_assignments": "{count} tugasan tertunggak:",
        "no_assignments": "Tiada tugasan tertunggak!",
        "assignment_added": "Tugasan ditambah: '{title}'\nTarikh akhir: {due_date}\nID: {id}",
        "assignment_completed": "'{title}' ditandakan sebagai selesai!",

        # Tasks
        "pending_tasks": "{count} tugas akan datang:",
        "no_tasks": "Tiada tugas akan datang!",
        "task_added": "Tugas ditambah: '{title}'\nDijadualkan: {date}",
        "task_completed": "'{title}' ditandakan sebagai selesai!",

        # TODOs
        "pending_todos": "{count} TODO tertunggak:",
        "no_todos": "Tiada TODO tertunggak!",
        "todo_added": "TODO ditambah: '{title}'\nID: {id}",
        "todo_completed": "'{title}' ditandakan sebagai selesai!",

        # Exams
        "upcoming_exams": "Peperiksaan Akan Datang:",
        "no_exams": "Tiada peperiksaan akan datang.",
        "exam_added": "Peperiksaan ditambah: {type} untuk {subject} pada {date}",

        # Actions
        "deleted": "{type} '{name}' telah dipadam.",
        "delete_confirm": "Padam {type} '{name}' (ID: {id})?\n\nBalas 'ya' untuk sahkan atau 'tidak' untuk batal.",
        "cancelled": "Tindakan dibatalkan.",
        "not_found": "{type} #{id} tidak dijumpai.",

        # Stats
        "stats_header": "Statistik ({days} Hari Lepas)",
        "completed": "Selesai: {completed}/{total} ({percent}%)",
        "pending": "Tertunggak: {count}",

        # Notifications
        "muted": "Notifikasi disenyapkan untuk {duration} jam.",
        "unmuted": "Notifikasi disambung semula.",

        # Errors
        "error_generic": "Sesuatu tidak kena. Sila cuba lagi.",
        "invalid_id": "ID tidak sah. Sila berikan nombor.",
        "unknown_type": "Jenis item tidak diketahui.",
    }
}

# Day names in both languages
DAY_NAMES = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "my": ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"]
}


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get translated text for a key."""
    if lang not in TRANSLATIONS:
        lang = "en"

    text = TRANSLATIONS[lang].get(key)
    if not text:
        # Fallback to English
        text = TRANSLATIONS["en"].get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    return text


def get_day_name(day_index: int, lang: str = "en") -> str:
    """Get day name in the specified language."""
    if lang not in DAY_NAMES:
        lang = "en"
    return DAY_NAMES[lang][day_index % 7]
