"""PawPal+ Streamlit UI. All logic lives in pawpal_system.py; this file only wires it up."""

from dataclasses import replace
from datetime import date, time

import streamlit as st

from pawpal_system import FREQUENCIES, PRIORITY_RANK, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Plan your pets' care for the day: add pets and tasks, then generate a schedule.")

# --- App "memory" -----------------------------------------------------------
# Streamlit reruns this script top to bottom on every click, so the Owner lives in
# st.session_state; it's created once and then reused on every rerun.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes=120)
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

if "flash" in st.session_state:  # message from the action that triggered the last rerun
    kind, msg = st.session_state.pop("flash")
    getattr(st, kind)(msg)


def flash(kind: str, msg: str) -> None:
    """Show a message after the rerun that refreshes the page with new data."""
    st.session_state.flash = (kind, msg)
    st.rerun()


def entry_label(entry) -> str:
    """Readable one-line label for a (pet, task) pair."""
    pet, task = entry
    done = " ✓" if task.completed else ""
    return f"{task.due_date} {task.time} · {pet.name} · {task.description}{done}"


# --- Owner -------------------------------------------------------------------
st.subheader("Owner")
c1, c2 = st.columns(2)
owner.name = c1.text_input("Owner name", value=owner.name) or owner.name
owner.available_minutes = int(c2.number_input(
    "Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes, step=15,
    help="The scheduler won't plan more task time than this.",
))

# --- Pets --------------------------------------------------------------------
st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    pet_name = c1.text_input("Pet name")
    species = c2.selectbox("Species", ["dog", "cat", "other"])
    age = c3.number_input("Age", min_value=0, max_value=40, value=1)
    if st.form_submit_button("Add pet"):
        try:
            owner.add_pet(Pet(pet_name, species, int(age)))
            flash("success", f"Added {pet_name.strip()}.")
        except ValueError as e:
            st.error(str(e))

if owner.pets:
    st.write(", ".join(f"**{p.name}** ({p.species}, {p.age}y, {p.task_count()} tasks)" for p in owner.pets))
else:
    st.info("No pets yet. Add one above to start scheduling tasks.")
    st.stop()

# --- Add task ----------------------------------------------------------------
st.subheader("Add a task")
with st.form("add_task", clear_on_submit=True):
    c1, c2 = st.columns(2)
    target = c1.selectbox("Pet", [p.name for p in owner.pets])
    description = c2.text_input("Task", placeholder="e.g. Morning walk")
    c1, c2, c3 = st.columns(3)
    start = c1.time_input("Start time", value=time(8, 0), step=300)
    duration = c2.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    due = c3.date_input("Date", value=date.today())
    c1, c2 = st.columns(2)
    priority = c1.selectbox("Priority", list(PRIORITY_RANK), index=0)
    frequency = c2.selectbox("Repeats", FREQUENCIES)
    if st.form_submit_button("Add task"):
        try:
            task = Task(description, start.strftime("%H:%M"), int(duration), priority, frequency, due)
            owner.get_pet(target).add_task(task)
            flash("success", f"Added '{task.description}' for {target} at {task.time}.")
        except ValueError as e:
            st.error(str(e))

# --- Task list: sorting + filtering -----------------------------------------
st.subheader("Tasks")
c1, c2 = st.columns(2)
pet_filter = c1.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
status_filter = c2.selectbox("Show status", ["Incomplete", "Completed", "All"])
entries = scheduler.sort_by_time(scheduler.filter_tasks(
    pet_name=None if pet_filter == "All pets" else pet_filter,
    completed={"Incomplete": False, "Completed": True, "All": None}[status_filter],
))

if entries:
    st.table([{
        "Date": str(t.due_date), "Time": f"{t.time}-{t.end_time}", "Pet": p.name, "Task": t.description,
        "Priority": t.priority, "Repeats": t.frequency, "Done": "✓" if t.completed else "",
    } for p, t in entries])
else:
    st.info("No tasks match these filters.")

# --- Edit / complete / delete -----------------------------------------------
all_entries = scheduler.sort_by_time(scheduler.get_all_tasks())
if all_entries:
    with st.expander("Edit, complete or delete a task"):
        # Pick by index, not by object: Streamlit may hand back a *copy* of an object
        # option, and editing a copy would silently leave the real task unchanged.
        idx = st.selectbox("Task", range(len(all_entries)), format_func=lambda i: entry_label(all_entries[i]))
        pet, task = all_entries[idx]
        c1, c2, c3 = st.columns(3)
        new_time = c1.time_input("Start", value=time.fromisoformat(task.time), step=300, key=f"edit_time_{id(task)}")
        new_dur = c2.number_input("Duration (min)", 1, 240, task.duration_minutes, key=f"edit_dur_{id(task)}")
        new_pri = c3.selectbox("Priority", list(PRIORITY_RANK), list(PRIORITY_RANK).index(task.priority),
                               key=f"edit_pri_{id(task)}")
        b1, b2, b3 = st.columns(3)
        if b1.button("Save changes"):
            try:
                pet.replace_task(task, replace(task, time=new_time.strftime("%H:%M"),
                                               duration_minutes=int(new_dur), priority=new_pri))
                flash("success", f"Updated '{task.description}'.")
            except ValueError as e:
                st.error(str(e))
        if b2.button("Mark complete", disabled=task.completed):
            nxt = scheduler.mark_task_complete(pet.name, task)
            extra = f" Next one scheduled for {nxt.due_date}." if nxt else ""
            flash("success", f"Completed '{task.description}'.{extra}")
        if b3.button("Delete"):
            pet.remove_task(task)
            flash("info", f"Deleted '{task.description}'.")

# --- Daily plan --------------------------------------------------------------
st.divider()
st.subheader("Build today's schedule")
plan_day = st.date_input("Plan for", value=date.today(), key="plan_day")
if st.button("Generate schedule", type="primary"):
    plan = scheduler.build_daily_plan(plan_day)
    if not plan.scheduled and not plan.skipped:
        st.info("Nothing is due that day. 🎉")
    else:
        st.success(f"Scheduled {len(plan.scheduled)} task(s) using {plan.minutes_used} of "
                   f"{plan.minutes_available} available minutes.")
        for warning in plan.conflicts:
            st.warning(f"⚠️ {warning}. You can't do both at once; consider moving one.")
        if plan.scheduled:
            st.table([{
                "Time": f"{i.task.time}-{i.task.end_time}", "Pet": i.pet.name, "Task": i.task.description,
                "Why it's in the plan": i.reason,
            } for i in plan.scheduled])
        if plan.skipped:
            st.markdown("**Left out today**")
            for i in plan.skipped:
                st.info(f"{i.pet.name}: {i.task.description} — {i.reason}")
        with st.expander("Plain-text explanation"):
            st.code(plan.explain(), language=None)
