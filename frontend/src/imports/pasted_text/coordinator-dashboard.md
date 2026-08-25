Design a production-quality coordinator dashboard for a real-time college Placement Week Scheduler.

This is an operational dashboard for a placement coordinator who is managing 35 companies, 800 students, 4 placement days, 20 interview rooms, and 127 interview panels. The coordinator is stressed and needs to make fast decisions during live placement operations.

The dashboard should feel like a serious internal operations product, not a generic SaaS analytics dashboard.

PRODUCT NAME
Placement Week Scheduler

PRIMARY GOAL
Give the placement coordinator an immediate view of:
- current placement state
- today's schedule
- upcoming interviews
- room and panel availability
- conflicts and disruptions
- affected students
- one-click replanning
- clear before/after schedule changes

DESIGN STYLE
Use a modern, high-trust operations interface.
Dark charcoal/navy application shell with a light content area or a very light neutral background.
Use red only for critical disruptions and warnings.
Use green for healthy/success states.
Use amber/orange for warnings.
Use blue/indigo for neutral informational states.
Avoid excessive gradients, glassmorphism, excessive rounded cards, and decorative illustrations.
Prioritize information density, readability, hierarchy, and fast scanning.
Use compact spacing but maintain strong readability.
Use professional typography such as Inter or a similar modern UI font.

DESKTOP-FIRST
Design primarily for a 1440px desktop coordinator workstation.
Also make the layout reasonably responsive for a 1280px viewport.

GLOBAL LAYOUT

LEFT SIDEBAR
Width around 240px.

Top:
Placement Week Scheduler logo/icon and product name.

Navigation:
- Overview
- Live Schedule
- Students
- Companies
- Rooms
- Panels
- Disruptions
- Replan History
- Metrics

Bottom of sidebar:
- System status: "All systems operational"
- Coordinator profile
- Settings

TOP BAR
Full-width top header.

Left:
- Page title: "Placement Operations"
- Current day indicator: "Day 3 of 4"

Center:
- Search field: "Search student, company, room or interview..."

Right:
- Current time
- Notification bell
- Coordinator avatar

OVERVIEW DASHBOARD

Hero/header section:
Title:
"Placement Operations"

Subtitle:
"Live placement status and upcoming coordination actions"

Right side:
Primary red button:
"Trigger Replan"

Secondary button:
"View Full Schedule"

SUMMARY KPI ROW
Use 5 compact but prominent KPI cards:

1. Scheduled Interviews
"1,312"
Subtext:
"21.42% of shortlist"

2. Students Served
"695"
Subtext:
"Active candidates"

3. Active Companies
"35"
Subtext:
"Across 4 placement days"

4. Rooms
"20 / 20"
Subtext:
"Current room utilization"

5. Conflicts
"0"
Subtext:
"No student, room or panel conflicts"

Add tiny trend/context indicators but don't invent fake historical trends. Use static status labels instead.

MAIN CONTENT GRID

LEFT / LARGE SECTION:
"Live Schedule"

Add filter row:
- Day selector
- Time range
- Company filter
- Room filter
- Panel filter
- Status filter

Below that, create a dense schedule timeline/table.

Columns:
- Time
- Student
- Company
- Room
- Panel
- Duration
- Status

Example rows:
09:00 — Student 788 — Infosys — Room 20 — Panel 2 — 20 min — Scheduled
09:20 — Student 756 — Google — Room 11 — Panel 14 — 45 min — Scheduled
09:45 — Student 479 — Microsoft — Room 18 — Panel 43 — 45 min — Scheduled

Use subtle row grouping by time.
Current/upcoming interviews should be visually emphasized.
Do not use excessive colors.

RIGHT / SIDE PANEL:
"Needs Attention"

Show operational alerts:

CRITICAL
"Company 2 — Infosys delayed 60 min"
"63 interviews affected"
Button: "Replan"

WARNING
"Room 12 unavailable"
"42 interviews affected"
Button: "Review"

INFO
"Panel 4 dropped"
"24 interviews affected"
Button: "View Impact"

For each disruption card show:
- severity
- disruption type
- affected interview count
- affected students
- timestamp
- action button

RESOURCE STATUS SECTION

Create two compact visual panels:

ROOM STATUS
Show all 20 rooms in a grid/list with statuses:
- Available
- In use
- Offline

Example:
Room 01 — In use
Room 02 — Available
Room 03 — In use
Room 12 — Offline
Room 19 — In use

