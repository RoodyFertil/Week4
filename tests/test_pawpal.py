"""Automated tests for the PawPal+ logic layer (run with: python -m pytest)."""

import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Owner, Pet, Scheduler, Task  # noqa: E402

DAY = date(2026, 11, 1)  # fixed date so results don't depend on when tests run


@pytest.fixture
def setup():
    """An owner with two pets and a scheduler, no tasks yet."""
    owner = Owner("Jordan", available_minutes=120)
    dog, cat = Pet("Mochi", "dog"), Pet("Luna", "cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner, dog, cat, Scheduler(owner)


# --- Phase 2 basics -------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task("Feed", "08:00", due_date=DAY)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Mochi")
    assert pet.task_count() == 0
    pet.add_task(Task("Walk", "07:00", due_date=DAY))
    assert pet.task_count() == 1


# --- Sorting ----------------------------------------------------------------

def test_sort_by_time_returns_chronological_order(setup):
    owner, dog, cat, scheduler = setup
    dog.add_task(Task("Evening walk", "18:00", due_date=DAY))
    cat.add_task(Task("Breakfast", "07:05", due_date=DAY))
    dog.add_task(Task("Lunch", "12:30", due_date=DAY))
    times = [t.time for _, t in scheduler.sort_by_time(scheduler.get_all_tasks())]
    assert times == ["07:05", "12:30", "18:00"]


def test_unpadded_times_are_normalized_and_sort_correctly(setup):
    # As raw strings, "9:00" > "10:00"; normalization + numeric sort must prevent that bug.
    owner, dog, _, scheduler = setup
    dog.add_task(Task("Late", "10:00", due_date=DAY))
    dog.add_task(Task("Early", "9:00", due_date=DAY))
    ordered = [t.description for _, t in scheduler.sort_by_time(scheduler.get_all_tasks())]
    assert ordered == ["Early", "Late"]
    assert dog.tasks[1].time == "09:00"


def test_sort_orders_by_date_before_time(setup):
    owner, dog, _, scheduler = setup
    dog.add_task(Task("Tomorrow early", "06:00", due_date=DAY + timedelta(days=1)))
    dog.add_task(Task("Today late", "22:00", due_date=DAY))
    ordered = [t.description for _, t in scheduler.sort_by_time(scheduler.get_all_tasks())]
    assert ordered == ["Today late", "Tomorrow early"]


# --- Filtering --------------------------------------------------------------

def test_filter_by_pet_and_status(setup):
    owner, dog, cat, scheduler = setup
    walk = Task("Walk", "07:00", due_date=DAY)
    dog.add_task(walk)
    dog.add_task(Task("Pill", "08:00", due_date=DAY))
    cat.add_task(Task("Feed", "07:30", due_date=DAY))
    walk.mark_complete()

    assert {t.description for _, t in scheduler.filter_tasks(pet_name="mochi")} == {"Walk", "Pill"}
    assert [t.description for _, t in scheduler.filter_tasks(completed=True)] == ["Walk"]
    assert [t.description for _, t in scheduler.filter_tasks(pet_name="Mochi", completed=False)] == ["Pill"]


def test_pet_with_no_tasks_is_handled(setup):
    _, _, _, scheduler = setup
    assert scheduler.filter_tasks(pet_name="Luna") == []
    plan = scheduler.build_daily_plan(DAY)
    assert plan.scheduled == [] and plan.skipped == [] and plan.conflicts == []


# --- Recurrence -------------------------------------------------------------

def test_completing_daily_task_creates_next_day_instance(setup):
    owner, dog, _, scheduler = setup
    walk = Task("Walk", "07:00", frequency="daily", due_date=DAY)
    dog.add_task(walk)
    nxt = scheduler.mark_task_complete("Mochi", walk, on=DAY)
    assert nxt is not None
    assert nxt.due_date == DAY + timedelta(days=1)
    assert nxt.completed is False and nxt.time == "07:00"
    assert dog.task_count() == 2


def test_completing_weekly_task_creates_instance_seven_days_later(setup):
    _, _, cat, scheduler = setup
    brush = Task("Brush", "19:00", frequency="weekly", due_date=DAY)
    cat.add_task(brush)
    assert scheduler.mark_task_complete("Luna", brush, on=DAY).due_date == DAY + timedelta(days=7)


def test_one_time_task_does_not_recur(setup):
    _, dog, _, scheduler = setup
    vet = Task("Vet visit", "10:00", frequency="once", due_date=DAY)
    dog.add_task(vet)
    assert scheduler.mark_task_complete("Mochi", vet) is None
    assert dog.task_count() == 1


def test_completing_twice_does_not_duplicate_next_occurrence(setup):
    _, dog, _, scheduler = setup
    walk = Task("Walk", "07:00", frequency="daily", due_date=DAY)
    dog.add_task(walk)
    scheduler.mark_task_complete("Mochi", walk)
    assert scheduler.mark_task_complete("Mochi", walk) is None
    assert dog.task_count() == 2


def test_completing_overdue_daily_task_schedules_from_completion_day(setup):
    # Regression: next copy used to be old due_date + 1, so a task missed 3 days ago
    # spawned a copy that was *still* overdue and reappeared in today's plan.
    _, dog, _, scheduler = setup
    walk = Task("Walk", "07:00", frequency="daily", due_date=DAY - timedelta(days=3))
    dog.add_task(walk)
    nxt = scheduler.mark_task_complete("Mochi", walk, on=DAY)
    assert nxt.due_date == DAY + timedelta(days=1)
    assert scheduler.build_daily_plan(DAY).scheduled == []


def test_completing_overdue_weekly_task_schedules_a_week_after_completion(setup):
    _, _, cat, scheduler = setup
    brush = Task("Brush", "19:00", frequency="weekly", due_date=DAY - timedelta(days=2))
    cat.add_task(brush)
    assert scheduler.mark_task_complete("Luna", brush, on=DAY).due_date == DAY + timedelta(days=7)


def test_completing_a_future_task_early_keeps_its_cadence(setup):
    # Doing tomorrow's walk today shouldn't schedule another one for tomorrow.
    _, dog, _, scheduler = setup
    walk = Task("Walk", "07:00", frequency="daily", due_date=DAY + timedelta(days=1))
    dog.add_task(walk)
    assert scheduler.mark_task_complete("Mochi", walk, on=DAY).due_date == DAY + timedelta(days=2)


def test_mark_complete_rejects_task_from_another_pet(setup):
    _, dog, _, scheduler = setup
    walk = Task("Walk", "07:00", due_date=DAY)
    dog.add_task(walk)
    with pytest.raises(ValueError):
        scheduler.mark_task_complete("Luna", walk)


# --- Conflict detection -----------------------------------------------------

def test_detects_tasks_at_the_exact_same_time(setup):
    _, dog, cat, scheduler = setup
    dog.add_task(Task("Walk", "08:00", 30, due_date=DAY))
    cat.add_task(Task("Feed", "08:00", 10, due_date=DAY))
    warnings = scheduler.detect_conflicts(scheduler.tasks_due(DAY))
    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Feed" in warnings[0]


def test_detects_partial_overlap(setup):
    _, dog, cat, scheduler = setup
    dog.add_task(Task("Walk", "07:30", 30, due_date=DAY))
    cat.add_task(Task("Feed", "07:45", 10, due_date=DAY))
    assert len(scheduler.detect_conflicts(scheduler.tasks_due(DAY))) == 1


def test_back_to_back_tasks_do_not_conflict(setup):
    _, dog, _, scheduler = setup
    dog.add_task(Task("Walk", "07:00", 30, due_date=DAY))
    dog.add_task(Task("Feed", "07:30", 10, due_date=DAY))
    assert scheduler.detect_conflicts(scheduler.tasks_due(DAY)) == []


def test_long_task_conflicts_with_every_task_inside_it(setup):
    # The early `break` must not stop checking a long task against later overlaps.
    _, dog, cat, scheduler = setup
    dog.add_task(Task("Hike", "09:00", 120, due_date=DAY))
    cat.add_task(Task("Feed", "09:30", 10, due_date=DAY))
    cat.add_task(Task("Play", "10:30", 10, due_date=DAY))
    assert len(scheduler.detect_conflicts(scheduler.tasks_due(DAY))) == 2


# --- Daily plan -------------------------------------------------------------

def test_plan_keeps_high_priority_when_time_runs_out(setup):
    owner, dog, _, scheduler = setup
    owner.available_minutes = 40
    dog.add_task(Task("Grooming", "07:00", 30, "low", due_date=DAY))
    dog.add_task(Task("Meds", "09:00", 10, "high", due_date=DAY))
    dog.add_task(Task("Walk", "08:00", 30, "high", due_date=DAY))
    plan = scheduler.build_daily_plan(DAY)
    assert [i.task.description for i in plan.scheduled] == ["Walk", "Meds"]  # time order
    assert [i.task.description for i in plan.skipped] == ["Grooming"]
    assert "only 0 min left" in plan.skipped[0].reason
    assert plan.minutes_used == 40


def test_plan_excludes_completed_and_future_tasks_but_includes_overdue(setup):
    _, dog, _, scheduler = setup
    done = Task("Done", "07:00", due_date=DAY)
    done.mark_complete()
    dog.add_task(done)
    dog.add_task(Task("Tomorrow", "07:00", due_date=DAY + timedelta(days=1)))
    dog.add_task(Task("Missed yesterday", "08:00", frequency="daily", due_date=DAY - timedelta(days=1)))
    plan = scheduler.build_daily_plan(DAY)
    assert [i.task.description for i in plan.scheduled] == ["Missed yesterday"]
    assert "overdue" in plan.scheduled[0].reason


# --- Validation -------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"time": "25:00"}, {"time": "noon"}, {"duration_minutes": 0},
    {"priority": "urgent"}, {"frequency": "monthly"}, {"description": "  "},
    {"time": "23:50", "duration_minutes": 30},
])
def test_invalid_task_fields_are_rejected(bad):
    fields = {"description": "Walk", "time": "08:00", **bad}
    with pytest.raises(ValueError):
        Task(**fields)


def test_duplicate_pet_names_are_rejected(setup):
    owner, *_ = setup
    with pytest.raises(ValueError):
        owner.add_pet(Pet("mochi"))
