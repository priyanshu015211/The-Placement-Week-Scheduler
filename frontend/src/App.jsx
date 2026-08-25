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
} from "lucide-react";

import {
  getDashboard,
  getInterviews,
  getRooms,
  getPanels,
  getReplanLog,
  getStudents,
  getCompanies,
  getMetrics,
  delayCompany,
  dropPanel,
  offlineRoom,
  withdrawStudent,
} from "./api";
export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [showReplanModal, setShowReplanModal] = useState(false);
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

  async function loadData() {
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
      setInterviews(interviewRows);
      setRooms(roomRows);
      setPanels(panelRows);
      setStudents(studentRows);
      setCompanies(companyRows);
      setMetrics(metricData);
      setReplanLog(logRows);
    } catch (err) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 30000);
    return () => clearInterval(timer);
  }, []);

  function closeReplan() {
    setShowReplanModal(false);
  }

  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] font-sans antialiased">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <TopBar />

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6">
          {error && (
            <div className="mb-5 flex items-start gap-3 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <div className="font-semibold">Backend connection problem</div>
                <div>{error}</div>
              </div>
            </div>
          )}

          {loading && !dashboard ? (
            <LoadingState />
          ) : (
            <>
              {activeTab === "overview" && (
                <OverviewTab
                  dashboard={dashboard}
                  interviews={interviews}
                  rooms={rooms}
                  panels={panels}
                  replanLog={replanLog}
                  onTriggerReplan={() => setShowReplanModal(true)}
                />
              )}

              {activeTab === "schedule" && (
                <SchedulePage interviews={interviews} />
              )}

              {activeTab === "rooms" && <RoomsPage rooms={rooms} />}
              {activeTab === "panels" && <PanelsPage panels={panels} />}
              {activeTab === "history" && <HistoryPage logs={replanLog} />}

              {activeTab === "students" && <StudentsPage students={students} />}

              {activeTab === "companies" && (
                <CompaniesPage companies={companies} />
              )}

              {activeTab === "disruptions" && (
                <DisruptionsPage
                  onTriggerReplan={() => setShowReplanModal(true)}
                />
              )}

              {activeTab === "metrics" && <MetricsPage metrics={metrics} />}
            </>
          )}
        </main>
      </div>

      {showReplanModal && (
        <ReplanModal onClose={closeReplan} onCompleted={loadData} />
      )}
    </div>
  );
}

function navLabel(tab) {
  return {
    students: "Students",
    companies: "Companies",
    disruptions: "Disruptions",
    metrics: "Metrics",
  }[tab];
}

function LoadingState() {
  return (
    <div className="flex h-full min-h-[500px] items-center justify-center">
      <div className="text-sm text-slate-500">Loading placement data...</div>
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
    <div className="flex h-full w-[240px] shrink-0 flex-col border-r border-slate-800 bg-[var(--sidebar)] text-[var(--sidebar-foreground)]">
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
            <div className="truncate text-xs text-slate-500">Coordinator</div>
          </div>
          <Settings className="h-4 w-4 cursor-pointer text-slate-500 hover:text-white" />
        </div>
      </div>
    </div>
  );
}

function TopBar() {
  return (
    <header className="z-10 flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] bg-white px-6">
      <div className="flex flex-1 items-center space-x-4">
        <h1 className="text-lg font-semibold tracking-tight text-[var(--foreground)]">
          Placement Operations
        </h1>
        <div className="border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          Live
        </div>
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

      <div className="flex flex-1 items-center justify-end text-sm font-medium text-slate-600">
        <button className="relative text-slate-400 hover:text-slate-600">
          <Bell className="h-5 w-5" />
          <span className="absolute right-0 top-0 h-2 w-2 rounded-full border border-white bg-red-500" />
        </button>
      </div>
    </header>
  );
}

