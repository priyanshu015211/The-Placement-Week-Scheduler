from db import get_connection
from generator import (
    generate_students,
    generate_companies,
    generate_shortlists,
    generate_rooms,
    generate_panels,
    print_summary,
)

def reset_tables(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ["replan_log", "disruptions", "interviews",
                  "shortlists", "panels", "rooms", "students", "companies"]:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def seed_database():
    students = generate_students()
    companies = generate_companies()
    shortlists = generate_shortlists(students, companies)
    rooms = generate_rooms()
    panels = generate_panels(companies)

    print_summary(students, companies, shortlists, rooms, panels)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        reset_tables(cursor)

        # ---- companies ----
        cursor.executemany(
            """INSERT INTO companies
               (name, placement_day, arrival_time, cgpa_cutoff,
                panels, interview_duration_min, priority_tier)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [
                (c["name"], c["placement_day"], c["arrival_time"], c["cgpa_cutoff"],
                 c["panels"], c["interview_duration_min"], c["priority_tier"])
                for c in companies
            ]
        )
        first_company_id = cursor.lastrowid
        company_id_map = {c["id"]: first_company_id + i for i, c in enumerate(companies)}

        # ---- panels ----
        cursor.executemany(
            "INSERT INTO panels (company_id, panel_number, status) VALUES (%s, %s, %s)",
            [
                (company_id_map[p["company_id"]], p["panel_number"], p["status"])
                for p in panels
            ]
        )

        # ---- students ----
        cursor.executemany(
            "INSERT INTO students (name, cgpa, branch, status) VALUES (%s, %s, %s, %s)",
            [(s["name"], s["cgpa"], s["branch"], s["status"]) for s in students]
        )
        first_student_id = cursor.lastrowid
        student_id_map = {s["id"]: first_student_id + i for i, s in enumerate(students)}

        # ---- rooms ----
        cursor.executemany(
            "INSERT INTO rooms (name, capacity) VALUES (%s, %s)",
            [(r["name"], r["capacity"]) for r in rooms]
        )

        # ---- shortlists ----
        cursor.executemany(
            "INSERT IGNORE INTO shortlists (student_id, company_id) VALUES (%s, %s)",
            [
                (student_id_map[s["student_id"]], company_id_map[s["company_id"]])
                for s in shortlists
            ]
        )

        conn.commit()
        print("\nSeed complete — all tables populated successfully.")

    except Exception as e:
        conn.rollback()
        print("Seeding failed, rolled back:", e)
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    seed_database()