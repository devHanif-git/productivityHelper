"""Telegram inline keyboard layouts for interactive UI."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data="cmd_today"),
            InlineKeyboardButton("📆 Tomorrow", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton("📚 Assignments", callback_data="cmd_assignments"),
            InlineKeyboardButton("📋 Tasks", callback_data="cmd_tasks"),
        ],
        [
            InlineKeyboardButton("✅ TODOs", callback_data="cmd_todos"),
            InlineKeyboardButton("📊 Stats", callback_data="cmd_stats"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton("❓ Help", callback_data="cmd_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_schedule_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the schedule submenu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data="cmd_today"),
            InlineKeyboardButton("Tomorrow", callback_data="cmd_tomorrow"),
            InlineKeyboardButton("This Week", callback_data="cmd_week"),
        ],
        [
            InlineKeyboardButton("Set Online", callback_data="menu_setonline"),
            InlineKeyboardButton("Edit Room", callback_data="menu_editroom"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard(has_date_override: bool = False, has_time_override: bool = False) -> InlineKeyboardMarkup:
    """Create the settings menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Semester", callback_data="menu_semester"),
            InlineKeyboardButton("🌐 Language", callback_data="menu_language"),
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="menu_notifications"),
        ],
        [
            InlineKeyboardButton("🔇 Mute (1h)", callback_data="mute_1h"),
            InlineKeyboardButton("🔇 Mute (3h)", callback_data="mute_3h"),
        ],
    ]

    # Add reset buttons if overrides are active
    if has_date_override or has_time_override:
        reset_row = []
        if has_date_override:
            reset_row.append(InlineKeyboardButton("🔄 Reset Date", callback_data="reset_date"))
        if has_time_override:
            reset_row.append(InlineKeyboardButton("🔄 Reset Time", callback_data="reset_time"))
        keyboard.append(reset_row)

    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data="menu_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇲🇾 Bahasa Melayu", callback_data="lang_my"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_initial_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard for first-time users (no back button)."""
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="initial_lang_en"),
            InlineKeyboardButton("🇲🇾 Bahasa Melayu", callback_data="initial_lang_my"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_semester_keyboard() -> InlineKeyboardMarkup:
    """Create semester settings keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Set Semester Start", callback_data="semester_set"),
        ],
        [
            InlineKeyboardButton("📊 Current Week", callback_data="semester_week"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Create notification settings keyboard with current status."""
    briefing = settings.get("daily_briefing", "on")
    offday = settings.get("offday_alert", "on")
    midnight = settings.get("midnight_review", "on")

    keyboard = [
        [
            InlineKeyboardButton(
                f"{'✅' if briefing == 'on' else '❌'} Daily Briefing",
                callback_data=f"toggle_briefing_{briefing}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if offday == 'on' else '❌'} Off-Day Alert",
                callback_data=f"toggle_offday_{offday}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{'✅' if midnight == 'on' else '❌'} Midnight Review",
                callback_data=f"toggle_midnight_{midnight}"
            ),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_item_actions_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Create action buttons for an item (assignment/task/todo)."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Done", callback_data=f"done_{item_type}_{item_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{item_type}_{item_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{item_type}_{item_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str, item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}_{item_type}_{item_id}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_snooze_keyboard(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Create snooze options keyboard for reminders."""
    keyboard = [
        [
            InlineKeyboardButton("30 min", callback_data=f"snooze_{item_type}_{item_id}_30"),
            InlineKeyboardButton("1 hour", callback_data=f"snooze_{item_type}_{item_id}_60"),
            InlineKeyboardButton("2 hours", callback_data=f"snooze_{item_type}_{item_id}_120"),
        ],
        [
            InlineKeyboardButton("✅ Done", callback_data=f"done_{item_type}_{item_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_export_keyboard() -> InlineKeyboardMarkup:
    """Create export options keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Schedule", callback_data="export_schedule"),
            InlineKeyboardButton("📚 Assignments", callback_data="export_assignments"),
        ],
        [
            InlineKeyboardButton("📋 All Data", callback_data="export_all"),
            InlineKeyboardButton("📆 iCal", callback_data="export_ical"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Create a simple back to menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_content_with_menu_keyboard() -> InlineKeyboardMarkup:
    """Create quick actions + back to menu keyboard for content views."""
    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data="cmd_today"),
            InlineKeyboardButton("📆 Tomorrow", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton("📚 Assignments", callback_data="cmd_assignments"),
            InlineKeyboardButton("📋 Tasks", callback_data="cmd_tasks"),
        ],
        [
            InlineKeyboardButton("✅ TODOs", callback_data="cmd_todos"),
            InlineKeyboardButton("📊 Stats", callback_data="cmd_stats"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton("❓ Help", callback_data="cmd_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_voice_processing_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Create voice message processing options keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📝 Summary", callback_data=f"voice_summary_{message_id}"),
            InlineKeyboardButton("📋 Meeting Minutes", callback_data=f"voice_minutes_{message_id}"),
        ],
        [
            InlineKeyboardButton("✅ Extract Tasks", callback_data=f"voice_tasks_{message_id}"),
            InlineKeyboardButton("📚 Study Notes", callback_data=f"voice_study_{message_id}"),
        ],
        [
            InlineKeyboardButton("💾 Save Transcript", callback_data=f"voice_transcript_{message_id}"),
            InlineKeyboardButton("🎯 Smart Analysis", callback_data=f"voice_smart_{message_id}"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"voice_cancel_{message_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notes_list_keyboard(notes: list) -> InlineKeyboardMarkup:
    """Create keyboard for voice notes list with view buttons."""
    keyboard = []
    for note in notes[:5]:  # Show max 5 notes
        note_id = note.get("id")
        title = note.get("title") or f"Note #{note_id}"
        if len(title) > 25:
            title = title[:22] + "..."
        keyboard.append([
            InlineKeyboardButton(f"📄 {title}", callback_data=f"view_note_{note_id}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_note_actions_keyboard(note_id: int) -> InlineKeyboardMarkup:
    """Create action buttons for a voice note."""
    keyboard = [
        [
            InlineKeyboardButton("📖 Full Content", callback_data=f"note_full_{note_id}"),
            InlineKeyboardButton("📝 Original", callback_data=f"note_transcript_{note_id}"),
        ],
        [
            InlineKeyboardButton("✏️ Rename", callback_data=f"note_rename_{note_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"note_delete_{note_id}"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Notes", callback_data="cmd_notes"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
