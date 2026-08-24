# ============================================================
# replan_metrics.py — Replan Churn Metrics
# Mirai Labs Assignment A — Task 3
# ============================================================
#
# Usage:
#   python replan_metrics.py --save-baseline
#   python replan_metrics.py --compare
#   python replan_metrics.py --restore
# ============================================================

import argparse
from datetime import datetime
from collections import defaultdict
from db import get_connection

BASELINE_TABLE = "interviews_baseline"


def create_baseline_table_if_needed(cursor):
    """Create the baseline table if it doesn't exist."""
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BASELINE_TABLE} (
            id INT PRIMARY KEY,
            student_id INT,
            company_id INT,
            room_id INT,
            panel_id INT,
            start_time DATETIME,
            end_time DATETIME,
            status VARCHAR(20),
            reason VARCHAR(255),
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def save_baseline(cursor):
    """Copy the current scheduled interviews into the baseline table."""
    create_baseline_table_if_needed(cursor)

    # Clear previous baseline
    cursor.execute(f"DELETE FROM {BASELINE_TABLE}")

    # Copy all interviews (scheduled and unscheduled) to baseline
    cursor.execute(
        f"""
        INSERT INTO {BASELINE_TABLE}
        SELECT id, student_id, company_id, room_id, panel_id,
               start_time, end_time, status, reason, NOW()
        FROM interviews
        """
    )
    count = cursor.rowcount
    cursor.connection.commit()
    print(f"✅ Baseline saved: {count} interviews copied.")
    return count


def restore_baseline(cursor):
    """Restore the interviews table from the baseline."""
    # Ensure baseline exists
    cursor.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = '{BASELINE_TABLE}'
        """
    )
    if cursor.fetchone()["cnt"] == 0:
        print("❌ No baseline table found. Use --save-baseline first.")
        return

    # Clear current interviews
    cursor.execute("DELETE FROM interviews")

    # Insert from baseline
    cursor.execute(
        f"""
        INSERT INTO interviews
        SELECT id, student_id, company_id, room_id, panel_id,
               start_time, end_time, status, reason
        FROM {BASELINE_TABLE}
        """
    )
    count = cursor.rowcount
    cursor.connection.commit()
    print(f"✅ Restored: {count} interviews from baseline.")


def compute_metrics(cursor):
    """Compare current interviews against baseline and compute churn metrics."""
    # Ensure baseline exists
    cursor.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = '{BASELINE_TABLE}'
        """
    )
    if cursor.fetchone()["cnt"] == 0:
        print("❌ No baseline table found. Use --save-baseline first.")
        return None

    # Load baseline scheduled interviews
    cursor.execute(
        f"""
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time, status
        FROM {BASELINE_TABLE}
        WHERE status = 'scheduled'
        """
    )
    baseline_rows = cursor.fetchall()
    baseline_by_id = {row["id"]: row for row in baseline_rows}
    baseline_scheduled_count = len(baseline_rows)

    # Load current scheduled interviews
    cursor.execute(
        """
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time, status
        FROM interviews
        WHERE status = 'scheduled'
        """
    )
    current_scheduled = cursor.fetchall()
    current_by_id = {row["id"]: row for row in current_scheduled}

    # Load current cancelled interviews (those that were scheduled in baseline but now cancelled)
    cursor.execute(
        """
        SELECT id, student_id, room_id, panel_id,
               start_time, end_time, status, reason
        FROM interviews
        WHERE status = 'cancelled'
        """
    )
    current_cancelled = cursor.fetchall()
    cancelled_by_id = {row["id"]: row for row in current_cancelled}

    # Metrics containers
    unchanged = []
    moved = []
    cancelled = []
    newly_scheduled = []

    # 1. Check baseline interviews
    for iid, baseline in baseline_by_id.items():
        if iid in current_by_id:
            curr = current_by_id[iid]
            # Check if anything changed
            changed = (
                curr["room_id"] != baseline["room_id"] or
                curr["panel_id"] != baseline["panel_id"] or
                curr["start_time"] != baseline["start_time"] or
                curr["end_time"] != baseline["end_time"]
            )
            if changed:
                moved.append({
                    "id": iid,
                    "student_id": curr["student_id"],
                    "old_room": baseline["room_id"],
                    "new_room": curr["room_id"],
                    "old_panel": baseline["panel_id"],
                    "new_panel": curr["panel_id"],
                    "old_start": baseline["start_time"],
                    "new_start": curr["start_time"],
                    "old_end": baseline["end_time"],
                    "new_end": curr["end_time"],
                    "displacement": abs(
                        int((curr["start_time"] - baseline["start_time"]).total_seconds() // 60)
                    )
                })
            else:
                unchanged.append(iid)
        elif iid in cancelled_by_id:
            cancelled.append({
                "id": iid,
                "student_id": baseline["student_id"],
                "room_id": baseline["room_id"],
                "panel_id": baseline["panel_id"],
                "start_time": baseline["start_time"],
                "end_time": baseline["end_time"],
                "reason": cancelled_by_id[iid]["reason"]
            })
        else:
            # This interview disappeared (shouldn't happen normally)
            cancelled.append({
                "id": iid,
                "student_id": baseline["student_id"],
                "room_id": baseline["room_id"],
                "panel_id": baseline["panel_id"],
                "start_time": baseline["start_time"],
                "end_time": baseline["end_time"],
                "reason": "Missing from current schedule (unknown)"
            })

    # 2. Check for newly scheduled interviews (not in baseline)
    for iid, curr in current_by_id.items():
        if iid not in baseline_by_id:
            newly_scheduled.append(curr)

    # Compute summary
    total_baseline = baseline_scheduled_count
    unchanged_count = len(unchanged)
    moved_count = len(moved)
    cancelled_count = len(cancelled)
    newly_count = len(newly_scheduled)

    # Students affected
    affected_students = set()
    for m in moved:
        affected_students.add(m["student_id"])
    for c in cancelled:
        affected_students.add(c["student_id"])
    # Also add students from newly scheduled? Not needed.

    # Displacements
    displacements = [m["displacement"] for m in moved]
    avg_displacement = sum(displacements) / len(displacements) if displacements else 0
    max_displacement = max(displacements) if displacements else 0

    # Churn percentage = (moved + cancelled) / total_baseline * 100
    churn_pct = ((moved_count + cancelled_count) / total_baseline * 100) if total_baseline else 0

    metrics = {
        "baseline_scheduled": total_baseline,
        "unchanged": unchanged_count,
        "moved": moved_count,
        "cancelled": cancelled_count,
        "newly_scheduled": newly_count,
        "students_affected": len(affected_students),
        "avg_displacement_min": avg_displacement,
        "max_displacement_min": max_displacement,
        "churn_pct": churn_pct,
        "moved_details": moved,
        "cancelled_details": cancelled,
        "unchanged_ids": unchanged,
        "newly_details": newly_scheduled,
    }
    return metrics


def print_metrics(metrics):
    """Pretty‑print the metrics report."""
    if not metrics:
        return

    print("\n" + "=" * 80)
    print("REPLAN CHURN METRICS")
    print("=" * 80)

    print(f"Baseline scheduled interviews : {metrics['baseline_scheduled']}")
    print(f"Unchanged                    : {metrics['unchanged']}")
    print(f"Moved                        : {metrics['moved']}")
    print(f"Cancelled                    : {metrics['cancelled']}")
    print(f"Newly scheduled              : {metrics['newly_scheduled']}")
    print(f"Students affected            : {metrics['students_affected']}")
    print(f"Average displacement (min)   : {metrics['avg_displacement_min']:.1f}")
    print(f"Maximum displacement (min)   : {metrics['max_displacement_min']:.0f}")
    print(f"Churn percentage             : {metrics['churn_pct']:.1f}%")

    # Show moved interviews (top 10 by displacement)
    if metrics["moved_details"]:
        moved_sorted = sorted(metrics["moved_details"], key=lambda x: x["displacement"], reverse=True)
        print("\n" + "-" * 80)
        print("Top 10 moved interviews (by displacement):")
        for m in moved_sorted[:10]:
            old_time = f"{m['old_start']:%H:%M}-{m['old_end']:%H:%M}"
            new_time = f"{m['new_start']:%H:%M}-{m['new_end']:%H:%M}"
            print(
                f"  Intv {m['id']} | "
                f"OLD Rm {m['old_room']} Pan {m['old_panel']} {old_time} | "
                f"NEW Rm {m['new_room']} Pan {m['new_panel']} {new_time} | "
                f"shift {m['displacement']} min"
            )

    # Show cancelled interviews
    if metrics["cancelled_details"]:
        print("\n" + "-" * 80)
        print(f"Cancelled interviews ({len(metrics['cancelled_details'])}):")
        for c in metrics["cancelled_details"][:20]:
            time_str = f"{c['start_time']:%H:%M}-{c['end_time']:%H:%M}"
            print(
                f"  Intv {c['id']} | "
                f"Rm {c['room_id']} Pan {c['panel_id']} {time_str} | "
                f"reason: {c['reason']}"
            )
        if len(metrics["cancelled_details"]) > 20:
            print(f"  ... and {len(metrics['cancelled_details'])-20} more")

    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Replan churn metrics")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--save-baseline", action="store_true", help="Save current schedule as baseline")
    group.add_argument("--compare", action="store_true", help="Compare current schedule against baseline")
    group.add_argument("--restore", action="store_true", help="Restore baseline schedule to interviews")
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if args.save_baseline:
            save_baseline(cursor)
        elif args.compare:
            metrics = compute_metrics(cursor)
            if metrics:
                print_metrics(metrics)
        elif args.restore:
            restore_baseline(cursor)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()