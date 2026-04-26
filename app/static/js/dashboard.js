const userChip = document.getElementById("userChip");
const guestsNavLink = document.getElementById("guestsNavLink");
const checkinNavLink = document.getElementById("checkinNavLink");
const usersNavLink = document.getElementById("usersNavLink");
const adminNavLink = document.getElementById("adminNavLink");

const totalGuestsLink = document.getElementById("totalGuestsLink");
const checkedInLink = document.getElementById("checkedInLink");
const totalUsersLink = document.getElementById("totalUsersLink");
const totalUsersCard = document.getElementById("totalUsersCard");

const totalGuestsEl = document.getElementById("totalGuests");
const checkedInEl = document.getElementById("checkedIn");
const totalUsersEl = document.getElementById("totalUsers");

const recentCheckinsBody = document.getElementById("recentCheckinsBody");
const dashboardSearchInput = document.getElementById("dashboardSearchInput");
const dashboardSearchBody = document.getElementById("dashboardSearchBody");
const logoutBtn = document.getElementById("logoutBtn");

const checkinLockBadge = document.getElementById("checkinLockBadge");
const manualLockUntil = document.getElementById("manualLockUntil");
const manualLockBtn = document.getElementById("manualLockBtn");
const manualUnlockBtn = document.getElementById("manualUnlockBtn");
const eventEndTimeDisplay = document.getElementById("eventEndTimeDisplay");
const eventEndTimeInput = document.getElementById("eventEndTimeInput");
const saveEventEndTimeBtn = document.getElementById("saveEventEndTimeBtn");
const clearEventEndTimeBtn = document.getElementById("clearEventEndTimeBtn");

const reportsCard = document.getElementById("reportsCard");
const openAdminBtn = document.getElementById("openAdminBtn");
const openReportsSummaryBtn = document.getElementById("openReportsSummaryBtn");
const exportGuestsCsvBtn = document.getElementById("exportGuestsCsvBtn");

const dashboardPageWrap = document.getElementById("dashboardPageWrap");

let liveUser = null;


function logoutLocal() {
  localStorage.removeItem("current_user");
  window.location.href = "/login";
}


function isAdmin(user) {
  return (user?.role || "").toLowerCase() === "admin";
}


function applyRoleUI(user) {
  liveUser = user;

  const displayName =
    user && user.full_name && user.full_name.trim() !== ""
      ? user.full_name
      : (user?.username || "User");

  if (userChip) {
    userChip.textContent = displayName;
  }

  const permissions = user?.permissions || {};
  const role = (user?.role || "").toLowerCase();

  const canManageGuests = role === "admin";
  const canCheckin = !!permissions.can_checkin || role === "admin";
  const canManageUsers = role === "admin";
  const canAccessAdmin = role === "admin";
  const adminOnly = role === "admin";

  if (guestsNavLink) {
    guestsNavLink.classList.toggle("hidden-link", !canManageGuests);
  }

  if (checkinNavLink) {
    checkinNavLink.classList.toggle("hidden-link", !canCheckin);
  }

  if (usersNavLink) {
    usersNavLink.classList.toggle("hidden-link", !canManageUsers);
  }

  if (adminNavLink) {
    adminNavLink.classList.toggle("hidden-link", !canAccessAdmin);
  }

  if (totalGuestsLink) {
    totalGuestsLink.style.display = canManageGuests ? "inline-block" : "none";
  }

  if (checkedInLink) {
    checkedInLink.style.display = canCheckin ? "inline-block" : "none";
  }

  if (totalUsersLink) {
    totalUsersLink.style.display = adminOnly ? "inline-block" : "none";
  }

  if (totalUsersCard) {
    totalUsersCard.style.display = adminOnly ? "" : "none";
  }

  if (!adminOnly) {
    manualLockUntil?.setAttribute("disabled", "disabled");
    manualLockBtn?.setAttribute("disabled", "disabled");
    manualUnlockBtn?.setAttribute("disabled", "disabled");
    eventEndTimeInput?.setAttribute("disabled", "disabled");
    saveEventEndTimeBtn?.setAttribute("disabled", "disabled");
    clearEventEndTimeBtn?.setAttribute("disabled", "disabled");

    if (reportsCard) {
      reportsCard.style.display = "none";
    }

    dashboardPageWrap?.classList.add("user-dashboard-mode");
  } else {
    manualLockUntil?.removeAttribute("disabled");
    manualLockBtn?.removeAttribute("disabled");
    manualUnlockBtn?.removeAttribute("disabled");
    eventEndTimeInput?.removeAttribute("disabled");
    saveEventEndTimeBtn?.removeAttribute("disabled");
    clearEventEndTimeBtn?.removeAttribute("disabled");

    if (reportsCard) {
      reportsCard.style.display = "";
    }

    dashboardPageWrap?.classList.remove("user-dashboard-mode");
  }
}


