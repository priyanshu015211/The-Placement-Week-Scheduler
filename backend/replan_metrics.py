# ============================================================
# replan_metrics.py — Replan Churn Metrics
# Mirai Labs Assignment A — Task 3
# ============================================================

import argparse

from db import get_connection


BASELINE_TABLE = "interviews_baseline"
ROOMS_BASELINE_TABLE = "rooms_baseline"
PANELS_BASELINE_TABLE = "panels_baseline"
STUDENTS_BASELINE_TABLE = "students_baseline"


def create_baseline_tables(cursor):
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

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {ROOMS_BASELINE_TABLE} (
            id INT PRIMARY KEY,
            status VARCHAR(20) NOT NULL
        )
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {PANELS_BASELINE_TABLE} (
            id INT PRIMARY KEY,
            status VARCHAR(20) NOT NULL
        )
        """
    )

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {STUDENTS_BASELINE_TABLE} (
            id INT PRIMARY KEY,
            status VARCHAR(20) NOT NULL
        )
        """
    )


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table_name,),
    )
    return cursor.fetchone()["cnt"] > 0


def save_baseline(cursor):
    create_baseline_tables(cursor)

    for table in (
        BASELINE_TABLE,
        ROOMS_BASELINE_TABLE,
        PANELS_BASELINE_TABLE,
        STUDENTS_BASELINE_TABLE,
    ):
        cursor.execute(f"DELETE FROM {table}")

    cursor.execute(
        f"""
        INSERT INTO {BASELINE_TABLE} (
            id, student_id, company_id, room_id, panel_id,
            start_time, end_time, status, reason, saved_at
        )
        SELECT
            id, student_id, company_id, room_id, panel_id,
            start_time, end_time, status, reason, NOW()
        FROM interviews
        """
    )
    interview_count = cursor.rowcount

    cursor.execute(
        f"""
        INSERT INTO {ROOMS_BASELINE_TABLE} (id, status)
        SELECT id, status
        FROM rooms
        """
    )

    cursor.execute(
        f"""
        INSERT INTO {PANELS_BASELINE_TABLE} (id, status)
        SELECT id, status
        FROM panels
        """
    )

    cursor.execute(
        f"""
        INSERT INTO {STUDENTS_BASELINE_TABLE} (id, status)
        SELECT id, status
        FROM students
        """
    )

    print(
        f"Baseline saved: {interview_count} interviews + "
        "resource/student state."
    )


def baseline_ready(cursor):
    if not all(
        table_exists(cursor, table)
        for table in (
            BASELINE_TABLE,
            ROOMS_BASELINE_TABLE,
            PANELS_BASELINE_TABLE,
            STUDENTS_BASELINE_TABLE,
        )
    ):
        return False

    cursor.execute(f"SELECT COUNT(*) AS cnt FROM {BASELINE_TABLE}")
    return cursor.fetchone()["cnt"] > 0


def restore_baseline(cursor):
    if not baseline_ready(cursor):
        raise RuntimeError(
            "No complete baseline found. Run --save-baseline first."
        )

    # replan_log has an FK to interviews.
    cursor.execute("DELETE FROM replan_log")
    cursor.execute("DELETE FROM interviews")

    cursor.execute(
        f"""
        INSERT INTO interviews (
            id, student_id, company_id, room_id, panel_id,
            start_time, end_time, status, reason
        )
        SELECT
            id, student_id, company_id, room_id, panel_id,
            start_time, end_time, status, reason
        FROM {BASELINE_TABLE}
        """
    )
    restored_interviews = cursor.rowcount

    cursor.execute(
        f"""
        UPDATE rooms r
        JOIN {ROOMS_BASELINE_TABLE} b ON b.id = r.id
        SET r.status = b.status
        """
    )

    cursor.execute(
        f"""
        UPDATE panels p
        JOIN {PANELS_BASELINE_TABLE} b ON b.id = p.id
        SET p.status = b.status
        """
    )

    cursor.execute(
        f"""
        UPDATE students s
        JOIN {STUDENTS_BASELINE_TABLE} b ON b.id = s.id
        SET s.status = b.status
        """
    )

    print(
        f"Restored: {restored_interviews} interviews + "
        "resource/student state."
    )