function OverviewTab({
  dashboard,
  interviews,
  rooms,
  panels,
  replanLog,
  onTriggerReplan,
}) {
  const scheduled = dashboard?.scheduled ?? 0;
  const studentsServed = dashboard?.students_served ?? 0;
  const companies = dashboard?.companies ?? 0;
  const roomCount = dashboard?.rooms ?? rooms.length ?? 0;

  const currentConflicts = dashboard?.conflicts ?? 0;

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
            onClick={() => setActiveTab("schedule")}
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
          value={scheduled.toLocaleString()}
          subtext="Current schedule"
        />
        <KPICard
          title="Students Served"
          value={studentsServed.toLocaleString()}
          subtext="Active candidates"
        />
        <KPICard
          title="Active Companies"
          value={companies.toLocaleString()}
          subtext="Across placement week"
        />
        <KPICard
          title="Rooms"
          value={`${roomCount}`}
          subtext="Configured rooms"
        />
        <KPICard
          title="Conflicts"
          value={`${currentConflicts}`}
          subtext={
            currentConflicts === 0
              ? "No detected hard conflicts"
              : "Review immediately"
          }
          status={currentConflicts === 0 ? "healthy" : "critical"}
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
  const rows = interviews.slice(0, 12);

  return (
    <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 p-4">
        <h3 className="font-semibold text-slate-900">Live Schedule</h3>
        <div className="flex items-center space-x-2">
          <FilterSelect label="All Rooms" />
          <FilterSelect label="All Companies" />
          <FilterSelect label="All Status" />
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
                    {row.company_name}
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
        Showing {rows.length} of {interviews.length} scheduled interviews
      </div>
    </div>
  );
}

function FilterSelect({ label }) {
  return (
    <button className="flex items-center border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-50">
      <Filter className="mr-1.5 h-3 w-3 text-slate-400" />
      {label}
      <ChevronDown className="ml-2 h-3 w-3 text-slate-400" />
    </button>
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
            Use the live replanner to update the schedule safely.
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
            <div className="text-sm text-slate-500">No recent replans.</div>
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
                  <div className="text-slate-500">{item.reason}</div>
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
      panelMap.set(key, { total: 0, available: 0 });
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
            const inUse = Number(room.scheduled_interviews || 0) > 0;

            return (
              <div key={room.id} className="flex items-center justify-between">
                <span className="text-slate-600">{room.name}</span>
                <span
                  className={`flex items-center text-xs ${
                    inUse ? "text-blue-600" : "text-green-600"
                  }`}
                >
                  <span
                    className={`mr-1.5 h-1.5 w-1.5 rounded-full ${
                      inUse ? "bg-blue-500" : "bg-green-500"
                    }`}
                  />
                  {inUse ? "In use" : "Available"}
                </span>
              </div>
            );
          })}
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
            <div key={company} className="flex items-center justify-between">
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
      </div>
    </div>
  );
}

function UpcomingInterviews({ interviews }) {
  const upcoming = [...interviews]
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    .slice(0, 5);

  return (
    <div className="flex flex-col border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 p-3">
        <h3 className="font-semibold text-slate-900">Next 60 Minutes</h3>

        <span className="text-xs text-slate-500">{upcoming.length} shown</span>
      </div>

      <div className="divide-y divide-slate-100 font-mono text-xs">
        {upcoming.map((row) => (
          <div key={row.id} className="flex items-center p-3 hover:bg-slate-50">
            <div className="w-14 font-bold text-slate-900">
              {formatTime(new Date(row.start_time))}
            </div>

            <div className="flex-1">
              <div className="font-medium text-slate-900">
                {row.student_name || `Student ${row.student_id}`}
              </div>

              <div className="text-slate-500">
                {row.company_name} • {row.room_name || `Room ${row.room_id}`} •{" "}
                Panel {row.panel_id}
              </div>
            </div>
          </div>
        ))}
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
  }

  return (
    <span
      className={`inline-flex border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${classes}`}
    >
      {normalized}
    </span>
  );
}

function SchedulePage({ interviews }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Live Schedule" />
      <LiveSchedule interviews={interviews} />
    </div>
  );
}

