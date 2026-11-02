# PawPal+ Project Reflection

> **Note to self:** Sections marked ✍️ ask about *my* experience and decisions. I need to write those myself. The other sections describe the system and are drafted from the code; I should reword them in my own voice and correct anything I'd explain differently.

## 1. System Design

**Three core user actions**

1. Add a pet (name, species, age) to my household.
2. Schedule a care task for a pet: what, when, how long, how important, and whether it repeats.
3. See today's plan: which tasks fit my available time, in order, with warnings about clashes.

**a. Initial design**

Four core classes, each with one job:

- **`Task`** (dataclass): one care activity. Holds description, start time (`HH:MM`), duration, priority, frequency (once/daily/weekly), due date, and completion status. It validates its own fields and knows how to mark itself complete and produce its next occurrence.
- **`Pet`** (dataclass): a pet profile that owns a list of `Task`s. It can add, remove, replace, and count tasks.
- **`Owner`** (dataclass): the person doing the care. Holds their pets and their daily time budget (`available_minutes`). It's the single entry point for "all tasks across all pets."
- **`Scheduler`**: the "brain." It reads tasks through the `Owner`, then sorts, filters, detects conflicts, handles recurrence, and builds the daily plan.

Two small result classes, **`DailyPlan`** and **`PlanItem`**, carry the scheduler's output (scheduled, skipped, conflicts, and the reason for each) so the CLI and the UI can display the same plan.

**b. Design changes**

- **Tasks don't store their pet.** The scheduler passes `(pet, task)` pairs instead. A back-reference would mean every task has to be kept in sync with its pet, so pairs keep `Task` simpler. The cost: method signatures say `list[Entry]` instead of `list[Task]`.
- **Added `DailyPlan`/`PlanItem`.** The first idea was for the scheduler to return a sorted list. But the scenario asks the app to *explain* its plan, so each task needed a reason attached, and skipped tasks needed a place to go.
- **Identity, not equality, for tasks.** Dataclasses compare by value, so two identical "Walk 07:00" tasks are `==`. `Pet.remove_task` and `replace_task` find tasks with `is` so the wrong one is never removed.
- **Bug found while wiring the UI:** Streamlit's selectbox handed back a *copy* of the selected task object, so "Mark complete" failed to find the real task. The fix was to select by list index and look up the real object.

✍️ *Add: which of these came from AI feedback on the skeleton (Phase 1 Step 5) vs. from my own testing, and whether I agreed.*

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

1. **Due date and completion**: only incomplete tasks due today or overdue are candidates.
2. **Priority**: high before medium before low when deciding what to keep.
3. **Time budget**: total scheduled minutes can't exceed the owner's `available_minutes`.
4. **Start time**: decides display order and breaks priority ties.
5. **Overlaps**: detected and reported, but not resolved.

Priority comes first because missing a high-priority task like medication matters more than missing enrichment play. The time budget is the hard limit because it's the constraint the owner actually runs into.

✍️ *Add: whether I'd rank these the same way, and why.*

**b. Tradeoffs**

- **Greedy selection, not optimal.** The scheduler takes the highest-priority tasks first and keeps each one if it still fits. In the demo, with 15 minutes left, it skipped a 20-minute *medium* task and kept a 15-minute *low* task. A perfect solver (a knapsack algorithm) could maximize total priority, but it would be harder to read and harder to explain. For a handful of daily tasks, greedy is usually right, and its reasoning fits in one sentence.
- **Conflicts are warned about, not fixed.** Overlapping tasks still both appear in the plan with a warning. Auto-moving a task could put a pill at a time the vet didn't intend, so the owner decides.
- **Overlap uses full duration, not just exact start times.** This catches a 07:30–08:00 walk clashing with a 07:45 feeding, which exact-match checking would miss.
- **Recurrence only advances on completion.** A daily task that's never marked done doesn't spawn tomorrow's copy. It shows as "overdue" instead, so a missed task stays visible rather than piling up duplicates.
- **No tasks across midnight.** These are rejected rather than modeled, which keeps time math to one day.

---

## 3. AI Collaboration ✍️

**a. How you used AI**

✍️ *Which AI features helped most (chat, inline edits, agent mode)? Which prompts worked best? How did separate chat sessions per phase help (or not)?*

**b. Judgment and verification**

✍️ *One AI suggestion I rejected or modified, and how I verified what the AI produced.*

Candidate examples to check against what actually happened:
- The AI's code passed all tests on the first run. That isn't proof the tests work, so bugs were planted on purpose (e.g. changing `>=` to `>` in conflict detection) to confirm each test fails when it should.
- The Streamlit selectbox copy bug only showed up when the UI was actually exercised; the unit tests didn't catch it.

---

## 4. Testing and Verification

**a. What you tested**

26 tests covering:
- **Task completion and addition.**
- **Sorting**: chronological order, unpadded times, date before time.
- **Filtering**: by pet, by status, combined; a pet with no tasks.
- **Recurrence**: daily, weekly, one-time, double completion, wrong pet.
- **Conflict detection**: exact match, partial overlap, back-to-back, one long task overlapping several.
- **Daily-plan selection**: under a tight budget; completed, future and overdue tasks.
- **Input validation.**

These matter because sorting, recurrence and conflicts are where off-by-one and boundary bugs hide. Back-to-back tasks and double completion are exactly the cases a quick manual check skips.

**b. Confidence**

✍️ *My rating and why.* (README currently says 4/5: core logic is well tested, and each test was confirmed to fail when the code is broken; the UI is only smoke-tested.)

Edge cases to test next:
- Automated tests for the Streamlit UI (e.g. with `streamlit.testing`).
- Tasks spanning midnight.
- Owner availability windows (e.g. only free 7–9am and 6–9pm) instead of a single minute total.
- Large numbers of tasks, to check conflict detection stays fast.

---

## 5. Reflection ✍️

**a. What went well**

✍️

**b. What you would improve**

✍️ *Ideas: let the owner set availability windows; auto-suggest a new time for a conflicting task; save data to a file so it survives closing the app.*

**c. Key takeaway**

✍️ *What I learned about being the "lead architect" with AI tools.*
