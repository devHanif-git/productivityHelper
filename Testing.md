# Testing Guide - UTeM Student Assistant Bot

Complete A-Z manual testing checklist for the bot.

---

## Pre-requisites

Before testing, ensure:
1. `.env` file exists with `TELEGRAM_TOKEN` and `GEMINI_API_KEY`
2. Bot is running: `python -m src.main`
3. You have the bot added on Telegram

---

## PHASE 1: BASIC SETUP TESTS

### Test A: Bot Startup
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| A1 | Run `python -m src.main` | No errors, "Bot is running" message | [x] |
| A2 | Check `data/bot.db` exists | File created | [x] |
| A3 | Check `logs/bot.log` exists | Log file created | [x] |

### Test B: Basic Commands
| Step | Command | Expected Result | Pass? |
|------|---------|-----------------|-------|
| B1 | `/start` | Welcome message with your name | [x] |
| B2 | `/start` again | Same message (no duplicate user created) | [x] |
| B3 | `/help` | All commands listed with formatting | [x] |
| B4 | `/status` | Shows "0 pending" for all items | [x] |

---

## PHASE 2: ONBOARDING FLOW

### Test C: Setup Command
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| C1 | Send `/setup` | Asks for academic calendar image | [x] |
| C2 | Send calendar image | Shows extracted events, asks "yes/no" | [x] |
| C3 | Reply "yes" | Saves events, asks for timetable | [x] |
| C4 | Send timetable image | Shows extracted schedule, asks "yes/no" | [x] |
| C5 | Reply "yes" | "Setup complete!" message | [x] |
| C6 | `/status` | Shows semester start date | [x] |

### Test D: Setup Alternative Paths
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| D1 | During setup, reply "no" to calendar | Asks to upload again | [x] |
| D2 | During setup, send `/skip` | Skips to next step | [x] |
| D3 | During setup, send `/cancel` | Cancels entire flow | [x] |

---

## PHASE 3: SCHEDULE COMMANDS

### Test E: View Schedule
| Step | Command | Expected Result | Pass? |
|------|---------|-----------------|-------|
| E1 | `/tomorrow` | Tomorrow's classes OR "No classes" | [x] |
| E2 | `/week` | Full week schedule grouped by day | [x] |
| E3 | `/week_number` | Current week number (1-14) or period name | [x] |
| E4 | `/offday` | Next holiday with date | [x] |

### Test F: Schedule Edge Cases
| Step | Scenario | Expected Result | Pass? |
|------|----------|-----------------|-------|
| F1 | `/tomorrow` on Friday night | Weekend - "No classes" | [x] |
| F2 | `/tomorrow` before holiday | Shows holiday info | [x] |
| F3 | `/week_number` during break | Shows "Mid-semester Break" (or similar) | [ ] |

---

## PHASE 4: ADDING ASSIGNMENTS

### Test G: Add Assignments via Chat
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| G1 | "Assignment report for BITP1113 due Friday 5pm" | "Assignment added: report..." | [x] |
| G2 | "Assignment quiz due tomorrow" | Assignment with tomorrow's date | [x] |
| G3 | "I have assignment presentation due 25/1/2025 3pm" | Correct date parsed | [x] |
| G4 | `/assignments` | Shows all 3 assignments | [x] |

---

## PHASE 5: ADDING TASKS

### Test H: Add Tasks via Chat
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| H1 | "Meet Dr Intan tomorrow 10am" | "Task added: Meet Dr Intan..." | [x] |
| H2 | "Meeting with advisor next Monday 2pm" | Correct weekday | [x] |
| H3 | "Task submit report at FTK office" | Task with location shown | [FIXED - retest] |
| H4 | `/tasks` | Shows all 3 tasks | [x] |

---

## PHASE 6: ADDING TODOS

### Test I: Add TODOs via Chat
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| I1 | "Take wife at Satria at 3pm" | "TODO added" with time | [x] |
| I2 | "Buy groceries" | TODO without date/time | [x] |
| I3 | "Remember to call mom tomorrow" | TODO with date | [x] |
| I4 | `/todos` | Shows all 3 TODOs | [FIXED - retest] |

---

## PHASE 7: COMPLETING ITEMS

### Test J: Complete via Command
| Step | Command | Expected Result | Pass? |
|------|---------|-----------------|-------|
| J1 | `/done assignment 1` | "Marked as completed" | [x] |
| J2 | `/done task 1` | "Marked as completed" | [x] |
| J3 | `/done todo 1` | "Marked as completed" | [x] |
| J4 | `/assignments` | One less assignment listed | [x] |

### Test K: Complete via Natural Language
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| K1 | "Done with BITP report" | Finds and completes matching assignment | [x] |
| K2 | "Finished the quiz" | Matches by partial title | [x] |

