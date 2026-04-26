const userChip = document.getElementById("userChip");
const logoutBtn = document.getElementById("logoutBtn");

const profileForm = document.getElementById("profileForm");
const profileUsername = document.getElementById("profileUsername");
const profileOldPassword = document.getElementById("profileOldPassword");
const profileNewPassword = document.getElementById("profileNewPassword");
const profileClearBtn = document.getElementById("profileClearBtn");
const profileMessage = document.getElementById("profileMessage");

const adminActivityBody = document.getElementById("adminActivityBody");
const navGuests = document.getElementById("guestsNavLink");
const navCheckin = document.getElementById("checkinNavLink");
const navUsers = document.getElementById("usersNavLink");
const navAdmin = document.getElementById("adminNavLink");

const adminTotalGuests = document.getElementById("adminTotalGuests");
const adminCheckedIn = document.getElementById("adminCheckedIn");
const adminTotalUsers = document.getElementById("adminTotalUsers");

const adminLockStatusBadge = document.getElementById("adminLockStatusBadge");
const adminManualLockUntil = document.getElementById("adminManualLockUntil");
const adminEventEndTime = document.getElementById("adminEventEndTime");

const reportTotalGuests = document.getElementById("reportTotalGuests");
const reportCheckedIn = document.getElementById("reportCheckedIn");
const reportPending = document.getElementById("reportPending");

const reportSearchInput = document.getElementById("reportSearchInput");
const reportStatusFilter = document.getElementById("reportStatusFilter");
const reportStartDate = document.getElementById("reportStartDate");
const reportEndDate = document.getElementById("reportEndDate");
const applyReportFiltersBtn = document.getElementById("applyReportFiltersBtn");
const clearReportFiltersBtn = document.getElementById("clearReportFiltersBtn");

const statusChartCanvas = document.getElementById("statusChartCanvas");
const trendChartCanvas = document.getElementById("trendChartCanvas");
const reportsGuestsBody = document.getElementById("reportsGuestsBody");

const exportFilteredGuestsBtn = document.getElementById("exportFilteredGuestsBtn");
const exportCheckinsBtn = document.getElementById("exportCheckinsBtn");
const exportAuditLogsBtn = document.getElementById("exportAuditLogsBtn");

const downloadDbBackupBtn = document.getElementById("downloadDbBackupBtn");
const downloadQrBackupBtn = document.getElementById("downloadQrBackupBtn");

const eventNameInput = document.getElementById("event_name");
const clientNameInput = document.getElementById("client_name");
const eventDateInput = document.getElementById("event_date");
const venueInput = document.getElementById("venue");
const logoUrlInput = document.getElementById("logo_url");
const saveEventSettingsBtn = document.getElementById("saveEventSettingsBtn");
const eventSettingsMessage = document.getElementById("eventSettingsMessage");

let statusChart = null;
let trendChart = null;


document.addEventListener("DOMContentLoaded", async () => {
  bindPasswordToggles();
  bindLogout();
  bindProfileForm();
  bindClearButton();
  bindReportControls();
  bindBackupControls();
  bindEventSettings();

  const user = await loadCurrentUser();
  if (!user) return;

  await loadEventSettings();
  await loadAdminProfile();
  await loadDashboardSummary();
  await loadReportsSummary();
  await loadStatusChart();
  await loadTrendChart();
  await loadReportGuests();
  await loadAdminActivity();
});


async function fetchWithSession(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {})
      }
    });

    if (response.status === 401) {
      window.location.href = "/login";
      return null;
    }

    return response;
  } catch (error) {
    console.error("FETCH ERROR:", error);
    return null;
  }
}


function bindPasswordToggles() {
  const toggleButtons = document.querySelectorAll(".toggle-password-btn");

  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const input = document.getElementById(targetId);

      if (!input) return;

      input.type = input.type === "password" ? "text" : "password";
      btn.textContent = input.type === "password" ? "👁" : "🙈";
    });
  });
}


function bindLogout() {
  logoutBtn?.addEventListener("click", async (e) => {
    e.preventDefault();

    try {
      await fetch("/api/auth/logout", {
        method: "GET"
      });
    } catch (error) {
      console.error("LOGOUT ERROR:", error);
    }

    localStorage.removeItem("current_user");
    window.location.href = "/login";
  });
}


