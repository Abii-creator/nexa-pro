const userChip = document.getElementById("userChip");
const guestsNavLink = document.getElementById("guestsNavLink");
const checkinNavLink = document.getElementById("checkinNavLink");
const usersNavLink = document.getElementById("usersNavLink");
const adminNavLink = document.getElementById("adminNavLink");

const guestForm = document.getElementById("guestForm");
const guestIdInput = document.getElementById("guestId");
const fullNameInput = document.getElementById("fullName");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const organizationInput = document.getElementById("organization");
const titleInput = document.getElementById("title");

const bulkCsvInput = document.getElementById("bulkCsvInput");
const bulkImportBtn = document.getElementById("bulkImportBtn");
const bulkImportMessage = document.getElementById("bulkImportMessage");

const guestsTableBody = document.getElementById("guestsTableBody");
const searchInput = document.getElementById("searchInput");
const clearBtn = document.getElementById("clearBtn");
const refreshBtn = document.getElementById("refreshBtn");
const printBadgesBtn = document.getElementById("printBadgesBtn");
const logoutBtn = document.getElementById("logoutBtn");

let guestsCache = [];


function logoutLocal() {
  localStorage.removeItem("current_user");
  window.location.href = "/login";
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


function isAdmin(user) {
  return (user?.role || "").toLowerCase() === "admin";
}


function applyRoleUI(user) {
  if (userChip) {
    const displayName =
      user?.full_name && user.full_name.trim() !== ""
        ? user.full_name
        : (user?.username || "User");

    userChip.textContent = displayName;
  }

  const permissions = user?.permissions || {};
  const role = (user?.role || "").toLowerCase();

  const canManageGuests = role === "admin";
  const canCheckin = !!permissions.can_checkin || role === "admin";
  const canManageUsersFlag = role === "admin";
  const canAccessAdmin = role === "admin";

  if (guestsNavLink) {
    guestsNavLink.classList.toggle("hidden-link", !canManageGuests);
  }

  if (checkinNavLink) {
    checkinNavLink.classList.toggle("hidden-link", !canCheckin);
  }

  if (usersNavLink) {
    usersNavLink.classList.toggle("hidden-link", !canManageUsersFlag);
  }

  if (adminNavLink) {
    adminNavLink.classList.toggle("hidden-link", !canAccessAdmin);
  }
}


async function getLiveUser() {
  const res = await fetchWithSession("/api/auth/me");
  if (!res) return null;

  const user = await res.json();

  if (!res.ok) {
    logoutLocal();
    return null;
  }

  localStorage.setItem("current_user", JSON.stringify(user));
  applyRoleUI(user);

  return user;
}


async function requireGuestsPageAccess() {
  const user = await getLiveUser();
  if (!user) return null;

  if (!isAdmin(user)) {
    window.location.replace("/dashboard");
    return null;
  }

  return user;
}


function clearForm() {
  if (guestIdInput) guestIdInput.value = "";
  if (fullNameInput) fullNameInput.value = "";
  if (phoneInput) phoneInput.value = "";
  if (emailInput) emailInput.value = "";
  if (organizationInput) organizationInput.value = "";
  if (titleInput) titleInput.value = "";
}


function formatDateTime(value) {
  if (!value) return "-";

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


function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function setBulkMessage(message, type) {
  if (!bulkImportMessage) return;

  bulkImportMessage.textContent = message;
  bulkImportMessage.classList.remove("success-message", "error-message");

  if (type === "success") {
    bulkImportMessage.classList.add("success-message");
  }

  if (type === "error") {
    bulkImportMessage.classList.add("error-message");
  }
}


function renderGuestsTable(guests) {
  if (!guestsTableBody) return;

  guestsTableBody.innerHTML = "";

  if (!Array.isArray(guests) || guests.length === 0) {
    guestsTableBody.innerHTML = `
      <tr>
        <td colspan="8" class="muted-cell">No guests found.</td>
      </tr>
    `;
    return;
  }

  guests.forEach((guest) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${escapeHtml(guest.full_name || "-")}</td>
      <td>${escapeHtml(guest.phone || "-")}</td>
      <td>${escapeHtml(guest.email || "-")}</td>
      <td>${escapeHtml(guest.code_no || "-")}</td>
      <td>${escapeHtml(guest.status || "-")}</td>
      <td>${guest.checked_in_at ? formatDateTime(guest.checked_in_at) : "-"}</td>
      <td>
        <button class="table-btn small-green-btn" data-action="qr" data-id="${guest.id}">
          QR
        </button>
      </td>
      <td class="action-buttons-cell">
        <button class="table-btn small-blue-btn" data-action="edit" data-id="${guest.id}">
          Edit
        </button>
        <button class="table-btn small-red-btn" data-action="delete" data-id="${guest.id}">
          Delete
        </button>
      </td>
    `;

    guestsTableBody.appendChild(tr);
  });
}


async function loadGuests(search = "") {
  if (!guestsTableBody) return;

  guestsTableBody.innerHTML = `
    <tr>
      <td colspan="8" class="muted-cell">Loading guests...</td>
    </tr>
  `;

  const query = search.trim()
    ? `/api/guests/?search=${encodeURIComponent(search.trim())}`
    : "/api/guests/";

  const res = await fetchWithSession(query);
  if (!res) return;

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  let guests = await res.json();

  if (!Array.isArray(guests)) {
    guests = [];
  }

  guestsCache = guests;
  renderGuestsTable(guestsCache);
}


function fillGuestForm(guest) {
  if (guestIdInput) guestIdInput.value = guest.id || "";
  if (fullNameInput) fullNameInput.value = guest.full_name || "";
  if (phoneInput) phoneInput.value = guest.phone || "";
  if (emailInput) emailInput.value = guest.email || "";
  if (organizationInput) organizationInput.value = guest.organization || "";
  if (titleInput) titleInput.value = guest.title || "";

  window.scrollTo({ top: 0, behavior: "smooth" });
}


async function saveGuest(e) {
  e.preventDefault();

  const guestId = guestIdInput?.value.trim() || "";

  const payload = {
    full_name: fullNameInput?.value.trim() || "",
    phone: phoneInput?.value.trim() || "",
    email: emailInput?.value.trim() || "",
    organization: organizationInput?.value.trim() || "",
    title: titleInput?.value.trim() || ""
  };

  const url = guestId ? `/api/guests/${guestId}` : "/api/guests/";
  const method = guestId ? "PUT" : "POST";

  const res = await fetchWithSession(url, {
    method,
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!res) return;

  const data = await res.json();

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  if (!res.ok) {
    alert(data.error || "Failed to save guest.");
    return;
  }

  clearForm();
  await loadGuests(searchInput?.value || "");
}


async function bulkImportGuests() {
  const file = bulkCsvInput?.files?.[0];

  if (!file) {
    setBulkMessage("Please choose a CSV file first.", "error");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".csv")) {
    setBulkMessage("Only CSV files are allowed.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  setBulkMessage("Importing guests. Please wait...", "success");

  const res = await fetchWithSession("/api/guests/bulk-import", {
    method: "POST",
    body: formData
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    setBulkMessage(data.error || "Bulk import failed.", "error");
    return;
  }

  let message = `Import completed. Created: ${data.created}, Skipped: ${data.skipped}`;

  if (data.errors && data.errors.length > 0) {
    message += ` | First errors: ${data.errors.slice(0, 3).join(" | ")}`;
  }

  setBulkMessage(message, data.skipped > 0 ? "error" : "success");

  if (bulkCsvInput) {
    bulkCsvInput.value = "";
  }

  await loadGuests(searchInput?.value || "");
}


async function deleteGuestById(id) {
  const confirmed = confirm("Delete this guest?");
  if (!confirmed) return;

  const res = await fetchWithSession(`/api/guests/${id}`, {
    method: "DELETE"
  });

  if (!res) return;

  const data = await res.json();

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  if (!res.ok) {
    alert(data.error || "Failed to delete guest.");
    return;
  }

  await loadGuests(searchInput?.value || "");
}


function openQrCard(id) {
  window.open(`/api/guests/${id}/qr-card`, "_blank");
}


function openPrintBadges() {
  const search = searchInput?.value.trim() || "";

  const url = search
    ? `/api/guests/print-badges?search=${encodeURIComponent(search)}`
    : "/api/guests/print-badges";

  window.open(url, "_blank");
}


function bindTableActions() {
  guestsTableBody?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.getAttribute("data-action");
    const id = Number(btn.getAttribute("data-id"));

    if (!id || !action) return;

    const guest = guestsCache.find((g) => Number(g.id) === id);

    if (action === "qr") {
      openQrCard(id);
      return;
    }

    if (!guest) return;

    if (action === "edit") {
      fillGuestForm(guest);
      return;
    }

    if (action === "delete") {
      await deleteGuestById(id);
      return;
    }
  });
}


function bindSearch() {
  let timer = null;

  searchInput?.addEventListener("input", (e) => {
    clearTimeout(timer);
    const value = e.target.value;

    timer = setTimeout(() => {
      loadGuests(value);
    }, 250);
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


document.addEventListener("DOMContentLoaded", async () => {
  const user = await requireGuestsPageAccess();
  if (!user) return;

  bindTableActions();
  bindSearch();
  bindLogout();

  guestForm?.addEventListener("submit", saveGuest);

  clearBtn?.addEventListener("click", () => {
    clearForm();
  });

  refreshBtn?.addEventListener("click", () => {
    loadGuests(searchInput?.value || "");
  });

  bulkImportBtn?.addEventListener("click", bulkImportGuests);

  printBadgesBtn?.addEventListener("click", openPrintBadges);

  await loadGuests();
});