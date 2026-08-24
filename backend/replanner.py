# ============================================================
# Placement Week Scheduler — Real-Time Replanner
# Mirai Labs Assignment A — Task 3
# ============================================================

import argparse
from datetime import timedelta

from db import get_connection
from scheduler import generate_slots_for_company


MAX_REPLAN_SHIFT_MINUTES = 120


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def exclusion_sql(ids):
    ids = list(ids or [])

    if not ids:
        return "", []

    placeholders = ",".join(["%s"] * len(ids))

    return (
        f" AND id NOT IN ({placeholders}) ",
        ids,
    )


def log_replan(
    cursor,
    interview_id,
    old_room,
    old_panel,
    old_start,
    old_end,
    new_room,
    new_panel,
    new_start,
    new_end,
    reason,
):
    cursor.execute(
        """
        INSERT INTO replan_log (
            interview_id,
            old_room_id,
            old_panel_id,
            old_start_time,
            old_end_time,
            new_room_id,
            new_panel_id,
            new_start_time,
            new_end_time,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            interview_id,
            old_room,
            old_panel,
            old_start,
            old_end,
            new_room,
            new_panel,
            new_start,
            new_end,
            reason,
        ),
    )


def log_disruption(
    cursor,
    disruption_type,
    company_id=None,
    panel_id=None,
    student_id=None,
    room_id=None,
    delay_minutes=None,
    reason=None,
):
    cursor.execute(
        """
        INSERT INTO disruptions (
            type,
            company_id,
            panel_id,
            student_id,
            room_id,
            delay_minutes,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            disruption_type,
            company_id,
            panel_id,
            student_id,
            room_id,
            delay_minutes,
            reason,
        ),
    )


# ------------------------------------------------------------
# Resource checks
# ------------------------------------------------------------

def free_room(
    cursor,
    start,
    end,
    excluded_ids,
    banned_room=None,
):
    ex_sql, ex_params = exclusion_sql(
        excluded_ids
    )

    query = f"""
        SELECT id
        FROM rooms
        WHERE id != COALESCE(%s, -1)
          AND id NOT IN (
              SELECT room_id
              FROM interviews
              WHERE status = 'scheduled'
                AND start_time < %s
                AND end_time > %s
                {ex_sql}
          )
        ORDER BY id
        LIMIT 1
    """

    cursor.execute(
        query,
        [
            banned_room,
            end,
            start,
            *ex_params,
        ],
    )

    return cursor.fetchone()


def free_panel(
    cursor,
    company_id,
    start,
    end,
    excluded_ids,
    banned_panel=None,
):
    ex_sql, ex_params = exclusion_sql(
        excluded_ids
    )

    query = f"""
        SELECT id
        FROM panels
        WHERE company_id = %s
          AND status = 'available'
          AND id != COALESCE(%s, -1)
          AND id NOT IN (
              SELECT panel_id
              FROM interviews
              WHERE status = 'scheduled'
                AND start_time < %s
                AND end_time > %s
                {ex_sql}
          )
        ORDER BY id
        LIMIT 1
    """

    cursor.execute(
        query,
        [
            company_id,
            banned_panel,
            end,
            start,
            *ex_params,
        ],
    )

    return cursor.fetchone()


def student_conflict(
    cursor,
    student_id,
    start,
    end,
    excluded_ids,
):
    ex_sql, ex_params = exclusion_sql(
        excluded_ids
    )

    cursor.execute(
        f"""
        SELECT id
        FROM interviews
        WHERE student_id = %s
          AND status = 'scheduled'
          AND start_time < %s
          AND end_time > %s
          {ex_sql}
        LIMIT 1
        """,
        [
            student_id,
            end,
            start,
            *ex_params,
        ],
    )

    return cursor.fetchone() is not None


def panel_conflict(
    cursor,
    panel_id,
    start,
    end,
    excluded_ids,
):
    ex_sql, ex_params = exclusion_sql(
        excluded_ids
    )

    cursor.execute(
        f"""
        SELECT id
        FROM interviews
        WHERE panel_id = %s
          AND status = 'scheduled'
          AND start_time < %s
          AND end_time > %s
          {ex_sql}
        LIMIT 1
        """,
        [
            panel_id,
            end,
            start,
            *ex_params,
        ],
    )

    return cursor.fetchone() is not None


# ------------------------------------------------------------
# Company slots
# ------------------------------------------------------------

def get_company_slots(cursor, company_id):
    cursor.execute(
        """
        SELECT *
        FROM companies
        WHERE id = %s
        """,
        (company_id,),
    )

    company = cursor.fetchone()

    if not company:
        raise ValueError(
            f"Company {company_id} not found"
        )

    return generate_slots_for_company(company)


# ------------------------------------------------------------
# Find replacement
# ------------------------------------------------------------