function bindEventSettings() {
  saveEventSettingsBtn?.addEventListener("click", async () => {
    setEventSettingsMessage("", "");

    const payload = {
      event_name: eventNameInput?.value.trim() || "",
      client_name: clientNameInput?.value.trim() || "",
      event_date: eventDateInput?.value.trim() || "",
      venue: venueInput?.value.trim() || "",
      logo_url: logoUrlInput?.value.trim() || ""
    };

    if (!payload.event_name) {
      setEventSettingsMessage("Event name is required.", "error");
      return;
    }

    try {
      const res = await fetchWithSession("/api/admin/event-settings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!res) return;

      const data = await res.json();

      if (!res.ok) {
        setEventSettingsMessage(data.error || "Failed to save event settings.", "error");
        return;
      }

      setEventSettingsMessage("Event settings saved successfully.", "success");

      await loadDashboardSummary();
      await loadAdminActivity();

    } catch (error) {
      console.error("SAVE EVENT SETTINGS ERROR:", error);
      setEventSettingsMessage("Unable to connect to server.", "error");
    }
  });
}


async function loadEventSettings() {
  try {
    const res = await fetchWithSession("/api/admin/event-settings");
    if (!res) return;

    const data = await res.json();

    if (!res.ok) {
      setEventSettingsMessage(data.error || "Failed to load event settings.", "error");
      return;
    }

    if (eventNameInput) eventNameInput.value = data.event_name || "";
    if (clientNameInput) clientNameInput.value = data.client_name || "";
    if (eventDateInput) eventDateInput.value = data.event_date || "";
    if (venueInput) venueInput.value = data.venue || "";
    if (logoUrlInput) logoUrlInput.value = data.logo_url || "";

  } catch (error) {
    console.error("LOAD EVENT SETTINGS ERROR:", error);
  }
}


function setEventSettingsMessage(message, type) {
  if (!eventSettingsMessage) return;

  eventSettingsMessage.textContent = message;
  eventSettingsMessage.classList.remove("success-message", "error-message");

  if (type === "success") {
    eventSettingsMessage.classList.add("success-message");
  } else if (type === "error") {
    eventSettingsMessage.classList.add("error-message");
  }
}


function bindProfileForm() {
  profileForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    setProfileMessage("", "");

    const payload = {
      username: profileUsername.value.trim(),
      old_password: profileOldPassword.value.trim(),
      new_password: profileNewPassword.value.trim()
    };

    if (!payload.username) {
      setProfileMessage("Username is required.", "error");
      return;
    }

    try {
      const res = await fetchWithSession("/api/admin/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!res) return;

      const data = await res.json();

      if (res.status === 403) {
        setProfileMessage("You do not have permission to access this page.", "error");
        return;
      }

      if (!res.ok) {
        setProfileMessage(data.error || "Failed to update account.", "error");
        return;
      }

      setProfileMessage(data.message || "Account updated successfully.", "success");

      if (data.username) {
        profileUsername.value = data.username;
        if (userChip) {
          userChip.textContent = data.username;
        }
      }

      profileOldPassword.value = "";
      profileNewPassword.value = "";

      const storedUser = JSON.parse(localStorage.getItem("current_user") || "{}");
      storedUser.username = data.username || storedUser.username;
      localStorage.setItem("current_user", JSON.stringify(storedUser));

      await loadAdminActivity();

    } catch (error) {
      console.error("UPDATE PROFILE ERROR:", error);
      setProfileMessage("Unable to connect to server.", "error");
    }
  });
}


function bindClearButton() {
  profileClearBtn?.addEventListener("click", () => {
    profileOldPassword.value = "";
    profileNewPassword.value = "";
    setProfileMessage("", "");
  });
}


function bindReportControls() {
  applyReportFiltersBtn?.addEventListener("click", async () => {
    await loadReportGuests();
  });

  clearReportFiltersBtn?.addEventListener("click", async () => {
    if (reportSearchInput) reportSearchInput.value = "";
    if (reportStatusFilter) reportStatusFilter.value = "";
    if (reportStartDate) reportStartDate.value = "";
    if (reportEndDate) reportEndDate.value = "";
    await loadReportGuests();
  });

  let searchTimer = null;

  reportSearchInput?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      loadReportGuests();
    }, 350);
  });

  reportStatusFilter?.addEventListener("change", loadReportGuests);
  reportStartDate?.addEventListener("change", loadReportGuests);
  reportEndDate?.addEventListener("change", loadReportGuests);

  exportFilteredGuestsBtn?.addEventListener("click", () => {
    window.location.href = `/api/reports/export/guests.csv${buildReportQueryString()}`;
  });

  exportCheckinsBtn?.addEventListener("click", () => {
    window.location.href = "/api/reports/export/checkins.csv";
  });

  exportAuditLogsBtn?.addEventListener("click", () => {
    window.location.href = "/api/reports/export/audit-logs.csv";
  });
}


function bindBackupControls() {
  downloadDbBackupBtn?.addEventListener("click", () => {
    const confirmed = confirm("Download full database backup?");
    if (!confirmed) return;

    window.location.href = "/api/admin/backup/database";

    setTimeout(() => {
      loadAdminActivity();
    }, 1500);
  });

  downloadQrBackupBtn?.addEventListener("click", () => {
    const confirmed = confirm("Download all QR codes as ZIP?");
    if (!confirmed) return;

    window.location.href = "/api/admin/backup/qrcodes";

    setTimeout(() => {
      loadAdminActivity();
    }, 1500);
  });
}


