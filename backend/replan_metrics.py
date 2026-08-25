# ============================================================
# replan_metrics.py — Replan Churn Metrics
# Mirai Labs Assignment A — Task 3
# ============================================================

import argparse

from db import get_connection


BASELINE_TABLE = "interviews_baseline"


# ------------------------------------------------------------
# Baseline table
# ------------------------------------------------------------

def create_baseline_table_if_needed(cursor):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BASELINE_TABLE} (
            id INT PRIMARY KEY,
            student_id INT,
            company_id INT,
            room_id INT NULL,
            panel_id INT NULL,
            start_time DATETIME NULL,
            end_time DATETIME NULL,
            status VARCHAR(20),
            reason VARCHAR(255) NULL,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def baseline_exists(cursor):
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (BASELINE_TABLE,),
    )

    return cursor.fetchone()["cnt"] > 0


# ------------------------------------------------------------
# Save baseline
# ------------------------------------------------------------

def save_baseline(cursor):
    create_baseline_table_if_needed(cursor)

    cursor.execute(
        f"DELETE FROM {BASELINE_TABLE}"
    )

    cursor.execute(
        f"""
        INSERT INTO {BASELINE_TABLE} (
            id,
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            reason,
            saved_at
        )
        SELECT
            id,
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            reason,
            NOW()
        FROM interviews
        """
    )

    count = cursor.rowcount

    print(
        f"Baseline saved: {count} interviews copied."
    )


# ------------------------------------------------------------
# Restore baseline
# ------------------------------------------------------------

