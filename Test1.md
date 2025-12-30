# UTeM Student Assistant Bot - Full System Test Cases

Complete end-to-end test cases for the entire bot system.

---

## PRE-TEST SETUP

1. Start the bot: `python -m src.main`
2. Clear test data if needed (delete `data/bot.db`)
3. Have test images ready:
   - A timetable screenshot
   - A calendar screenshot
   - An assignment photo
4. Prepare a voice message for testing

---

## TEST 1: ONBOARDING FLOW

### 1.1 First Time User
**Action:** Send `/start` as a new user
**Expected:**
- [x] Welcome message appears
- [x] Language selection keyboard shown (English/Malay)
- [x] User config created in database

### 1.2 Language Selection
**Action:** Select "English" or "Bahasa Melayu"
**Expected:**
- [x] Confirmation message in selected language
- [x] Main menu keyboard appears
- [x] Language saved to user_config

### 1.3 Returning User
**Action:** Send `/start` again
**Expected:**
- [x] Welcome back message (not onboarding)
- [x] Main menu shown
- [x] Previous settings preserved

---

## TEST 2: SEMESTER CONFIGURATION

### 2.1 Set Semester Start Date
**Action:** Use settings or command to set semester start
**Expected:**
- [x] Date picker or input prompt shown
- [x] Date saved correctly
- [x] Week calculations work from this date

### 2.2 Query Current Week
**Action:** Send "minggu ni week berapa?" or "what week is this?"
**Expected:**
- [x] Shows current week number (Week 1-14)
- [x] Shows if mid-semester break or inter-semester
- [x] Date range for current week displayed

---

## TEST 3: TIMETABLE SETUP (Image Upload)

### 3.1 Upload Timetable Image
**Action:** Send a timetable screenshot to the bot
**Expected:**
- [x] Bot detects it's a timetable image
- [x] AI extracts class schedule (subjects, times, days, rooms)
- [x] Confirmation prompt shown with extracted data
- [x] User can confirm or edit

### 3.2 Confirm Timetable
**Action:** Confirm the extracted timetable
**Expected:**
- [x] Schedule saved to database
- [x] Success message shown
- [x] Classes appear in schedule queries

### 3.3 Query Today's Classes
**Action:** Send "kelas harini apa je?"
**Expected:**
- [x] Shows today's classes from uploaded timetable
- [x] Includes subject code, time, room, lecturer
- [x] "No classes today" if none scheduled

### 3.4 Query Tomorrow's Classes
**Action:** Send "esok ada kelas x?"
**Expected:**
- [x] Shows tomorrow's schedule
- [x] Correct day of week detected

---

## TEST 4: CALENDAR UPLOAD

### 4.1 Upload Academic Calendar
**Action:** Send an academic calendar image
**Expected:**
- [x] Bot detects calendar type
- [x] Extracts important dates (holidays, exam weeks, breaks)
- [x] Shows extracted events for confirmation

### 4.2 Confirm Calendar Events
**Action:** Confirm extracted events
**Expected:**
- [x] Events saved to database
- [x] Can query holidays/breaks after

### 4.3 Query Next Holiday
**Action:** Send "bila next cuti?" or "when is next holiday?"
**Expected:**
- [x] Shows next upcoming holiday/off day
- [x] Date and name of holiday displayed

---

## TEST 5: ASSIGNMENTS

### 5.1 Add Assignment via Text
**Action:** Send "I have assignment report for BITP1113 due Friday 5pm"
**Expected:**
- [x] Bot parses: title="report", subject="BITP1113", due="Friday 5pm"
- [x] Confirmation prompt shown
- [x] Assignment saved after confirm

### 5.2 Add Assignment (Malay)
**Action:** Send "assignment presentation BITD2123 due next Monday"
**Expected:**
- [ ] Correctly parses mixed language
- [ ] Due date calculated correctly (next Monday)

