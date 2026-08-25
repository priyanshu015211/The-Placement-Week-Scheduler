# ============================================================
# Placement Week Scheduler — Scheduling Engine
# Mirai Labs Assignment A — Task 2
# ============================================================
#
# Purpose:
#   Generate a feasible placement interview schedule from MySQL.
#
# Scheduling policy:
#   1. Tier 1 companies are processed before Tier 2/3.
#   2. Earlier placement days are processed first within a tier.
#   3. Students with fewer scheduled interviews are preferred.
#   4. Maximum interviews per student = 8.
#   5. No student can have overlapping interviews.
#   6. No room can be double-booked.
#   7. No panel can be double-booked.
#   8. Company arrival time is respected.
#   9. Company interview duration is respected.
#  10. Every unscheduled interview receives a specific reason.
#
# ============================================================

from datetime import datetime, timedelta, time
from collections import defaultdict

from db import get_connection


# ============================================================
# Configuration
# ============================================================

DAY_START = time(9, 0)
DAY_END = time(17, 0)

# Synthetic date used for the 4-day placement week.
# Day 1 = 2026-03-01
PLACEMENT_START_DATE = datetime(2026, 3, 1)

# Fairness policy.
# This is a maximum, not a target.
MAX_INTERVIEWS_PER_STUDENT = 8


# ============================================================
# Data Loading
# ============================================================

def load_data(cursor):
    """Load companies, students, shortlists, rooms and panels."""

    cursor.execute("""
        SELECT *
        FROM companies
    """)
    companies = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM students
        WHERE status = 'active'
    """)
    students = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM shortlists
    """)
    shortlists = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM rooms
        WHERE status = 'available'
        ORDER BY id
    """)
    rooms = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM panels
        WHERE status = 'available'
    """)
    panels = cursor.fetchall()

    return (
        companies,
        students,
        shortlists,
        rooms,
        panels,
    )


# ============================================================
# Slot Generation
# ============================================================

def generate_slots_for_company(company):
    """
    Generate all sequential interview slots available to a company.

    Rules:
      - Placement day determines the date.
      - Interview cannot begin before 09:00.
      - Interview cannot begin before company arrival.
      - Interview cannot finish after 17:00.
      - Slot length equals company interview duration.
    """

    placement_day = company["placement_day"]

    duration = timedelta(
        minutes=company["interview_duration_min"]
    )

    base_date = (
        PLACEMENT_START_DATE
        + timedelta(days=placement_day - 1)
    )

    arrival = company["arrival_time"]

    if arrival is None:
        arrival_time = DAY_START

    elif isinstance(arrival, timedelta):
        arrival_time = (
            datetime.min + arrival
        ).time()

    else:
        arrival_time = arrival

    start_time = max(
        DAY_START,
        arrival_time
    )

    start_dt = datetime.combine(
        base_date,
        start_time
    )

    end_dt = datetime.combine(
        base_date,
        DAY_END
    )

    slots = []

    current = start_dt

    while current + duration <= end_dt:

        slots.append(
            (
                current,
                current + duration
            )
        )

        current += duration

    return slots


# ============================================================
# Time Conflict Helpers
# ============================================================

def overlaps(
    a_start,
    a_end,
    b_start,
    b_end,
):
    """Return True when two time intervals overlap."""

    return (
        a_start < b_end
        and b_start < a_end
    )


def is_student_busy(
    student_id,
    start_time,
    end_time,
    student_busy,
):
    """Check whether a student has a conflicting interview."""

    return any(
        overlaps(
            start_time,
            end_time,
            busy_start,
            busy_end,
        )
        for busy_start, busy_end
        in student_busy[student_id]
    )


def is_panel_busy(
    panel_id,
    start_time,
    end_time,
    panel_busy,
):
    """Check whether a panel is already occupied."""

    return any(
        overlaps(
            start_time,
            end_time,
            busy_start,
            busy_end,
        )
        for busy_start, busy_end
        in panel_busy[panel_id]
    )


def find_free_room(
    rooms,
    start_time,
    end_time,
    room_busy,
):
    """
    Return an available room.

    Returns None if every room is occupied during
    the requested interval.
    """

    for room in rooms:

        room_id = room["id"]

        if not any(
            overlaps(
                start_time,
                end_time,
                busy_start,
                busy_end,
            )
            for busy_start, busy_end
            in room_busy[room_id]
        ):
            return room_id

    return None


