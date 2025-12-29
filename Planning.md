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

## FUTURE IMPLEMENTATION (Backlog)

### Priority 1: High Value Features

#### Feature: Set Exam Dates Per Subject
**Status:** Not implemented (only query existing calendar events works)
**Description:** Allow users to manually set exam dates for specific subjects

**Schema change:**
```sql
ALTER TABLE events ADD COLUMN subject_code TEXT;
```

**New commands:**
- `/setexam <subject> <type> <date> [time]` - Set exam date
- `/exams` - List all upcoming exams

**Examples:**
```
/setexam BITP1113 final 2025-01-15
/setexam BITI1213 midterm 2024-12-20 10:00
"Final exam BITP1113 on 15 Jan 2025"
"Midterm BITI1213 on 20 Dec 10am"
```

**Files to modify:**
- `src/database/models.py` - Add subject_code to events
- `src/database/operations.py` - Add exam-specific CRUD
- `src/bot/handlers.py` - Add /setexam, /exams commands
- `src/ai/intent_parser.py` - Add ADD_EXAM intent

---

#### Feature: Delete/Remove Items
**Status:** Not implemented
**Description:** Allow users to delete assignments, tasks, todos, online overrides

**New commands:**
- `/delete <type> <id>` - Delete item with confirmation
- Natural language: "delete assignment 5", "remove todo 3"

**Examples:**
```
/delete assignment 5
/delete online 1
"delete task 3"
"remove the quiz assignment"
```

---

#### Feature: View Schedule by Subject
**Status:** Not implemented
**Description:** Query schedule for a specific subject

**New commands:**
- `/schedule <subject>` - Show all slots for a subject

**Examples:**
```
/schedule BITP1113
"when is database design class"
"bila kelas programming"
```

---

### Priority 2: UI Improvements

#### Feature: Telegram Inline Keyboards
**Status:** Not implemented
**Complexity:** HIGH
**Description:** Replace slash commands with interactive buttons

**Implementation approach:**
1. Add `InlineKeyboardMarkup` to key responses
2. Create menu flows for common actions
3. Add callback query handlers

**Menu structure:**
```
Main Menu:
[📅 Schedule] [📝 Tasks]
[📚 Assignments] [✅ TODOs]
[⚙️ Settings] [❓ Help]

Schedule Menu:
[Today] [Tomorrow] [This Week]
[Set Online] [Edit Room]
[🔙 Back]
```

**Files to modify:**
- `src/bot/handlers.py` - Add callback handlers
- `src/bot/keyboards.py` - New file for keyboard layouts
- All command handlers - Add keyboard responses

---

#### Feature: Quick Action Buttons
**Status:** Not implemented
**Description:** Add action buttons to list responses

**Example:** When showing assignments:
```
📚 3 pending assignments:
[ID:5] Report (BITP1113) - due Fri 5PM
  [✅ Done] [✏️ Edit] [🗑️ Delete]

[ID:8] Quiz (BITI1213) - due Mon 10AM
  [✅ Done] [✏️ Edit] [🗑️ Delete]
```

---

### Priority 3: Enhanced Features

#### Feature: Recurring Tasks/Reminders
**Status:** Not implemented
**Description:** Support for weekly/monthly recurring items

**Schema change:**
```sql
ALTER TABLE tasks ADD COLUMN recurrence TEXT; -- 'daily', 'weekly', 'monthly'
ALTER TABLE tasks ADD COLUMN recurrence_end TEXT;
```

**Examples:**
```
"Remind me to submit report every Friday"
"Weekly meeting with advisor on Monday 2pm"
```

---

#### Feature: Export Data
**Status:** Not implemented
**Description:** Export schedule, assignments to file/calendar format

**New commands:**
- `/export schedule` - Export as text/image
- `/export ical` - Export to iCal format
- `/export all` - Full data backup

---

#### Feature: Statistics & Analytics
**Status:** Not implemented
**Description:** Show completion rates, productivity stats

**New commands:**
- `/stats` - Show weekly/monthly stats
- `/stats assignments` - Assignment completion rate

**Example output:**
```
📊 This Week's Stats:
- Assignments: 5/7 completed (71%)
- Tasks: 8/10 completed (80%)
- TODOs: 12/15 completed (80%)
- Classes attended: 15/18
```

---

#### Feature: Notification Customization
**Status:** Not implemented
**Description:** Let users customize reminder times/frequency

**New commands:**
- `/settings notifications` - Open notification settings
- `/mute <hours>` - Temporarily mute notifications

**Settings:**
- Daily briefing time (default 10PM)
- Assignment reminder intervals
- Enable/disable specific notification types

---

### Priority 4: Quality of Life

#### Feature: Undo Last Action
**Status:** Not implemented
**Description:** Undo the last action (complete, delete, edit)

**Command:**
- `/undo` - Undo last action

---

#### Feature: Search Everything
**Status:** Not implemented
**Description:** Global search across all data

**Command:**
- `/search <query>` - Search assignments, tasks, todos, schedule

**Example:**
```
/search database
> Found 3 results:
> 📚 Assignment: Database report (due Fri)
> 📅 Schedule: BITI1213 Database Design (Mon 8AM)
> ✅ TODO: Review database notes
```

---

#### Feature: Snooze Reminders
**Status:** Not implemented
**Description:** Snooze a reminder for later

**Implementation:**
When reminder is sent, add buttons:
```
⏰ Assignment "Report" is due in 3 hours!
[Snooze 30min] [Snooze 1hr] [✅ Done]
```

---

#### Feature: Multi-language Full Support
**Status:** Partial (some Malay regex patterns)
**Description:** Full Malay language support for all features

**To implement:**
- All response messages in both EN/MY
- Language preference in user settings
- `/language` command to switch

---

#### Feature: Group Chat Support
**Status:** Not implemented
**Description:** Support for class group chats

**Features:**
- Shared class schedule for group
- Group assignments/deadlines
- @mentions for reminders

---

### Priority 5: Advanced Features

#### Feature: AI-Powered Suggestions
**Status:** Not implemented
**Description:** Use Gemini to suggest task priorities, study times

**Examples:**
- "You have 3 assignments due this week. I suggest starting with Database report as it's worth more marks."
- "Based on your schedule, you have free time Tuesday afternoon for studying."

---

#### Feature: Calendar Sync
**Status:** Not implemented
**Description:** Two-way sync with Google Calendar

**Features:**
- Import events from Google Calendar
- Export schedule to Google Calendar
- Sync assignment deadlines

---

#### Feature: Voice Messages
**Status:** Not implemented
**Description:** Accept voice messages for adding items

**Implementation:**
- Use Telegram voice message API
- Transcribe with Gemini
- Process as text input

---

## Implementation Notes

When implementing future features:
1. Always add to intent_parser.py for NL support
2. Add both slash command AND natural language
3. Include Malay language patterns where possible
4. Update /help message
5. Add to Testing.md test cases
6. Consider mobile UX (short responses, buttons)