### 5.3 Query Assignments
**Action:** Send "what assignments pending?" or "show assignments"
**Expected:**
- [ ] Lists all pending assignments
- [ ] Shows: title, subject code, due date, days remaining
- [ ] Sorted by due date (nearest first)

### 5.4 Complete Assignment
**Action:** Send "done with BITP report" or "siap assignment 1"
**Expected:**
- [ ] Bot identifies correct assignment
- [ ] Marks as completed
- [ ] Removed from pending list

### 5.5 Upload Assignment Image
**Action:** Send a photo of an assignment sheet
**Expected:**
- [ ] Bot detects assignment image
- [ ] Extracts: title, subject, due date, requirements
- [ ] Confirmation flow for adding

---

## TEST 6: TASKS (Meetings/Appointments)

### 6.1 Add Task
**Action:** Send "Meet Dr Intan tomorrow 10am at office"
**Expected:**
- [ ] Parses: title="Meet Dr Intan", date="tomorrow", time="10am", location="office"
- [ ] Task created after confirmation

### 6.2 Add Task (Malay)
**Action:** Send "jumpa lecturer pukul 2pm hari rabu"
**Expected:**
- [ ] Correctly parses Malay day name (rabu = Wednesday)
- [ ] Time parsed correctly

### 6.3 Query Tasks
**Action:** Send "show tasks" or "what meetings"
**Expected:**
- [ ] Lists upcoming tasks/meetings
- [ ] Shows date, time, location

### 6.4 Complete Task
**Action:** Send "done meeting with Dr Intan"
**Expected:**
- [ ] Task marked as complete
- [ ] Removed from active list

---

## TEST 7: TODOS (Quick Personal Tasks)

### 7.1 Add Todo
**Action:** Send "remind me to buy groceries"
**Expected:**
- [ ] Creates todo: "buy groceries"
- [ ] No date required (unlike assignments)

### 7.2 Add Todo with Time
**Action:** Send "pick up parcel at 3pm"
**Expected:**
- [ ] Todo created with time
- [ ] Time-based reminder set

### 7.3 Query Todos
**Action:** Send "show my todos" or "list todos"
**Expected:**
- [ ] Lists all pending todos
- [ ] Shows creation date and optional scheduled time

### 7.4 Complete Todo
**Action:** Send "done groceries" or "siap todo 1"
**Expected:**
- [ ] Todo marked complete
- [ ] Removed from list

---

## TEST 8: VOICE MESSAGES

### 8.1 Send Voice Message
**Action:** Record and send a voice message saying "add assignment report due Friday"
**Expected:**
- [ ] Bot acknowledges voice received
- [ ] Shows processing options keyboard

### 8.2 Transcribe Only
**Action:** Select "Transcribe Only" option
**Expected:**
- [ ] Shows transcription text
- [ ] No action taken, just displays text

### 8.3 Process as Command
**Action:** Select "Process as Command" (or similar)
**Expected:**
- [ ] Voice transcribed
- [ ] Transcription processed as text input
- [ ] Appropriate action taken (e.g., add assignment)

### 8.4 Save as Voice Note
**Action:** Select "Save as Note"
**Expected:**
- [ ] Voice note saved to database
- [ ] Can retrieve later

---

## TEST 9: ONLINE CLASS OVERRIDE

### 9.1 Set Class Online
**Action:** Send "set BITP1113 online on week 12"
**Expected:**
- [ ] Online override created for specified class/week
- [ ] Confirmation shown

### 9.2 Set All Classes Online
**Action:** Send "set all classes online tomorrow"
**Expected:**
- [ ] All classes marked online for that date
- [ ] Shows in schedule queries

### 9.3 Query Online Classes
**Action:** Send "which classes online?"
**Expected:**
- [ ] Lists all online overrides
- [ ] Shows subject, date/week

### 9.4 Remove Online Override
**Action:** Send "delete online 1"
**Expected:**
- [ ] Override removed
- [ ] Class returns to normal mode

