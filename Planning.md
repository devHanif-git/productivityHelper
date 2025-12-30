# Implementation Plan: UTeM Student Assistant Bot Enhancements

## Overview
This plan addresses known bugs and new features from Testing.md for the UTeM Student Assistant Bot.

## User Decisions
- **Edit confirmation:** Require confirmation before applying changes
- **Online mode:** Support both per-class per-week AND global per-week options
- **Event filtering:** Completely ignore unwanted events during parsing
- **Priority:** All features (bug fixes, /today + NL queries, edit data, online mode)

---

## PART 1: BUG FIXES

### Bug 1: /done marks as done but item still shows in list
**Root Cause Analysis:** Likely a caching/display issue. The database update is correct (`is_completed=1`).
**Files:** `src/bot/handlers.py`, `src/database/operations.py`
**Fix:** Verify the completion logic and ensure immediate database commit.

### Bug 2: IDs not showing in /assignments, /todos, /tasks
**Root Cause:** CONFIRMED - Formatters use `enumerate(items, 1)` instead of actual database IDs.
**Files:** `src/bot/conversations.py` (Lines 430-506)
**Fix:** Modify formatters to display actual `id` field from database instead of enumeration index.

**Before:**
```python
for i, a in enumerate(assignments, 1):
    line = f"{i}. {title}"  # Shows 1, 2, 3...
```

**After:**
```python
for a in assignments:
    item_id = a.get("id")
    line = f"[ID:{item_id}] {title}"  # Shows actual database ID
```

---

## PART 2: NEW FEATURES

### Feature 1: Add /today command for schedule
**Files to modify:**
- `src/bot/handlers.py` - Add `today_command()` handler
- `src/bot/conversations.py` - Add `format_today_classes()` formatter
- `src/ai/intent_parser.py` - Add regex for "today" schedule queries

**Implementation:**
1. Add `/today` command handler that:
   - Gets today's day of week
   - Fetches schedule for that day
   - Checks for events affecting today
   - Formats and returns result

2. Add intent `QUERY_TODAY_CLASSES` with regex patterns:
   - "what class today"
   - "any class today"
   - "do I have class today"
   - "kelas hari ini"

---

### Feature 2: Filter unwanted calendar events
**Events to completely ignore (not stored):**
- "Pendaftaran Kursus untuk Pelajar Baharu" (New undergraduate registration)
- "Minggu Harian Siswa"

**Files to modify:**
- `src/ai/image_parser.py` - Add filter during calendar parsing

**Implementation:**
Add a blocklist in `parse_academic_calendar()` to completely skip events containing:
- "pelajar baharu"
- "harian siswa"
- "pendaftaran kursus"
- "pendaftaran pelajar"

These events will NOT be stored in database at all.

---

### Feature 3: Edit database data (e.g., change room)
**Behavior:** Require confirmation before applying changes

**New commands:**
- `/edit schedule <id> room <new_room>` - Edit class room
- `/edit assignment <id> due <new_date>` - Edit assignment due date

**Files to modify:**
- `src/bot/handlers.py` - Add `edit_command()` handler with confirmation flow
- `src/bot/conversations.py` - Add edit confirmation conversation state
- `src/database/operations.py` - Add `update_schedule_slot()`, `update_assignment()` methods

**Flow:**
1. User: `/edit schedule 1 room BK12`
2. Bot: "Change BITP1113 (Monday 8AM) room from BK13 to BK12? (yes/no)"
3. User: "yes"
4. Bot: "Updated successfully!"

**Natural language support:**
- "change BITP1113 room to BK12"
- "update assignment 1 due date to Friday"

---

### Feature 4: Use subject name alongside subject code
**Current:** Only `subject_code` used for matching
**Goal:** Allow both "BITP1113" and "Programming Technique" to work

**Files to modify:**
- `src/database/operations.py` - Add `get_schedule_by_subject_name()` method
- `src/ai/intent_parser.py` - Extract both subject_code and subject_name

**Implementation:**
1. Add fuzzy matching function for subject names
2. When user says "DBD class" or "Database Design class", match to BITI1113
3. Build subject alias mapping from schedule table

---

### Feature 5: Natural language queries for academic dates
**New queries:**
- "when midterm break" / "bila cuti pertengahan"
- "when final exam" / "bila peperiksaan akhir"
- "when midterm exam" / "bila ujian pertengahan"
- "what is schedule today" / "jadual hari ini"
- "do I have class today"

