"""CLI demo for PawPal+: exercises the logic layer in the terminal before the UI."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_entries(title, entries):
    """Print (pet, task) pairs as an aligned table."""
    print(f"\n{title}")
    print("-" * len(title))
    if not entries:
        print("  (none)")
    for pet, task in entries:
        status = "done" if task.completed else "todo"
        print(
            f"  {task.time}-{task.end_time}  {pet.name:<6} {task.description:<18} "
            f"{task.priority:<6} {task.frequency:<6} {task.due_date}  [{status}]"
        )


def main():
    today = date.today()
    owner = Owner("Jordan", available_minutes=90)
    mochi = Pet("Mochi", species="dog", age=3)
    luna = Pet("Luna", species="cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added deliberately out of order to show sorting.
    mochi.add_task(Task("Evening walk", "18:00", 30, "high", "daily", today))
    luna.add_task(Task("Brush fur", "19:00", 15, "low", "weekly", today))
    mochi.add_task(Task("Morning walk", "07:30", 30, "high", "daily", today))
    luna.add_task(Task("Breakfast", "07:45", 10, "high", "daily", today))  # overlaps the walk
    mochi.add_task(Task("Heartworm pill", "08:15", 5, "medium", "once", today))
    luna.add_task(Task("Laser-toy play", "12:00", 20, "medium", "daily", today))

    scheduler = Scheduler(owner)

    print_entries("All tasks (as entered)", scheduler.get_all_tasks())
    print_entries("Today's Schedule (sorted by time)", scheduler.sort_by_time(scheduler.get_all_tasks()))
    print_entries("Filter: Luna's tasks only", scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Luna")))

    print("\nConflict check")
    print("--------------")
    for warning in scheduler.detect_conflicts(scheduler.tasks_due(today)) or ["  No conflicts."]:
        print(f"  {warning}")

    print("\nDaily plan (90-minute budget)")
    print("-----------------------------")
    print(scheduler.build_daily_plan(today).explain())

    morning_walk = mochi.tasks[1]
    next_walk = scheduler.mark_task_complete("Mochi", morning_walk)
    print(f"\nMarked '{morning_walk.description}' complete -> next one auto-created for {next_walk.due_date}")
    print_entries("Filter: completed tasks", scheduler.filter_tasks(completed=True))
    print_entries("Filter: Mochi's incomplete tasks", scheduler.sort_by_time(
        scheduler.filter_tasks(pet_name="Mochi", completed=False)))


if __name__ == "__main__":
    main()
