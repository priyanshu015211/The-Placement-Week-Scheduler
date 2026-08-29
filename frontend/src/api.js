<<<<<<< HEAD
const API_BASE = import.meta.env.VITE_API_BASE || "";
=======
const API_BASE = "";
>>>>>>> 570756796cf9b8d1a793db9a58128c18abce722c

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `API request failed (${response.status})`;

    try {
      const data = await response.json();
      message = data?.detail || data?.message || message;
    } catch {
      // Keep the HTTP status message when the response is not JSON.
    }

    throw new Error(message);
  }

  return response.json();
}

export function getDashboard() {
  return request("/api/dashboard");
}

export function getInterviews() {
  return request("/api/interviews");
}

export function getRooms() {
  return request("/api/rooms");
}

export function getPanels() {
  return request("/api/panels");
}

export function getStudents() {
  return request("/api/students");
}

export function getCompanies() {
  return request("/api/companies");
}

export function getMetrics() {
  return request("/api/metrics");
}

export function getReplanLog() {
  return request("/api/replan-log");
}

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

export function restoreBaseline() {
  return request("/api/replan/restore-baseline", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