async function loadCurrentUser() {
  try {
    const res = await fetchWithSession("/api/auth/me");
    if (!res) return null;

    const data = await res.json();

    if (!res.ok) {
      window.location.href = "/login";
      return null;
    }

    const displayName =
      data.full_name && data.full_name.trim() !== ""
        ? data.full_name
        : (data.username || "Admin");

    const role = (data.role || "").toLowerCase();

    if (role !== "admin") {
      window.location.href = "/dashboard";
      return null;
    }

    if (userChip) {
      userChip.textContent = displayName;
    }

    localStorage.setItem("current_user", JSON.stringify(data));

    navGuests?.classList.remove("hidden-link");
    navCheckin?.classList.remove("hidden-link");
    navUsers?.classList.remove("hidden-link");
    navAdmin?.classList.remove("hidden-link");

    return data;

  } catch (error) {
    console.error("LOAD CURRENT USER ERROR:", error);
    window.location.href = "/login";
    return null;
  }
}


async function loadAdminProfile() {
  try {
    const res = await fetchWithSession("/api/admin/profile");
    if (!res) return;

    const data = await res.json();

    if (res.status === 403) {
      setProfileMessage("You do not have permission to access admin profile.", "error");
      return;
    }

    if (!res.ok) {
      setProfileMessage(data.error || "Failed to load admin profile.", "error");
      return;
    }

    profileUsername.value = data.username || "";

  } catch (error) {
    console.error("LOAD ADMIN PROFILE ERROR:", error);
    setProfileMessage("Unable to connect to server.", "error");
  }
}


async function loadDashboardSummary() {
  try {
    const res = await fetchWithSession("/api/admin/dashboard-summary");
    if (!res) return;

    const data = await res.json();
    if (!res.ok) return;

    if (adminTotalGuests) adminTotalGuests.textContent = data.total_guests ?? 0;
    if (adminCheckedIn) adminCheckedIn.textContent = data.checked_in ?? 0;
    if (adminTotalUsers) adminTotalUsers.textContent = data.total_users ?? 0;

    const settings = data.checkin_settings || {};

    if (adminLockStatusBadge) {
      if (settings.is_locked) {
        adminLockStatusBadge.textContent =
          settings.lock_reason === "event_ended" ? "EVENT ENDED" : "LOCKED";
      } else {
        adminLockStatusBadge.textContent = "OPEN";
      }
    }

    if (adminManualLockUntil) {
      adminManualLockUntil.textContent = settings.manual_lock_until
        ? formatEAT(settings.manual_lock_until)
        : "Not set";
    }

    if (adminEventEndTime) {
      adminEventEndTime.textContent = settings.event_end_time
        ? formatEAT(settings.event_end_time)
        : "Not set";
    }

  } catch (error) {
    console.error("LOAD DASHBOARD SUMMARY ERROR:", error);
  }
}


async function loadReportsSummary() {
  try {
    const res = await fetchWithSession("/api/reports/summary");
    if (!res) return;

    const data = await res.json();
    if (!res.ok) return;

    if (reportTotalGuests) reportTotalGuests.textContent = data.total_guests ?? 0;
    if (reportCheckedIn) reportCheckedIn.textContent = data.checked_in ?? 0;
    if (reportPending) reportPending.textContent = data.pending ?? 0;

  } catch (error) {
    console.error("LOAD REPORTS SUMMARY ERROR:", error);
  }
}


async function loadStatusChart() {
  if (!statusChartCanvas || typeof Chart === "undefined") return;

  try {
    const res = await fetchWithSession("/api/reports/status-chart");
    if (!res) return;

    const data = await res.json();
    if (!res.ok) return;

    if (statusChart) {
      statusChart.destroy();
    }

    statusChart = new Chart(statusChartCanvas, {
      type: "doughnut",
      data: {
        labels: data.labels || [],
        datasets: [
          {
            data: data.values || []
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: {
              color: "#f4f7ff"
            }
          }
        }
      }
    });

  } catch (error) {
    console.error("STATUS CHART ERROR:", error);
  }
}


