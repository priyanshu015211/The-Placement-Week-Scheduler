from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import get_connection
from replanner import (
    handle_company_delay,
    handle_panel_drop,
    handle_room_offline,
    handle_withdrawal,
)

app = FastAPI(
    title="Placement Week Scheduler API",
    version="1.0.0",
)


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
        cursor.execute("""
            SELECT COUNT(*) AS scheduled
            FROM interviews
            WHERE status = 'scheduled'
        """)
        scheduled = cursor.fetchone()["scheduled"]

        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) AS students_served
            FROM interviews
            WHERE status = 'scheduled'
        """)
        students_served = cursor.fetchone()["students_served"]

        cursor.execute("""
            SELECT COUNT(*) AS companies
            FROM companies
        """)
        companies = cursor.fetchone()["companies"]

        cursor.execute("""
            SELECT COUNT(*) AS rooms
            FROM rooms
        """)
        rooms = cursor.fetchone()["rooms"]

        cursor.execute("""
            SELECT COUNT(*) AS panels
            FROM panels
            WHERE status = 'available'
        """)
        available_panels = cursor.fetchone()["panels"]

        return {
            "scheduled": scheduled,
            "students_served": students_served,
            "companies": companies,
            "rooms": rooms,
            "available_panels": available_panels,
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
        cursor.execute("""
            SELECT
                i.id,
                i.student_id,
                s.name AS student_name,
                i.company_id,
                c.name AS company_name,
                i.room_id,
                r.name AS room_name,
                i.panel_id,
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
            WHERE i.status = 'scheduled'
            ORDER BY i.start_time
        """)

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
        cursor.execute("""
            SELECT
                r.id,
                r.name,
                COUNT(i.id) AS scheduled_interviews
            FROM rooms r
            LEFT JOIN interviews i
                ON i.room_id = r.id
               AND i.status = 'scheduled'
            GROUP BY r.id, r.name
            ORDER BY r.id
        """)

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
        cursor.execute("""
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
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# Replan request models
# ---------------------------------------------------------

class CompanyDelayRequest(BaseModel):
    company_id: int
    delay_minutes: int


class PanelDropRequest(BaseModel):
    panel_id: int


class RoomOfflineRequest(BaseModel):
    room_id: int


class StudentWithdrawalRequest(BaseModel):
    student_id: int


# ---------------------------------------------------------
# Replanning endpoints
# ---------------------------------------------------------

@app.post("/api/replan/company-delay")
def company_delay(request: CompanyDelayRequest):
    if request.delay_minutes < 0:
        raise HTTPException(
            status_code=400,
            detail="Delay must be non-negative",
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        handle_company_delay(
            cursor,
            request.company_id,
            request.delay_minutes,
        )

        conn.commit()

        return {
            "status": "completed",
            "type": "company_delay",
            "company_id": request.company_id,
            "delay_minutes": request.delay_minutes,
        }

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
        handle_panel_drop(
            cursor,
            request.panel_id,
        )

        conn.commit()

        return {
            "status": "completed",
            "type": "panel_drop",
            "panel_id": request.panel_id,
        }

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
        handle_room_offline(
            cursor,
            request.room_id,
        )

        conn.commit()

        return {
            "status": "completed",
            "type": "room_offline",
            "room_id": request.room_id,
        }

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
        handle_withdrawal(
            cursor,
            request.student_id,
        )

        conn.commit()

        return {
            "status": "completed",
            "type": "student_withdrawal",
            "student_id": request.student_id,
        }

    except Exception:
        conn.rollback()
        raise

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
        cursor.execute("""
            SELECT *
            FROM replan_log
            ORDER BY logged_at DESC, id DESC
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

@app.get("/api/students")
def students():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
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
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


@app.get("/api/companies")
def companies():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
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
                COUNT(DISTINCT p.id) AS actual_panels
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
            ORDER BY
                c.placement_day,
                c.priority_tier,
                c.id
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


@app.get("/api/metrics")
def metrics():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM interviews
        """)
        total = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS scheduled
            FROM interviews
            WHERE status = 'scheduled'
        """)
        scheduled = cursor.fetchone()["scheduled"]

        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) AS students_served
            FROM interviews
            WHERE status = 'scheduled'
        """)
        students_served = cursor.fetchone()["students_served"]

        cursor.execute("""
            SELECT
                MAX(x.cnt) AS max_interviews,
                AVG(x.cnt) AS avg_interviews
            FROM (
                SELECT
                    student_id,
                    COUNT(*) AS cnt
                FROM interviews
                WHERE status = 'scheduled'
                GROUP BY student_id
            ) x
        """)
        fairness = cursor.fetchone()

        return {
            "total_interviews": total,
            "scheduled": scheduled,
            "unscheduled": total - scheduled,
            "scheduling_rate": (
                scheduled / total * 100
                if total
                else 0
            ),
            "students_served": students_served,
            "average_interviews": float(
                fairness["avg_interviews"] or 0
            ),
            "maximum_interviews": (
                fairness["max_interviews"] or 0
            ),
        }

    finally:
        cursor.close()
        conn.close()