def find_replacement(
    cursor,
    row,
    affected_ids,
    earliest_start=None,
    banned_room=None,
    banned_panel=None,
):
    company_id = row["company_id"]
    student_id = row["student_id"]

    slots = get_company_slots(
        cursor,
        company_id,
    )

    old_start = row["start_time"]
    old_room = row["room_id"]
    old_panel = row["panel_id"]

    candidates = []

    for start, end in slots:

        if earliest_start is not None:
            if start < earliest_start:
                continue

        displacement = abs(
            int(
                (
                    start - old_start
                ).total_seconds() // 60
            )
        )

        # Critical fairness/minimal-displacement rule.
        if MAX_REPLAN_SHIFT_MINUTES is not None and displacement > MAX_REPLAN_SHIFT_MINUTES:
            continue

        if student_conflict(
            cursor,
            student_id,
            start,
            end,
            affected_ids,
        ):
            continue

        # ----------------------------------------------------
        # Panel
        # ----------------------------------------------------

        panel = None

        if (
            banned_panel is None
            and old_panel is not None
            and not panel_conflict(
                cursor,
                old_panel,
                start,
                end,
                affected_ids,
            )
        ):
            panel = {
                "id": old_panel
            }
        else:
            panel = free_panel(
                cursor,
                company_id,
                start,
                end,
                affected_ids,
                banned_panel,
            )

        if not panel:
            continue

        # ----------------------------------------------------
        # Room
        # ----------------------------------------------------

        room = None

        if banned_room is None and old_room is not None:

            ex_sql, ex_params = exclusion_sql(
                affected_ids
            )

            cursor.execute(
                f"""
                SELECT id
                FROM rooms
                WHERE id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM interviews
                      WHERE room_id = %s
                        AND status = 'scheduled'
                        AND start_time < %s
                        AND end_time > %s
                        {ex_sql}
                  )
                """,
                [
                    old_room,
                    old_room,
                    end,
                    start,
                    *ex_params,
                ],
            )

            room = cursor.fetchone()

        if not room:
            room = free_room(
                cursor,
                start,
                end,
                affected_ids,
                banned_room,
            )

        if not room:
            continue

        candidates.append(
            {
                "start": start,
                "end": end,
                "room_id": room["id"],
                "panel_id": panel["id"],
                "displacement": displacement,
            }
        )

    candidates.sort(
        key=lambda c: (
            c["displacement"],
            c["start"],
            c["room_id"],
            c["panel_id"],
        )
    )

    return (
        candidates[0]
        if candidates
        else None
    )


# ------------------------------------------------------------
# Cooperative batch reassignment
# ------------------------------------------------------------

def batch_reassign(
    cursor,
    affected,
    banned_room=None,
    banned_panel=None,
    earliest_times=None,
):
    if not affected:
        return {}

    affected_ids = {
        row["id"]
        for row in affected
    }

    affected_by_id = {
        row["id"]: row
        for row in affected
    }

    assigned = {}

    # Keep deterministic chronological order.
    ordered = sorted(
        affected,
        key=lambda r: (
            r["start_time"],
            r["id"],
        ),
    )

    for row in ordered:

        earliest = None

        if earliest_times:
            earliest = earliest_times.get(
                row["id"]
            )

        candidate = find_replacement(
            cursor,
            row,
            affected_ids,
            earliest_start=earliest,
            banned_room=banned_room,
            banned_panel=banned_panel,
        )

        if not candidate:
            continue

        conflict = False

        for other_id, other in assigned.items():

            # Resource conflicts inside the new batch.
            if (
                candidate["room_id"]
                == other["room_id"]
                and overlaps(
                    candidate["start"],
                    candidate["end"],
                    other["start"],
                    other["end"],
                )
            ):
                conflict = True
                break

            if (
                candidate["panel_id"]
                == other["panel_id"]
                and overlaps(
                    candidate["start"],
                    candidate["end"],
                    other["start"],
                    other["end"],
                )
            ):
                conflict = True
                break

            # Student conflicts inside the new batch.
            other_row = affected_by_id[
                other_id
            ]

            if (
                row["student_id"]
                == other_row["student_id"]
                and overlaps(
                    candidate["start"],
                    candidate["end"],
                    other["start"],
                    other["end"],
                )
            ):
                conflict = True
                break

        if not conflict:
            assigned[row["id"]] = candidate

    return assigned


# ------------------------------------------------------------
# Student withdrawal
# ------------------------------------------------------------

