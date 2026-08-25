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
    let message = `API request failed (${response.status})`;
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

export const getHealth = () => request("/api/health");
export const getDashboard = () => request("/api/dashboard");
export const getInterviews = () => request("/api/interviews");
export const getRooms = () => request("/api/rooms");
export const getPanels = () => request("/api/panels");
export const getStudents = () => request("/api/students");
export const getCompanies = () => request("/api/companies");
export const getMetrics = () => request("/api/metrics");
export const getReplanLog = () => request("/api/replan-log");

export const delayCompany = (companyId, delayMinutes) =>
  request("/api/replan/company-delay", {
    method: "POST",
    body: JSON.stringify({
      company_id: Number(companyId),
      delay_minutes: Number(delayMinutes),
    }),
  });

export const dropPanel = (panelId) =>
  request("/api/replan/panel-drop", {
    method: "POST",
    body: JSON.stringify({ panel_id: Number(panelId) }),
  });

export const offlineRoom = (roomId) =>
  request("/api/replan/room-offline", {
    method: "POST",
    body: JSON.stringify({ room_id: Number(roomId) }),
  });

export const withdrawStudent = (studentId) =>
  request("/api/replan/withdraw", {
    method: "POST",
    body: JSON.stringify({ student_id: Number(studentId) }),
  });
