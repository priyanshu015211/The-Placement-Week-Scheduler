import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import get_connection
from replan_metrics import baseline_ready, restore_baseline as restore_saved_baseline
from replanner import (
    handle_company_delay,
    handle_panel_drop,
    handle_room_offline,
    handle_withdrawal,
)

app = FastAPI(
    title="Placement Week Scheduler API",
    version="1.1.0",
)

# Comma-separated list of allowed origins, e.g.
# "https://your-frontend.vercel.app,http://localhost:5173"
# Set ALLOWED_ORIGINS in the backend's environment variables.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def fetch_one(cursor, query, params=()):
    cursor.execute(query, params)
    return cursor.fetchone()


def conflict_counts(cursor):
    queries = {
        "student_conflicts": """
            SELECT COUNT(*) AS count
            FROM interviews a
            JOIN interviews b
              ON a.id < b.id
             AND a.student_id = b.student_id
             AND a.status = 'scheduled'
             AND b.status = 'scheduled'
             AND a.start_time < b.end_time
             AND b.start_time < a.end_time
        """,
        "room_conflicts": """
            SELECT COUNT(*) AS count
            FROM interviews a
            JOIN interviews b
              ON a.id < b.id
             AND a.room_id = b.room_id
             AND a.status = 'scheduled'
             AND b.status = 'scheduled'
             AND a.start_time < b.end_time
             AND b.start_time < a.end_time
        """,
        "panel_conflicts": """
            SELECT COUNT(*) AS count
            FROM interviews a
            JOIN interviews b
              ON a.id < b.id
             AND a.panel_id = b.panel_id
             AND a.status = 'scheduled'
             AND b.status = 'scheduled'
             AND a.start_time < b.end_time
             AND b.start_time < a.end_time
        """,
    }

    result = {}
    for key, query in queries.items():
        result[key] = fetch_one(cursor, query)["count"]

    return result


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        scheduled = fetch_one(
            cursor,
            """
            SELECT COUNT(*) AS count
            FROM interviews
            WHERE status = 'scheduled'
            """,
        )["count"]

        students_served = fetch_one(
            cursor,
            """
            SELECT COUNT(DISTINCT student_id) AS count
            FROM interviews
            WHERE status = 'scheduled'
            """,
        )["count"]

        companies = fetch_one(
            cursor,
            "SELECT COUNT(*) AS count FROM companies",
        )["count"]

        room_state = fetch_one(
            cursor,
            """
            SELECT
                COUNT(*) AS total,
                SUM(status = 'available') AS operational,
                SUM(status = 'offline') AS offline
            FROM rooms
            """,
        )

        panel_state = fetch_one(
            cursor,
            """
            SELECT
                COUNT(*) AS total,
                SUM(status = 'available') AS available,
                SUM(status <> 'available') AS unavailable
            FROM panels
            """,
        )

        conflicts = conflict_counts(cursor)

        return {
            "scheduled": scheduled,
            "students_served": students_served,
            "companies": companies,
            "rooms_total": room_state["total"],
            "rooms_operational": room_state["operational"] or 0,
            "rooms_offline": room_state["offline"] or 0,
            "panels_total": panel_state["total"],
            "panels_available": panel_state["available"] or 0,
            "panels_unavailable": panel_state["unavailable"] or 0,
            **conflicts,
            "hard_conflicts": sum(conflicts.values()),
        }

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Live interviews
# ---------------------------------------------------------

@app.get("/api/interviews")
def interviews():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                i.id,
                i.student_id,
                s.name AS student_name,
                i.company_id,
                c.name AS company_name,
                i.room_id,
                r.name AS room_name,
                r.status AS room_status,
                i.panel_id,
                p.status AS panel_status,
                i.start_time,
                i.end_time,
                i.status,
                i.reason
            FROM interviews i
            JOIN students s
              ON s.id = i.student_id
            JOIN companies c
              ON c.id = i.company_id
            LEFT JOIN rooms r
              ON r.id = i.room_id
            LEFT JOIN panels p
              ON p.id = i.panel_id
            WHERE i.start_time IS NOT NULL
               OR i.status = 'cancelled'
            ORDER BY i.start_time, i.id
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Rooms
# ---------------------------------------------------------