async function fetchWithSession(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {})
      }
    });

    if (response.status === 401) {
      logoutLocal();
      return null;
    }

    return response;
  } catch (error) {
    console.error("FETCH ERROR:", error);
    return null;
  }
}


async function syncCurrentUser() {
  const res = await fetchWithSession("/api/auth/me");
  if (!res) return null;

  const user = await res.json();
  localStorage.setItem("current_user", JSON.stringify(user));
  applyRoleUI(user);
  return user;
}


function formatDateTime(value) {
  const date = new Date(value);
  if (isNaN(date.getTime())) return value;

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


function toDatetimeLocalValue(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return "";

  const tzOffset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - tzOffset * 60000);
  return localDate.toISOString().slice(0, 16);
}


function updateLockUI(settings) {
  if (!settings) return;

  if (checkinLockBadge) {
    checkinLockBadge.classList.remove("danger");

    if (settings.is_locked) {
      if (settings.lock_reason === "event_ended") {
        checkinLockBadge.textContent = "EVENT ENDED";
      } else {
        checkinLockBadge.textContent = "LOCKED";
      }
      checkinLockBadge.classList.add("danger");
    } else {
      checkinLockBadge.textContent = "OPEN";
    }
  }

  if (manualLockUntil) {
    manualLockUntil.value = toDatetimeLocalValue(settings.manual_lock_until);
  }

  if (eventEndTimeDisplay) {
    eventEndTimeDisplay.textContent = settings.event_end_time
      ? formatDateTime(settings.event_end_time)
      : "Not set";
  }

  if (eventEndTimeInput) {
    eventEndTimeInput.value = settings.event_end_time
      ? toDatetimeLocalValue(settings.event_end_time)
      : "";
  }
}


async function loadDashboardSummary() {
  try {
    const res = await fetchWithSession("/api/admin/dashboard-summary");
    if (!res) return;

    const data = await res.json();
    if (!res.ok) return;

    if (totalGuestsEl) {
      totalGuestsEl.textContent = data.total_guests ?? 0;
    }

    if (checkedInEl) {
      checkedInEl.textContent = data.checked_in ?? 0;
    }

    if (totalUsersEl) {
      totalUsersEl.textContent = data.total_users ?? 0;
    }

    if (data.checkin_settings) {
      updateLockUI(data.checkin_settings);
    }

    if (!recentCheckinsBody) return;

    recentCheckinsBody.innerHTML = "";

    const latestCheckins = data.latest_checkins || [];

    if (latestCheckins.length === 0) {
      recentCheckinsBody.innerHTML = `
        <tr>
          <td colspan="4" class="muted-cell">No guest check-ins yet.</td>
        </tr>
      `;
      return;
    }

    latestCheckins.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(item.name || "-")}</td>
        <td>${escapeHtml(item.code || "-")}</td>
        <td>${item.time ? formatDateTime(item.time) : "-"}</td>
        <td>${escapeHtml(item.action || "-")}</td>
      `;
      recentCheckinsBody.appendChild(tr);
    });
  } catch (error) {
    console.error("Dashboard summary error:", error);
  }
}


async function loadDashboardSearch(search = "") {
  if (!dashboardSearchBody) return;

  const cleanSearch = search.trim();

  if (!cleanSearch) {
    dashboardSearchBody.innerHTML = `
      <tr>
        <td colspan="4" class="muted-cell">Start typing to search guests...</td>
      </tr>
    `;
    return;
  }

  dashboardSearchBody.innerHTML = `
    <tr>
      <td colspan="4" class="muted-cell">Searching guests...</td>
    </tr>
  `;

  try {
    const res = await fetchWithSession(`/api/reports/guests?search=${encodeURIComponent(cleanSearch)}`);
    if (!res) return;

    if (res.status === 403) {
      dashboardSearchBody.innerHTML = `
        <tr>
          <td colspan="4" class="muted-cell">Search access denied.</td>
        </tr>
      `;
      return;
    }

    const guests = await res.json();
    dashboardSearchBody.innerHTML = "";

    if (!Array.isArray(guests) || guests.length === 0) {
      dashboardSearchBody.innerHTML = `
        <tr>
          <td colspan="4" class="muted-cell">No matching guests found.</td>
        </tr>
      `;
      return;
    }

    guests.slice(0, 10).forEach((guest) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(guest.full_name || "-")}</td>
        <td>${escapeHtml(guest.phone || "-")}</td>
        <td>${escapeHtml(guest.code_no || "-")}</td>
        <td>${escapeHtml(guest.status || "-")}</td>
      `;
      dashboardSearchBody.appendChild(tr);
    });
  } catch (error) {
    console.error("Dashboard search error:", error);
  }
}