# ============================================================
# Student Feasibility Helpers
# ============================================================

def has_any_feasible_slot(
    student_id,
    slots,
    student_busy,
):
    """
    Check whether the student is available for at least
    one slot belonging to the company.

    This checks the student's own schedule only.
    Room/panel availability is handled separately.
    """

    for start_time, end_time in slots:

        if not is_student_busy(
            student_id,
            start_time,
            end_time,
            student_busy,
        ):
            return True

    return False


# ============================================================
# Core Scheduling
# ============================================================

def schedule(
    companies,
    students,
    shortlists,
    rooms,
    panels,
):
    """
    Generate a feasible baseline placement schedule.

    Returns:
        scheduled
        unscheduled
    """

    # --------------------------------------------------------
    # Lookup tables
    # --------------------------------------------------------

    students_by_id = {
        student["id"]: student
        for student in students
    }

    # company_id -> student IDs
    shortlist_map = defaultdict(list)

    for shortlist in shortlists:

        company_id = shortlist["company_id"]
        student_id = shortlist["student_id"]

        # Defensive validation.
        if student_id in students_by_id:
            shortlist_map[company_id].append(
                student_id
            )

    # Remove any accidental duplicates.
    for company_id in shortlist_map:

        shortlist_map[company_id] = list(
            dict.fromkeys(
                shortlist_map[company_id]
            )
        )

    # company_id -> panels
    panels_by_company = defaultdict(list)

    for panel in panels:

        panels_by_company[
            panel["company_id"]
        ].append(panel)

    # --------------------------------------------------------
    # Scheduling state
    # --------------------------------------------------------

    # student_id -> [(start, end), ...]
    student_busy = defaultdict(list)

    # panel_id -> [(start, end), ...]
    panel_busy = defaultdict(list)

    # room_id -> [(start, end), ...]
    room_busy = defaultdict(list)

    # student_id -> number of scheduled interviews
    student_interview_count = defaultdict(int)

    scheduled = []
    unscheduled = []

    # --------------------------------------------------------
    # Company ordering
    # --------------------------------------------------------
    #
    # Priority:
    #   Tier 1 → Tier 2 → Tier 3
    #
    # Within same tier:
    #   Day 1 → Day 2 → Day 3 → Day 4
    #
    # ID is used as deterministic tie-breaker.
    #
    # --------------------------------------------------------

    companies_sorted = sorted(
        companies,
        key=lambda company: (
            company["priority_tier"],
            company["placement_day"],
            company["id"],
        ),
    )

    # ========================================================
    # Process companies
    # ========================================================

    for company in companies_sorted:

        company_id = company["id"]

        company_panels = panels_by_company.get(
            company_id,
            [],
        )

        company_students = list(
            shortlist_map.get(
                company_id,
                [],
            )
        )

        # ----------------------------------------------------
        # No panels
        # ----------------------------------------------------

        if not company_panels:

            for student_id in company_students:

                unscheduled.append(
                    (
                        student_id,
                        company_id,
                        "company has no available panels",
                    )
                )

            continue

        # ----------------------------------------------------
        # Generate company slots
        # ----------------------------------------------------

        slots = generate_slots_for_company(
            company
        )

        # ----------------------------------------------------
        # Candidate queue
        # ----------------------------------------------------

        queue = company_students

        # ====================================================
        # Dynamic queue ranking
        # ====================================================

        def sort_queue():

            queue.sort(
                key=lambda student_id: (
                    # First: fewer interviews
                    student_interview_count[
                        student_id
                    ],

                    # Second: higher CGPA
                    -students_by_id[
                        student_id
                    ]["cgpa"],

                    # Third: deterministic student ID
                    student_id,
                )
            )

        sort_queue()

        # ====================================================
        # Process slots
        # ====================================================

        for slot_start, slot_end in slots:

            if not queue:
                break

            sort_queue()

            # ------------------------------------------------
            # Process panels
            # ------------------------------------------------

            for panel in company_panels:

                if not queue:
                    break

                panel_id = panel["id"]

                # Panel already occupied.
                if is_panel_busy(
                    panel_id,
                    slot_start,
                    slot_end,
                    panel_busy,
                ):
                    continue

                # ------------------------------------------------
                # Find best candidate.
                # ------------------------------------------------

                selected_student_id = None
                selected_index = None

                for index, student_id in enumerate(queue):

                    # ------------------------------------------
                    # Fairness limit
                    # ------------------------------------------

                    if (
                        student_interview_count[
                            student_id
                        ]
                        >= MAX_INTERVIEWS_PER_STUDENT
                    ):
                        continue

                    # ------------------------------------------
                    # Student conflict
                    # ------------------------------------------

                    if is_student_busy(
                        student_id,
                        slot_start,
                        slot_end,
                        student_busy,
                    ):
                        continue

                    selected_student_id = student_id
                    selected_index = index

                    break

                # No eligible student for this particular slot.
                if selected_student_id is None:
                    continue

                # ------------------------------------------------
                # Find room
                # ------------------------------------------------

                free_room_id = find_free_room(
                    rooms,
                    slot_start,
                    slot_end,
                    room_busy,
                )

                # ------------------------------------------------
                # No room NOW.
                #
                # Do not permanently reject the student.
                # They can be considered for a later slot.
                # ------------------------------------------------

                if free_room_id is None:
                    continue

                # ------------------------------------------------
                # Book interview
                # ------------------------------------------------

                student_busy[
                    selected_student_id
                ].append(
                    (
                        slot_start,
                        slot_end,
                    )
                )

                panel_busy[
                    panel_id
                ].append(
                    (
                        slot_start,
                        slot_end,
                    )
                )

                room_busy[
                    free_room_id
                ].append(
                    (
                        slot_start,
                        slot_end,
                    )
                )

                student_interview_count[
                    selected_student_id
                ] += 1

                scheduled.append(
                    (
                        selected_student_id,
                        company_id,
                        free_room_id,
                        panel_id,
                        slot_start,
                        slot_end,
                        "scheduled",
                    )
                )

                queue.pop(selected_index)

        # ====================================================
        # Classify remaining students
        # ====================================================

        for student_id in queue:

            interview_count = (
                student_interview_count[
                    student_id
                ]
            )

            # ------------------------------------------------
            # Reason 1: Fairness cap
            # ------------------------------------------------

            if (
                interview_count
                >= MAX_INTERVIEWS_PER_STUDENT
            ):

                unscheduled.append(
                    (
                        student_id,
                        company_id,
                        (
                            "student reached maximum "
                            f"interview limit of "
                            f"{MAX_INTERVIEWS_PER_STUDENT}"
                        ),
                    )
                )

                continue

            # ------------------------------------------------
            # Reason 2: Student unavailable in every
            # company slot
            # ------------------------------------------------

            if not has_any_feasible_slot(
                student_id,
                slots,
                student_busy,
            ):

                unscheduled.append(
                    (
                        student_id,
                        company_id,
                        (
                            "student unavailable for "
                            "all remaining company slots"
                        ),
                    )
                )

                continue

            # ------------------------------------------------
            # Reason 3:
            # Student has possible timing but the available
            # company resources were exhausted.
            # ------------------------------------------------

            unscheduled.append(
                (
                    student_id,
                    company_id,
                    (
                        "company panel/day capacity "
                        "or room capacity exhausted "
                        "before reaching this student"
                    ),
                )
            )

    return scheduled, unscheduled