@app.get("/api/rooms")
def rooms():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                r.id,
                r.name,
                r.capacity,
                r.status,
                COUNT(i.id) AS scheduled_interviews
            FROM rooms r
            LEFT JOIN interviews i
              ON i.room_id = r.id
             AND i.status = 'scheduled'
            GROUP BY r.id, r.name, r.capacity, r.status
            ORDER BY r.id
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Panels
# ---------------------------------------------------------

@app.get("/api/panels")
def panels():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.id,
                p.company_id,
                c.name AS company_name,
                p.panel_number,
                p.status,
                COUNT(i.id) AS scheduled_interviews
            FROM panels p
            JOIN companies c
              ON c.id = p.company_id
            LEFT JOIN interviews i
              ON i.panel_id = p.id
             AND i.status = 'scheduled'
            GROUP BY
                p.id,
                p.company_id,
                c.name,
                p.panel_number,
                p.status
            ORDER BY p.company_id, p.panel_number
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Students
# ---------------------------------------------------------

@app.get("/api/students")
def students():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                s.id,
                s.name,
                s.cgpa,
                s.branch,
                s.status,
                COUNT(DISTINCT CASE
                    WHEN i.status = 'scheduled' THEN i.id
                END) AS scheduled_interviews,
                COUNT(DISTINCT sl.company_id) AS shortlisted_companies
            FROM students s
            LEFT JOIN interviews i
              ON i.student_id = s.id
            LEFT JOIN shortlists sl
              ON sl.student_id = s.id
            GROUP BY
                s.id,
                s.name,
                s.cgpa,
                s.branch,
                s.status
            ORDER BY s.id
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Companies
# ---------------------------------------------------------

@app.get("/api/companies")
def companies():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                c.priority_tier,
                c.placement_day,
                c.panels,
                c.interview_duration_min,
                c.arrival_time,
                COUNT(DISTINCT sl.student_id) AS shortlisted,
                COUNT(DISTINCT CASE
                    WHEN i.status = 'scheduled' THEN i.id
                END) AS scheduled,
                COUNT(DISTINCT p.id) AS actual_panels,
                COUNT(DISTINCT CASE
                    WHEN p.status = 'available' THEN p.id
                END) AS available_panels
            FROM companies c
            LEFT JOIN shortlists sl
              ON sl.company_id = c.id
            LEFT JOIN interviews i
              ON i.company_id = c.id
            LEFT JOIN panels p
              ON p.company_id = c.id
            GROUP BY
                c.id,
                c.name,
                c.priority_tier,
                c.placement_day,
                c.panels,
                c.interview_duration_min,
                c.arrival_time
            ORDER BY c.placement_day, c.priority_tier, c.id
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