def handle_withdrawal(
    cursor,
    student_id,
):
    print(
        f"\n[DISRUPTION] Student {student_id} withdrawal"
    )

    cursor.execute(
        """
        SELECT *
        FROM interviews
        WHERE student_id = %s
          AND status = 'scheduled'
        """,
        (student_id,),
    )

    affected = cursor.fetchall()

    cursor.execute(
        """
        UPDATE students
        SET status = 'withdrawn'
        WHERE id = %s
        """,
        (student_id,),
    )

    log_disruption(
        cursor,
        "student_withdrawal",
        student_id=student_id,
        reason="Student withdrew",
    )

    for row in affected:

        cursor.execute(
            """
            UPDATE interviews
            SET status = 'cancelled',
                reason = 'Student withdrew'
            WHERE id = %s
            """,
            (row["id"],),
        )

        log_replan(
            cursor,
            row["id"],
            row["room_id"],
            row["panel_id"],
            row["start_time"],
            row["end_time"],
            None,
            None,
            None,
            None,
            "Student withdrew",
        )

    print(
        f"-> Cancelled {len(affected)} interviews"
    )


# ------------------------------------------------------------
# Room unavailable
# ------------------------------------------------------------

def handle_room_offline(
    cursor,
    room_id,
):
    print(
        f"\n[DISRUPTION] Room {room_id} offline"
    )

    cursor.execute(
        """
        SELECT *
        FROM interviews
        WHERE room_id = %s
          AND status = 'scheduled'
        ORDER BY start_time, id
        """,
        (room_id,),
    )

    affected = cursor.fetchall()

    log_disruption(
        cursor,
        "room_unavailable",
        room_id=room_id,
        reason=f"Room {room_id} offline",
    )

    assignment = batch_reassign(
        cursor,
        affected,
        banned_room=room_id,
    )

    repaired = 0
    cancelled = 0

    for row in affected:

        iid = row["id"]

        if iid in assignment:

            new = assignment[iid]

            cursor.execute(
                """
                UPDATE interviews
                SET start_time=%s,
                    end_time=%s,
                    room_id=%s,
                    panel_id=%s
                WHERE id=%s
                """,
                (
                    new["start"],
                    new["end"],
                    new["room_id"],
                    new["panel_id"],
                    iid,
                ),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                new["room_id"],
                new["panel_id"],
                new["start"],
                new["end"],
                (
                    f"Room {room_id} offline; "
                    f"shifted {new['displacement']} min"
                ),
            )

            repaired += 1

        else:

            cursor.execute(
                """
                UPDATE interviews
                SET status='cancelled',
                    reason='Room unavailable'
                WHERE id=%s
                """,
                (iid,),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                None,
                None,
                None,
                None,
                (
                    f"Room {room_id} offline; "
                    "no feasible replacement within "
                    f"{MAX_REPLAN_SHIFT_MINUTES} min"
                ),
            )

            cancelled += 1

    print(
        f"-> Affected: {len(affected)} | "
        f"Repaired: {repaired} | "
        f"Cancelled: {cancelled}"
    )


# ------------------------------------------------------------
# Panel dropped
# ------------------------------------------------------------

def handle_panel_drop(
    cursor,
    panel_id,
):
    print(
        f"\n[DISRUPTION] Panel {panel_id} dropped"
    )

    cursor.execute(
        """
        SELECT *
        FROM interviews
        WHERE panel_id = %s
          AND status = 'scheduled'
        ORDER BY start_time, id
        """,
        (panel_id,),
    )

    affected = cursor.fetchall()

    log_disruption(
        cursor,
        "panel_unavailable",
        panel_id=panel_id,
        reason=f"Panel {panel_id} dropped",
    )

    assignment = batch_reassign(
        cursor,
        affected,
        banned_panel=panel_id,
    )

    repaired = 0
    cancelled = 0

    for row in affected:

        iid = row["id"]

        if iid in assignment:

            new = assignment[iid]

            cursor.execute(
                """
                UPDATE interviews
                SET start_time=%s,
                    end_time=%s,
                    room_id=%s,
                    panel_id=%s
                WHERE id=%s
                """,
                (
                    new["start"],
                    new["end"],
                    new["room_id"],
                    new["panel_id"],
                    iid,
                ),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                new["room_id"],
                new["panel_id"],
                new["start"],
                new["end"],
                (
                    f"Panel {panel_id} dropped; "
                    f"shifted {new['displacement']} min"
                ),
            )

            repaired += 1

        else:

            cursor.execute(
                """
                UPDATE interviews
                SET status='cancelled',
                    reason='Panel dropped'
                WHERE id=%s
                """,
                (iid,),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                None,
                None,
                None,
                None,
                (
                    f"Panel {panel_id} dropped; "
                    "no feasible replacement within "
                    f"{MAX_REPLAN_SHIFT_MINUTES} min"
                ),
            )

            cancelled += 1

    print(
        f"-> Affected: {len(affected)} | "
        f"Repaired: {repaired} | "
        f"Cancelled: {cancelled}"
    )


# ------------------------------------------------------------
# Company delay
# ------------------------------------------------------------

