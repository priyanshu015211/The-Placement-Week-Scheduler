import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Search,
  LayoutDashboard,
  CalendarDays,
  Users,
  Building,
  MapPin,
  UsersRound,
  AlertOctagon,
  History,
  BarChart3,
  Settings,
  AlertTriangle,
  Info,
  CheckCircle2,
  ChevronDown,
  X,
  ArrowRight,
  Filter,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

import {
  getDashboard,
  getInterviews,
  getRooms,
  getPanels,
  getStudents,
  getCompanies,
  getMetrics,
  getReplanLog,
  delayCompany,
  dropPanel,
  offlineRoom,
  withdrawStudent,
  restoreBaseline,
} from "./api";

/*
  Placement Week Scheduler
  ------------------------
  Full coordinator dashboard.

  Important:
  - JavaScript/JSX only. No TypeScript syntax.
  - Uses the existing API layer in ./api.js.
  - Does not use the PC clock.
  - "Next Scheduled Interviews" is based on the schedule timestamps
    rather than the developer machine's current date.
*/

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedDay, setSelectedDay] = useState(1);

  const [dashboard, setDashboard] = useState(null);
  const [interviews, setInterviews] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [panels, setPanels] = useState([]);
  const [students, setStudents] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [replanLog, setReplanLog] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showReplanModal, setShowReplanModal] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  async function loadAllData() {
    try {
      setError("");

      const [
        dash,
        interviewRows,
        roomRows,
        panelRows,
        studentRows,
        companyRows,
        metricData,
        logRows,
      ] = await Promise.all([
        getDashboard(),
        getInterviews(),
        getRooms(),
        getPanels(),
        getStudents(),
        getCompanies(),
        getMetrics(),
        getReplanLog(),
      ]);

      setDashboard(dash);
      setInterviews(Array.isArray(interviewRows) ? interviewRows : []);
      setRooms(Array.isArray(roomRows) ? roomRows : []);
      setPanels(Array.isArray(panelRows) ? panelRows : []);
      setStudents(Array.isArray(studentRows) ? studentRows : []);
      setCompanies(Array.isArray(companyRows) ? companyRows : []);
      setMetrics(metricData || null);
      setReplanLog(Array.isArray(logRows) ? logRows : []);
    } catch (err) {
      setError(err?.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  async function loadOperationalData() {
    try {
      const [dash, interviewRows, roomRows, panelRows, logRows] =
        await Promise.all([
          getDashboard(),
          getInterviews(),
          getRooms(),
          getPanels(),
          getReplanLog(),
        ]);

      setDashboard(dash);
      setInterviews(Array.isArray(interviewRows) ? interviewRows : []);
      setRooms(Array.isArray(roomRows) ? roomRows : []);
      setPanels(Array.isArray(panelRows) ? panelRows : []);
      setReplanLog(Array.isArray(logRows) ? logRows : []);
    } catch (err) {
      setError(err?.message || "Failed to refresh live data.");
    }
  }

  useEffect(() => {
    loadAllData();

    const timer = setInterval(() => {
      loadOperationalData();
    }, 15000);

    return () => clearInterval(timer);
  }, []);

  const notificationCount = replanLog.length;

  async function handleRestoreBaseline() {
    const confirmed = window.confirm(
      "Restore the saved baseline schedule? This will undo current replanning changes, clear replan history, and reset disrupted resources."
    );

    if (!confirmed) return;

    try {
      setError("");
      await restoreBaseline();
      await loadAllData();
      setActiveTab("overview");
    } catch (err) {
      setError(err?.message || "Failed to restore the baseline schedule.");
    }
  }
  const placementDates = useMemo(() => {
    const dates = Array.from(
      new Set(
        interviews
          .map((row) => {
            if (!row.start_time) return null;
            return String(row.start_time).slice(0, 10);
          })
          .filter(Boolean)
      )
    ).sort();

    return dates;
  }, [interviews]);

  const selectedDate =
    placementDates[selectedDay - 1] || placementDates[0] || "";

  const dayInterviews = useMemo(() => {
    if (!selectedDate) return interviews;

    return interviews.filter(
      (row) =>
        row.start_time &&
        String(row.start_time).slice(0, 10) === selectedDate
    );
  }, [interviews, selectedDate]);


  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] font-sans antialiased">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="relative flex flex-1 flex-col h-screen overflow-hidden">
        <TopBar
          selectedDay={selectedDay}
          setSelectedDay={setSelectedDay}
          totalDays={placementDates.length || 4}
          placementDates={placementDates}
          onOpenNotifications={() =>
            setShowNotifications((current) => !current)
          }
          notificationCount={notificationCount}
        />

        {showNotifications && (
          <NotificationPanel
            logs={replanLog}
            onClose={() => setShowNotifications(false)}
            onOpenHistory={() => {
              setActiveTab("history");
              setShowNotifications(false);
            }}
          />
        )}

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6">
          {error && (
            <div className="mb-5 flex items-start gap-3 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="flex-1">
                <div className="font-semibold">
                  Backend connection problem
                </div>
                <div>{error}</div>
              </div>

              <button
                onClick={loadAllData}
                className="inline-flex items-center gap-1 border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            </div>
          )}

          {loading && !dashboard ? (
            <LoadingState />
          ) : (
            <>
              {activeTab === "overview" && (
                <OverviewTab
                  dashboard={dashboard}
                  interviews={dayInterviews}
                  rooms={rooms}
                  panels={panels}
                  replanLog={replanLog}
                  onTriggerReplan={() => setShowReplanModal(true)}
                  onOpenSchedule={() => setActiveTab("schedule")}
                />
              )}

              {activeTab === "schedule" && (
                <SchedulePage
                  interviews={dayInterviews}
                  selectedDate={selectedDate}
                  selectedDay={selectedDay}
                />
              )}

              {activeTab === "students" && (
                <StudentsPage students={students} />
              )}

              {activeTab === "companies" && (
                <CompaniesPage companies={companies} />
              )}

              {activeTab === "rooms" && <RoomsPage rooms={rooms} />}

              {activeTab === "panels" && <PanelsPage panels={panels} />}

              {activeTab === "disruptions" && (
                <DisruptionsPage
                  onTriggerReplan={() => setShowReplanModal(true)}
                />
              )}

              {activeTab === "history" && (
                <HistoryPage logs={replanLog} onRestoreBaseline={handleRestoreBaseline} />
              )}

              {activeTab === "metrics" && <MetricsPage metrics={metrics} />}
            </>
          )}
        </main>
      </div>

      {showReplanModal && (
        <ReplanModal
          onClose={() => setShowReplanModal(false)}
          onCompleted={async () => {
            await loadAllData();
          }}
        />
      )}
    </div>
  );
}