PANEL STATUS
Show panel availability by company.
Use compact rows:
Infosys — 2/3 available
Google — 3/3 available
Microsoft — 4/4 available
etc.

Use colored status dots rather than giant cards.

UPCOMING INTERVIEWS

Create a section:
"Next 60 Minutes"

Show a compact list with:
- time
- student
- company
- room
- panel
- countdown/status

Example:
09:20 — Student 788 — Infosys — Room 20 — Panel 2
09:30 — Student 756 — Google — Room 18 — Panel 14
09:40 — Student 479 — Infosys — Room 11 — Panel 3

STUDENT IMPACT PANEL

Create a section:
"Affected Students"

When a disruption is active, show:
- student name / ID
- company
- old appointment
- new appointment
- notification status

Example:
Student 788
Infosys
OLD: Room 12 • 10:00–10:20
NEW: Room 16 • 11:00–11:20
Status: Notify student

REPLAN FLOW

Create a prominent modal/page state for the "Trigger Replan" action.

STEP 1 — SELECT DISRUPTION
Large selectable cards:
- Company Delay
- Panel Unavailable
- Student Withdrawal
- Room Unavailable

STEP 2 — DETAILS
Depending on selected disruption:
Company Delay:
Company dropdown
Delay minutes input

Panel:
Panel dropdown

Student:
Student search

Room:
Room dropdown

STEP 3 — IMPACT PREVIEW

Show:
"Affected: 63 interviews"
"Students affected: 61"
"Potential cancellations: 9"
"Maximum automatic displacement: 120 min"

Then:
Primary button:
"Run Replan"

Secondary:
"Cancel"

STEP 4 — REPLAN RESULT

Show a strong summary:

"Replan completed"

Metrics:
54 Moved
9 Cancelled
63 Affected
4.86% Churn
60 min Max Displacement

Then create a before/after diff table:

INTERVIEW 258972
OLD
10:00–10:20
Room 20
Panel 2

NEW
11:00–11:20
Room 20
Panel 2

Reason:
"Company delayed 60 minutes"

Use green for accepted changes and red for cancellations.

Include:
"Notify affected students"
button
"Return to schedule"
button

REPLAN HISTORY PAGE

Create a dedicated table showing previous replans:

Columns:
- Timestamp
- Disruption
- Affected
- Moved
- Cancelled
- Churn
- Max displacement
- Status

Example:
25 Aug, 10:32
Company delay — Infosys
63 affected
54 moved
9 cancelled
4.86%
60 min
Completed

METRICS PAGE

Show meaningful project metrics:

Scheduling:
- Scheduled interviews
- Scheduling rate
- Unscheduled interviews

Fairness:
- Students served
- Average interviews/student
- Maximum interviews/student

Constraints:
- Student conflicts
- Room conflicts
- Panel conflicts

Utilization:
- Room utilization
- Panel utilization

Waiting:
- Average waiting time
- Maximum waiting time

Replanning:
- Recovery rate
- Replan churn
- Average displacement
- Maximum displacement

Include a "Greedy vs CP-SAT" comparison card:

Greedy:
1,302 scheduled

CP-SAT:
1,316 scheduled

Use the comparison to communicate improvement, but do not invent fake charts or fake historical trend data.

IMPORTANT UX REQUIREMENTS

1. A coordinator should understand system health in under 5 seconds.
2. The "Trigger Replan" action must always be obvious.
3. Disruptions must visually stand out without overwhelming the interface.
4. The dashboard should prioritize current operational state over analytics.
5. Every replan must expose:
   - what changed
   - who was affected
   - old schedule
   - new schedule
   - cancellations
   - reason
6. Use clear labels like:
   Scheduled
   Affected
   Repaired
   Cancelled
   Conflict
   Offline
7. Avoid generic marketing language.
8. Do not add unnecessary decorative charts.
9. Make tables sortable/filterable.
10. Use sticky headers for long schedule tables.

IMPORTANT VISUAL PRIORITY

Highest priority:
- active disruptions
- upcoming interviews
- conflicts
- room/panel availability
- replan action

Secondary:
- fairness metrics
- utilization
- waiting time
- historical replan information

Create the final design as a polished enterprise operations dashboard with:
- Overview screen
- Live Schedule screen
- Replan modal/workflow
- Replan Result screen
- Replan History screen
- Metrics screen
- Room/Panel management screens

Make the interface feel like software that a real placement coordinator could use during a chaotic live placement day.