@app.get("/api/metrics")
def metrics():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        totals = fetch_one(
            cursor,
            """
            SELECT
                COUNT(*) AS total,
                SUM(status = 'scheduled') AS scheduled,
                SUM(status = 'unscheduled') AS unscheduled,
                SUM(status = 'cancelled') AS cancelled
            FROM interviews
            """,
        )

        fairness = fetch_one(
            cursor,
            """
            SELECT
                MAX(x.cnt) AS max_interviews,
                AVG(x.cnt) AS avg_interviews
            FROM (
                SELECT student_id, COUNT(*) AS cnt
                FROM interviews
                WHERE status = 'scheduled'
                GROUP BY student_id
            ) x
            """,
        )

        conflicts = conflict_counts(cursor)

        scheduled = totals["scheduled"] or 0
        total = totals["total"] or 0

        # Match evaluator.py definitions exactly:
        # - rooms: 8 hours/day across 4 placement days per room
        # - panels: 8 hours on their placement day per panel
        # - waiting: gaps between consecutive same-day interviews per student
        room_used = fetch_one(
            cursor,
            """
            SELECT COALESCE(
                SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 0
            ) AS used_minutes
            FROM interviews
            WHERE status = 'scheduled'
              AND room_id IS NOT NULL
              AND start_time IS NOT NULL
              AND end_time IS NOT NULL
            """,
        )["used_minutes"] or 0

        room_count = fetch_one(
            cursor,
            "SELECT COUNT(*) AS count FROM rooms",
        )["count"] or 0

        room_available = room_count * 4 * 8 * 60
        room_utilization = (
            float(room_used) / room_available * 100
            if room_available else 0.0
        )

        panel_used = fetch_one(
            cursor,
            """
            SELECT COALESCE(
                SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 0
            ) AS used_minutes
            FROM interviews
            WHERE status = 'scheduled'
              AND panel_id IS NOT NULL
              AND start_time IS NOT NULL
              AND end_time IS NOT NULL
            """,
        )["used_minutes"] or 0

        panel_count = fetch_one(
            cursor,
            "SELECT COUNT(*) AS count FROM panels",
        )["count"] or 0

        panel_available = panel_count * 8 * 60
        panel_utilization = (
            float(panel_used) / panel_available * 100
            if panel_available else 0.0
        )

        cursor.execute(
            """
            SELECT student_id, start_time, end_time
            FROM interviews
            WHERE status = 'scheduled'
              AND start_time IS NOT NULL
              AND end_time IS NOT NULL
            ORDER BY student_id, start_time
            """
        )
        scheduled_rows = cursor.fetchall()

        by_student = defaultdict(list)
        for row in scheduled_rows:
            by_student[row["student_id"]].append(row)

        waits = []
        for student_rows in by_student.values():
            for first, second in zip(student_rows, student_rows[1:]):
                if first["start_time"].date() != second["start_time"].date():
                    continue
                wait_minutes = (
                    second["start_time"] - first["end_time"]
                ).total_seconds() / 60
                if wait_minutes >= 0:
                    waits.append(wait_minutes)

        average_wait = sum(waits) / len(waits) if waits else 0.0
        maximum_wait = max(waits) if waits else 0.0

        # Classify each affected interview by its latest logged change so
        # repaired + cancelled == affected even after multiple disruptions.
        replan = fetch_one(
            cursor,
            """
            SELECT
                COUNT(*) AS affected,
                SUM(CASE
                    WHEN latest.new_start_time IS NOT NULL
                      OR latest.new_end_time IS NOT NULL
                    THEN 1 ELSE 0
                END) AS repaired,
                SUM(CASE
                    WHEN latest.new_start_time IS NULL
                     AND latest.new_end_time IS NULL
                    THEN 1 ELSE 0
                END) AS cancelled,
                COALESCE(MAX(
                    CASE
                        WHEN latest.old_start_time IS NOT NULL
                         AND latest.new_start_time IS NOT NULL
                        THEN ABS(TIMESTAMPDIFF(
                            MINUTE,
                            latest.old_start_time,
                            latest.new_start_time
                        ))
                        ELSE 0
                    END
                ), 0) AS maximum_displacement
            FROM replan_log latest
            JOIN (
                SELECT interview_id, MAX(id) AS latest_id
                FROM replan_log
                GROUP BY interview_id
            ) newest
              ON newest.latest_id = latest.id
            """,
        )

        # Use the baseline scheduled count when available so churn reflects
        # the proportion of the original schedule that was touched.
        baseline_table = fetch_one(
            cursor,
            """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = 'interviews_baseline'
            """,
        )

        baseline_scheduled = 0
        if baseline_table and baseline_table["count"]:
            baseline = fetch_one(
                cursor,
                """
                SELECT COUNT(*) AS count
                FROM interviews_baseline
                WHERE status = 'scheduled'
                """,
            )
            baseline_scheduled = (baseline or {}).get("count") or 0

        replan_affected = replan["affected"] or 0
        replan_churn = (
            replan_affected / baseline_scheduled * 100
            if baseline_scheduled
            else 0
        )

        return {
            "total_interviews": total,
            "scheduled": scheduled,
            "unscheduled": totals["unscheduled"] or 0,
            "cancelled": totals["cancelled"] or 0,
            "scheduling_rate": scheduled / total * 100 if total else 0,
            "students_served": fetch_one(
                cursor,
                """
                SELECT COUNT(DISTINCT student_id) AS count
                FROM interviews
                WHERE status = 'scheduled'
                """,
            )["count"],
            "average_interviews": float(fairness["avg_interviews"] or 0),
            "maximum_interviews": fairness["max_interviews"] or 0,
            "room_utilization": room_utilization,
            "panel_utilization": panel_utilization,
            "average_wait_minutes": average_wait,
            "maximum_wait_minutes": maximum_wait,
            "waiting_samples": len(waits),
            "replan_affected": replan_affected,
            "replan_repaired": replan["repaired"] or 0,
            "replan_cancelled": replan["cancelled"] or 0,
            "maximum_displacement": replan["maximum_displacement"] or 0,
            "replan_churn": replan_churn,
            **conflicts,
            "hard_conflicts": sum(conflicts.values()),
        }

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Replan request models
# ---------------------------------------------------------