async function loadTrendChart() {
  if (!trendChartCanvas || typeof Chart === "undefined") return;

  try {
    const res = await fetchWithSession("/api/reports/checkins-trend?days=7");
    if (!res) return;

    const data = await res.json();
    if (!res.ok) return;

    if (trendChart) {
      trendChart.destroy();
    }

    trendChart = new Chart(trendChartCanvas, {
      type: "line",
      data: {
        labels: data.labels || [],
        datasets: [
          {
            label: "Check-ins",
            data: data.values || [],
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          x: {
            ticks: {
              color: "#c8d5ff"
            },
            grid: {
              color: "rgba(255,255,255,0.08)"
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: "#c8d5ff",
              precision: 0
            },
            grid: {
              color: "rgba(255,255,255,0.08)"
            }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: "#f4f7ff"
            }
          }
        }
      }
    });

  } catch (error) {
    console.error("TREND CHART ERROR:", error);
  }
}


async function loadReportGuests() {
  if (!reportsGuestsBody) return;

  reportsGuestsBody.innerHTML = `
    <tr>
      <td colspan="6" class="muted-cell">Loading report guests...</td>
    </tr>
  `;

  try {
    const res = await fetchWithSession(`/api/reports/guests${buildReportQueryString()}`);
    if (!res) return;

    const guests = await res.json();

    if (!res.ok) {
      reportsGuestsBody.innerHTML = `
        <tr>
          <td colspan="6" class="muted-cell">${escapeHtml(guests.error || "Failed to load report guests.")}</td>
        </tr>
      `;
      return;
    }

    if (!Array.isArray(guests) || guests.length === 0) {
      reportsGuestsBody.innerHTML = `
        <tr>
          <td colspan="6" class="muted-cell">No report records found.</td>
        </tr>
      `;
      return;
    }

    reportsGuestsBody.innerHTML = guests.map((guest) => `
      <tr>
        <td>${escapeHtml(guest.full_name || "-")}</td>
        <td>${escapeHtml(guest.phone || "-")}</td>
        <td>${escapeHtml(guest.email || "-")}</td>
        <td>${escapeHtml(guest.code_no || "-")}</td>
        <td>${escapeHtml(guest.status || "-")}</td>
        <td>${guest.checked_in_at ? formatEAT(guest.checked_in_at) : "-"}</td>
      </tr>
    `).join("");

  } catch (error) {
    console.error("LOAD REPORT GUESTS ERROR:", error);
    reportsGuestsBody.innerHTML = `
      <tr>
        <td colspan="6" class="muted-cell">Unable to connect to server.</td>
      </tr>
    `;
  }
}


async function loadAdminActivity() {
  if (!adminActivityBody) return;

  adminActivityBody.innerHTML = `
    <tr>
      <td colspan="5" class="muted-cell">Loading admin activity...</td>
    </tr>
  `;

  try {
    const res = await fetchWithSession("/api/admin/activity");
    if (!res) return;

    const data = await res.json();

    if (res.status === 403) {
      adminActivityBody.innerHTML = `
        <tr>
          <td colspan="5" class="muted-cell">You do not have permission to view admin activity.</td>
        </tr>
      `;
      return;
    }

    if (!res.ok) {
      adminActivityBody.innerHTML = `
        <tr>
          <td colspan="5" class="muted-cell">${escapeHtml(data.error || "Failed to load admin activity.")}</td>
        </tr>
      `;
      return;
    }

    const logs = data.logs || [];

    if (logs.length === 0) {
      adminActivityBody.innerHTML = `
        <tr>
          <td colspan="5" class="muted-cell">No activity found.</td>
        </tr>
      `;
      return;
    }

    adminActivityBody.innerHTML = logs.map((log) => `
      <tr>
        <td>${formatEAT(log.created_at)}</td>
        <td>${escapeHtml(log.full_name || log.username || "System")}</td>
        <td>${escapeHtml(log.action || "-")}</td>
        <td>${escapeHtml(log.description || "-")}</td>
        <td>${escapeHtml(log.ip_address || "-")}</td>
      </tr>
    `).join("");

  } catch (error) {
    console.error("LOAD ADMIN ACTIVITY ERROR:", error);
    adminActivityBody.innerHTML = `
      <tr>
        <td colspan="5" class="muted-cell">Unable to connect to server.</td>
      </tr>
    `;
  }
}


function buildReportQueryString() {
  const params = new URLSearchParams();

  const search = reportSearchInput?.value.trim() || "";
  const status = reportStatusFilter?.value || "";
  const startDate = reportStartDate?.value || "";
  const endDate = reportEndDate?.value || "";

  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);

  const query = params.toString();
  return query ? `?${query}` : "";
}


function setProfileMessage(message, type) {
  if (!profileMessage) return;

  profileMessage.textContent = message;
  profileMessage.classList.remove("success-message", "error-message");

  if (type === "success") {
    profileMessage.classList.add("success-message");
  } else if (type === "error") {
    profileMessage.classList.add("error-message");
  }
}


function formatEAT(dateString) {
  if (!dateString) return "-";

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleString("en-GB", {
    timeZone: "Africa/Dar_es_Salaam",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}


function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}