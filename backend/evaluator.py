# ============================================================
# Placement Week Scheduler — Baseline Evaluator
# Mirai Labs Assignment A
# ============================================================

from collections import defaultdict
from db import get_connection


# ============================================================
# Helpers
# ============================================================

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def load_schedule(cursor):
    cursor.execute("""
        SELECT *
        FROM interviews
    """)
    return cursor.fetchall()


def load_rooms(cursor):
    cursor.execute("""
        SELECT *
        FROM rooms
    """)
    return cursor.fetchall()


def load_panels(cursor):
    cursor.execute("""
        SELECT
            p.*,
            c.placement_day,
            c.interview_duration_min
        FROM panels p
        JOIN companies c
            ON c.id = p.company_id
    """)
    return cursor.fetchall()


# ============================================================
# Basic metrics
# ============================================================

def calculate_basic_metrics(interviews):
    total = len(interviews)

    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    unscheduled = [
        i for i in interviews
        if i["status"] == "unscheduled"
    ]

    scheduled_count = len(scheduled)
    unscheduled_count = len(unscheduled)

    scheduling_rate = (
        scheduled_count / total * 100
        if total else 0
    )

    return {
        "total": total,
        "scheduled": scheduled_count,
        "unscheduled": unscheduled_count,
        "scheduling_rate": scheduling_rate,
    }


# ============================================================
# Student metrics
# ============================================================

def calculate_student_metrics(interviews):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    counts = defaultdict(int)

    for interview in scheduled:
        counts[interview["student_id"]] += 1

    students_served = len(counts)

    max_interviews = (
        max(counts.values())
        if counts else 0
    )

    average_interviews = (
        sum(counts.values()) / students_served
        if students_served else 0
    )

    distribution = defaultdict(int)

    for count in counts.values():
        distribution[count] += 1

    return {
        "students_served": students_served,
        "max_interviews_per_student": max_interviews,
        "average_interviews_per_served_student":
            average_interviews,
        "interview_distribution":
            dict(sorted(distribution.items())),
    }


# ============================================================
# Student overlap detection
# ============================================================

def count_student_conflicts(interviews):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    conflicts = []

    for index, a in enumerate(scheduled):

        for b in scheduled[index + 1:]:

            if a["student_id"] != b["student_id"]:
                continue

            if overlaps(
                a["start_time"],
                a["end_time"],
                b["start_time"],
                b["end_time"],
            ):
                conflicts.append(
                    (a["id"], b["id"])
                )

    return conflicts


# ============================================================
# Room overlap detection
# ============================================================

def count_room_conflicts(interviews):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    conflicts = []

    for index, a in enumerate(scheduled):

        for b in scheduled[index + 1:]:

            if a["room_id"] != b["room_id"]:
                continue

            if overlaps(
                a["start_time"],
                a["end_time"],
                b["start_time"],
                b["end_time"],
            ):
                conflicts.append(
                    (a["id"], b["id"])
                )

    return conflicts


# ============================================================
# Panel overlap detection
# ============================================================

def count_panel_conflicts(interviews):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    conflicts = []

    for index, a in enumerate(scheduled):

        for b in scheduled[index + 1:]:

            if a["panel_id"] != b["panel_id"]:
                continue

            if overlaps(
                a["start_time"],
                a["end_time"],
                b["start_time"],
                b["end_time"],
            ):
                conflicts.append(
                    (a["id"], b["id"])
                )

    return conflicts


# ============================================================
# Room utilization
# ============================================================

def calculate_room_utilization(interviews, rooms):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    # Each room is available 8 hours/day.
    # There are 4 placement days.
    available_minutes_per_room = 4 * 8 * 60

    utilization = {}

    total_used = 0
    total_available = (
        len(rooms)
        * available_minutes_per_room
    )

    for room in rooms:

        room_id = room["id"]

        used_minutes = 0

        for interview in scheduled:

            if interview["room_id"] != room_id:
                continue

            duration = (
                interview["end_time"]
                - interview["start_time"]
            ).total_seconds() / 60

            used_minutes += duration

        percentage = (
            used_minutes
            / available_minutes_per_room
            * 100
        )

        utilization[room_id] = {
            "used_minutes": used_minutes,
            "available_minutes":
                available_minutes_per_room,
            "utilization_pct": percentage,
        }

        total_used += used_minutes

    overall_percentage = (
        total_used / total_available * 100
        if total_available else 0
    )

    return {
        "rooms": utilization,
        "total_used_minutes": total_used,
        "total_available_minutes": total_available,
        "overall_utilization_pct": overall_percentage,
    }


# ============================================================
# Panel utilization
# ============================================================

def calculate_panel_utilization(interviews, panels):
    scheduled = [
        i for i in interviews
        if i["status"] == "scheduled"
    ]

    utilization = {}

    total_used = 0
    total_available = 0

    for panel in panels:

        panel_id = panel["id"]

        placement_day = panel["placement_day"]

        # One panel has an 8-hour working day.
        available_minutes = 8 * 60

        used_minutes = 0

        for interview in scheduled:

            if interview["panel_id"] != panel_id:
                continue

            duration = (
                interview["end_time"]
                - interview["start_time"]
            ).total_seconds() / 60

            used_minutes += duration

        percentage = (
            used_minutes
            / available_minutes
            * 100
        )

        utilization[panel_id] = {
            "placement_day": placement_day,
            "used_minutes": used_minutes,
            "available_minutes": available_minutes,
            "utilization_pct": percentage,
        }

        total_used += used_minutes
        total_available += available_minutes

    overall_percentage = (
        total_used / total_available * 100
        if total_available else 0
    )

    return {
        "panels": utilization,
        "total_used_minutes": total_used,
        "total_available_minutes": total_available,
        "overall_utilization_pct": overall_percentage,
    }