class CompanyDelayRequest(BaseModel):
    company_id: int
    delay_minutes: int = Field(ge=0, le=480)


class PanelDropRequest(BaseModel):
    panel_id: int


class RoomOfflineRequest(BaseModel):
    room_id: int


class StudentWithdrawalRequest(BaseModel):
    student_id: int


# ---------------------------------------------------------
# Replanning validation helpers
# ---------------------------------------------------------

def ensure_exists(cursor, table_name, record_id, label):
    cursor.execute(
        f"SELECT id FROM {table_name} WHERE id = %s",
        (record_id,),
    )
    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail=f"{label} {record_id} was not found.",
        )


# ---------------------------------------------------------
# Replanning endpoints
# ---------------------------------------------------------

@app.post("/api/replan/company-delay")
def company_delay(request: CompanyDelayRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ensure_exists(cursor, "companies", request.company_id, "Company")
        result = handle_company_delay(
            cursor,
            request.company_id,
            request.delay_minutes,
        )
        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


@app.post("/api/replan/panel-drop")
def panel_drop(request: PanelDropRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ensure_exists(cursor, "panels", request.panel_id, "Panel")
        result = handle_panel_drop(cursor, request.panel_id)
        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


@app.post("/api/replan/room-offline")
def room_offline(request: RoomOfflineRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ensure_exists(cursor, "rooms", request.room_id, "Room")
        result = handle_room_offline(cursor, request.room_id)
        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


@app.post("/api/replan/withdraw")
def withdraw(request: StudentWithdrawalRequest):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        ensure_exists(cursor, "students", request.student_id, "Student")
        result = handle_withdrawal(cursor, request.student_id)
        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Restore baseline
# ---------------------------------------------------------

@app.post("/api/replan/restore-baseline")
def restore_baseline():
    """Restore the saved baseline using the same source as the CLI tool."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if not baseline_ready(cursor):
            raise HTTPException(
                status_code=409,
                detail="No complete baseline exists. Run: python replan_metrics.py --save-baseline",
            )

        restore_saved_baseline(cursor)

        # Restore means a clean baseline state, so stale disruption records
        # must not remain visible after the schedule has been restored.
        cursor.execute("DELETE FROM disruptions")

        conn.commit()

        restored = fetch_one(
            cursor,
            "SELECT COUNT(*) AS count FROM interviews",
        )["count"]
        logs = fetch_one(
            cursor,
            "SELECT COUNT(*) AS count FROM replan_log",
        )["count"]

        return {
            "status": "restored",
            "restored_interviews": restored,
            "cleared_replan_logs": logs,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Baseline restore failed: {exc}",
        ) from exc

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Replan log
# ---------------------------------------------------------

@app.get("/api/replan-log")
def replan_log():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM replan_log
            ORDER BY logged_at DESC, id DESC
            """
        )
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()
