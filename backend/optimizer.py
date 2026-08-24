# ============================================================
# Placement Week Scheduler — CP-SAT Optimizer (V2 Enhanced)
# Mirai Labs Assignment A — Task 2
# ============================================================

from collections import defaultdict
from datetime import datetime, timedelta

from db import get_connection
from ortools.sat.python import cp_model
from scheduler import (
    MAX_INTERVIEWS_PER_STUDENT,
    PLACEMENT_START_DATE,
    generate_slots_for_company,
    load_data,
)

# Priority tier secondary bonuses
TIER_WEIGHT = {1: 3, 2: 2, 3: 1}

# Large primary weight ensuring interview count strictly dominates tier score
PRIMARY_COUNT_WEIGHT = 10000

SOLVE_TIME_LIMIT_SECONDS = 120


def to_minutes(dt):
  return int((dt - PLACEMENT_START_DATE).total_seconds() // 60)


def from_minutes(m):
  return PLACEMENT_START_DATE + timedelta(minutes=m)


def fetch_baseline_hints(read_cursor, presence_keys):
  """Loads existing scheduled interviews from the baseline database run

  to seed CP-SAT with a warm-start incumbent.
  """
  read_cursor.execute(
      "SELECT student_id, company_id, start_time FROM interviews WHERE status"
      " = 'scheduled'"
  )
  rows = read_cursor.fetchall()
  hints = {}
  for row in rows:
    sid = row["student_id"] if isinstance(row, dict) else row[0]
    cid = row["company_id"] if isinstance(row, dict) else row[1]
    start_dt = row["start_time"] if isinstance(row, dict) else row[2]
    if start_dt and (sid, cid) in presence_keys:
      hints[(sid, cid)] = to_minutes(start_dt)
  return hints


def build_and_solve(
    companies, students, shortlists, rooms, panels, read_cursor=None
):
  students_by_id = {s["id"]: s for s in students}
  companies_by_id = {c["id"]: c for c in companies}

  panels_by_company = defaultdict(list)
  for p in panels:
    panels_by_company[p["company_id"]].append(p)

  shortlist_map = defaultdict(list)
  for sl in shortlists:
    if sl["student_id"] in students_by_id:
      shortlist_map[sl["company_id"]].append(sl["student_id"])

  model = cp_model.CpModel()

  # Per-shortlist CP-SAT variables
  presence = {}  # (student_id, company_id) -> BoolVar
  start_var = {}  # (student_id, company_id) -> IntVar
  interval_var = {}  # (student_id, company_id) -> IntervalVar

  student_intervals = defaultdict(list)
  company_intervals = defaultdict(list)
  all_intervals = []

  company_slot_cache = {}
  company_duration = {}

  for company in companies:
    cid = company["id"]
    if cid not in panels_by_company:
      continue
    slots = generate_slots_for_company(company)
    if not slots:
      continue
    company_slot_cache[cid] = [to_minutes(s) for s, _ in slots]
    company_duration[cid] = company["interview_duration_min"]

  for cid, student_ids in shortlist_map.items():
    if cid not in company_slot_cache:
      continue
    duration = company_duration[cid]
    allowed_starts = company_slot_cache[cid]
    domain = cp_model.Domain.FromValues(allowed_starts)

    for sid in student_ids:
      key = (sid, cid)
      pres = model.NewBoolVar(f"pres_{sid}_{cid}")
      start = model.NewIntVarFromDomain(domain, f"start_{sid}_{cid}")
      interval = model.NewOptionalIntervalVar(
          start, duration, start + duration, pres, f"iv_{sid}_{cid}"
      )

      presence[key] = pres
      start_var[key] = start
      interval_var[key] = interval

      student_intervals[sid].append(interval)
      company_intervals[cid].append(interval)
      all_intervals.append(interval)

  # 1. Panel capacity per company
  for cid, intervals in company_intervals.items():
    num_panels = len(panels_by_company[cid])
    demands = [1] * len(intervals)
    model.AddCumulative(intervals, demands, num_panels)

  # 2. Global room capacity constraint
  if all_intervals:
    model.AddCumulative(all_intervals, [1] * len(all_intervals), len(rooms))

  # 3. Student no-double-booking & fairness cap
  for sid, intervals in student_intervals.items():
    model.AddNoOverlap(intervals)

  for sid in student_intervals:
    keys = [k for k in presence if k[0] == sid]
    model.Add(sum(presence[k] for k in keys) <= MAX_INTERVIEWS_PER_STUDENT)

  # 4. Lexicographic Objective: Total count dominates; tier priority breaks ties
  objective_terms = []
  for (sid, cid), pres in presence.items():
    tier = companies_by_id[cid]["priority_tier"]
    tier_bonus = TIER_WEIGHT.get(tier, 1)
    weight = PRIMARY_COUNT_WEIGHT + tier_bonus
    objective_terms.append(weight * pres)
  model.Maximize(sum(objective_terms))

  # 5. Load baseline hints (Warm Start / Incumbent)
  if read_cursor:
    baseline_hints = fetch_baseline_hints(read_cursor, set(presence.keys()))
    hint_count = 0
    for key, pres in presence.items():
      if key in baseline_hints:
        model.AddHint(pres, 1)
        model.AddHint(start_var[key], baseline_hints[key])
        hint_count += 1
      else:
        model.AddHint(pres, 0)
    print(f"Loaded {hint_count} baseline interview hints for solver warm-start.")

  # Solve
  solver = cp_model.CpSolver()
  solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT_SECONDS
  solver.parameters.num_search_workers = 8

  status = solver.Solve(model)

  if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    raise RuntimeError(
        f"Solver did not find a feasible solution (status={status})"
    )

  raw_obj = solver.ObjectiveValue()
  scheduled_cnt = int(raw_obj // PRIMARY_COUNT_WEIGHT)
  tier_score = int(raw_obj % PRIMARY_COUNT_WEIGHT)

  print(
      f"Solver status: {solver.StatusName(status)} | Total Scheduled:"
      f" {scheduled_cnt} | Tier Bonus: {tier_score} | Time:"
      f" {solver.WallTime():.1f}s"
  )

  # Collect chosen intervals
  chosen = []
  unscheduled = []
  for (sid, cid), pres in presence.items():
    if solver.Value(pres):
      start_m = solver.Value(start_var[(sid, cid)])
      chosen.append((sid, cid, start_m, start_m + company_duration[cid]))
    else:
      unscheduled.append((
          sid,
          cid,
          "not selected by optimizer under capacity/fairness constraints",
      ))

  return chosen, unscheduled, panels_by_company


def assign_panel_ids(chosen, panels_by_company):
  """Greedy interval coloring per company to assign specific panel_id."""
  by_company = defaultdict(list)
  for row in chosen:
    by_company[row[1]].append(row)

  result = []
  for cid, rows in by_company.items():
    rows.sort(key=lambda r: r[2])
    panel_free_at = {p["id"]: -1 for p in panels_by_company[cid]}

    for sid, cid_, start_m, end_m in rows:
      chosen_panel = None
      for pid, free_at in panel_free_at.items():
        if free_at <= start_m:
          chosen_panel = pid
          break
      if chosen_panel is None:
        raise RuntimeError(
            f"Panel assignment failed for company {cid_} "
            f"at interval {start_m}-{end_m}. "
            "CP-SAT solution and panel post-processing disagree."
        )
      panel_free_at[chosen_panel] = end_m
      result.append((sid, cid_, chosen_panel, start_m, end_m))

  return result


def assign_room_ids(rows_with_panels, rooms):
  """Greedy interval coloring across global room pool."""
  rows_sorted = sorted(rows_with_panels, key=lambda r: r[3])
  room_free_at = {r["id"]: -1 for r in rooms}

  final = []
  for sid, cid, panel_id, start_m, end_m in rows_sorted:
    chosen_room = None
    for rid, free_at in room_free_at.items():
      if free_at <= start_m:
        chosen_room = rid
        break
    if chosen_room is None:
      raise RuntimeError(
          f"Room assignment failed for interval {start_m}-{end_m}. "
          "CP-SAT solution and room post-processing disagree."
      )
    room_free_at[chosen_room] = end_m
    final.append((sid, cid, chosen_room, panel_id, start_m, end_m))

  return final


def to_scheduled_rows(final):
  rows = []
  for sid, cid, room_id, panel_id, start_m, end_m in final:
    start_dt = from_minutes(start_m)
    end_dt = from_minutes(end_m)
    rows.append((sid, cid, room_id, panel_id, start_dt, end_dt, "scheduled"))
  return rows


def write_results(cursor, scheduled_rows, unscheduled):
  cursor.execute("DELETE FROM replan_log")
  cursor.execute("DELETE FROM interviews")

  insert_sql = """
        INSERT INTO interviews (student_id, company_id, room_id, panel_id, start_time, end_time, status, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

  rows = [
      (sid, cid, room_id, panel_id, start, end, status, None)
      for sid, cid, room_id, panel_id, start, end, status in scheduled_rows
  ]
  if rows:
    cursor.executemany(insert_sql, rows)

  unsched_rows = [
      (sid, cid, None, None, None, None, "unscheduled", reason)
      for sid, cid, reason in unscheduled
  ]
  if unsched_rows:
    cursor.executemany(insert_sql, unsched_rows)


def print_metrics(scheduled_rows, unscheduled):
  total = len(scheduled_rows) + len(unscheduled)
  pct = (len(scheduled_rows) / total * 100) if total else 0

  print("\n" + "=" * 70)
  print("OPTIMIZER RESULTS (OR-Tools CP-SAT)")
  print("=" * 70)
  print(f"Total shortlist entries : {total}")
  print(f"Scheduled               : {len(scheduled_rows)} ({pct:.1f}%)")
  print(f"Unscheduled             : {len(unscheduled)} ({100 - pct:.1f}%)")

  student_counts = defaultdict(int)
  for sid, cid, room_id, panel_id, start, end, status in scheduled_rows:
    student_counts[sid] += 1

  if student_counts:
    print(f"\nStudents with interviews : {len(student_counts)}")
    print(
        "Average interviews      :"
        f" {sum(student_counts.values())/len(student_counts):.2f}"
    )
    print(f"Maximum interviews       : {max(student_counts.values())}")

  print("=" * 70)


def run():
  conn = get_connection()
  read_cursor = conn.cursor(dictionary=True)

  try:
    companies, students, shortlists, rooms, panels = load_data(read_cursor)

    chosen, unscheduled, panels_by_company = build_and_solve(
        companies, students, shortlists, rooms, panels, read_cursor=read_cursor
    )

    with_panels = assign_panel_ids(chosen, panels_by_company)
    final = assign_room_ids(with_panels, rooms)
    scheduled_rows = to_scheduled_rows(final)

    write_cursor = conn.cursor()
    write_results(write_cursor, scheduled_rows, unscheduled)
    conn.commit()
    write_cursor.close()

    print_metrics(scheduled_rows, unscheduled)
    print("\nOptimized schedule written to `interviews` table.")

  except Exception as e:
    conn.rollback()
    print("Optimization failed, rolled back:", e)
    raise
  finally:
    read_cursor.close()
    conn.close()


if __name__ == "__main__":
  run()