const userChip = document.getElementById("userChip");
const guestsNavLink = document.getElementById("guestsNavLink");
const checkinNavLink = document.getElementById("checkinNavLink");
const usersNavLink = document.getElementById("usersNavLink");
const adminNavLink = document.getElementById("adminNavLink");

const userForm = document.getElementById("userForm");
const userIdInput = document.getElementById("userId");
const userFullNameInput = document.getElementById("userFullName");
const userUsernameInput = document.getElementById("userUsername");
const userEmailInput = document.getElementById("userEmail");
const userPasswordInput = document.getElementById("userPassword");
const userRoleInput = document.getElementById("userRole");
const userIsActiveInput = document.getElementById("userIsActive");

const permCheckin = document.getElementById("permCheckin");
const permAccessAdmin = document.getElementById("permAccessAdmin");
const permViewReports = document.getElementById("permViewReports");

const usersTableBody = document.getElementById("usersTableBody");
const userSearchInput = document.getElementById("userSearchInput");
const clearUserBtn = document.getElementById("clearUserBtn");
const refreshUsersBtn = document.getElementById("refreshUsersBtn");
const logoutBtn = document.getElementById("logoutBtn");

let usersCache = [];


function logoutLocal() {
  localStorage.removeItem("current_user");
  window.location.replace("/login");
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
  localStorage.setItem("current_user", JSON.stringify(user));
  applyRoleUI(user);
  return user;
}


async function requireUsersPageAccess() {
  const user = await getLiveUser();
  if (!user) return null;

  if (!isAdmin(user)) {
    window.location.replace("/dashboard");
    return null;
  }

  return user;
}


function setupPasswordToggles() {
  const buttons = document.querySelectorAll(".toggle-password-btn");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-target");
      const input = document.getElementById(targetId);

      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      button.textContent = isPassword ? "🙈" : "👁";
    });
  });
}


function setPermissionInputs(data = {}) {
  if (permCheckin) permCheckin.checked = !!data.can_checkin;
  if (permAccessAdmin) permAccessAdmin.checked = !!data.can_access_admin;
  if (permViewReports) permViewReports.checked = !!data.can_view_reports;
}


function getPermissionInputs() {
  return {
    can_checkin: !!permCheckin?.checked,
    can_access_admin: !!permAccessAdmin?.checked,
    can_view_reports: !!permViewReports?.checked
  };
}


function handleRolePermissionDefaults() {
  const role = userRoleInput.value;

  if (role === "Admin") {
    setPermissionInputs({
      can_checkin: true,
      can_access_admin: true,
      can_view_reports: true
    });
  }
}


function clearUserForm() {
  userIdInput.value = "";
  userFullNameInput.value = "";
  userUsernameInput.value = "";
  userEmailInput.value = "";
  userPasswordInput.value = "";
  userRoleInput.value = "User";
  userIsActiveInput.value = "true";

  setPermissionInputs({
    can_checkin: false,
    can_access_admin: false,
    can_view_reports: false
  });

  document.querySelectorAll(".toggle-password-btn").forEach((btn) => {
    const targetId = btn.getAttribute("data-target");
    const input = document.getElementById(targetId);
    if (input) input.type = "password";
    btn.textContent = "👁";
  });
}


function permissionText(perms, role) {
  if ((role || "").toLowerCase() === "admin") {
    return "Full Access";
  }

  const items = [];
  if (perms?.can_checkin) items.push("Check-in");
  if (perms?.can_access_admin) items.push("Admin");
  if (perms?.can_view_reports) items.push("Reports");
  return items.length ? items.join(", ") : "-";
}


function renderUsersTable(users) {
  if (!usersTableBody) return;

  usersTableBody.innerHTML = "";

  if (!Array.isArray(users) || users.length === 0) {
    usersTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="muted-cell">No users found.</td>
      </tr>
    `;
    return;
  }

  users.forEach((user) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(user.full_name || "-")}</td>
      <td>${escapeHtml(user.username || "-")}</td>
      <td>${escapeHtml(user.email || "-")}</td>
      <td>${escapeHtml(user.role || "-")}</td>
      <td>${user.is_active ? "Active" : "Inactive"}</td>
      <td>${escapeHtml(permissionText(user.permissions, user.role))}</td>
      <td class="action-buttons-cell">
        <button class="table-btn small-blue-btn" data-action="edit" data-id="${user.id}">Edit</button>
        <button class="table-btn small-red-btn" data-action="delete" data-id="${user.id}">Delete</button>
      </td>
    `;
    usersTableBody.appendChild(tr);
  });
}