---

## TEST 10: SEARCH FUNCTIONALITY

### 10.1 Search by Keyword
**Action:** Send "search report"
**Expected:**
- [ ] Searches across: assignments, tasks, todos, events
- [ ] Shows all matching items
- [ ] Indicates item type for each result

### 10.2 Search by Subject Code
**Action:** Send "cari BITP1113"
**Expected:**
- [ ] Finds all items related to that subject
- [ ] Includes assignments, schedule entries

---

## TEST 11: STATISTICS

### 11.1 View Stats
**Action:** Send "show my stats"
**Expected:**
- [ ] Shows productivity statistics:
  - Total assignments completed
  - Tasks completed
  - Todos completed
  - Completion rate
  - Current streaks

---

## TEST 12: SETTINGS

### 12.1 Change Language
**Action:** Send "set language to malay" or use settings menu
**Expected:**
- [ ] Language updated
- [ ] All subsequent messages in new language

### 12.2 Mute Notifications
**Action:** Send "mute 2 hours"
**Expected:**
- [ ] Notifications paused for 2 hours
- [ ] Confirmation with unmute time shown

### 12.3 Access Settings Menu
**Action:** Press Settings button in main menu
**Expected:**
- [ ] Settings keyboard appears
- [ ] Options: Language, Notifications, Semester dates

---

## TEST 13: NOTIFICATIONS (Debug Commands)

### 13.1 Set Test Date
**Action:** Send `/setdate 2025-01-15`
**Expected:**
- [ ] Test date override set
- [ ] All date calculations use this date
- [ ] Confirmation message shown

### 13.2 Set Test Time
**Action:** Send `/settime 08:00`
**Expected:**
- [ ] Test time override set
- [ ] Time-based features use this time

### 13.3 Trigger Daily Briefing
**Action:** Send `/trigger briefing`
**Expected:**
- [ ] Daily briefing notification sent
- [ ] Includes: today's classes, pending assignments, tasks, AI suggestions

### 13.4 Trigger Assignment Reminder
**Action:** Send `/trigger assignments`
**Expected:**
- [ ] Assignment reminder notification
- [ ] Lists assignments due soon

### 13.5 Trigger Midnight Summary
**Action:** Send `/trigger midnight`
**Expected:**
- [ ] End-of-day summary
- [ ] Shows what was completed today

### 13.6 Reset Date/Time Override
**Action:** Send `/setdate reset` and `/settime reset`
**Expected:**
- [ ] Overrides cleared
- [ ] Returns to real date/time

---

## TEST 14: EXAM MANAGEMENT

### 14.1 Add Exam
**Action:** Send "final exam BITP1113 on 15 Jan 2025 9am"
**Expected:**
- [ ] Exam entry created
- [ ] Type (final/midterm), subject, date, time saved

### 14.2 Query Exams
**Action:** Send "when are my exams?" or "show exams"
**Expected:**
- [ ] Lists all upcoming exams
- [ ] Sorted by date

### 14.3 Query Specific Exam Type
**Action:** Send "when is final exam?"
**Expected:**
- [ ] Shows final exam dates only

---

## TEST 15: DELETE OPERATIONS

### 15.1 Delete Assignment
**Action:** Send "delete assignment 1"
**Expected:**
- [ ] Assignment removed from database
- [ ] Confirmation message

### 15.2 Delete Task
**Action:** Send "remove task 2"
**Expected:**
- [ ] Task deleted
- [ ] Confirmation shown

### 15.3 Delete Todo
**Action:** Send "hapus todo 1"
**Expected:**
- [ ] Todo removed
- [ ] Works with Malay command

---

## TEST 16: EDGE CASES

### 16.1 Empty Schedule Day
**Action:** Query schedule for a day with no classes
**Expected:**
- [ ] "No classes scheduled" message
- [ ] Not an error