function setupDashboardSearch() {
  if (!dashboardSearchInput) return;

  let debounceTimer = null;

  dashboardSearchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    const value = e.target.value;

    debounceTimer = setTimeout(() => {
      loadDashboardSearch(value);
    }, 250);
  });
}


async function applyManualLock() {
  if (!isAdmin(liveUser)) return;

  const value = manualLockUntil?.value || "";

  const res = await fetchWithSession("/api/admin/checkin-lock/manual-lock", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      manual_lock_until: value || null
    })
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    alert(data.error || "Failed to lock check-in.");
    return;
  }

  updateLockUI(data.settings);
  alert(data.message || "Manual lock applied.");
}


async function unlockCheckin() {
  if (!isAdmin(liveUser)) return;

  const res = await fetchWithSession("/api/admin/checkin-lock/unlock", {
    method: "POST"
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    alert(data.error || "Failed to unlock check-in.");
    return;
  }

  updateLockUI(data.settings);
  alert(data.message || "Check-in unlocked.");
}


async function saveEventEndTime() {
  if (!isAdmin(liveUser)) return;

  const value = eventEndTimeInput?.value || "";

  const res = await fetchWithSession("/api/admin/checkin-lock/event-end-time", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      event_end_time: value || null
    })
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    alert(data.error || "Failed to save event end time.");
    return;
  }

  updateLockUI(data.settings);
  alert(data.message || "Event end time saved.");
}


async function clearEventEndTime() {
  if (!isAdmin(liveUser)) return;

  const res = await fetchWithSession("/api/admin/checkin-lock/event-end-time", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      event_end_time: null
    })
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    alert(data.error || "Failed to clear event end time.");
    return;
  }

  if (eventEndTimeInput) {
    eventEndTimeInput.value = "";
  }

  updateLockUI(data.settings);
  alert(data.message || "Event end time cleared.");
}


function bindLockControls() {
  manualLockBtn?.addEventListener("click", applyManualLock);
  manualUnlockBtn?.addEventListener("click", unlockCheckin);
  saveEventEndTimeBtn?.addEventListener("click", saveEventEndTime);
  clearEventEndTimeBtn?.addEventListener("click", clearEventEndTime);
}


function bindReportsButtons() {
  openAdminBtn?.addEventListener("click", () => {
    if (!isAdmin(liveUser)) return;
    window.location.href = "/admin";
  });

  openReportsSummaryBtn?.addEventListener("click", async () => {
    if (!isAdmin(liveUser)) return;

    const res = await fetchWithSession("/api/reports/summary");
    if (!res) return;

    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Failed to load report summary.");
      return;
    }

    alert(
      `Reports Summary\n\n` +
      `Total Guests: ${data.total_guests}\n` +
      `Checked-in: ${data.checked_in}\n` +
      `Pending: ${data.pending}\n` +
      `Total Users: ${data.total_users}`
    );
  });

  exportGuestsCsvBtn?.addEventListener("click", () => {
    if (!isAdmin(liveUser)) return;
    window.location.href = "/api/reports/export/guests.csv";
  });
}


function bindLogout() {
  logoutBtn?.addEventListener("click", async (e) => {
    e.preventDefault();

    try {
      await fetch("/api/auth/logout", { method: "GET" });
    } catch (error) {
      console.error("Logout error:", error);
    }

    logoutLocal();
  });
}


function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


document.addEventListener("DOMContentLoaded", async () => {
  bindLogout();
  bindLockControls();
  bindReportsButtons();
  await syncCurrentUser();
  setupDashboardSearch();
  await loadDashboardSummary();
});