function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "schedule", label: "Live Schedule", icon: CalendarDays },
    { id: "students", label: "Students", icon: Users },
    { id: "companies", label: "Companies", icon: Building },
    { id: "rooms", label: "Rooms", icon: MapPin },
    { id: "panels", label: "Panels", icon: UsersRound },
    { id: "disruptions", label: "Disruptions", icon: AlertOctagon },
    { id: "history", label: "Replan History", icon: History },
    { id: "metrics", label: "Metrics", icon: BarChart3 },
  ];

  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-slate-800 bg-[var(--sidebar)] text-[var(--sidebar-foreground)]">
      <div className="flex h-14 items-center border-b border-slate-800/60 px-4 font-semibold tracking-tight text-white">
        <div className="mr-3 flex h-6 w-6 items-center justify-center bg-blue-600 text-xs font-bold text-white">
          P
        </div>
        Placement Week
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        <div className="space-y-0.5 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex w-full items-center px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-[var(--sidebar-accent)] font-medium text-white"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                }`}
              >
                <Icon className="mr-3 h-4 w-4 shrink-0" />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-4 border-t border-slate-800/60 p-4 text-sm">
        <div className="flex items-center text-xs font-medium text-green-400">
          <div className="mr-2 h-2 w-2 rounded-full bg-green-500" />
          All systems operational
        </div>

        <div className="flex items-center text-slate-300">
          <div className="mr-3 flex h-8 w-8 items-center justify-center bg-slate-700 text-xs font-semibold">
            PR
          </div>

          <div className="flex-1 overflow-hidden">
            <div className="truncate font-medium text-white">Priyanshu</div>
            <div className="truncate text-xs text-slate-500">
              Placement Coordinator
            </div>
          </div>

          <Settings className="h-4 w-4 cursor-pointer text-slate-500 hover:text-white" />
        </div>
      </div>
    </aside>
  );
}

function TopBar({ selectedDay, setSelectedDay, totalDays, placementDates, onOpenNotifications, notificationCount }) {
  return (
    <header className="z-10 flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] bg-white px-6">
      <div className="flex flex-1 items-center space-x-4">
        <h1 className="text-lg font-semibold tracking-tight text-[var(--foreground)]">
          Placement Operations
        </h1>

        <label className="border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          <select
            value={selectedDay}
            onChange={(event) => setSelectedDay(Number(event.target.value))}
            className="bg-transparent pr-1 text-xs font-medium text-slate-600 outline-none"
          >
            {Array.from({ length: totalDays }, (_, index) => {
              const day = index + 1;
              const date = placementDates[index];

              return (
                <option key={day} value={day}>
                  {date ? `Day ${day} — ${formatDateLabel(date)}` : `Day ${day}`}
                </option>
              );
            })}
          </select>
        </label>
      </div>

      <div className="mx-4 flex w-full max-w-md flex-1 justify-center">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search student, company, room or interview..."
            className="w-full border border-slate-200 bg-slate-50 py-1.5 pl-9 pr-4 text-sm text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex flex-1 items-center justify-end">
        <button
          onClick={onOpenNotifications}
          className="relative rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          title="Notifications"
        >
          <Bell className="h-5 w-5" />

          {notificationCount > 0 && (
            <span className="absolute right-0 top-0 h-2 w-2 rounded-full border border-white bg-red-500" />
          )}
        </button>
      </div>
    </header>
  );
}

function NotificationPanel({ logs, onClose, onOpenHistory }) {
  const recentLogs = logs.slice(0, 8);

  return (
    <div className="absolute right-6 top-16 z-40 w-[380px] border border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h3 className="font-semibold text-slate-900">Notifications</h3>
          <p className="text-xs text-slate-500">
            Recent scheduling activity
          </p>
        </div>

        <button
          onClick={onClose}
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="max-h-[420px] overflow-y-auto">
        {recentLogs.length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-500">
            No scheduling notifications.
          </div>
        ) : (
          recentLogs.map((log) => (
            <div
              key={log.id}
              className="border-b border-slate-100 px-4 py-3 hover:bg-slate-50"
            >
              <div className="text-sm font-medium text-slate-900">
                Interview {log.interview_id}
              </div>

              <div className="mt-1 text-xs text-slate-500">
                {log.reason || "Schedule updated"}
              </div>

              <div className="mt-1 font-mono text-[10px] text-slate-400">
                {log.old_start_time
                  ? formatDateTime(log.old_start_time)
                  : "Recent update"}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3">
        <button
          onClick={onOpenHistory}
          className="text-xs font-medium text-blue-600 hover:text-blue-800"
        >
          View full history
        </button>

        <button
          onClick={onClose}
          className="text-xs font-medium text-slate-600 hover:text-slate-900"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function OverviewTab({
  dashboard,
  interviews,
  rooms,
  panels,
  replanLog,
  onTriggerReplan,
  onOpenSchedule,
}) {
  const scheduled = dashboard?.scheduled ?? 0;
  const studentsServed = dashboard?.students_served ?? 0;
  const companies = dashboard?.companies ?? 0;

  const roomsTotal =
    dashboard?.rooms_total ??
    dashboard?.rooms ??
    rooms.length ??
    0;

  const roomsOperational =
    dashboard?.rooms_operational ??
    rooms.filter((room) => room.status !== "offline").length;

  const conflicts = dashboard?.conflicts ?? 0;

  return (
    <div className="mx-auto max-w-[1600px] space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Live Dashboard
          </h2>

          <p className="mt-1 text-slate-500">
            Live placement status and upcoming coordination actions
          </p>
        </div>

        <div className="flex space-x-3">
          <button
            onClick={onOpenSchedule}
            className="border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          >
            View Full Schedule
          </button>

          <button
            onClick={onTriggerReplan}
            className="flex items-center bg-[var(--critical)] px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700"
          >
            <AlertOctagon className="mr-2 h-4 w-4" />
            Trigger Replan
          </button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <KPICard
          title="Scheduled Interviews"
          value={Number(scheduled).toLocaleString()}
          subtext="Current schedule"
        />

        <KPICard
          title="Students Served"
          value={Number(studentsServed).toLocaleString()}
          subtext="Active candidates"
        />

        <KPICard
          title="Active Companies"
          value={Number(companies).toLocaleString()}
          subtext="Across placement week"
        />

        <KPICard
          title="Rooms"
          value={`${roomsOperational} / ${roomsTotal}`}
          subtext={
            roomsOperational === roomsTotal
              ? "All operational"
              : `${roomsTotal - roomsOperational} offline`
          }
          status={roomsOperational === roomsTotal ? "healthy" : "warning"}
        />

        <KPICard
          title="Conflicts"
          value={`${conflicts}`}
          subtext={
            conflicts === 0 ? "No detected hard conflicts" : "Review immediately"
          }
          status={conflicts === 0 ? "healthy" : "critical"}
        />
      </div>

      <div className="grid grid-cols-12 items-start gap-6">
        <div className="col-span-12 space-y-6 xl:col-span-8">
          <LiveSchedule interviews={interviews} />
        </div>

        <div className="col-span-12 space-y-6 xl:col-span-4">
          <NeedsAttention
            replanLog={replanLog}
            onTriggerReplan={onTriggerReplan}
          />

          <ResourceStatus rooms={rooms} panels={panels} />

          <UpcomingInterviews interviews={interviews} />
        </div>
      </div>
    </div>
  );
}

function KPICard({ title, value, subtext, status }) {
  return (
    <div className="flex flex-col justify-between border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-1 text-sm font-medium text-slate-500">{title}</div>

      <div className="mb-1 text-2xl font-bold tracking-tight text-slate-900">
        {value}
      </div>

      <div className="mt-auto flex items-center text-xs text-slate-500">
        {status && (
          <span
            className={`mr-2 h-2 w-2 rounded-full ${
              status === "healthy"
                ? "bg-green-500"
                : status === "warning"
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
          />
        )}

        {subtext}
      </div>
    </div>
  );
}