### 16.2 Past Due Assignment
**Action:** Query assignments when one is past due
**Expected:**
- [ ] Shows overdue indicator
- [ ] Still visible in list (not auto-removed)

### 16.3 Invalid Date Input
**Action:** Send "assignment due on 32 January"
**Expected:**
- [ ] Graceful error handling
- [ ] Asks for correct date format

### 16.4 Unknown Intent
**Action:** Send gibberish like "asdfghjkl"
**Expected:**
- [ ] "I'm not sure what you mean" or similar
- [ ] Suggests using menu or help

### 16.5 Very Long Message
**Action:** Send a 500+ character message
**Expected:**
- [ ] Processed without crash
- [ ] Reasonable response

### 16.6 Special Characters
**Action:** Send message with emojis and special chars
**Expected:**
- [ ] Handled gracefully
- [ ] No encoding errors

---

## TEST 17: MENU NAVIGATION

### 17.1 Main Menu Persistence
**Action:** Press any button, then check if menu remains
**Expected:**
- [ ] Inline keyboard stays visible after button press
- [ ] Can continue navigating without /start

### 17.2 Back Navigation
**Action:** Go into sub-menu, press Back
**Expected:**
- [ ] Returns to previous menu
- [ ] State preserved correctly

### 17.3 Callback Button Response
**Action:** Press various inline buttons
**Expected:**
- [ ] Each button triggers correct action
- [ ] Loading indicator if processing
- [ ] Response within reasonable time

---

## TEST 18: AI FEATURES

### 18.1 AI Suggestions in Briefing
**Action:** Trigger briefing with pending items
**Expected:**
- [ ] AI suggestions included
- [ ] Relevant to pending assignments/tasks
- [ ] Actionable advice

### 18.2 Complex Intent Parsing
**Action:** Send "I need to finish the database report for software engineering class by end of this week"
**Expected:**
- [ ] AI correctly parses complex sentence
- [ ] Extracts: title, subject hint, due date
- [ ] Creates appropriate item

---

## TEST 19: DATABASE INTEGRITY

### 19.1 Concurrent Operations
**Action:** Rapidly send multiple commands
**Expected:**
- [ ] All operations complete
- [ ] No database locks or crashes
- [ ] Data integrity maintained

### 19.2 Restart Bot
**Action:** Stop and restart the bot
**Expected:**
- [ ] All data persisted
- [ ] User config preserved
- [ ] Schedule intact

---

## TEST CHECKLIST SUMMARY

| Category | Tests | Passed |
|----------|-------|--------|
| Onboarding | 3 | [ ] |
| Semester Config | 2 | [ ] |
| Timetable | 4 | [ ] |
| Calendar | 3 | [ ] |
| Assignments | 5 | [ ] |
| Tasks | 4 | [ ] |
| Todos | 4 | [ ] |
| Voice | 4 | [ ] |
| Online Override | 4 | [ ] |
| Search | 2 | [ ] |
| Statistics | 1 | [ ] |
| Settings | 3 | [ ] |
| Notifications | 6 | [ ] |
| Exams | 3 | [ ] |
| Delete | 3 | [ ] |
| Edge Cases | 6 | [ ] |
| Menu Navigation | 3 | [ ] |
| AI Features | 2 | [ ] |
| Database | 2 | [ ] |
| **TOTAL** | **64** | **[ ] / 64** |

---

## QUICK SMOKE TEST (5 minutes)

Run these in order for a quick system validation:

```
1. /start
2. (Select language)
3. kelas harini apa je?
4. add assignment report due Friday
5. (Confirm assignment)
6. show assignments
7. done with report
8. show my todos
9. remind me to study
10. show todos
11. minggu ni week berapa?
12. /trigger briefing
13. show my stats
```

If all 13 steps work, core system is functional.

---

## NOTES

- Test on both English and Malay language settings
- Test with real semester dates configured
- Keep bot logs open to catch errors
- Document any failures for fixing
