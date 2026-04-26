// =========================
// STATE
// =========================
let auditData = [];
let filteredData = [];
let currentPage = 1;
const pageSize = 10;


// =========================
// INIT
// =========================
document.addEventListener("DOMContentLoaded", () => {
  loadAuditLogs();

  const searchInput = document.getElementById("auditSearch");
  if (searchInput) {
    searchInput.addEventListener("input", handleSearch);
  }

  const refreshBtn = document.getElementById("refreshAudit");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadAuditLogs);
  }
});


// =========================
// FETCH DATA
// =========================
async function loadAuditLogs() {
  try {
    const res = await fetch("/api/admin/audit-logs");

    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Failed to load audit logs");
      return;
    }

    auditData = data.logs || [];
    filteredData = [...auditData];

    renderTable();
    renderPagination();

  } catch (err) {
    console.error("AUDIT LOAD ERROR:", err);
    showError("Unable to connect to server.");
  }
}


// =========================
// SEARCH
// =========================
function handleSearch(e) {
  const term = e.target.value.toLowerCase();

  filteredData = auditData.filter(item => {
    return (
      (item.username || "").toLowerCase().includes(term) ||
      (item.action || "").toLowerCase().includes(term) ||
      (item.ip_address || "").toLowerCase().includes(term)
    );
  });

  currentPage = 1;
  renderTable();
  renderPagination();
}


// =========================
// TABLE RENDER
// =========================
function renderTable() {
  const tbody = document.getElementById("auditTableBody");
  if (!tbody) return;

  tbody.innerHTML = "";

  const start = (currentPage - 1) * pageSize;
  const pageItems = filteredData.slice(start, start + pageSize);

  if (pageItems.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center;">No data found</td>
      </tr>
    `;
    return;
  }

  pageItems.forEach(log => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${log.id || "-"}</td>
      <td>${log.username || "-"}</td>
      <td>${log.action || "-"}</td>
      <td>${log.ip_address || "-"}</td>
      <td>${formatDate(log.created_at)}</td>
    `;

    tbody.appendChild(row);
  });
}


// =========================
// PAGINATION
// =========================
function renderPagination() {
  const container = document.getElementById("auditPagination");
  if (!container) return;

  container.innerHTML = "";

  const totalPages = Math.ceil(filteredData.length / pageSize);
  if (totalPages <= 1) return;

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;

    if (i === currentPage) {
      btn.classList.add("active");
    }

    btn.addEventListener("click", () => {
      currentPage = i;
      renderTable();
      renderPagination();
    });

    container.appendChild(btn);
  }
}


// =========================
// UTIL
// =========================
function formatDate(dateString) {
  if (!dateString) return "-";

  const date = new Date(dateString);
  if (isNaN(date)) return dateString;

  return date.toLocaleString();
}

function showError(message) {
  const box = document.getElementById("auditError");
  if (box) {
    box.textContent = message;
  } else {
    alert(message);
  }
}