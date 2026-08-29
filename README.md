# Placement Week Scheduler

![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)
![Frontend](https://img.shields.io/badge/frontend-Vercel-black?logo=vercel)
![Backend](https://img.shields.io/badge/backend-Render-46E3B7?logo=render)
![Database](https://img.shields.io/badge/database-MySQL%20(Aiven)-4479A1?logo=mysql&logoColor=white)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/backend%20framework-FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/frontend%20framework-React%20%2B%20Vite-61DAFB?logo=react&logoColor=white)
![OR-Tools](https://img.shields.io/badge/optimizer-OR--Tools%20CP--SAT-4285F4?logo=google&logoColor=white)

A placement-week scheduling system for the Mirai Labs Software Developer Intern technical assessment.

## Live deployment

- **Dashboard:** [https://placement-week-scheduler-priyanshu.vercel.app/](https://placement-week-scheduler-priyanshu.vercel.app/)
- **Backend API:** hosted on Render, connected to a managed MySQL instance on Aiven

## System architecture

```text
React + Vite dashboard
        │
        │ HTTP / JSON
        ▼
FastAPI backend
        │
        ├── scheduler.py
        ├── optimizer.py (OR-Tools CP-SAT)
        ├── replanner.py
        └── replan_metrics.py
        │
        ▼
MySQL
```

## What the system does

- Generates a realistic placement dataset for 35 companies, about 800 students, 20 rooms and company-specific interview panels.
- Produces a feasible baseline schedule while preventing student, room and panel overlaps.
- Uses OR-Tools CP-SAT to improve the baseline schedule while respecting the configured fairness cap.
- Replans under four live disruptions:
  - company delay
  - panel drop
  - room outage
  - student withdrawal
- Caps automatic displacement at 120 minutes during disruption recovery.
- Records a before/after diff in `replan_log`.
- Measures replan churn, movement and cancellations.
- Provides a coordinator dashboard backed by the real MySQL schedule.

## Database setup

Create the MySQL database and complete schema first:

```sql
SOURCE database/schema.sql;
```

The schema includes the live tables plus the four baseline snapshot tables used by Restore Baseline. It does not include generated seed data.

## Backend setup

Create `backend/.env`:

```env
DB_HOST=localhost
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=placement_scheduler
```

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Run the data generator/seed when a clean database is required:

```powershell
python backend/seed.py
```

Seeding also clears any previous baseline snapshots. After generating the schedule you want to return to, save a new baseline.

Run the baseline scheduler:

```powershell
python backend/scheduler.py
```

Run the optimizer:

```powershell
python backend/optimizer.py
```

Run the evaluator:

```powershell
python backend/evaluator.py
```

## Replanning

Examples:

```powershell
python backend/replanner.py --delay-company 2 60
python backend/replanner.py --panel-dropped 4
python backend/replanner.py --room-offline 12
python backend/replanner.py --withdraw 788
```

For churn measurements, save the clean optimized state first:

```powershell
python backend/replan_metrics.py --save-baseline
```

Then apply a disruption and compare:

```powershell
python backend/replan_metrics.py --compare
```

Restore the baseline schedule and resource/student state:

```powershell
python backend/replan_metrics.py --restore
```

## API

Start FastAPI from `backend/`:

```powershell
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:

```text
GET  /api/health
GET  /api/dashboard
GET  /api/interviews
GET  /api/rooms
GET  /api/panels
GET  /api/students
GET  /api/companies
GET  /api/metrics
GET  /api/replan-log

POST /api/replan/company-delay
POST /api/replan/panel-drop
POST /api/replan/room-offline
POST /api/replan/withdraw
POST /api/replan/restore-baseline
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

## Frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

The Vite development server is exposed on the LAN with:

```text
http://localhost:5173
```

The frontend proxies `/api/*` requests to FastAPI on port 8000.

## Operational-state model

Rooms have an operational status:

```text
available
offline
```

Panels already use:

```text
available
unavailable
```

A room outage or panel drop updates the resource state as well as the affected interviews. The scheduler only loads operational rooms and available panels.

## Scheduling policy

The project treats hard feasibility constraints as non-negotiable:

- no student overlap
- no room overlap
- no panel overlap
- company arrival time respected
- interview duration respected

When a replan cannot find an acceptable replacement within the 120-minute automatic displacement budget, the affected interview is explicitly cancelled and the reason is logged rather than silently moved an unreasonable distance.

### Coordinator restore

The dashboard supports restoring the saved baseline through `POST /api/replan/restore-baseline`. The restore uses the same baseline tables as `backend/replan_metrics.py`, clears the replan log first, and restores interview, room, panel, and student state together.
