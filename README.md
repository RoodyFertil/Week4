# PawPal+ (Module 2 Project)

**PawPal+** is a Streamlit app that helps a busy pet owner plan care tasks (walks, feeding, meds, enrichment, grooming) across multiple pets. It sorts tasks by time, filters them, repeats daily and weekly tasks automatically, warns about scheduling conflicts, and builds a daily plan that fits the owner's available time and explains every choice.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

## Features

- **Owner, multiple pets, and tasks**: each task has a start time, duration, priority, repeat frequency, due date, and completion status.
- **Sorting by time**: tasks are listed chronologically by date, then start time.
- **Filtering**: by pet, by completion status, or by due date, in any combination.
- **Daily and weekly recurrence**: completing a repeating task automatically creates the next one (+1 day or +7 days).
- **Conflict warnings**: overlapping tasks are flagged with a readable warning, including tasks for *different* pets, since one owner can't be in two places at once.
- **Time-budgeted daily plan**: picks the highest-priority tasks that fit the owner's available minutes, lists what was left out and why, and explains each scheduled task.
- **Overdue carry-over**: an unfinished task from an earlier day still shows up in today's plan, marked "overdue."
- **Input validation**: bad times (`25:00`, `noon`), non-positive durations, unknown priorities, tasks running past midnight, and duplicate pet names are rejected with a clear message instead of crashing.

## Project structure

| File | Purpose |
|------|---------|
| `pawpal_system.py` | Logic layer: `Task`, `Pet`, `Owner`, `Scheduler`, plus `DailyPlan`/`PlanItem` results |
| `main.py` | CLI demo that exercises every feature in the terminal |
| `app.py` | Streamlit UI wired to the logic layer |
| `tests/test_pawpal.py` | Automated pytest suite |
| `diagrams/uml_final.mmd` | Mermaid class diagram of the final design (`uml_final.png` is a rendered copy) |

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python main.py          # CLI demo
streamlit run app.py    # web app
```

## 🖥️ Sample Output

Output of `python main.py`:

```
All tasks (as entered)
----------------------
  18:00-18:30  Mochi  Evening walk       high   daily  2026-11-01  [todo]
  07:30-08:00  Mochi  Morning walk       high   daily  2026-11-01  [todo]
  08:15-08:20  Mochi  Heartworm pill     medium once   2026-11-01  [todo]
  19:00-19:15  Luna   Brush fur          low    weekly 2026-11-01  [todo]
  07:45-07:55  Luna   Breakfast          high   daily  2026-11-01  [todo]
  12:00-12:20  Luna   Laser-toy play     medium daily  2026-11-01  [todo]

Today's Schedule (sorted by time)
---------------------------------
  07:30-08:00  Mochi  Morning walk       high   daily  2026-11-01  [todo]
  07:45-07:55  Luna   Breakfast          high   daily  2026-11-01  [todo]
  08:15-08:20  Mochi  Heartworm pill     medium once   2026-11-01  [todo]
  12:00-12:20  Luna   Laser-toy play     medium daily  2026-11-01  [todo]
  18:00-18:30  Mochi  Evening walk       high   daily  2026-11-01  [todo]
  19:00-19:15  Luna   Brush fur          low    weekly 2026-11-01  [todo]

Filter: Luna's tasks only
-------------------------
  07:45-07:55  Luna   Breakfast          high   daily  2026-11-01  [todo]
  12:00-12:20  Luna   Laser-toy play     medium daily  2026-11-01  [todo]
  19:00-19:15  Luna   Brush fur          low    weekly 2026-11-01  [todo]

Conflict check
--------------
  Conflict: Mochi's 'Morning walk' (07:30-08:00) overlaps Luna's 'Breakfast' (07:45-07:55)

Daily plan (90-minute budget)
-----------------------------
Plan for 2026-11-01: 5 task(s), 90 of 90 available minutes used.
  07:30-08:00  Mochi: Morning walk -- high priority; fits in your time budget; repeats daily
  07:45-07:55  Luna: Breakfast -- high priority; fits in your time budget; repeats daily
  08:15-08:20  Mochi: Heartworm pill -- medium priority; fits in your time budget
  18:00-18:30  Mochi: Evening walk -- high priority; fits in your time budget; repeats daily
  19:00-19:15  Luna: Brush fur -- low priority; fits in your time budget; repeats weekly
  SKIPPED  Luna: Laser-toy play -- medium priority, needs 20 min but only 15 min left in today's budget
  WARNING  Conflict: Mochi's 'Morning walk' (07:30-08:00) overlaps Luna's 'Breakfast' (07:45-07:55)

Marked 'Morning walk' complete -> next one auto-created for 2026-11-02

Filter: completed tasks
-----------------------
  07:30-08:00  Mochi  Morning walk       high   daily  2026-11-01  [done]

Filter: Mochi's incomplete tasks
--------------------------------
  08:15-08:20  Mochi  Heartworm pill     medium once   2026-11-01  [todo]
  18:00-18:30  Mochi  Evening walk       high   daily  2026-11-01  [todo]
  07:30-08:00  Mochi  Morning walk       high   daily  2026-11-02  [todo]