def handle_company_delay(
    cursor,
    company_id,
    delay_minutes,
):
    print(
        f"\n[DISRUPTION] Company {company_id} "
        f"delayed by {delay_minutes} min"
    )

    cursor.execute(
        """
        SELECT *
        FROM interviews
        WHERE company_id = %s
          AND status = 'scheduled'
        ORDER BY start_time, id
        """,
        (company_id,),
    )

    affected = cursor.fetchall()

    log_disruption(
        cursor,
        "company_delay",
        company_id=company_id,
        delay_minutes=delay_minutes,
        reason=(
            f"Company delayed by "
            f"{delay_minutes} minutes"
        ),
    )

    delay = timedelta(
        minutes=delay_minutes
    )

    earliest_times = {
        row["id"]:
            row["start_time"] + delay
        for row in affected
    }

    assignment = batch_reassign(
        cursor,
        affected,
        earliest_times=earliest_times,
    )

    repaired = 0
    cancelled = 0

    for row in affected:

        iid = row["id"]

        if iid in assignment:

            new = assignment[iid]

            cursor.execute(
                """
                UPDATE interviews
                SET start_time=%s,
                    end_time=%s,
                    room_id=%s,
                    panel_id=%s
                WHERE id=%s
                """,
                (
                    new["start"],
                    new["end"],
                    new["room_id"],
                    new["panel_id"],
                    iid,
                ),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                new["room_id"],
                new["panel_id"],
                new["start"],
                new["end"],
                (
                    f"Company delay {delay_minutes} min; "
                    f"actual shift {new['displacement']} min"
                ),
            )

            repaired += 1

        else:

            cursor.execute(
                """
                UPDATE interviews
                SET status='cancelled',
                    reason='No feasible slot after company delay'
                WHERE id=%s
                """,
                (iid,),
            )

            log_replan(
                cursor,
                iid,
                row["room_id"],
                row["panel_id"],
                row["start_time"],
                row["end_time"],
                None,
                None,
                None,
                None,
                (
                    "No feasible slot after company "
                    f"delay within {MAX_REPLAN_SHIFT_MINUTES} "
                    "min displacement"
                ),
            )

            cancelled += 1

    print(
        f"-> Affected: {len(affected)} | "
        f"Repaired: {repaired} | "
        f"Cancelled: {cancelled}"
    )


# ------------------------------------------------------------
# View log
# ------------------------------------------------------------

def view_log(cursor):
    print("\n" + "=" * 100)
    print("REPLAN LOG")
    print("=" * 100)

    cursor.execute(
        """
        SELECT *
        FROM replan_log
        ORDER BY logged_at, id
        """
    )

    rows = cursor.fetchall()

    if not rows:
        print("No disruptions logged.")
        return

    for row in rows:

        old_time = (
            f"{row['old_start_time']:%H:%M}-"
            f"{row['old_end_time']:%H:%M}"
        )

        if row["new_start_time"]:
            new_time = (
                f"{row['new_start_time']:%H:%M}-"
                f"{row['new_end_time']:%H:%M}"
            )
        else:
            new_time = "CANCELLED"

        old_room = row["old_room_id"] or "-"
        old_panel = row["old_panel_id"] or "-"
        new_room = row["new_room_id"] or "-"
        new_panel = row["new_panel_id"] or "-"

        print(
            f"Intv {row['interview_id']} | "
            f"OLD Rm {old_room} "
            f"Pan {old_panel} "
            f"{old_time} | "
            f"NEW Rm {new_room} "
            f"Pan {new_panel} "
            f"{new_time} | "
            f"{row['reason']}"
        )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--withdraw",
        type=int,
    )

    parser.add_argument(
        "--room-offline",
        type=int,
    )

    parser.add_argument(
        "--panel-dropped",
        type=int,
    )

    parser.add_argument(
        "--delay-company",
        nargs=2,
        type=int,
        metavar=("COMPANY_ID", "MINUTES"),
    )

    parser.add_argument(
        "--view-log",
        action="store_true",
    )

    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor(
        dictionary=True
    )

    try:

        changed = False

        if args.withdraw is not None:
            handle_withdrawal(
                cursor,
                args.withdraw,
            )
            changed = True

        if args.room_offline is not None:
            handle_room_offline(
                cursor,
                args.room_offline,
            )
            changed = True

        if args.panel_dropped is not None:
            handle_panel_drop(
                cursor,
                args.panel_dropped,
            )
            changed = True

        if args.delay_company is not None:

            company_id, delay_minutes = (
                args.delay_company
            )

            if delay_minutes < 0:
                raise ValueError(
                    "Delay must be non-negative."
                )

            handle_company_delay(
                cursor,
                company_id,
                delay_minutes,
            )

            changed = True

        if changed:
            conn.commit()
            print(
                "\nChanges committed to database."
            )

        if args.view_log or not changed:
            view_log(cursor)

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()