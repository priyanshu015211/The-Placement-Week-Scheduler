const API_BASE = "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = "API request failed";

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep the default message.
    }

    throw new Error(message);
  }

  return response.json();
}


// ============================================================
// Dashboard
// ============================================================

export function getDashboard() {
  return request("/api/dashboard");
}


// ============================================================
// Schedule
// ============================================================

export function getInterviews() {
  return request("/api/interviews");
}


// ============================================================
// Rooms
// ============================================================

export function getRooms() {
  return request("/api/rooms");
}


// ============================================================
// Panels
// ============================================================

export function getPanels() {
  return request("/api/panels");
}


// ============================================================
// Students
// ============================================================

export function getStudents() {
  return request("/api/students");
}


// ============================================================
// Companies
// ============================================================

export function getCompanies() {
  return request("/api/companies");
}


// ============================================================
// Metrics
// ============================================================

export function getMetrics() {
  return request("/api/metrics");
}


// ============================================================
// Replan history
// ============================================================

export function getReplanLog() {
  return request("/api/replan-log");
}


// ============================================================
// Replanning actions
// ============================================================

export function delayCompany(companyId, delayMinutes) {
  return request("/api/replan/company-delay", {
    method: "POST",
    body: JSON.stringify({
      company_id: Number(companyId),
      delay_minutes: Number(delayMinutes),
    }),
  });
}


export function dropPanel(panelId) {
  return request("/api/replan/panel-drop", {
    method: "POST",
    body: JSON.stringify({
      panel_id: Number(panelId),
    }),
  });
}


export function offlineRoom(roomId) {
  return request("/api/replan/room-offline", {
    method: "POST",
    body: JSON.stringify({
      room_id: Number(roomId),
    }),
  });
}


export function withdrawStudent(studentId) {
  return request("/api/replan/withdraw", {
    method: "POST",
    body: JSON.stringify({
      student_id: Number(studentId),
    }),
  });
}