```

(Dates reflect the day the demo is run.)

## 🧪 Testing PawPal+

```bash
python -m pytest                       # run the full suite
python -m pytest --cov=pawpal_system   # with coverage (needs pytest-cov, included in requirements.txt)
```

The suite (26 tests) covers:

- **Basics**: `mark_complete()` flips status; adding a task increases a pet's task count.
- **Sorting**: chronological order; unpadded times like `9:00` sort before `10:00`; date sorts before time.
- **Filtering**: by pet (case-insensitive), by status, and both combined; a pet with no tasks.
- **Recurrence**: daily → +1 day, weekly → +7 days, one-time tasks don't repeat, completing twice doesn't create a duplicate, and a task can't be completed under the wrong pet.
- **Conflicts**: exact same start time, partial overlap, back-to-back (*not* a conflict), and one long task overlapping several shorter ones.
- **Daily plan**: high priority kept when time runs out; completed and future tasks excluded; overdue tasks included and labeled.
- **Validation**: bad times, durations, priorities, frequencies, empty descriptions, past-midnight tasks, and duplicate pet names are rejected.

Sample test output:

```
============================= test session starts ==============================
collected 26 items

tests/test_pawpal.py ..........................                          [100%]

============================== 26 passed in 0.05s ==============================
```

Coverage of `pawpal_system.py`: 93%.

**Confidence level: ★★★★☆ (4/5).** Every core behavior has a test, and each test was checked by deliberately breaking the code to confirm it fails. One star is held back because the Streamlit UI is only smoke-tested, not covered by the automated suite, and the scheduler doesn't model things like tasks that span midnight or owner time windows.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Sorts by `(due_date, start_minutes)` with a lambda key. Times are converted to minutes, so `"9:00"` can't sort after `"10:00"` the way raw strings would. |
| Filtering | `Scheduler.filter_tasks(pet_name, completed, due_on)`, `Scheduler.tasks_due(day)` | Filters combine; any left as `None` is ignored. `tasks_due` returns incomplete tasks due that day *or overdue*. |
| Time-budget selection | `Scheduler.build_daily_plan(day)` | Greedy: highest priority first (earlier start breaks ties), keep each task if it still fits the remaining minutes. Skipped tasks are reported with a reason. |
| Conflict handling | `Scheduler.detect_conflicts(entries)` | Flags any overlap of `[start, end)` windows, across all pets. Returns warning strings instead of raising. Back-to-back tasks are fine. |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Completing a daily/weekly task creates a copy due `+1 day`/`+7 days` using `timedelta`, and adds it to the same pet. |
| Explanations | `DailyPlan.explain()`, `PlanItem.reason` | Every scheduled or skipped task carries a plain-English reason. |

## 📸 Demo Walkthrough

1. **Start the app** with `streamlit run app.py`. Set the owner name and how many minutes you have today (default 120).
2. **Add pets** using the "Add pet" form (name, species, age), e.g. Mochi the dog and Luna the cat. Duplicate names are rejected.
3. **Add tasks** with the "Add a task" form: pick the pet, then set description, start time, duration, date, priority, and whether it repeats (once/daily/weekly).
4. **Browse tasks** in the Tasks table, which is always sorted by time. Use the "Show pet" and "Show status" filters to narrow it down.
5. **Edit, complete, or delete** a task in the expander. Marking a daily task complete shows a message that the next one was created for tomorrow.
6. **Generate the schedule.** Choose a date and click "Generate schedule." The app shows:
   - a green summary of how many minutes are used,
   - a yellow warning for each pair of overlapping tasks,
   - a table of scheduled tasks with "Why it's in the plan,"
   - blue notes for tasks left out because time ran out.

Example workflow: add Mochi → add "Morning walk" 07:30, 30 min, high, daily → add Luna → add "Breakfast" 07:45, 10 min, high → generate the schedule → see a conflict warning that the walk and breakfast overlap.

Key scheduler behavior in the CLI (`python main.py`):

```
Conflict check
--------------
  Conflict: Mochi's 'Morning walk' (07:30-08:00) overlaps Luna's 'Breakfast' (07:45-07:55)

Daily plan (90-minute budget)
-----------------------------
Plan for 2026-11-01: 5 task(s), 90 of 90 available minutes used.
  07:30-08:00  Mochi: Morning walk -- high priority; fits in your time budget; repeats daily
  07:45-07:55  Luna: Breakfast -- high priority; fits in your time budget; repeats daily
  08:15-08:20  Mochi: Heartworm pill -- medium priority; fits in your time budget
  18:00-18:30  Mochi: Evening walk -- high priority; fits in your time budget; repeats daily
  19:00-19:15  Luna: Brush fur -- low priority; fits in your time budget; repeats weekly
  SKIPPED  Luna: Laser-toy play -- medium priority, needs 20 min but only 15 min left in today's budget
  WARNING  Conflict: Mochi's 'Morning walk' (07:30-08:00) overlaps Luna's 'Breakfast' (07:45-07:55)

Marked 'Morning walk' complete -> next one auto-created for 2026-11-02
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