def restore_baseline(cursor):
    if not baseline_exists(cursor):
        raise RuntimeError(
            "No baseline found. Run --save-baseline first."
        )

    cursor.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM {BASELINE_TABLE}
        """
    )

    baseline_count = cursor.fetchone()["cnt"]

    if baseline_count == 0:
        raise RuntimeError(
            "Baseline table exists but is empty. "
            "Run --save-baseline again."
        )

    # replan_log references interviews, so it must be cleared first.
    cursor.execute(
        "DELETE FROM replan_log"
    )

    # Clear current schedule.
    cursor.execute(
        "DELETE FROM interviews"
    )

    # Restore exact original IDs and schedule state.
    cursor.execute(
        f"""
        INSERT INTO interviews (
            id,
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            reason
        )
        SELECT
            id,
            student_id,
            company_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            status,
            reason
        FROM {BASELINE_TABLE}
        """
    )

    print(
        f"Restored: {cursor.rowcount} interviews."
    )


# ------------------------------------------------------------
# Metrics
# ------------------------------------------------------------

def compute_metrics(cursor):
    if not baseline_exists(cursor):
        raise RuntimeError(
            "No baseline found. Run --save-baseline first."
        )

    # Baseline scheduled interviews.
    cursor.execute(
        f"""
        SELECT
            id,
            student_id,
            room_id,
            panel_id,
            start_time,
            end_time
        FROM {BASELINE_TABLE}
        WHERE status = 'scheduled'
        """
    )

    baseline_rows = cursor.fetchall()

    baseline_by_id = {
        row["id"]: row
        for row in baseline_rows
    }

    # Current scheduled interviews.
    cursor.execute(
        """
        SELECT
            id,
            student_id,
            room_id,
            panel_id,
            start_time,
            end_time
        FROM interviews
        WHERE status = 'scheduled'
        """
    )

    current_rows = cursor.fetchall()

    current_by_id = {
        row["id"]: row
        for row in current_rows
    }

    # Current cancelled interviews.
    cursor.execute(
        """
        SELECT
            id,
            student_id,
            room_id,
            panel_id,
            start_time,
            end_time,
            reason
        FROM interviews
        WHERE status = 'cancelled'
        """
    )

    cancelled_rows = cursor.fetchall()

    cancelled_by_id = {
        row["id"]: row
        for row in cancelled_rows
    }

    unchanged = []
    moved = []
    cancelled = []
    newly_scheduled = []

    # Compare baseline scheduled rows with current state.
    for iid, old in baseline_by_id.items():

        if iid in current_by_id:

            new = current_by_id[iid]

            changed = (
                new["room_id"] != old["room_id"]
                or new["panel_id"] != old["panel_id"]
                or new["start_time"] != old["start_time"]
                or new["end_time"] != old["end_time"]
            )

            if changed:
                displacement = 0

                if (
                    new["start_time"] is not None
                    and old["start_time"] is not None
                ):
                    displacement = abs(
                        int(
                            (
                                new["start_time"]
                                - old["start_time"]
                            ).total_seconds()
                            // 60
                        )
                    )

                moved.append(
                    {
                        "id": iid,
                        "student_id": new["student_id"],
                        "old_room": old["room_id"],
                        "new_room": new["room_id"],
                        "old_panel": old["panel_id"],
                        "new_panel": new["panel_id"],
                        "old_start": old["start_time"],
                        "new_start": new["start_time"],
                        "old_end": old["end_time"],
                        "new_end": new["end_time"],
                        "displacement": displacement,
                    }
                )

            else:
                unchanged.append(iid)

        elif iid in cancelled_by_id:

            row = cancelled_by_id[iid]

            cancelled.append(
                {
                    "id": iid,
                    "student_id": old["student_id"],
                    "room_id": old["room_id"],
                    "panel_id": old["panel_id"],
                    "start_time": old["start_time"],
                    "end_time": old["end_time"],
                    "reason": row["reason"],
                }
            )

        else:

            # Baseline interview disappeared without a current row.
            cancelled.append(
                {
                    "id": iid,
                    "student_id": old["student_id"],
                    "room_id": old["room_id"],
                    "panel_id": old["panel_id"],
                    "start_time": old["start_time"],
                    "end_time": old["end_time"],
                    "reason": "Missing from current schedule",
                }
            )

    # Current scheduled rows that did not exist in baseline.
    for iid, row in current_by_id.items():
        if iid not in baseline_by_id:
            newly_scheduled.append(row)

    affected_students = set()

    for row in moved:
        affected_students.add(row["student_id"])

    for row in cancelled:
        affected_students.add(row["student_id"])

    displacements = [
        row["displacement"]
        for row in moved
    ]

    average_displacement = (
        sum(displacements) / len(displacements)
        if displacements
        else 0
    )

    maximum_displacement = (
        max(displacements)
        if displacements
        else 0
    )

    baseline_count = len(
        baseline_by_id
    )

    churn = (
        (
            len(moved)
            + len(cancelled)
        )
        / baseline_count
        * 100
        if baseline_count
        else 0
    )

    return {
        "baseline_scheduled": baseline_count,
        "unchanged": len(unchanged),
        "moved": len(moved),
        "cancelled": len(cancelled),
        "newly_scheduled": len(newly_scheduled),
        "students_affected": len(affected_students),
        "average_displacement": average_displacement,
        "maximum_displacement": maximum_displacement,
        "churn": churn,
        "moved_details": moved,
        "cancelled_details": cancelled,
    }


# ------------------------------------------------------------
# Print report
# ------------------------------------------------------------

def print_metrics(metrics):
    print("\n" + "=" * 80)
    print("REPLAN CHURN METRICS")
    print("=" * 80)

    print(
        f"Baseline scheduled interviews : "
        f"{metrics['baseline_scheduled']}"
    )

    print(
        f"Unchanged                    : "
        f"{metrics['unchanged']}"
    )

    print(
        f"Moved                        : "
        f"{metrics['moved']}"
    )

    print(
        f"Cancelled                    : "
        f"{metrics['cancelled']}"
    )

    print(
        f"Newly scheduled              : "
        f"{metrics['newly_scheduled']}"
    )

    print(
        f"Students affected            : "
        f"{metrics['students_affected']}"
    )

    print(
        f"Average displacement (min)   : "
        f"{metrics['average_displacement']:.1f}"
    )

    print(
        f"Maximum displacement (min)   : "
        f"{metrics['maximum_displacement']:.0f}"
    )

    print(
        f"Churn percentage             : "
        f"{metrics['churn']:.2f}%"
    )

    if metrics["moved_details"]:

        print("\n" + "-" * 80)
        print("Largest interview movements:")
        print("-" * 80)

        moved = sorted(
            metrics["moved_details"],
            key=lambda x: x["displacement"],
            reverse=True,
        )

        for row in moved[:10]:

            old_time = (
                f"{row['old_start']:%H:%M}-"
                f"{row['old_end']:%H:%M}"
            )

            new_time = (
                f"{row['new_start']:%H:%M}-"
                f"{row['new_end']:%H:%M}"
            )

            print(
                f"Intv {row['id']} | "
                f"{old_time} → {new_time} | "
                f"{row['displacement']} min"
            )

    if metrics["cancelled_details"]:

        print("\n" + "-" * 80)
        print("Cancelled interviews:")
        print("-" * 80)

        for row in metrics["cancelled_details"][:20]:

            print(
                f"Intv {row['id']} | "
                f"Student {row['student_id']} | "
                f"{row['reason']}"
            )

        if len(metrics["cancelled_details"]) > 20:
            print(
                f"... and "
                f"{len(metrics['cancelled_details']) - 20} more"
            )

    print("=" * 80)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Replan churn metrics"
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--save-baseline",
        action="store_true",
    )

    group.add_argument(
        "--compare",
        action="store_true",
    )

    group.add_argument(
        "--restore",
        action="store_true",
    )

    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor(
        dictionary=True
    )

    try:

        if args.save_baseline:

            save_baseline(cursor)

        elif args.compare:

            metrics = compute_metrics(
                cursor
            )

            print_metrics(metrics)

        elif args.restore:

            restore_baseline(cursor)

        conn.commit()

    except Exception as exc:

        conn.rollback()

        print(
            f"Error: {exc}"
        )

        raise

    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()