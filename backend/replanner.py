# ============================================================
# Placement Week Scheduler — Real-Time Replanner
# Mirai Labs Assignment A — Task 3
# ============================================================
#
# Core Policy: MINIMAL DISPLACEMENT
# Disruption Repair Sequence:
# 1. Same-time repair (swap resource locally)
# 2. Nearby-time repair (shift within +/- 3 hours)
# 3. Cancellation (only if no feasible alternative exists)
# ============================================================

import argparse
from datetime import timedelta
from db import get_connection

def log_replan(cursor, interview_id, old_room, old_panel, old_start, old_end, 
               new_room, new_panel, new_start, new_end, reason):
    """Writes a full before/after diff to replan_log based on the schema."""
    cursor.execute("""
        INSERT INTO replan_log 
        (interview_id, old_room_id, old_panel_id, old_start_time, old_end_time, 
         new_room_id, new_panel_id, new_start_time, new_end_time, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (interview_id, old_room, old_panel, old_start, old_end, 
          new_room, new_panel, new_start, new_end, reason))


def get_free_room(cursor, start_time, end_time, exclude_room_id=None):
    query = """
        SELECT id, name
        FROM rooms
        WHERE id NOT IN (
            SELECT room_id
            FROM interviews
            WHERE status = 'scheduled'
              AND start_time < %s
              AND end_time > %s
        )
    """
    params = [end_time, start_time]
    
    if exclude_room_id is not None:
        query += " AND id != %s"
        params.append(exclude_room_id)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return rows[0] if rows else None


def get_free_panel(cursor, company_id, start_time, end_time, exclude_panel_id=None):
    query = """
        SELECT id
        FROM panels
        WHERE company_id = %s
          AND id NOT IN (
              SELECT panel_id
              FROM interviews
              WHERE status = 'scheduled'
                AND start_time < %s
                AND end_time > %s
          )
    """
    params = [company_id, end_time, start_time]
    
    if exclude_panel_id is not None:
        query += " AND id != %s"
        params.append(exclude_panel_id)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return rows[0] if rows else None


def has_student_conflict(cursor, student_id, new_start, new_end, exclude_interview_id):
    cursor.execute("""
        SELECT id
        FROM interviews
        WHERE student_id = %s
          AND status = 'scheduled'
          AND id != %s
          AND start_time < %s
          AND end_time > %s
    """, (student_id, exclude_interview_id, new_end, new_start))
    
    rows = cursor.fetchall()
    return bool(rows)


def is_panel_conflict(cursor, panel_id, new_start, new_end, exclude_interview_id):
    cursor.execute("""
        SELECT id
        FROM interviews
        WHERE panel_id = %s
          AND status = 'scheduled'
          AND id != %s
          AND start_time < %s
          AND end_time > %s
    """, (panel_id, exclude_interview_id, new_end, new_start))
    
    rows = cursor.fetchall()
    return bool(rows)


def handle_student_withdrawal(cursor, student_id):
    print(f"\n[DISRUPTION] Processing withdrawal for Student {student_id}...")
    cursor.execute("UPDATE students SET status = 'withdrawn' WHERE id = %s", (student_id,))
    
    cursor.execute("""
        SELECT * FROM interviews 
        WHERE student_id = %s AND status = 'scheduled'
    """, (student_id,))
    affected = cursor.fetchall()
    
    if not affected:
        print(f"-> Student {student_id} withdrawn. They had 0 active scheduled interviews. No disruption.")
        return

    for row in affected:
        iid = row['id']
        cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Student withdrew' WHERE id = %s", (iid,))
        log_replan(cursor, iid, 
                   row['room_id'], row['panel_id'], row['start_time'], row['end_time'],
                   None, None, None, None, "Student withdrew")
        
    print(f"-> Cancelled {len(affected)} scheduled interviews for Student {student_id}.")


def handle_room_unavailable(cursor, room_id):
    print(f"\n[DISRUPTION] Processing offline status for Room {room_id}...")
    cursor.execute("""
        SELECT * FROM interviews 
        WHERE room_id = %s AND status = 'scheduled'
        ORDER BY start_time ASC
    """, (room_id,))
    affected = cursor.fetchall()
    
    repaired_same_time = 0
    repaired_shifted = 0
    cancelled = 0
    
    for row in affected:
        iid, sid, pid = row['id'], row['student_id'], row['panel_id']
        start, end = row['start_time'], row['end_time']
        
        # 1. Try exact same time with a different room
        alt_room = get_free_room(cursor, start, end, exclude_room_id=room_id)
        if alt_room:
            cursor.execute("UPDATE interviews SET room_id = %s WHERE id = %s", (alt_room['id'], iid))
            log_replan(cursor, iid, room_id, pid, start, end, alt_room['id'], pid, start, end, f"Room {room_id} dropped")
            repaired_same_time += 1
            continue

        # 2 & 3. Try nearby slots (expand search outward up to +/- 3 hours in 20 min intervals)
        found_alt = False
        for offset in range(20, 181, 20):
            for sign in [1, -1]:
                shift = timedelta(minutes=offset * sign)
                new_start = start + shift
                new_end = end + shift
                
                if new_start.hour < 9: continue
                if new_end.hour > 17 or (new_end.hour == 17 and new_end.minute > 0): continue
                if new_start.date() != start.date(): continue
                
                if has_student_conflict(cursor, sid, new_start, new_end, iid): continue
                if is_panel_conflict(cursor, pid, new_start, new_end, iid): continue
                
                alt_room_shifted = get_free_room(cursor, new_start, new_end)
                if not alt_room_shifted: continue
                
                cursor.execute("""
                    UPDATE interviews 
                    SET start_time = %s, end_time = %s, room_id = %s 
                    WHERE id = %s
                """, (new_start, new_end, alt_room_shifted['id'], iid))
                
                log_replan(cursor, iid, room_id, pid, start, end, 
                           alt_room_shifted['id'], pid, new_start, new_end, 
                           f"Room {room_id} offline. Shifted {offset*sign}m")
                repaired_shifted += 1
                found_alt = True
                break
                
            if found_alt: break
                
        if found_alt: continue

        # 4. Cancel
        cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Room unavailable' WHERE id = %s", (iid,))
        log_replan(cursor, iid, room_id, pid, start, end, None, None, None, None, f"Room {room_id} offline, no replacement")
        cancelled += 1
            
    print(f"-> Affected: {len(affected)} | Same-Time Repair: {repaired_same_time} | Shifted Repair: {repaired_shifted} | Cancelled: {cancelled}")


def handle_panel_dropped(cursor, panel_id):
    print(f"\n[DISRUPTION] Processing dropped Panel {panel_id}...")
    cursor.execute("""
        SELECT * FROM interviews 
        WHERE panel_id = %s AND status = 'scheduled'
        ORDER BY start_time ASC
    """, (panel_id,))
    affected = cursor.fetchall()
    
    repaired_same_time = 0
    repaired_shifted = 0
    cancelled = 0
    
    for row in affected:
        iid, cid, sid, rid = row['id'], row['company_id'], row['student_id'], row['room_id']
        start, end = row['start_time'], row['end_time']
        
        # 1. Try exact same time with a different panel
        alt_panel = get_free_panel(cursor, cid, start, end, exclude_panel_id=panel_id)
        if alt_panel:
            cursor.execute("UPDATE interviews SET panel_id = %s WHERE id = %s", (alt_panel['id'], iid))
            log_replan(cursor, iid, rid, panel_id, start, end, rid, alt_panel['id'], start, end, f"Panel {panel_id} dropped")
            repaired_same_time += 1
            continue
            
        # 2 & 3. Try nearby slots (expand search outward up to +/- 3 hours in 20 min intervals)
        found_alt = False
        for offset in range(20, 181, 20):
            for sign in [1, -1]: # +1 is later, -1 is earlier
                shift = timedelta(minutes=offset * sign)
                new_start = start + shift
                new_end = end + shift
                
                if new_start.hour < 9: continue
                if new_end.hour > 17 or (new_end.hour == 17 and new_end.minute > 0): continue
                if new_start.date() != start.date(): continue
                
                if has_student_conflict(cursor, sid, new_start, new_end, iid): continue
                
                alt_room = get_free_room(cursor, new_start, new_end)
                if not alt_room: continue
                
                alt_panel_shifted = get_free_panel(cursor, cid, new_start, new_end, exclude_panel_id=panel_id)
                if not alt_panel_shifted: continue
                
                cursor.execute("""
                    UPDATE interviews 
                    SET start_time = %s, end_time = %s, room_id = %s, panel_id = %s 
                    WHERE id = %s
                """, (new_start, new_end, alt_room['id'], alt_panel_shifted['id'], iid))
                
                log_replan(cursor, iid, rid, panel_id, start, end, 
                           alt_room['id'], alt_panel_shifted['id'], new_start, new_end, 
                           f"Panel {panel_id} dropped. Shifted {offset*sign}m")
                repaired_shifted += 1
                found_alt = True
                break
                
            if found_alt: break
                
        if found_alt: continue
            
        # 4. Cancel
        cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Panel dropped' WHERE id = %s", (iid,))
        log_replan(cursor, iid, rid, panel_id, start, end, None, None, None, None, f"Panel {panel_id} dropped, no capacity")
        cancelled += 1

    print(f"-> Affected: {len(affected)} | Same-Time Repair: {repaired_same_time} | Shifted Repair: {repaired_shifted} | Cancelled: {cancelled}")


def handle_company_delay(cursor, company_id, delay_minutes):
    print(f"\n[DISRUPTION] Processing {delay_minutes} min delay for Company {company_id}...")
    cursor.execute("""
        SELECT * FROM interviews 
        WHERE company_id = %s AND status = 'scheduled'
        ORDER BY start_time ASC
    """, (company_id,))
    affected = cursor.fetchall()
    
    repaired = 0
    cancelled = 0
    delay = timedelta(minutes=delay_minutes)
    
    for row in affected:
        iid, sid, rid, pid = row['id'], row['student_id'], row['room_id'], row['panel_id']
        old_start, old_end = row['start_time'], row['end_time']
        new_start = old_start + delay
        new_end = old_end + delay
        
        # Check end of day bounds
        if new_end.hour > 17 or (new_end.hour == 17 and new_end.minute > 0):
            cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Pushed past end of day' WHERE id = %s", (iid,))
            log_replan(cursor, iid, rid, pid, old_start, old_end, None, None, None, None, f"Company {company_id} delay OOB")
            cancelled += 1
            continue

        # Check student conflict
        if has_student_conflict(cursor, sid, new_start, new_end, iid):
            cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Student schedule conflict' WHERE id = %s", (iid,))
            log_replan(cursor, iid, rid, pid, old_start, old_end, None, None, None, None, "Student time conflict after delay")
            cancelled += 1
            continue

        # Check panel conflict natively caused by the delay
        new_panel_id = pid
        if is_panel_conflict(cursor, pid, new_start, new_end, iid):
            alt_panel = get_free_panel(cursor, company_id, new_start, new_end, exclude_panel_id=pid)
            if alt_panel:
                new_panel_id = alt_panel['id']
            else:
                cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'Panel schedule conflict' WHERE id = %s", (iid,))
                log_replan(cursor, iid, rid, pid, old_start, old_end, None, None, None, None, "Panel time conflict after delay")
                cancelled += 1
                continue
            
        # Check room conflict natives caused by the delay
        new_room_id = rid
        cursor.execute("""
            SELECT id FROM interviews 
            WHERE room_id = %s AND status = 'scheduled' AND id != %s
            AND start_time < %s AND end_time > %s
        """, (rid, iid, new_end, new_start))
        
        if cursor.fetchall():
            alt_room = get_free_room(cursor, new_start, new_end, exclude_room_id=rid)
            if alt_room:
                new_room_id = alt_room['id']
            else:
                cursor.execute("UPDATE interviews SET status = 'cancelled', reason = 'No rooms at delayed time' WHERE id = %s", (iid,))
                log_replan(cursor, iid, rid, pid, old_start, old_end, None, None, None, None, "No room available after delay")
                cancelled += 1
                continue
                
        cursor.execute("UPDATE interviews SET start_time = %s, end_time = %s, room_id = %s, panel_id = %s WHERE id = %s", 
                       (new_start, new_end, new_room_id, new_panel_id, iid))
        log_replan(cursor, iid, rid, pid, old_start, old_end, new_room_id, new_panel_id, new_start, new_end, f"Delayed +{delay_minutes}m")
        repaired += 1
        
    print(f"-> Affected: {len(affected)} | Shifted: {repaired} | Cancelled: {cancelled}")


def view_replan_log(cursor):
    print("\n" + "="*80)
    print("REPLAN LOG (Coordinator Diff Dashboard)")
    print("="*80)
    cursor.execute("SELECT * FROM replan_log ORDER BY logged_at ASC")
    logs = cursor.fetchall()
    
    if not logs:
        print("No disruptions logged.")
        return
        
    for log in logs:
        iid = log['interview_id']
        reason = log.get('reason', 'N/A')
        
        o_start = log['old_start_time'].strftime("%H:%M") if log['old_start_time'] else ""
        o_end = log['old_end_time'].strftime("%H:%M") if log['old_end_time'] else ""
        n_start = log['new_start_time'].strftime("%H:%M") if log['new_start_time'] else "CANCELLED"
        n_end = log['new_end_time'].strftime("%H:%M") if log['new_end_time'] else "CANCELLED"
        
        o_room = f"Rm {log['old_room_id']}" if log['old_room_id'] else ""
        o_pan = f"Pan {log['old_panel_id']}" if log['old_panel_id'] else ""
        
        n_room = f"Rm {log['new_room_id']}" if log['new_room_id'] else "-"
        n_pan = f"Pan {log['new_panel_id']}" if log['new_panel_id'] else "-"
        
        old_str = f"OLD: {o_room}, {o_pan}, {o_start}-{o_end}"
        new_str = f"NEW: {n_room}, {n_pan}, {n_start}-{n_end}"
        
        if not log['new_room_id']:
            new_str = "NEW: CANCELLED"
            
        print(f"Intv {iid:<4} | {old_str:<32} | {new_str:<32} | {reason}")
    print("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mirai Labs Real-Time Replanner")
    parser.add_argument("--withdraw", type=int, help="Student ID who is withdrawing")
    parser.add_argument("--room-offline", type=int, help="Room ID that became unavailable")
    parser.add_argument("--panel-dropped", type=int, help="Panel ID that dropped out")
    parser.add_argument("--delay-company", nargs=2, type=int, metavar=('COMPANY_ID', 'MINUTES'), help="Company ID and delay in minutes")
    parser.add_argument("--view-log", action="store_true", help="View the replan log")
    
    args = parser.parse_args()
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if args.withdraw:
            handle_student_withdrawal(cursor, args.withdraw)
        if args.room_offline:
            handle_room_unavailable(cursor, args.room_offline)
        if args.panel_dropped:
            handle_panel_dropped(cursor, args.panel_dropped)
        if args.delay_company:
            handle_company_delay(cursor, args.delay_company[0], args.delay_company[1])
            
        if any([args.withdraw, args.room_offline, args.panel_dropped, args.delay_company]):
            conn.commit()
            print("Changes committed to database.")
            
        if args.view_log or not any(vars(args).values()):
            view_replan_log(cursor)
            
    except Exception as e:
        conn.rollback()
        print(f"Replanning failed, rolled back: {e}")
    finally:
        cursor.close()
        conn.close()    