### Test L: Completion Errors
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| L1 | `/done assignment 999` | "Not found" error | [x] |
| L2 | `/done invalid 1` | "Unknown type" error | [x] |
| L3 | "Done with nonexistent thing" | "Couldn't find" message | [x] |

---

## PHASE 8: NATURAL LANGUAGE QUERIES

### Test M: Schedule Queries (English)
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| M1 | "What class tomorrow?" | Tomorrow's schedule | [x] |
| M2 | "Any class tomorrow" | Tomorrow's schedule | [x] |
| M3 | "What week is this?" | Current week number | [x] |
| M4 | "What week next week?" | Next week number | [x] |
| M5 | "When is next holiday?" | Next off day info | [x] |

### Test N: Schedule Queries (Malay)
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| N1 | "Kelas esok apa?" | Tomorrow's schedule | [x] |
| N2 | "Minggu berapa sekarang?" | Current week | [x] |
| N3 | "Bila cuti seterusnya?" | Next off day | [x] |

### Test O: Item Queries
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| O1 | "What assignments pending?" | Assignment list | [ ] |
| O2 | "Show my tasks" | Task list | [ ] |
| O3 | "What todos left?" | TODO list | [ ] |

### Test P: General Chat
| Step | Message | Expected Result | Pass? |
|------|---------|-----------------|-------|
| P1 | "Hi" | Greeting response | [ ] |
| P2 | "Assalamualaikum" | "Waalaikumussalam" response | [ ] |
| P3 | "Thanks" | "You're welcome" response | [ ] |
| P4 | "Bye" | Goodbye response | [ ] |
| P5 | "asdfghjkl" (random) | Help suggestion | [ ] |

---

## PHASE 9: IMAGE RECOGNITION

### Test Q: Academic Calendar
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| Q1 | Send UTeM calendar image | Detects as "calendar" | [x] |
| Q2 | Check extracted events | Holidays, breaks, exams listed | [x] |
| Q3 | Verify filtering | No "Mesyuarat Senat" or admin items | [x] |

### Test R: Class Timetable
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| R1 | Send timetable image | Detects as "timetable" | [x] |
| R2 | Check extracted data | Day, time, subject, room, lecturer | [x] |
| R3 | Verify class types | LEC and LAB distinguished | [x] |

### Test S: Assignment Sheet
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| S1 | Send assignment sheet photo | Detects as "assignment" | [x] |
| S2 | Check extraction | Title, subject, due date shown | [x] |
| S3 | Confirm "yes" | Saved to database | [x] |
| S4 | Try "no" | Cancelled, not saved | [x] |

### Test T: Unknown Images
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| T1 | Send selfie or random photo | "Couldn't determine type" | [x] |
| T2 | Send blurry image | Error or retry message | [x] |

---

## PHASE 10: NOTIFICATION TESTS

### Test U: Daily Briefings
To test notifications, you can either:
- Wait for scheduled times (10PM, 8PM, 12AM)
- Or temporarily modify scheduler times in code

| Time | What to Verify | Pass? |
|------|----------------|-------|
| 10:00 PM | Class briefing for tomorrow received | [ ] |
| 8:00 PM | Off-day alert (if holiday tomorrow) | [ ] |
| 12:00 AM | Midnight TODO review received | [ ] |

### Test V: Assignment Reminders
Create assignment with due date at different intervals:

| Due In | Expected Reminder Message | Pass? |
|--------|---------------------------|-------|
| 3 days | "Assignment X due in 3 days" | [ ] |
| 2 days | "Assignment X due in 2 days" | [ ] |
| 1 day | "Assignment X due TOMORROW" | [ ] |
| 8 hours | "8 hours left for X" | [ ] |
| 3 hours | "Only 3 hours left!" | [ ] |
| 1 hour | "URGENT: 1 hour remaining!" | [ ] |
| Now | "Assignment X is NOW DUE" | [ ] |

### Test W: Task & TODO Reminders
| Scenario | Expected | Pass? |
|----------|----------|-------|
| Task tomorrow with time | 1-day reminder at 8PM | [ ] |
| Task in 2 hours | 2-hour reminder | [ ] |
| TODO with time (1 hour before) | 1-hour reminder | [ ] |
| TODO without time | Listed in midnight review | [ ] |

---

## PHASE 11: ERROR HANDLING

### Test X: Invalid Commands
| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| X1 | `/done` (no arguments) | Usage instructions shown | [ ] |
| X2 | `/done abc xyz` | "Invalid ID" error | [ ] |
| X3 | Send very long message (5000+ chars) | Handles without crash | [ ] |

### Test Y: API Errors
| Step | How to Simulate | Expected Result | Pass? |
|------|-----------------|-----------------|-------|
| Y1 | Use invalid Gemini API key | Graceful error message | [x] |
| Y2 | Disconnect internet, send image | Network error message | [x] |

---

## PHASE 12: FULL USER JOURNEY

### Test Z: Complete Flow
Walk through entire flow:

| Step | Action | Expected | Pass? |
|------|--------|----------|-------|
| Z1 | `/start` | Welcome message | [ ] |
| Z2 | `/setup` | Asks for calendar | [ ] |
| Z3 | Upload calendar, confirm | Events saved | [ ] |
| Z4 | Upload timetable, confirm | Schedule saved | [ ] |
| Z5 | "What week is this?" | Current week shown | [ ] |
| Z6 | "What class tomorrow?" | Schedule shown | [ ] |
| Z7 | "Assignment report due Friday 5pm" | Assignment added | [ ] |
| Z8 | `/assignments` | Assignment listed | [ ] |
| Z9 | "Done with report" | Assignment completed | [ ] |
| Z10 | `/status` | All counts updated | [ ] |

---

## Summary Checklist

| Phase | Tests | Completed |
|-------|-------|-----------|
| Phase 1: Basic Setup | A-B | [x] |
| Phase 2: Onboarding | C-D | [x] |
| Phase 3: Schedule Commands | E-F | [retest E3] |
| Phase 4: Add Assignments | G | [x] |
| Phase 5: Add Tasks | H | [retest H3] |
| Phase 6: Add TODOs | I | [retest I4] |
| Phase 7: Complete Items | J-L | [retest K1, K2] |
| Phase 8: NL Queries | M-P | [ ] |
| Phase 9: Image Recognition | Q-T | [ ] |
| Phase 10: Notifications | U-W | [ ] |
| Phase 11: Error Handling | X-Y | [ ] |
| Phase 12: Full Journey | Z | [ ] |

---

## Bug Fixes Applied (2025-12-30)

| Bug | Issue | Fix |
|-----|-------|-----|
| E3 | Week number returned 9 instead of 12 | Fixed `get_current_week()` in `semester_logic.py` - now properly counts lecture weeks excluding breaks |
| H3 | Task location not shown in response | Fixed response message in `handlers.py` to display location |
| I4 | /todos caused connection error | Network issue - error handler catches this gracefully |
| K1/K2 | "Done with X" didn't match items | Fixed condition in `extract_completion_target()` in `intent_parser.py` |

**After restarting the bot, retest: E3, H3, I4, K1, K2**

---

## Quick Test Commands Reference

```bash
# Start the bot
python -m src.main

# View logs
type logs\bot.log

# Check database (using sqlite3)
sqlite3 data\bot.db ".tables"
sqlite3 data\bot.db "SELECT * FROM user_config"
sqlite3 data\bot.db "SELECT * FROM assignments"
```

---

## Test Data Samples

### Natural Language Inputs to Try

**Assignments:**
```
Assignment report for BITP1113 due Friday 5pm
I have quiz BITI1213 due tomorrow at noon
Submit project proposal by 25 Jan 2025
Assignment presentation next Monday 10am
```

**Tasks:**
```
Meet Dr Intan tomorrow 10am at FTK office
Appointment with advisor next Monday 2pm
Discussion with groupmates Thursday evening
Collect certificate from admin on Friday
```

**TODOs:**
```
Take wife at Satria at 3pm
Buy groceries after class
Call mom this weekend
Pay phone bill before Friday
Remember to print notes
```

**Queries:**
```
What class tomorrow?
What week is this?
Any assignment pending?
When next holiday?
Show my tasks
What todos left?
```

---

## Notes

- Mark each test with [x] when passed
- If a test fails, note the actual result
- Run tests in order (some depend on previous data)
- For notification tests, you may need to wait or adjust times
- Tests marked [FIXED - retest] had bugs that have been fixed

---

## Known Bugs (not fix yet)
- when send /done it say marks as done but not not remove from list (mby delay because later on when i check again it remove, or mby i restart the bot that why)
- when use /assignment, /todos, /tasks it show data but not [ID:] because it being filter so i thought its id 1, when i update it, its not.
- 

## To Add

- Add /today for schedule
- to Remove for student New, remove for new undergraduate student registration and cource registration for new undergraduate student.
- to Remove Minggu Harian Siswa
- able to edit data in database like -> BITP 3113 change room to BK12.
- able to use subject name instead of subject code so both can be use.
- able to talk like, "What is the schedule for today?", to i have class today?, when midterm break?, when final exam? when midterm exam? (can use midterm or mid semester) and so on.
- can use /online to search next online lecture week or something like that.
- can set class to online mode, like "set class Programming technique online on week 12". or "set class dbd (database design) online tomorrow" or "set class dbd (database design) online today" or "set class dbd (database design) online today 10am" or "set class OS (operating system) online today next week. or on * date" and something like that. you may suggest.
- mby instead of using "/" make it UI, so it better and more user friendly.
- able to set important date like final exam date for certain subject, midterm exam date for certain subject, the mode, online or offline (or you think this is just on tasks/todos? no need special place?)
- 