function RoomsPage({ rooms }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Rooms" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {rooms.map((room) => {
          const count = Number(room.scheduled_interviews || 0);
          return (
            <div
              key={room.id}
              className="border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="text-sm font-semibold text-slate-900">
                {room.name}
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
      <PageHeader title="Panels" />
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
            {panels.map((panel) => (
              <tr key={panel.id}>
                <td className="px-4 py-3">Panel {panel.id}</td>
                <td className="px-4 py-3">{panel.company_name}</td>
                <td className="px-4 py-3">{panel.status}</td>
                <td className="px-4 py-3">{panel.scheduled_interviews}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HistoryPage({ logs }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Replan History" />
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
                <td className="px-4 py-3">{log.interview_id}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  Rm {log.old_room_id ?? "-"} • Pan {log.old_panel_id ?? "-"} •{" "}
                  {formatDateTime(log.old_start_time)}
                </td>
                <td className="px-4 py-3 font-mono text-xs">
                  {log.new_start_time
                    ? `Rm ${log.new_room_id ?? "-"} • Pan ${
                        log.new_panel_id ?? "-"
                      } • ${formatDateTime(log.new_start_time)}`
                    : "CANCELLED"}
                </td>
                <td className="px-4 py-3 text-slate-600">{log.reason}</td>
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

function PageHeader({ title }) {
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">
        {title}
      </h2>
      <p className="mt-1 text-sm text-slate-500">Live placement operations</p>
    </div>
  );
}

function PlaceholderPage({ title }) {
  return (
    <div className="flex min-h-[500px] items-center justify-center">
      <div className="text-center">
        <div className="mb-2 text-lg font-semibold text-slate-900">{title}</div>
        <div className="text-sm text-slate-500">
          This section will be connected to the backend next.
        </div>
      </div>
    </div>
  );
}

function StudentsPage({ students }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Students" />

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
            {students.map((student) => (
              <tr key={student.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-mono">{student.id}</td>

                <td className="px-4 py-3 font-medium text-slate-900">
                  {student.name}
                </td>

                <td className="px-4 py-3">{Number(student.cgpa).toFixed(2)}</td>

                <td className="px-4 py-3">{student.branch}</td>

                <td className="px-4 py-3">{student.shortlisted_companies}</td>

                <td className="px-4 py-3">{student.scheduled_interviews}</td>

                <td className="px-4 py-3">
                  <StatusBadge status={student.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
function CompaniesPage({ companies }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Companies" />

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
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {companies.map((company) => (
              <tr key={company.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">
                  {company.name}
                </td>

                <td className="px-4 py-3">Tier {company.priority_tier}</td>

                <td className="px-4 py-3">Day {company.placement_day}</td>

                <td className="px-4 py-3">
                  {company.actual_panels}/{company.panels}
                </td>

                <td className="px-4 py-3">{company.shortlisted}</td>

                <td className="px-4 py-3">{company.scheduled}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
      <PageHeader title="Metrics" />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KPICard
          title="Scheduled"
          value={metrics.scheduled.toLocaleString()}
          subtext={`${metrics.scheduling_rate.toFixed(2)}% scheduling rate`}
        />

        <KPICard
          title="Unscheduled"
          value={metrics.unscheduled.toLocaleString()}
          subtext="Shortlist entries not scheduled"
        />

        <KPICard
          title="Students Served"
          value={metrics.students_served.toLocaleString()}
          subtext="Students with interviews"
        />

        <KPICard
          title="Avg Interviews"
          value={metrics.average_interviews.toFixed(2)}
          subtext={`Maximum: ${metrics.maximum_interviews}`}
        />
      </div>
    </div>
  );
}
function DisruptionsPage({ onTriggerReplan }) {
  return (
    <div className="space-y-5">
      <PageHeader title="Disruptions" />

      <div className="border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">
          Live disruption control
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Apply a company delay, panel drop, room outage, or student withdrawal
          without modifying the database manually.
        </p>

        <button
          onClick={onTriggerReplan}
          className="mt-5 bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Trigger Replan
        </button>
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
        response = await delayCompany(companyId, Number(delayMinutes));
      } else if (type === "panel-drop") {
        response = await dropPanel(Number(panelId));
      } else if (type === "room-offline") {
        response = await offlineRoom(Number(roomId));
      } else {
        response = await withdrawStudent(Number(studentId));
      }

      setResult(response);
      setStep(4);
      await onCompleted();
    } catch (err) {
      setLocalError(err.message || "Replan failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col border border-slate-200 bg-white shadow-2xl">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Trigger Replan</h2>
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
            <div className="mb-5 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {localError}
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
              <h3 className="font-semibold text-slate-900">
                Disruption Details
              </h3>

              {type === "company-delay" && (
                <>
                  <Field label="Company ID">
                    <input
                      type="number"
                      value={companyId}
                      onChange={(e) => setCompanyId(e.target.value)}
                      className="w-full border border-slate-300 p-2 text-sm"
                    />
                  </Field>

                  <Field label="Delay Minutes">
                    <input
                      type="number"
                      min="0"
                      value={delayMinutes}
                      onChange={(e) => setDelayMinutes(e.target.value)}
                      className="w-full border border-slate-300 p-2 text-sm"
                    />
                  </Field>
                </>
              )}

              {type === "panel-drop" && (
                <Field label="Panel ID">
                  <input
                    type="number"
                    value={panelId}
                    onChange={(e) => setPanelId(e.target.value)}
                    className="w-full border border-slate-300 p-2 text-sm"
                  />
                </Field>
              )}

              {type === "room-offline" && (
                <Field label="Room ID">
                  <input
                    type="number"
                    value={roomId}
                    onChange={(e) => setRoomId(e.target.value)}
                    className="w-full border border-slate-300 p-2 text-sm"
                  />
                </Field>
              )}

              {type === "student-withdrawal" && (
                <Field label="Student ID">
                  <input
                    type="number"
                    value={studentId}
                    onChange={(e) => setStudentId(e.target.value)}
                    className="w-full border border-slate-300 p-2 text-sm"
                  />
                </Field>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <h3 className="font-semibold text-slate-900">Confirm Replan</h3>

              <div className="border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                <div className="font-medium text-slate-900">
                  {type === "company-delay" &&
                    `Company ${companyId} delayed by ${delayMinutes} minutes`}
                  {type === "panel-drop" && `Panel ${panelId} unavailable`}
                  {type === "room-offline" && `Room ${roomId} unavailable`}
                  {type === "student-withdrawal" &&
                    `Student ${studentId} withdrawn`}
                </div>

                <div className="mt-3 flex items-start gap-2">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                  <span>
                    The backend will preserve unaffected interviews, search
                    valid slots, and apply the configured replanning policy.
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

              <div className="border border-slate-200 bg-slate-50 p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <ResultItem label="Type" value={result?.type || type} />
                  <ResultItem
                    label="Status"
                    value={result?.status || "completed"}
                  />
                  <ResultItem
                    label="Affected"
                    value={
                      result?.affected ??
                      result?.repaired + result?.cancelled ??
                      "See replan metrics"
                    }
                  />
                  <ResultItem
                    label="Repaired"
                    value={result?.repaired ?? "See replan metrics"}
                  />
                  <ResultItem
                    label="Cancelled"
                    value={result?.cancelled ?? "See replan metrics"}
                  />
                </div>
              </div>

              <div className="border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                Open Replan History to review the full before/after diff for
                every changed interview.
              </div>
            </div>
          )}
        </div>

        <div className="flex shrink-0 justify-end space-x-3 border-t border-slate-200 bg-slate-50 p-4">
          <button
            onClick={onClose}
            className="border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            {step === 4 ? "Close" : "Cancel"}
          </button>

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
      <div className="text-sm text-slate-600">{description}</div>
    </button>
  );
}

function Field({ label, children }) {
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
      <div className="text-xs uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className="mt-1 font-semibold text-slate-900">{String(value)}</div>
    </div>
  );
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

function durationText(start, end) {
  if (!start || !end) return "—";

  const minutes = Math.round((end - start) / 60000);
  return `${minutes} min`;
}