function LiveSchedule({ interviews }) {
  const [companyFilter, setCompanyFilter] = useState("All Companies");
  const [roomFilter, setRoomFilter] = useState("All Rooms");
  const [statusFilter, setStatusFilter] = useState("All Status");

  const companies = useMemo(() => {
    return [
      "All Companies",
      ...Array.from(
        new Set(
          interviews
            .map((row) => row.company_name)
            .filter(Boolean)
        )
      ).sort(),
    ];
  }, [interviews]);

  const rooms = useMemo(() => {
    return [
      "All Rooms",
      ...Array.from(
        new Set(
          interviews
            .map((row) => row.room_name)
            .filter(Boolean)
        )
      ).sort(),
    ];
  }, [interviews]);

  const statuses = useMemo(() => {
    return [
      "All Status",
      ...Array.from(
        new Set(interviews.map((row) => String(row.status || "scheduled")))
      ).sort(),
    ];
  }, [interviews]);

  const filteredRows = useMemo(() => {
    return interviews
      .filter((row) => {
        const companyMatch =
          companyFilter === "All Companies" ||
          row.company_name === companyFilter;

        const roomMatch =
          roomFilter === "All Rooms" || row.room_name === roomFilter;

        const statusMatch =
          statusFilter === "All Status" ||
          String(row.status || "scheduled") === statusFilter;

        return companyMatch && roomMatch && statusMatch;
      })
      .sort((a, b) => {
        return (
          new Date(a.start_time).getTime() -
          new Date(b.start_time).getTime()
        );
      });
  }, [interviews, companyFilter, roomFilter, statusFilter]);

  const rows = filteredRows.slice(0, 20);

  return (
    <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 p-4">
        <h3 className="font-semibold text-slate-900">Live Schedule</h3>

        <div className="flex items-center space-x-2">
          <SelectFilter
            value={roomFilter}
            options={rooms}
            onChange={setRoomFilter}
          />

          <SelectFilter
            value={companyFilter}
            options={companies}
            onChange={setCompanyFilter}
          />

          <SelectFilter
            value={statusFilter}
            options={statuses}
            onChange={setStatusFilter}
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 font-mono text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Student</th>
              <th className="px-4 py-3 font-medium">Company</th>
              <th className="px-4 py-3 font-medium">Room</th>
              <th className="px-4 py-3 font-medium">Panel</th>
              <th className="px-4 py-3 font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 font-mono">
            {rows.map((row) => {
              const start = row.start_time ? new Date(row.start_time) : null;
              const end = row.end_time ? new Date(row.end_time) : null;

              return (
                <tr key={row.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-2.5 font-medium text-slate-900">
                    {formatTime(start)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">
                    {row.student_name || `Student ${row.student_id}`}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5 font-medium text-slate-900">
                    {row.company_name || `Company ${row.company_id}`}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">
                    {row.room_name || `Room ${row.room_id ?? "-"}`}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-600">
                    Panel {row.panel_id ?? "-"}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5 text-slate-500">
                    {durationText(start, end)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-2.5">
                    <StatusBadge status={row.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="border-t border-slate-200 bg-slate-50 p-3 text-center text-xs text-slate-500">
        Showing {rows.length} of {filteredRows.length} matching interviews
      </div>
    </div>
  );
}

function SelectFilter({ value, options, onChange }) {
  return (
    <label className="flex items-center border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-600 shadow-sm">
      <Filter className="mr-1.5 h-3 w-3 text-slate-400" />

      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="bg-transparent text-xs outline-none"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function NeedsAttention({ replanLog, onTriggerReplan }) {
  const recent = replanLog.slice(0, 3);

  return (
    <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-4">
        <h3 className="font-semibold text-slate-900">Needs Attention</h3>
      </div>

      <div className="space-y-3 bg-slate-50 p-4">
        <div className="border border-[var(--critical-border)] bg-[var(--critical-light)] p-3 shadow-sm">
          <div className="mb-2 flex items-center text-xs font-bold uppercase tracking-wider text-[var(--critical)]">
            <AlertOctagon className="mr-1.5 h-3.5 w-3.5" />
            Replan
          </div>

          <div className="mb-0.5 text-sm font-semibold text-slate-900">
            Need to handle a disruption?
          </div>

          <div className="mb-3 text-sm text-slate-600">
            Use the replanner to update the schedule safely.
          </div>

          <button
            onClick={onTriggerReplan}
            className="w-full bg-[var(--critical)] py-1.5 text-xs font-medium text-white hover:bg-red-700"
          >
            Trigger Replan
          </button>
        </div>

        <div className="border border-slate-200 bg-white p-3 shadow-sm">
          <div className="mb-2 flex items-center text-xs font-bold uppercase tracking-wider text-slate-700">
            <History className="mr-1.5 h-3.5 w-3.5" />
            Recent Replan Activity
          </div>

          {recent.length === 0 ? (
            <div className="text-sm text-slate-500">
              No recent replans.
            </div>
          ) : (
            <div className="space-y-2">
              {recent.map((item) => (
                <div
                  key={item.id}
                  className="border-t border-slate-100 pt-2 text-xs"
                >
                  <div className="font-medium text-slate-800">
                    Interview {item.interview_id}
                  </div>
                  <div className="text-slate-500">
                    {item.reason || "Schedule updated"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResourceStatus({ rooms, panels }) {
  const roomPreview = rooms.slice(0, 8);

  const panelMap = new Map();

  panels.forEach((panel) => {
    const key = panel.company_name || `Company ${panel.company_id}`;

    if (!panelMap.has(key)) {
      panelMap.set(key, {
        total: 0,
        available: 0,
      });
    }

    const entry = panelMap.get(key);
    entry.total += 1;

    if (panel.status === "available") {
      entry.available += 1;
    }
  });

  const panelPreview = Array.from(panelMap.entries()).slice(0, 8);

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
            Room Status
          </h3>
        </div>

        <div className="max-h-[220px] space-y-2 overflow-y-auto p-3 font-mono text-sm">
          {roomPreview.map((room) => {
            const offline =
              String(room.status || "").toLowerCase() === "offline";

            const inUse =
              Number(room.scheduled_interviews || 0) > 0 && !offline;

            return (
              <div
                key={room.id}
                className="flex items-center justify-between"
              >
                <span className="text-slate-600">
                  {room.name || `Room-${String(room.id).padStart(2, "0")}`}
                </span>

                <span
                  className={`flex items-center text-xs ${
                    offline
                      ? "text-red-600"
                      : inUse
                      ? "text-blue-600"
                      : "text-green-600"
                  }`}
                >
                  <span
                    className={`mr-1.5 h-1.5 w-1.5 rounded-full ${
                      offline
                        ? "bg-red-500"
                        : inUse
                        ? "bg-blue-500"
                        : "bg-green-500"
                    }`}
                  />

                  {offline ? "Offline" : inUse ? "In use" : "Available"}
                </span>
              </div>
            );
          })}
        </div>

        <div className="border-t border-slate-200 bg-slate-50 p-2 text-center text-[11px] text-slate-500">
          Showing {Math.min(8, rooms.length)} of {rooms.length} rooms
        </div>
      </div>

      <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
            Panel Status
          </h3>
        </div>

        <div className="max-h-[220px] space-y-2 overflow-y-auto p-3 font-mono text-sm">
          {panelPreview.map(([company, stat]) => (
            <div
              key={company}
              className="flex items-center justify-between"
            >
              <span className="truncate pr-2 text-slate-600">{company}</span>

              <span
                className={`text-xs font-semibold ${
                  stat.available === stat.total
                    ? "text-green-600"
                    : stat.available > 0
                    ? "text-amber-600"
                    : "text-red-600"
                }`}
              >
                {stat.available}/{stat.total} available
              </span>
            </div>
          ))}
        </div>

        <div className="border-t border-slate-200 bg-slate-50 p-2 text-center text-[11px] text-slate-500">
          {panels.length} panels configured
        </div>
      </div>
    </div>
  );
}

function UpcomingInterviews({ interviews }) {
  const upcoming = [...interviews]
    .filter((row) => row.start_time)
    .sort(
      (a, b) =>
        new Date(a.start_time).getTime() -
        new Date(b.start_time).getTime()
    )
    .slice(0, 5);

  return (
    <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 p-3">
        <h3 className="font-semibold text-slate-900">
          Next Scheduled Interviews
        </h3>

        <span className="text-xs text-slate-500">
          {upcoming.length} shown
        </span>
      </div>

      <div className="divide-y divide-slate-100 font-mono text-xs">
        {upcoming.map((row) => (
          <div
            key={row.id}
            className="flex items-center p-3 hover:bg-slate-50"
          >
            <div className="w-14 font-bold text-slate-900">
              {formatTime(new Date(row.start_time))}
            </div>

            <div className="flex-1">
              <div className="font-medium text-slate-900">
                {row.student_name || `Student ${row.student_id}`}
              </div>

              <div className="text-slate-500">
                {row.company_name || `Company ${row.company_id}`} •{" "}
                {row.room_name || `Room ${row.room_id}`} • Panel{" "}
                {row.panel_id ?? "-"}
              </div>
            </div>
          </div>
        ))}

        {upcoming.length === 0 && (
          <div className="p-4 text-center text-slate-500">
            No scheduled interviews available.
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || "scheduled").toLowerCase();

  let classes = "bg-slate-100 text-slate-600 border-slate-200";

  if (normalized === "scheduled") {
    classes = "bg-slate-100 text-slate-600 border-slate-200";
  } else if (normalized === "cancelled") {
    classes = "bg-red-100 text-red-700 border-red-200";
  } else if (normalized === "affected") {
    classes = "bg-amber-100 text-amber-700 border-amber-200";
  } else if (normalized === "completed") {
    classes = "bg-green-100 text-green-700 border-green-200";
  }

  return (
    <span
      className={`inline-flex border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${classes}`}
    >
      {normalized}
    </span>
  );
}

function SchedulePage({ interviews, selectedDate, selectedDay }) {
  return (
    <div className="space-y-5">
      <PageHeader
        title="Live Schedule"
        subtitle={
          selectedDate
            ? `Day ${selectedDay} — ${formatDateLabel(selectedDate)}`
            : "Full interview schedule from the live database"
        }
      />

      <LiveSchedule interviews={interviews} />
    </div>
  );
}

function StudentsPage({ students }) {
  const [query, setQuery] = useState("");

  const filtered = students.filter((student) => {
    const text = [
      student.id,
      student.name,
      student.branch,
    ]
      .join(" ")
      .toLowerCase();

    return text.includes(query.toLowerCase());
  });

  return (
    <div className="space-y-5">
      <PageHeader
        title="Students"
        subtitle={`${students.length} students loaded from the backend`}
      />

      <div className="border border-slate-200 bg-white p-4 shadow-sm">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search student..."
            className="w-full border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">CGPA</th>
              <th className="px-4 py-3">Branch</th>
              <th className="px-4 py-3">Shortlisted</th>
              <th className="px-4 py-3">Scheduled</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {filtered.slice(0, 100).map((student) => (
              <tr key={student.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-mono">{student.id}</td>

                <td className="px-4 py-3 font-medium text-slate-900">
                  {student.name || `Student ${student.id}`}
                </td>

                <td className="px-4 py-3">
                  {student.cgpa != null
                    ? Number(student.cgpa).toFixed(2)
                    : "-"}
                </td>

                <td className="px-4 py-3">{student.branch || "-"}</td>

                <td className="px-4 py-3">
                  {student.shortlisted_companies ?? 0}
                </td>

                <td className="px-4 py-3">
                  {student.scheduled_interviews ?? 0}
                </td>

                <td className="px-4 py-3">
                  <StatusBadge status={student.status || "active"} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="border-t border-slate-200 bg-slate-50 p-3 text-center text-xs text-slate-500">
          Showing {Math.min(100, filtered.length)} of {filtered.length} matching students
        </div>
      </div>
    </div>
  );
}

function CompaniesPage({ companies }) {
  const [query, setQuery] = useState("");

  const filtered = companies.filter((company) =>
    String(company.name || "")
      .toLowerCase()
      .includes(query.toLowerCase())
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="Companies"
        subtitle={`${companies.length} companies loaded from the backend`}
      />

      <div className="border border-slate-200 bg-white p-4 shadow-sm">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />

          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search company..."
            className="w-full border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </div>
      </div>

      <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Tier</th>
              <th className="px-4 py-3">Day</th>
              <th className="px-4 py-3">Panels</th>
              <th className="px-4 py-3">Shortlisted</th>
              <th className="px-4 py-3">Scheduled</th>
              <th className="px-4 py-3">Duration</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {filtered.map((company) => (
              <tr key={company.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">
                  {company.name}
                </td>

                <td className="px-4 py-3">
                  Tier {company.priority_tier ?? "-"}
                </td>

                <td className="px-4 py-3">
                  Day {company.placement_day ?? "-"}
                </td>

                <td className="px-4 py-3">
                  {company.actual_panels ?? company.panels ?? 0}/
                  {company.panels ?? 0}
                </td>

                <td className="px-4 py-3">
                  {company.shortlisted ?? 0}
                </td>

                <td className="px-4 py-3">
                  {company.scheduled ?? 0}
                </td>

                <td className="px-4 py-3">
                  {company.interview_duration_min ?? "-"} min
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RoomsPage({ rooms }) {
  return (
    <div className="space-y-5">
      <PageHeader
        title="Rooms"
        subtitle={`${rooms.length} configured rooms`}
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {rooms.map((room) => {
          const offline =
            String(room.status || "").toLowerCase() === "offline";

          const count = Number(room.scheduled_interviews || 0);

          return (
            <div
              key={room.id}
              className={`border bg-white p-4 shadow-sm ${
                offline ? "border-red-200" : "border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-900">
                  {room.name || `Room-${String(room.id).padStart(2, "0")}`}
                </div>

                <span
                  className={`text-[10px] font-bold uppercase ${
                    offline ? "text-red-600" : "text-green-600"
                  }`}
                >
                  {offline ? "Offline" : "Operational"}
                </span>
              </div>

              <div className="mt-2 text-xs text-slate-500">
                {count} scheduled interviews
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PanelsPage({ panels }) {
  return (
    <div className="space-y-5">
      <PageHeader
        title="Panels"
        subtitle={`${panels.length} panels loaded from the backend`}
      />

      <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Panel</th>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Scheduled</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {panels.map((panel) => {
              const unavailable =
                String(panel.status || "").toLowerCase() !== "available";

              return (
                <tr key={panel.id}>
                  <td className="px-4 py-3 font-mono">
                    Panel {panel.id}
                  </td>

                  <td className="px-4 py-3">
                    {panel.company_name || `Company ${panel.company_id}`}
                  </td>

                  <td
                    className={`px-4 py-3 font-medium ${
                      unavailable ? "text-red-600" : "text-green-600"
                    }`}
                  >
                    {panel.status || "available"}
                  </td>

                  <td className="px-4 py-3">
                    {panel.scheduled_interviews ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DisruptionsPage({ onTriggerReplan }) {
  return (
    <div className="space-y-5">
      <PageHeader
        title="Disruptions"
        subtitle="Coordinator controls for live schedule changes"
      />

      <div className="grid grid-cols-2 gap-4">
        <ActionCard
          title="Company Delay"
          description="Shift a company's interviews after a late arrival."
          button="Start Company Delay"
          onClick={onTriggerReplan}
          danger
        />

        <ActionCard
          title="Panel Unavailable"
          description="Drop a panel and repair or cancel affected interviews."
          button="Drop Panel"
          onClick={onTriggerReplan}
        />

        <ActionCard
          title="Room Unavailable"
          description="Take a room offline and attempt to reassign interviews."
          button="Take Room Offline"
          onClick={onTriggerReplan}
        />

        <ActionCard
          title="Student Withdrawal"
          description="Cancel the student's scheduled interviews immediately."
          button="Withdraw Student"
          onClick={onTriggerReplan}
        />
      </div>
    </div>
  );
}

function ActionCard({ title, description, button, onClick, danger }) {
  return (
    <div className="border border-slate-200 bg-white p-5 shadow-sm">
      <div
        className={`mb-2 text-lg font-semibold ${
          danger ? "text-red-700" : "text-slate-900"
        }`}
      >
        {title}
      </div>

      <p className="mb-4 text-sm text-slate-500">{description}</p>

      <button
        onClick={onClick}
        className={`px-4 py-2 text-sm font-medium text-white ${
          danger ? "bg-red-600 hover:bg-red-700" : "bg-slate-900 hover:bg-slate-800"
        }`}
      >
        {button}
      </button>
    </div>
  );
}

function HistoryPage({ logs, onRestoreBaseline }) {
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <PageHeader
          title="Replan History"
          subtitle={`${logs.length} logged schedule changes`}
        />

        <button
          type="button"
          onClick={onRestoreBaseline}
          className="border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-800 shadow-sm transition-colors hover:bg-amber-50"
        >
          Restore Baseline
        </button>
      </div>

      <div className="overflow-hidden border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Interview</th>
              <th className="px-4 py-3">Old</th>
              <th className="px-4 py-3">New</th>
              <th className="px-4 py-3">Reason</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="px-4 py-3 font-mono text-xs">
                  {log.interview_id}
                </td>

                <td className="px-4 py-3 font-mono text-xs text-slate-600">
                  {formatHistoryLocation(
                    log.old_room_id,
                    log.old_panel_id,
                    log.old_start_time,
                    log.old_end_time
                  )}
                </td>

                <td className="px-4 py-3 font-mono text-xs text-slate-600">
                  {log.new_start_time
                    ? formatHistoryLocation(
                        log.new_room_id,
                        log.new_panel_id,
                        log.new_start_time,
                        log.new_end_time
                      )
                    : "CANCELLED"}
                </td>

                <td className="px-4 py-3 text-slate-600">
                  {log.reason || "Schedule updated"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {logs.length === 0 && (
          <div className="p-8 text-center text-sm text-slate-500">
            No replan history yet.
          </div>
        )}
      </div>
    </div>
  );
}

function MetricsPage({ metrics }) {
  if (!metrics) {
    return <LoadingState />;
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Metrics"
        subtitle="Current scheduling and fairness metrics"
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KPICard
          title="Scheduled"
          value={Number(metrics.scheduled || 0).toLocaleString()}
          subtext={`${Number(metrics.scheduling_rate || 0).toFixed(2)}% rate`}
        />

        <KPICard
          title="Unscheduled"
          value={Number(metrics.unscheduled || 0).toLocaleString()}
          subtext="Shortlist entries not scheduled"
        />

        <KPICard
          title="Cancelled"
          value={Number(metrics.cancelled || 0).toLocaleString()}
          subtext="Cancelled by disruption"
          status={Number(metrics.cancelled || 0) > 0 ? "warning" : "healthy"}
        />

        <KPICard
          title="Students Served"
          value={Number(metrics.students_served || 0).toLocaleString()}
          subtext="Students with interviews"
        />

        <KPICard
          title="Average Interviews"
          value={Number(metrics.average_interviews || 0).toFixed(2)}
          subtext={`Maximum ${metrics.maximum_interviews ?? 0}`}
        />

        <KPICard
          title="Room Utilization"
          value={`${Number(metrics.room_utilization || 0).toFixed(2)}%`}
          subtext="Scheduled room capacity used"
        />

        <KPICard
          title="Panel Utilization"
          value={`${Number(metrics.panel_utilization || 0).toFixed(2)}%`}
          subtext="Scheduled panel capacity used"
        />

        <KPICard
          title="Average Wait"
          value={`${Number(metrics.average_wait_minutes || 0).toFixed(1)} min`}
          subtext={`Maximum ${Number(metrics.maximum_wait_minutes || 0).toFixed(0)} min`}
        />

        {metrics.replan_churn != null && (
          <KPICard
            title="Replan Churn"
            value={`${Number(metrics.replan_churn).toFixed(2)}%`}
            subtext="Changed / baseline scheduled"
          />
        )}
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <div className="border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900">
            Constraint Validation
          </h3>

          <div className="mt-4 space-y-3">
            <MetricRow
              label="Student conflicts"
              value={metrics.student_conflicts ?? 0}
              good={Number(metrics.student_conflicts ?? 0) === 0}
            />

            <MetricRow
              label="Room conflicts"
              value={metrics.room_conflicts ?? 0}
              good={Number(metrics.room_conflicts ?? 0) === 0}
            />

            <MetricRow
              label="Panel conflicts"
              value={metrics.panel_conflicts ?? 0}
              good={Number(metrics.panel_conflicts ?? 0) === 0}
            />
          </div>
        </div>

        <div className="border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900">
            Replanning
          </h3>

          <div className="mt-4 space-y-3">
            <MetricRow
              label="Affected interviews"
              value={metrics.replan_affected ?? 0}
            />

            <MetricRow
              label="Repaired interviews"
              value={metrics.replan_repaired ?? 0}
            />

            <MetricRow
              label="Cancelled interviews"
              value={metrics.replan_cancelled ?? 0}
            />

            <MetricRow
              label="Maximum displacement"
              value={`${Number(metrics.maximum_displacement || 0)} min`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricRow({ label, value, good = false }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 pb-2 last:border-b-0">
      <span className="text-sm text-slate-600">{label}</span>

      <span
        className={`text-sm font-semibold ${
          good ? "text-green-600" : "text-slate-900"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function PageHeader({ title, subtitle }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">
        {title}
      </h2>

      <p className="mt-1 text-sm text-slate-500">
        {subtitle || "Live placement operations"}
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex min-h-[500px] items-center justify-center">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <RefreshCw className="h-4 w-4 animate-spin" />
        Loading placement data...
      </div>
    </div>
  );
}

function ReplanModal({ onClose, onCompleted }) {
  const [step, setStep] = useState(1);
  const [type, setType] = useState("company-delay");

  const [companyId, setCompanyId] = useState(2);
  const [delayMinutes, setDelayMinutes] = useState(60);

  const [panelId, setPanelId] = useState(4);
  const [roomId, setRoomId] = useState(12);
  const [studentId, setStudentId] = useState(788);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [localError, setLocalError] = useState("");

  async function runReplan() {
    setRunning(true);
    setLocalError("");

    try {
      let response;

      if (type === "company-delay") {
        response = await delayCompany(
          companyId,
          delayMinutes
        );
      } else if (type === "panel-drop") {
        response = await dropPanel(panelId);
      } else if (type === "room-offline") {
        response = await offlineRoom(roomId);
      } else {
        response = await withdrawStudent(studentId);
      }

      setResult(response);
      setStep(4);

      await onCompleted();
    } catch (err) {
      setLocalError(err?.message || "Replan failed.");
    } finally {
      setRunning(false);
    }
  }

  const title =
    type === "company-delay"
      ? "Company Delay"
      : type === "panel-drop"
      ? "Panel Unavailable"
      : type === "room-offline"
      ? "Room Unavailable"
      : "Student Withdrawal";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col border border-slate-200 bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Trigger Replan
            </h2>

            <p className="mt-0.5 font-mono text-xs text-slate-500">
              STEP {step} OF 4
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {localError && (
            <div className="mb-5 flex items-start gap-2 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{localError}</span>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-slate-900">
                Select Disruption Type
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <DisruptionChoice
                  title="Company Delay"
                  description="Company running behind schedule"
                  active={type === "company-delay"}
                  onClick={() => {
                    setType("company-delay");
                    setStep(2);
                  }}
                  danger
                />

                <DisruptionChoice
                  title="Panel Unavailable"
                  description="Interviewer dropped or absent"
                  active={type === "panel-drop"}
                  onClick={() => {
                    setType("panel-drop");
                    setStep(2);
                  }}
                />

                <DisruptionChoice
                  title="Student Withdrawal"
                  description="Candidate no-show or dropout"
                  active={type === "student-withdrawal"}
                  onClick={() => {
                    setType("student-withdrawal");
                    setStep(2);
                  }}
                />

                <DisruptionChoice
                  title="Room Unavailable"
                  description="Physical room offline"
                  active={type === "room-offline"}
                  onClick={() => {
                    setType("room-offline");
                    setStep(2);
                  }}
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h3 className="font-semibold text-slate-900">
                  {title}
                </h3>

                <p className="mt-1 text-sm text-slate-500">
                  Enter the identifier used by the scheduler.
                </p>
              </div>

              {type === "company-delay" && (
                <>
                  <FormField label="Company ID">
                    <input
                      type="number"
                      value={companyId}
                      min="1"
                      onChange={(event) =>
                        setCompanyId(Number(event.target.value))
                      }
                      className="w-full border border-slate-300 p-2 text-sm outline-none focus:border-blue-500"
                    />
                  </FormField>

                  <FormField label="Delay Minutes">
                    <input
                      type="number"
                      value={delayMinutes}
                      min="0"
                      onChange={(event) =>
                        setDelayMinutes(Number(event.target.value))
                      }
                      className="w-full border border-slate-300 p-2 text-sm outline-none focus:border-blue-500"
                    />
                  </FormField>
                </>
              )}

              {type === "panel-drop" && (
                <FormField label="Panel ID">
                  <input
                    type="number"
                    value={panelId}
                    min="1"
                    onChange={(event) =>
                      setPanelId(Number(event.target.value))
                    }
                    className="w-full border border-slate-300 p-2 text-sm outline-none focus:border-blue-500"
                  />
                </FormField>
              )}

              {type === "room-offline" && (
                <FormField label="Room ID">
                  <input
                    type="number"
                    value={roomId}
                    min="1"
                    onChange={(event) =>
                      setRoomId(Number(event.target.value))
                    }
                    className="w-full border border-slate-300 p-2 text-sm outline-none focus:border-blue-500"
                  />
                </FormField>
              )}

              {type === "student-withdrawal" && (
                <FormField label="Student ID">
                  <input
                    type="number"
                    value={studentId}
                    min="1"
                    onChange={(event) =>
                      setStudentId(Number(event.target.value))
                    }
                    className="w-full border border-slate-300 p-2 text-sm outline-none focus:border-blue-500"
                  />
                </FormField>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <h3 className="font-semibold text-slate-900">
                Confirm Replan
              </h3>

              <div className="border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm font-medium text-slate-900">
                  {type === "company-delay" &&
                    `Company ${companyId} delayed by ${delayMinutes} minutes`}
                  {type === "panel-drop" &&
                    `Panel ${panelId} unavailable`}
                  {type === "room-offline" &&
                    `Room ${roomId} unavailable`}
                  {type === "student-withdrawal" &&
                    `Student ${studentId} withdrawn`}
                </div>

                <div className="mt-3 flex items-start gap-2 text-sm text-blue-800">
                  <Info className="mt-0.5 h-4 w-4 shrink-0" />

                  <span>
                    The backend replanner will preserve unaffected
                    interviews and only change appointments where a
                    valid recovery is possible.
                  </span>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-6">
              <div className="flex items-center text-lg font-bold text-green-600">
                <CheckCircle2 className="mr-2 h-6 w-6" />
                Replan completed
              </div>

              <div className="grid grid-cols-2 gap-4 border border-slate-200 bg-slate-50 p-4 md:grid-cols-4">
                <ResultItem
                  label="Status"
                  value={result?.status || "completed"}
                />

                <ResultItem
                  label="Type"
                  value={result?.type || type}
                />

                <ResultItem
                  label="Affected"
                  value={result?.affected ?? "See History"}
                />

                <ResultItem
                  label="Repaired"
                  value={result?.repaired ?? "See History"}
                />

                <ResultItem
                  label="Cancelled"
                  value={result?.cancelled ?? "See History"}
                />

                <ResultItem
                  label="Max Displacement"
                  value={
                    result?.max_displacement != null
                      ? `${result.max_displacement} min`
                      : "See Metrics"
                  }
                />
              </div>

              <div className="flex items-start gap-2 border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Review Replan History for the complete OLD → NEW
                  appointment diff.
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="flex shrink-0 justify-end gap-3 border-t border-slate-200 bg-slate-50 p-4">
          {step !== 4 && (
            <button
              onClick={onClose}
              className="border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
          )}

          {step === 1 && (
            <button
              onClick={() => setStep(2)}
              className="bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Continue
            </button>
          )}

          {step === 2 && (
            <button
              onClick={() => setStep(3)}
              className="bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Review
            </button>
          )}

          {step === 3 && (
            <button
              onClick={runReplan}
              disabled={running}
              className="flex items-center bg-[var(--critical)] px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <AlertOctagon className="mr-2 h-4 w-4" />
              {running ? "Running..." : "Run Replan"}
            </button>
          )}

          {step === 4 && (
            <button
              onClick={onClose}
              className="bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function DisruptionChoice({
  title,
  description,
  active,
  onClick,
  danger = false,
}) {
  return (
    <button
      onClick={onClick}
      className={`border p-4 text-left transition-colors ${
        active
          ? danger
            ? "border-red-300 bg-red-50"
            : "border-blue-300 bg-blue-50"
          : "border-slate-200 hover:border-slate-400"
      }`}
    >
      <div
        className={`mb-1 font-bold ${
          danger ? "text-red-700" : "text-slate-900"
        }`}
      >
        {title}
      </div>

      <div className="text-sm text-slate-600">
        {description}
      </div>
    </button>
  );
}

function FormField({ label, children }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
    </div>
  );
}

function ResultItem({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </div>

      <div className="mt-1 font-semibold text-slate-900">
        {String(value)}
      </div>
    </div>
  );
}

function formatDateLabel(isoDate) {
  if (!isoDate) return "";

  try {
    const date = new Date(`${isoDate}T00:00:00`);
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

function formatTime(value) {
  if (!value) return "--:--";

  try {
    return value.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return "--:--";
  }
}

function formatDateTime(value) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return "—";
  }
}

function formatHistoryLocation(roomId, panelId, start, end) {
  if (!start) return "—";

  return `Rm ${roomId ?? "-"} • Pan ${panelId ?? "-"} • ${formatTime(
    new Date(start)
  )}-${end ? formatTime(new Date(end)) : "--:--"}`;
}

function durationText(start, end) {
  if (!start || !end) return "—";

  const minutes = Math.round(
    (end.getTime() - start.getTime()) / 60000
  );

  return `${minutes} min`;
}