**Files to modify:**
- `src/ai/intent_parser.py` - Add new intents and regex patterns
- `src/bot/handlers.py` - Add handlers for new intents
- `src/utils/semester_logic.py` - Add `get_midterm_break()`, `get_final_exam_period()` functions

**New Intent Enum values:**
- `QUERY_TODAY_CLASSES`
- `QUERY_MIDTERM_BREAK`
- `QUERY_FINAL_EXAM`
- `QUERY_MIDTERM_EXAM`

---

### Feature 6: /online command and set class to online mode
**Schema change required:**
Create new `online_overrides` table to track per-class or global online settings by week/date

**New table schema:**
```sql
CREATE TABLE online_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code TEXT,  -- NULL means ALL classes
    week_number INTEGER,  -- NULL if using specific date
    specific_date TEXT,   -- NULL if using week_number
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**New commands:**
- `/online` - Show next online lecture week/date
- `/setonline <subject|all> <week|date>` - Set online mode

**Files to modify:**
- `src/database/models.py` - Add `online_overrides` table
- `src/database/operations.py` - Add `set_online_override()`, `get_online_overrides()`, `is_class_online()` methods
- `src/bot/handlers.py` - Add handlers
- `src/ai/intent_parser.py` - Add SET_ONLINE intent

**Supported variations (both per-class AND global):**
- "set class DBD online tomorrow" (per-class, specific date)
- "set class OS online next week" (per-class, week)
- "set all classes online on week 12" (global, week)
- "set class BITP1113 online on 15 Jan" (per-class, specific date)
- `/setonline BITP1113 week12`
- `/setonline all week12`

---

### Feature 7: Set important exam dates
**Goal:** Track specific exam dates per subject (midterm/final)

**Option A:** Use existing `events` table with additional metadata
**Option B:** Create new `exams` table for per-subject tracking

**Recommended:** Option A - Add subject_code to events table for subject-specific exams

**Schema modification:**
```sql
ALTER TABLE events ADD COLUMN subject_code TEXT;
```

**Usage:**
- "Final exam BITP1113 on 15 Jan 2025"
- "Midterm BITI1213 on 20 Dec 2024 10am"

---

## PART 3: UI IMPROVEMENTS (Future - Complex)

### Feature: Replace "/" commands with UI buttons
**Complexity:** HIGH - Requires significant refactoring
**Recommendation:** Defer to future iteration

**If implemented:**
- Use Telegram inline keyboards
- Add `InlineKeyboardMarkup` to key responses
- Create menu flows for common actions

---

## IMPLEMENTATION STATUS: COMPLETED

### Step 1: Bug Fixes (2 items) - DONE
1. [x] **Fix ID display** in `/assignments`, `/todos`, `/tasks` formatters
2. [x] **Verify /done completion** - Logic verified correct

### Step 2: /today Command + NL Queries (4 items) - DONE
3. [x] **Add /today command**
4. [x] **Add QUERY_TODAY_CLASSES intent** with regex patterns
5. [x] **Add midterm/final exam query intents**
6. [x] **Filter unwanted calendar events during parsing**

### Step 3: Edit Data Feature (3 items) - DONE
7. [x] **Add database update methods**
8. [x] **Add /edit command with confirmation flow**
9. [x] **Add natural language edit intents**

### Step 4: Online Mode Feature (4 items) - DONE
10. [x] **Create online_overrides table**
11. [x] **Add online override CRUD operations**
12. [x] **Add /online and /setonline commands**
13. [x] **Add SET_ONLINE intent for NL support**

### Step 5: Subject Name Support (2 items) - DONE
14. [x] **Add subject name lookup method**
15. [x] **Enhance intent parser to match subject names**

---

## CRITICAL FILES TO MODIFY

| File | Purpose |
|------|---------|
| `src/bot/handlers.py` | Command handlers, intent routing |
| `src/bot/conversations.py` | Response formatters |
| `src/ai/intent_parser.py` | Intent enum, regex patterns |
| `src/database/operations.py` | CRUD operations |
| `src/database/models.py` | Schema changes |
| `src/utils/semester_logic.py` | Date/week calculations |
| `src/ai/image_parser.py` | Calendar event filtering |

---

## TOTAL: 15 Implementation Items

**Estimated scope:** Medium-Large (touches 7 core files, 1 new DB table)

---

## RECENTLY IMPLEMENTED FEATURES

### Priority 1: High Value Features - DONE

#### Feature: Set Exam Dates Per Subject
**Status:** ✅ IMPLEMENTED
**Description:** Allow users to manually set exam dates for specific subjects

**Commands:**
- `/setexam <subject> <type> <date> [time]` - Set exam date
- `/exams` - List all upcoming exams
- Natural language: "final exam BITP1113 on 15 Jan 2025"

**Files modified:**
- `src/database/models.py` - Added `subject_code` to events table
- `src/database/operations.py` - Added `add_exam()`, `get_upcoming_exams()`, `get_exams_for_subject()`
- `src/bot/handlers.py` - Added `/setexam`, `/exams` commands
- `src/ai/intent_parser.py` - Added `ADD_EXAM`, `QUERY_EXAMS` intents

---

#### Feature: Delete/Remove Items
**Status:** ✅ IMPLEMENTED
**Description:** Allow users to delete assignments, tasks, todos, online overrides, events

**Commands:**
- `/delete <type> <id>` - Delete item with confirmation
- Natural language: "delete assignment 5", "remove todo 3"

**Files modified:**
- `src/database/operations.py` - Added `delete_assignment()`, `delete_task()`, `delete_todo()`, `delete_event()`
- `src/bot/handlers.py` - Added `/delete` command with confirmation flow
- `src/ai/intent_parser.py` - Added `DELETE_ITEM` intent

---

#### Feature: View Schedule by Subject
**Status:** ✅ IMPLEMENTED
**Description:** Query schedule for a specific subject

**Commands:**
- `/schedule <subject>` - Show all slots for a subject (by code or name)

**Files modified:**
- `src/database/operations.py` - Added `get_schedule_by_subject()`
- `src/bot/handlers.py` - Added `/schedule` command

---

### Priority 2: UI Improvements - DONE

#### Feature: Telegram Inline Keyboards
**Status:** ✅ IMPLEMENTED
**Description:** Interactive button menus for common actions

**Commands:**
- `/menu` - Show main interactive menu
- `/settings` - Show settings menu

**Files created/modified:**
- `src/bot/keyboards.py` - NEW FILE with all keyboard layouts
- `src/bot/handlers.py` - Added `callback_query_handler()` for button callbacks

**Menu structure:**
- Main Menu: Today, Tomorrow, Assignments, Tasks, TODOs, Stats, Settings, Help
- Settings Menu: Notifications, Language, Mute options
- Language Menu: English, Bahasa Melayu

---

#### Feature: Quick Action Buttons
**Status:** ✅ IMPLEMENTED
**Description:** Action buttons for items (Done, Edit, Delete)

**Implementation:**
- `get_item_actions_keyboard()` - Creates [✅ Done] [✏️ Edit] [🗑️ Delete] buttons
- `get_confirmation_keyboard()` - Creates [Yes] [No] confirmation
- Callback handlers for all button actions

---

### Priority 3: Enhanced Features - DONE

#### Feature: Recurring Tasks/Reminders
**Status:** ✅ IMPLEMENTED (Schema ready)
**Description:** Support for weekly/monthly recurring items

**Schema changes:**
- `tasks` table: Added `recurrence`, `recurrence_end`, `parent_task_id` columns

**Files modified:**
- `src/database/models.py` - Schema updated
- `src/database/operations.py` - Added `add_recurring_task()`, `get_recurring_tasks()`, `create_recurring_instance()`

---

#### Feature: Export Data
**Status:** ✅ IMPLEMENTED
**Description:** Export schedule, assignments to file format

**Commands:**
- `/export schedule` - Export as Markdown file
- `/export assignments` - Export pending assignments
- `/export all` - Full data backup (JSON)

**Files modified:**
- `src/bot/handlers.py` - Added `/export` command
- `src/bot/keyboards.py` - Added `get_export_keyboard()`

---

#### Feature: Statistics & Analytics
**Status:** ✅ IMPLEMENTED
**Description:** Show completion rates, productivity stats

**Commands:**
- `/stats [days]` - Show stats for past N days (default 7)
- Natural language: "show my stats"

**Files modified:**
- `src/database/operations.py` - Added `get_completion_stats()`, `get_pending_counts()`
- `src/bot/handlers.py` - Added `/stats` command
- `src/ai/intent_parser.py` - Added `QUERY_STATS` intent

---

#### Feature: Notification Customization
**Status:** ✅ IMPLEMENTED
**Description:** Customize notification settings and mute

**Commands:**
- `/settings` - Open settings menu with notification toggles
- `/mute <hours>` - Temporarily mute notifications
- Natural language: "mute for 2 hours"

**Schema changes:**
- `user_config` table: Added `muted_until` column
- New table: `notification_settings` for per-user settings

**Files modified:**
- `src/database/models.py` - Schema updated
- `src/database/operations.py` - Added `set_notification_setting()`, `is_muted()`, `set_mute_until()`
- `src/scheduler/notifications.py` - Checks mute status before sending
- `src/ai/intent_parser.py` - Added `MUTE_NOTIFICATIONS` intent

---

### Priority 4: Quality of Life - DONE

#### Feature: Undo Last Action
**Status:** ✅ IMPLEMENTED
**Description:** Undo the last action (add, delete, complete)

**Commands:**
- `/undo` - Undo last action

**Schema changes:**
- New table: `action_history` (action_type, table_name, item_id, old_data, new_data)

**Files modified:**
- `src/database/models.py` - Added `action_history` table
- `src/database/operations.py` - Added `add_action_history()`, `get_last_action()`, `delete_action_history()`
- `src/bot/handlers.py` - Added `/undo` command

---

#### Feature: Search Everything
**Status:** ✅ IMPLEMENTED
**Description:** Global search across all data

**Commands:**
- `/search <query>` - Search assignments, tasks, todos, schedule, events
- Natural language: "search database", "find report"

**Files modified:**
- `src/database/operations.py` - Added `search_all()`
- `src/bot/handlers.py` - Added `/search` command
- `src/ai/intent_parser.py` - Added `SEARCH_ALL` intent

---

#### Feature: Snooze Reminders
**Status:** ✅ IMPLEMENTED
**Description:** Snooze buttons on reminder notifications

**Implementation:**
- `get_snooze_keyboard()` - Creates [30 min] [1 hour] [2 hours] [✅ Done] buttons
- Callback handler for snooze actions

---

#### Feature: Multi-language Full Support
**Status:** ✅ IMPLEMENTED
**Description:** Full English and Malay language support

**Commands:**
- `/language <en|my>` - Set language preference
- Natural language: "set language to malay", "tukar bahasa"

**Files created/modified:**
- `src/utils/translations.py` - NEW FILE with EN/MY translations
- `src/database/models.py` - Added `language` column to `user_config`
- `src/database/operations.py` - Added `set_language()`, `get_language()`
- `src/ai/intent_parser.py` - Added `SET_LANGUAGE` intent

---

## FUTURE IMPLEMENTATION (Backlog)

### Still To Be Implemented

#### Feature: Group Chat Support
**Status:** Not implemented
**Priority:** Medium
**Description:** Support for class group chats

**Features to implement:**
- Shared class schedule for group
- Group assignments/deadlines
- @mentions for reminders
- Per-group settings vs per-user settings

---

#### Feature: AI-Powered Suggestions
**Status:** Not implemented
**Priority:** Low
**Description:** Use Gemini to suggest task priorities, study times

**Examples:**
- "You have 3 assignments due this week. I suggest starting with Database report as it's worth more marks."
- "Based on your schedule, you have free time Tuesday afternoon for studying."

**Implementation approach:**
- Analyze user's pending items and schedule
- Send context to Gemini for prioritization suggestions
- Proactive suggestions during daily briefings

---

#### Feature: Calendar Sync
**Status:** Not implemented
**Priority:** Low
**Description:** Two-way sync with Google Calendar

**Features to implement:**
- Import events from Google Calendar
- Export schedule to Google Calendar
- Sync assignment deadlines
- OAuth2 authentication flow

**Complexity:** HIGH (requires Google API integration)

---

#### Feature: Voice Messages
**Status:** Not implemented
**Priority:** Low
**Description:** Accept voice messages for adding items

**Implementation approach:**
- Use Telegram voice message API to receive audio
- Send to Gemini for transcription
- Process transcribed text as normal message

---

#### Feature: iCal Export
**Status:** Not implemented
**Priority:** Low
**Description:** Export to standard iCal format for calendar apps

**Commands to add:**
- `/export ical` - Generate .ics file

---

## Implementation Notes

When implementing future features:
1. Always add to intent_parser.py for NL support
2. Add both slash command AND natural language
3. Include Malay language patterns where possible
4. Update /help message
5. Add to Testing.md test cases
6. Consider mobile UX (short responses, buttons)
