"""PawPal+ logic layer: the Owner, Pet, Task and Scheduler classes.

Everything the app "knows" lives here. Nothing in this module prints or touches
Streamlit, so the same classes power the CLI demo (main.py), the tests, and the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Optional

PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}
FREQUENCIES = ("once", "daily", "weekly")
RECURRENCE_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
MINUTES_PER_DAY = 24 * 60

# A (pet, task) pair. Tasks don't store their pet, so the Scheduler passes both around.
Entry = tuple["Pet", "Task"]


def parse_time(hhmm: str) -> int:
    """Convert an 'HH:MM' string to minutes after midnight, raising ValueError if malformed."""
    parts = str(hhmm).strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Time must look like HH:MM, got {hhmm!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"Time out of range: {hhmm!r}")
    return hours * 60 + minutes


def format_time(minutes: int) -> str:
    """Convert minutes after midnight back to a zero-padded 'HH:MM' string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """A single care activity, such as a walk, a feeding or a medication."""

    description: str
    time: str  # start time, "HH:MM" (normalized to zero-padded form)
    duration_minutes: int = 15
    priority: str = "medium"  # "low" | "medium" | "high"
    frequency: str = "once"  # "once" | "daily" | "weekly"
    due_date: date = field(default_factory=date.today)
    completed: bool = False

    def __post_init__(self) -> None:
        """Validate fields and normalize time/priority/frequency formatting."""
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("Task description cannot be empty")
        self.time = format_time(parse_time(self.time))  # "8:5" -> "08:05"
        self.priority = self.priority.strip().lower()
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"Priority must be one of {list(PRIORITY_RANK)}")
        self.frequency = self.frequency.strip().lower()
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"Frequency must be one of {list(FREQUENCIES)}")
        if int(self.duration_minutes) <= 0:
            raise ValueError("Duration must be a positive number of minutes")
        self.duration_minutes = int(self.duration_minutes)
        if self.end_minutes > MINUTES_PER_DAY:
            raise ValueError("Task would run past midnight; split it or start earlier")

    @property
    def start_minutes(self) -> int:
        """Start time as minutes after midnight."""
        return parse_time(self.time)

    @property
    def end_minutes(self) -> int:
        """End time as minutes after midnight."""
        return self.start_minutes + self.duration_minutes

    @property
    def end_time(self) -> str:
        """End time as an 'HH:MM' string."""
        return format_time(self.end_minutes)

    @property
    def priority_rank(self) -> int:
        """Numeric priority (high=3, medium=2, low=1) for sorting."""
        return PRIORITY_RANK[self.priority]

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task done and return its next occurrence if it recurs, else None."""
        if self.completed:
            return None  # completing twice must not spawn a duplicate next occurrence
        self.completed = True
        return self.next_occurrence()

    def next_occurrence(self) -> Optional["Task"]:
        """Build the next instance of a daily/weekly task (due_date + 1 day or + 7 days)."""
        step = RECURRENCE_STEP.get(self.frequency)
        if step is None:
            return None
        return replace(self, due_date=self.due_date + step, completed=False)


@dataclass
class Pet:
    """A pet profile and the care tasks that belong to it."""

    name: str
    species: str = "dog"
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the pet's name."""
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Pet name cannot be empty")

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove this exact task object (by identity, not equality)."""
        self.tasks.pop(self._index_of(task))

    def replace_task(self, old: Task, new: Task) -> None:
        """Swap an existing task for an edited version in the same position."""
        self.tasks[self._index_of(old)] = new

    def task_count(self) -> int:
        """Number of tasks attached to this pet."""
        return len(self.tasks)

    def _index_of(self, task: Task) -> int:
        """Find a task by identity so two identical-looking tasks are never confused."""
        for i, existing in enumerate(self.tasks):
            if existing is task:
                return i
        raise ValueError(f"{self.name} has no such task: {task.description}")


@dataclass
class Owner:
    """The person doing the care; holds their pets and their daily time budget."""

    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet, rejecting duplicate names because filtering looks pets up by name."""
        if any(p.name.lower() == pet.name.lower() for p in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet:
        """Look up a pet by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.strip().lower():
                return pet
        raise KeyError(f"No pet named {name!r}")

    def get_all_tasks(self) -> list[Entry]:
        """Every (pet, task) pair across all of this owner's pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class PlanItem:
    """One task in a daily plan, with the reason it was scheduled or skipped."""

    pet: Pet
    task: Task
    reason: str


@dataclass
class DailyPlan:
    """The scheduler's output for one day: what's in, what's out, and any clashes."""

    day: date
    scheduled: list[PlanItem]
    skipped: list[PlanItem]
    conflicts: list[str]
    minutes_available: int

    @property
    def minutes_used(self) -> int:
        """Total minutes of the scheduled tasks."""
        return sum(item.task.duration_minutes for item in self.scheduled)

    def explain(self) -> str:
        """A plain-text explanation of the plan, suitable for the terminal or the UI."""
        lines = [
            f"Plan for {self.day.isoformat()}: {len(self.scheduled)} task(s), "
            f"{self.minutes_used} of {self.minutes_available} available minutes used."
        ]
        for item in self.scheduled:
            t = item.task
            lines.append(f"  {t.time}-{t.end_time}  {item.pet.name}: {t.description} -- {item.reason}")
        for item in self.skipped:
            lines.append(f"  SKIPPED  {item.pet.name}: {item.task.description} -- {item.reason}")
        lines.extend(f"  WARNING  {c}" for c in self.conflicts)
        return "\n".join(lines)


class Scheduler:
    """The "brain": retrieves, sorts, filters and plans tasks across all of an owner's pets."""

    def __init__(self, owner: Owner) -> None:
        """Attach the scheduler to the owner whose pets it plans for."""
        self.owner = owner

    def get_all_tasks(self) -> list[Entry]:
        """All (pet, task) pairs, retrieved through the owner."""
        return self.owner.get_all_tasks()

    @staticmethod
    def sort_by_time(entries: list[Entry]) -> list[Entry]:
        """Return entries in chronological order: by due date, then start time.

        Sorting on minutes (not the raw string) stays correct even if a time were
        ever stored unpadded, where "9:00" > "10:00" as strings.
        """
        return sorted(entries, key=lambda e: (e[1].due_date, e[1].start_minutes))

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
        due_on: Optional[date] = None,
    ) -> list[Entry]:
        """Return tasks matching every filter given; a filter left as None is ignored."""
        results = []
        for pet, task in self.get_all_tasks():
            if pet_name is not None and pet.name.lower() != pet_name.strip().lower():
                continue
            if completed is not None and task.completed != completed:
                continue
            if due_on is not None and task.due_date != due_on:
                continue
            results.append((pet, task))
        return results

    def tasks_due(self, day: Optional[date] = None) -> list[Entry]:
        """Incomplete tasks due on `day` or overdue from earlier days, sorted by time."""
        day = day or date.today()
        due = [(p, t) for p, t in self.get_all_tasks() if not t.completed and t.due_date <= day]
        return self.sort_by_time(due)

    @staticmethod
    def detect_conflicts(entries: list[Entry]) -> list[str]:
        """Return a warning for every pair of tasks whose time windows overlap.

        Treats all entries as happening on the same day. Tasks for different pets
        still conflict, because one owner can't be in two places at once.
        Back-to-back tasks (one ends exactly when the next starts) do not conflict.
        Returns warnings rather than raising, so a clash never crashes the app.
        """
        ordered = sorted(entries, key=lambda e: e[1].start_minutes)
        warnings = []
        for i, (pet_a, a) in enumerate(ordered):
            for pet_b, b in ordered[i + 1:]:
                if b.start_minutes >= a.end_minutes:
                    break  # sorted by start, so nothing later can overlap `a` either
                warnings.append(
                    f"Conflict: {pet_a.name}'s '{a.description}' ({a.time}-{a.end_time}) "
                    f"overlaps {pet_b.name}'s '{b.description}' ({b.time}-{b.end_time})"
                )
        return warnings

    def mark_task_complete(self, pet_name: str, task: Task) -> Optional[Task]:
        """Complete a pet's task; for daily/weekly tasks, add and return the next occurrence."""
        pet = self.owner.get_pet(pet_name)
        pet._index_of(task)  # raises if this task doesn't belong to that pet
        next_task = task.mark_complete()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def build_daily_plan(self, day: Optional[date] = None) -> DailyPlan:
        """Choose which due tasks fit the owner's time budget and explain each choice.

        Selection is greedy: highest priority first (earlier start time breaks ties),
        each task kept if it still fits the remaining minutes. The kept tasks are then
        shown in time order, and overlapping ones are flagged rather than moved.
        """
        day = day or date.today()
        remaining = self.owner.available_minutes
        scheduled: list[PlanItem] = []
        skipped: list[PlanItem] = []

        candidates = sorted(self.tasks_due(day), key=lambda e: (-e[1].priority_rank, e[1].start_minutes))
        for pet, task in candidates:
            if task.duration_minutes <= remaining:
                remaining -= task.duration_minutes
                scheduled.append(PlanItem(pet, task, self._reason(task, day)))
            else:
                skipped.append(PlanItem(
                    pet, task,
                    f"{task.priority} priority, needs {task.duration_minutes} min "
                    f"but only {remaining} min left in today's budget",
                ))

        scheduled.sort(key=lambda item: item.task.start_minutes)
        conflicts = self.detect_conflicts([(item.pet, item.task) for item in scheduled])
        return DailyPlan(day, scheduled, skipped, conflicts, self.owner.available_minutes)

    @staticmethod
    def _reason(task: Task, day: date) -> str:
        """Build the human-readable reason a task made it into the plan."""
        parts = [f"{task.priority} priority", "fits in your time budget"]
        if task.frequency != "once":
            parts.append(f"repeats {task.frequency}")
        if task.due_date < day:
            parts.append(f"overdue since {task.due_date.isoformat()}")
        return "; ".join(parts)