# ============================================================
# Waiting time
# ============================================================

def calculate_waiting_time(interviews):
    """
    Calculate student waiting time between consecutive interviews
    on the SAME placement day.

    Overnight gaps are excluded.
    """

    scheduled = [
        i
        for i in interviews
        if i["status"] == "scheduled"
    ]

    by_student = defaultdict(list)

    for interview in scheduled:
        by_student[
            interview["student_id"]
        ].append(interview)

    waits = []

    for student_id, student_interviews in by_student.items():

        student_interviews.sort(
            key=lambda x: x["start_time"]
        )

        for first, second in zip(
            student_interviews,
            student_interviews[1:]
        ):
            # Only measure waiting within the same calendar day.
            if first["start_time"].date() != second["start_time"].date():
                continue

            wait = (
                second["start_time"]
                - first["end_time"]
            ).total_seconds() / 60

            if wait >= 0:
                waits.append(wait)

    average_wait = (
        sum(waits) / len(waits)
        if waits else 0
    )

    maximum_wait = (
        max(waits)
        if waits else 0
    )

    return {
        "average_waiting_minutes": average_wait,
        "maximum_waiting_minutes": maximum_wait,
        "waiting_samples": len(waits),
    }


# ============================================================
# Unscheduled reasons
# ============================================================

def calculate_unscheduled_reasons(interviews):
    reasons = defaultdict(int)

    for interview in interviews:

        if interview["status"] != "unscheduled":
            continue

        reason = (
            interview["reason"]
            or "unknown"
        )

        reasons[reason] += 1

    return dict(
        sorted(
            reasons.items(),
            key=lambda item: -item[1]
        )
    )


# ============================================================
# Full evaluation
# ============================================================

def evaluate(interviews, rooms, panels):

    basic = calculate_basic_metrics(
        interviews
    )

    student = calculate_student_metrics(
        interviews
    )

    student_conflicts = count_student_conflicts(
        interviews
    )

    room_conflicts = count_room_conflicts(
        interviews
    )

    panel_conflicts = count_panel_conflicts(
        interviews
    )

    room_utilization = calculate_room_utilization(
        interviews,
        rooms
    )

    panel_utilization = calculate_panel_utilization(
        interviews,
        panels
    )

    waiting = calculate_waiting_time(
        interviews
    )

    reasons = calculate_unscheduled_reasons(
        interviews
    )

    return {
        "basic": basic,
        "student": student,
        "student_conflicts": student_conflicts,
        "room_conflicts": room_conflicts,
        "panel_conflicts": panel_conflicts,
        "room_utilization": room_utilization,
        "panel_utilization": panel_utilization,
        "waiting": waiting,
        "unscheduled_reasons": reasons,
    }


# ============================================================
# Printing
# ============================================================

def print_report(results):

    basic = results["basic"]
    student = results["student"]
    room = results["room_utilization"]
    panel = results["panel_utilization"]
    waiting = results["waiting"]

    print()
    print("=" * 70)
    print("PLACEMENT SCHEDULER — BASELINE EVALUATION")
    print("=" * 70)

    print()
    print("Scheduling")
    print("-" * 70)

    print(
        f"Total shortlist entries : "
        f"{basic['total']}"
    )

    print(
        f"Scheduled               : "
        f"{basic['scheduled']}"
    )

    print(
        f"Unscheduled             : "
        f"{basic['unscheduled']}"
    )

    print(
        f"Scheduling rate         : "
        f"{basic['scheduling_rate']:.2f}%"
    )

    print()
    print("Student Fairness")
    print("-" * 70)

    print(
        f"Students served        : "
        f"{student['students_served']}"
    )

    print(
        f"Average interviews     : "
        f"{student['average_interviews_per_served_student']:.2f}"
    )

    print(
        f"Maximum interviews     : "
        f"{student['max_interviews_per_student']}"
    )

    print()
    print("Constraint Validation")
    print("-" * 70)

    print(
        f"Student conflicts      : "
        f"{len(results['student_conflicts'])}"
    )

    print(
        f"Room conflicts         : "
        f"{len(results['room_conflicts'])}"
    )

    print(
        f"Panel conflicts        : "
        f"{len(results['panel_conflicts'])}"
    )

    print()
    print("Resource Utilization")
    print("-" * 70)

    print(
        f"Room utilization       : "
        f"{room['overall_utilization_pct']:.2f}%"
    )

    print(
        f"Panel utilization      : "
        f"{panel['overall_utilization_pct']:.2f}%"
    )

    print()
    print("Waiting Time")
    print("-" * 70)

    print(
        f"Average waiting time   : "
        f"{waiting['average_waiting_minutes']:.2f} min"
    )

    print(
        f"Maximum waiting time   : "
        f"{waiting['maximum_waiting_minutes']:.2f} min"
    )

    print()
    print("Unscheduled Reasons")
    print("-" * 70)

    for reason, count in results[
        "unscheduled_reasons"
    ].items():

        print(
            f"{count:5d} — {reason}"
        )

    print()
    print("=" * 70)


# ============================================================
# Main
# ============================================================

def run():

    conn = get_connection()

    cursor = conn.cursor(
        dictionary=True
    )

    try:

        interviews = load_schedule(
            cursor
        )

        rooms = load_rooms(
            cursor
        )

        panels = load_panels(
            cursor
        )

        results = evaluate(
            interviews,
            rooms,
            panels
        )

        print_report(
            results
        )

    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":
    run()