# ============================================================
# Persistence
# ============================================================

def write_results(
    cursor,
    scheduled,
    unscheduled,
):
    """
    Replace the currently generated baseline schedule.
    """

    cursor.execute(
        "DELETE FROM replan_log"
    )

    cursor.execute(
        "DELETE FROM interviews"
    )

    insert_sql = """
        INSERT INTO interviews (
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            reason
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """

    # --------------------------------------------------------
    # Scheduled
    # --------------------------------------------------------

    scheduled_rows = [
        (
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            None,
        )
        for (
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
        ) in scheduled
    ]

    if scheduled_rows:

        cursor.executemany(
            insert_sql,
            scheduled_rows,
        )

    # --------------------------------------------------------
    # Unscheduled
    # --------------------------------------------------------

    unscheduled_rows = [
        (
            student_id,
            company_id,
            None,
            None,
            None,
            None,
            "unscheduled",
            reason,
        )
        for (
            student_id,
            company_id,
            reason,
        ) in unscheduled
    ]

    if unscheduled_rows:

        cursor.executemany(
            insert_sql,
            unscheduled_rows,
        )


# ============================================================
# Metrics
# ============================================================

def print_metrics(
    scheduled,
    unscheduled,
    rooms,
    panels,
):
    """Display useful baseline metrics."""

    total = (
        len(scheduled)
        + len(unscheduled)
    )

    scheduled_percentage = (
        (len(scheduled) / total) * 100
        if total
        else 0
    )

    unscheduled_percentage = (
        (len(unscheduled) / total) * 100
        if total
        else 0
    )

    print()
    print("=" * 70)
    print("PLACEMENT SCHEDULER — BASELINE RESULTS")
    print("=" * 70)

    print(
        f"Total shortlist entries : {total}"
    )

    print(
        f"Scheduled               : "
        f"{len(scheduled)} "
        f"({scheduled_percentage:.1f}%)"
    )

    print(
        f"Unscheduled             : "
        f"{len(unscheduled)} "
        f"({unscheduled_percentage:.1f}%)"
    )

    # --------------------------------------------------------
    # Student fairness metrics
    # --------------------------------------------------------

    student_counts = defaultdict(int)

    for (
        student_id,
        company_id,
        room_id,
        panel_id,
        start_time,
        end_time,
        status,
    ) in scheduled:

        student_counts[
            student_id
        ] += 1

    print()
    print("Student Fairness")
    print("-" * 70)

    if student_counts:

        max_interviews = max(
            student_counts.values()
        )

        average_interviews = (
            sum(student_counts.values())
            / len(student_counts)
        )

        print(
            f"Students with interviews : "
            f"{len(student_counts)}"
        )

        print(
            f"Average interviews       : "
            f"{average_interviews:.2f}"
        )

        print(
            f"Maximum interviews       : "
            f"{max_interviews}"
        )

    else:

        print(
            "No students were scheduled."
        )

    # --------------------------------------------------------
    # Unscheduled reasons
    # --------------------------------------------------------

    reasons = defaultdict(int)

    for (
        student_id,
        company_id,
        reason,
    ) in unscheduled:

        reasons[reason] += 1

    print()
    print("Unscheduled Breakdown")
    print("-" * 70)

    for reason, count in sorted(
        reasons.items(),
        key=lambda item: -item[1],
    ):

        print(
            f"{count:5d} — {reason}"
        )

    print("=" * 70)