def compute_metrics(cursor):
    if not baseline_ready(cursor):
        raise RuntimeError(
            "No complete baseline found. Run --save-baseline first."
        )

    cursor.execute(
        f"""
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time
        FROM {BASELINE_TABLE}
        WHERE status = 'scheduled'
        """
    )
    baseline_rows = cursor.fetchall()
    baseline_by_id = {row["id"]: row for row in baseline_rows}

    cursor.execute(
        """
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time
        FROM interviews
        WHERE status = 'scheduled'
        """
    )
    current_rows = cursor.fetchall()
    current_by_id = {row["id"]: row for row in current_rows}

    cursor.execute(
        """
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time, reason
        FROM interviews
        WHERE status = 'cancelled'
        """
    )
    cancelled_rows = cursor.fetchall()
    cancelled_by_id = {row["id"]: row for row in cancelled_rows}

    unchanged = []
    moved = []
    cancelled = []
    newly_scheduled = []

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
                displacement = abs(
                    int(
                        (
                            new["start_time"] - old["start_time"]
                        ).total_seconds()
                        // 60
                    )
                )
                moved.append({
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
                })
            else:
                unchanged.append(iid)

        elif iid in cancelled_by_id:
            row = cancelled_by_id[iid]
            cancelled.append({
                "id": iid,
                "student_id": old["student_id"],
                "room_id": old["room_id"],
                "panel_id": old["panel_id"],
                "start_time": old["start_time"],
                "end_time": old["end_time"],
                "reason": row["reason"],
            })
        else:
            cancelled.append({
                "id": iid,
                "student_id": old["student_id"],
                "room_id": old["room_id"],
                "panel_id": old["panel_id"],
                "start_time": old["start_time"],
                "end_time": old["end_time"],
                "reason": "Missing from current schedule",
            })

    for iid, row in current_by_id.items():
        if iid not in baseline_by_id:
            newly_scheduled.append(row)

    affected_students = {
        row["student_id"] for row in moved + cancelled
    }
    displacements = [row["displacement"] for row in moved]
    baseline_count = len(baseline_by_id)

    return {
        "baseline_scheduled": baseline_count,
        "unchanged": len(unchanged),
        "moved": len(moved),
        "cancelled": len(cancelled),
        "newly_scheduled": len(newly_scheduled),
        "students_affected": len(affected_students),
        "average_displacement": (
            sum(displacements) / len(displacements)
            if displacements else 0
        ),
        "maximum_displacement": max(displacements) if displacements else 0,
        "churn": (
            (len(moved) + len(cancelled)) / baseline_count * 100
            if baseline_count else 0
        ),
        "moved_details": moved,
        "cancelled_details": cancelled,
    }


def print_metrics(metrics):
    print("\n" + "=" * 80)
    print("REPLAN CHURN METRICS")
    print("=" * 80)
    print(f"Baseline scheduled interviews : {metrics['baseline_scheduled']}")
    print(f"Unchanged                    : {metrics['unchanged']}")
    print(f"Moved                        : {metrics['moved']}")
    print(f"Cancelled                    : {metrics['cancelled']}")
    print(f"Newly scheduled              : {metrics['newly_scheduled']}")
    print(f"Students affected            : {metrics['students_affected']}")
    print(f"Average displacement (min)   : {metrics['average_displacement']:.1f}")
    print(f"Maximum displacement (min)   : {metrics['maximum_displacement']:.0f}")
    print(f"Churn percentage             : {metrics['churn']:.2f}%")

    if metrics["moved_details"]:
        print("\n" + "-" * 80)
        print("Largest interview movements:")
        for row in sorted(
            metrics["moved_details"],
            key=lambda item: item["displacement"],
            reverse=True,
        )[:10]:
            print(
                f"Intv {row['id']} | "
                f"{row['old_start']:%H:%M}-{row['old_end']:%H:%M} → "
                f"{row['new_start']:%H:%M}-{row['new_end']:%H:%M} | "
                f"{row['displacement']} min"
            )

    if metrics["cancelled_details"]:
        print("\n" + "-" * 80)
        print("Cancelled interviews:")
        for row in metrics["cancelled_details"][:20]:
            print(
                f"Intv {row['id']} | Student {row['student_id']} | "
                f"{row['reason']}"
            )
        if len(metrics["cancelled_details"]) > 20:
            print(
                f"... and {len(metrics['cancelled_details']) - 20} more"
            )

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Replan churn metrics")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--save-baseline", action="store_true")
    group.add_argument("--compare", action="store_true")
    group.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if args.save_baseline:
            save_baseline(cursor)
        elif args.compare:
            print_metrics(compute_metrics(cursor))
        elif args.restore:
            restore_baseline(cursor)

        conn.commit()

    except Exception as exc:
        conn.rollback()
        print(f"Error: {exc}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