async function loadUsers(search = "") {
  if (!usersTableBody) return;

  usersTableBody.innerHTML = `
    <tr>
      <td colspan="7" class="muted-cell">Loading users...</td>
    </tr>
  `;

  const query = search.trim()
    ? `/api/users/?search=${encodeURIComponent(search.trim())}`
    : "/api/users/";

  const res = await fetchWithSession(query);
  if (!res) return;

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  let users = await res.json();
  if (!Array.isArray(users)) {
    users = [];
  }

  usersCache = users;
  renderUsersTable(usersCache);
}


function fillUserForm(user) {
  userIdInput.value = user.id || "";
  userFullNameInput.value = user.full_name || "";
  userUsernameInput.value = user.username || "";
  userEmailInput.value = user.email || "";
  userPasswordInput.value = "";
  userRoleInput.value = user.role || "User";
  userIsActiveInput.value = user.is_active ? "true" : "false";

  setPermissionInputs(user.permissions || {});

  document.querySelectorAll(".toggle-password-btn").forEach((btn) => {
    const targetId = btn.getAttribute("data-target");
    const input = document.getElementById(targetId);
    if (input) input.type = "password";
    btn.textContent = "👁";
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}


async function saveUser(e) {
  e.preventDefault();

  const userId = userIdInput.value.trim();
  const permissions = getPermissionInputs();

  const payload = {
    full_name: userFullNameInput.value.trim(),
    username: userUsernameInput.value.trim(),
    email: userEmailInput.value.trim(),
    password: userPasswordInput.value.trim(),
    role: userRoleInput.value,
    is_active: userIsActiveInput.value === "true",
    can_checkin: permissions.can_checkin,
    can_access_admin: permissions.can_access_admin,
    can_view_reports: permissions.can_view_reports
  };

  const url = userId ? `/api/users/${userId}` : "/api/users/";
  const method = userId ? "PUT" : "POST";

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
    alert(data.error || "Failed to save user.");
    return;
  }

  clearUserForm();
  await loadUsers(userSearchInput?.value || "");
}


async function deleteUserById(id) {
  const confirmed = confirm("Delete this user?");
  if (!confirmed) return;

  const res = await fetchWithSession(`/api/users/${id}`, {
    method: "DELETE"
  });

  if (!res) return;

  const data = await res.json();

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  if (!res.ok) {
    alert(data.error || "Failed to delete user.");
    return;
  }

  await loadUsers(userSearchInput?.value || "");
}


function bindUsersTableActions() {
  usersTableBody?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.getAttribute("data-action");
    const id = Number(btn.getAttribute("data-id"));

    const user = usersCache.find((u) => u.id === id);
    if (!user) return;

    if (action === "edit") {
      fillUserForm(user);
      return;
    }

    if (action === "delete") {
      await deleteUserById(id);
    }
  });
}


function bindSearch() {
  let timer = null;

  userSearchInput?.addEventListener("input", (e) => {
    clearTimeout(timer);
    const value = e.target.value;

    timer = setTimeout(() => {
      loadUsers(value);
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


function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


document.addEventListener("DOMContentLoaded", async () => {
  const user = await requireUsersPageAccess();
  if (!user) return;

  setupPasswordToggles();
  bindUsersTableActions();
  bindSearch();
  bindLogout();

  userRoleInput?.addEventListener("change", handleRolePermissionDefaults);
  userForm?.addEventListener("submit", saveUser);

  clearUserForm();

  clearUserBtn?.addEventListener("click", () => {
    clearUserForm();
  });

  refreshUsersBtn?.addEventListener("click", () => {
    loadUsers(userSearchInput?.value || "");
  });

  await loadUsers();
});