# ============================================================
# Main
# ============================================================

def run():

    conn = get_connection()

    read_cursor = conn.cursor(
        dictionary=True
    )

    write_cursor = None

    try:

        # ----------------------------------------------------
        # Load
        # ----------------------------------------------------

        (
            companies,
            students,
            shortlists,
            rooms,
            panels,
        ) = load_data(
            read_cursor
        )

        print()
        print("Loaded data:")
        print(
            f"  Companies : {len(companies)}"
        )
        print(
            f"  Students  : {len(students)}"
        )
        print(
            f"  Shortlists: {len(shortlists)}"
        )
        print(
            f"  Rooms     : {len(rooms)}"
        )
        print(
            f"  Panels    : {len(panels)}"
        )

        # ----------------------------------------------------
        # Generate schedule
        # ----------------------------------------------------

        scheduled, unscheduled = schedule(
            companies,
            students,
            shortlists,
            rooms,
            panels,
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        write_cursor = conn.cursor()

        write_results(
            write_cursor,
            scheduled,
            unscheduled,
        )

        conn.commit()

        # ----------------------------------------------------
        # Report
        # ----------------------------------------------------

        print_metrics(
            scheduled,
            unscheduled,
            rooms,
            panels,
        )

        print()
        print(
            "Schedule written successfully "
            "to the `interviews` table."
        )

    except Exception as exc:

        conn.rollback()

        print()
        print(
            "Scheduling failed. "
            "Transaction rolled back."
        )

        print(
            f"Error: {exc}"
        )

        raise

    finally:

        if write_cursor is not None:
            write_cursor.close()

        read_cursor.close()
        conn.close()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    run()