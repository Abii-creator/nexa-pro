const userChip = document.getElementById("userChip");
const guestsNavLink = document.getElementById("guestsNavLink");
const checkinNavLink = document.getElementById("checkinNavLink");
const usersNavLink = document.getElementById("usersNavLink");
const adminNavLink = document.getElementById("adminNavLink");

const checkinSearchInput = document.getElementById("checkinSearchInput");
const checkinSearchBtn = document.getElementById("checkinSearchBtn");
const checkinResultsBody = document.getElementById("checkinResultsBody");
const logoutBtn = document.getElementById("logoutBtn");
const checkinLockMessage = document.getElementById("checkinLockMessage");
const scanResult = document.getElementById("scanResult");

const startQrScanBtn = document.getElementById("startQrScanBtn");
const stopQrScanBtn = document.getElementById("stopQrScanBtn");
const qrImageInput = document.getElementById("qrImageInput");
const uploadQrImageBtn = document.getElementById("uploadQrImageBtn");

let currentUser = null;
let checkinLocked = false;
let qrScanner = null;
let qrScannerRunning = false;
let lastScannedValue = "";
let lastScannedAt = 0;


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


function applyRoleUI(user) {
  currentUser = user;

  if (userChip) {
    userChip.textContent =
      user?.full_name && user.full_name.trim() !== ""
        ? user.full_name
        : (user?.username || "User");
  }

  const permissions = user?.permissions || {};
  const role = (user?.role || "").toLowerCase();

  const canManageGuests = role === "admin";
  const canCheckin = !!permissions.can_checkin || role === "admin";
  const canManageUsers = role === "admin";
  const canAccessAdmin = role === "admin";

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
}


async function authenticatePage() {
  const res = await fetchWithSession("/api/auth/me");
  if (!res) return null;

  if (!res.ok) {
    logoutLocal();
    return null;
  }

  const user = await res.json();
  localStorage.setItem("current_user", JSON.stringify(user));
  applyRoleUI(user);

  const permissions = user.permissions || {};
  const role = (user.role || "").toLowerCase();

  if (!(permissions.can_checkin || role === "admin")) {
    window.location.replace("/dashboard");
    return null;
  }

  return user;
}


async function loadCheckinStatus() {
  const res = await fetchWithSession("/api/checkin/status");
  if (!res) return;

  const data = await res.json();
  if (!res.ok) return;

  checkinLocked = !!data.is_locked;

  checkinLockMessage.classList.remove("success-message", "error-message");

  if (data.is_locked) {
    checkinLockMessage.textContent =
      data.lock_reason === "event_ended"
        ? "Check-in is closed because the event has ended."
        : "Check-in is manually locked.";

    checkinLockMessage.classList.add("error-message");
  } else {
    checkinLockMessage.textContent = "Check-in is open.";
    checkinLockMessage.classList.add("success-message");
  }
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


function renderSingleGuest(guest) {
  const alreadyCheckedIn = guest.status === "Checked-in";

  checkinResultsBody.innerHTML = `
    <tr>
      <td>${escapeHtml(guest.full_name || "-")}</td>
      <td>${escapeHtml(guest.phone || "-")}</td>
      <td>${escapeHtml(guest.email || "-")}</td>
      <td>${escapeHtml(guest.code_no || "-")}</td>
      <td>${escapeHtml(guest.status || "-")}</td>
      <td>${guest.checked_in_at ? formatDateTime(guest.checked_in_at) : "-"}</td>
      <td>
        ${
          alreadyCheckedIn
            ? `<span class="action-pill">ALREADY CHECKED-IN</span>`
            : `<button class="table-btn small-green-btn" data-action="checkin" data-id="${guest.id}">Check-in Now</button>`
        }
      </td>
    </tr>
  `;
}


async function searchGuestsForCheckin() {
  const query = checkinSearchInput?.value.trim() || "";

  if (!query) {
    checkinResultsBody.innerHTML = `
      <tr>
        <td colspan="7" class="muted-cell">Search guest to begin check-in.</td>
      </tr>
    `;
    return;
  }

  checkinResultsBody.innerHTML = `
    <tr>
      <td colspan="7" class="muted-cell">Searching guests...</td>
    </tr>
  `;

  const res = await fetchWithSession(`/api/checkin/search?q=${encodeURIComponent(query)}`);
  if (!res) return;

  if (res.status === 403) {
    window.location.replace("/dashboard");
    return;
  }

  const guests = await res.json();
  checkinResultsBody.innerHTML = "";

  if (!Array.isArray(guests) || guests.length === 0) {
    checkinResultsBody.innerHTML = `
      <tr>
        <td colspan="7" class="muted-cell">No guest found for this search.</td>
      </tr>
    `;
    return;
  }

  guests.forEach((guest) => {
    const alreadyCheckedIn = guest.status === "Checked-in";
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${escapeHtml(guest.full_name || "-")}</td>
      <td>${escapeHtml(guest.phone || "-")}</td>
      <td>${escapeHtml(guest.email || "-")}</td>
      <td>${escapeHtml(guest.code_no || "-")}</td>
      <td>${escapeHtml(guest.status || "-")}</td>
      <td>${guest.checked_in_at ? formatDateTime(guest.checked_in_at) : "-"}</td>
      <td>
        ${
          alreadyCheckedIn
            ? `<span class="action-pill">ALREADY CHECKED-IN</span>`
            : `<button class="table-btn small-green-btn" data-action="checkin" data-id="${guest.id}">Check-in Now</button>`
        }
      </td>
    `;

    checkinResultsBody.appendChild(tr);
  });
}


async function autoCheckinFromScan(scannedValue) {
  if (!scannedValue) return;

  const now = Date.now();

  if (scannedValue === lastScannedValue && now - lastScannedAt < 2500) {
    return;
  }

  lastScannedValue = scannedValue;
  lastScannedAt = now;

  await loadCheckinStatus();

  if (checkinLocked) {
    showScanMessage("Check-in is locked. Scan ignored.", "error");
    playErrorBeep();
    return;
  }

  showScanMessage("QR detected. Processing check-in...", "success");

  const res = await fetchWithSession("/api/checkin/scan-checkin", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      code: scannedValue
    })
  });

  if (!res) return;

  const data = await res.json();

  if (!res.ok) {
    showScanMessage(data.error || "QR check-in failed.", "error");
    playErrorBeep();
    return;
  }

  const guest = data.guest;

  if (checkinSearchInput && guest?.code_no) {
    checkinSearchInput.value = guest.code_no;
  }

  if (guest) {
    renderSingleGuest(guest);
  }

  if (data.already_checked_in) {
    showScanMessage(`Already checked in: ${guest.full_name}`, "error");
    playErrorBeep();
  } else {
    showScanMessage(`Checked in successfully: ${guest.full_name}`, "success");
    playSuccessBeep();
    localStorage.setItem("checkin_updated_at", String(Date.now()));
  }

  await loadCheckinStatus();
}


async function checkInNow(guestId) {
  await loadCheckinStatus();

  if (checkinLocked) {
    alert("Check-in is currently locked.");
    return;
  }

  const res = await fetchWithSession(`/api/guests/${guestId}/check-in`, {
    method: "POST"
  });

  if (!res) return;

  const data = await res.json();

  if (res.status === 403) {
    alert(data.error || "You do not have check-in permission.");
    await loadCheckinStatus();
    return;
  }

  if (!res.ok) {
    alert(data.error || "Failed to check in guest.");
    return;
  }

  alert("Guest checked in successfully.");
  localStorage.setItem("checkin_updated_at", String(Date.now()));

  await loadCheckinStatus();
  await searchGuestsForCheckin();
}


function bindTableActions() {
  checkinResultsBody?.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action='checkin']");
    if (!btn) return;

    const guestId = Number(btn.getAttribute("data-id"));
    if (!guestId) return;

    await checkInNow(guestId);
  });
}


function bindSearch() {
  checkinSearchBtn?.addEventListener("click", searchGuestsForCheckin);

  checkinSearchInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      searchGuestsForCheckin();
    }
  });
}


async function startQrScanner() {
  if (typeof Html5Qrcode === "undefined") {
    alert("QR scanner library failed to load.");
    return;
  }

  if (qrScannerRunning) {
    return;
  }

  try {
    qrScanner = new Html5Qrcode("reader");

    await qrScanner.start(
      { facingMode: "environment" },
      {
        fps: 10,
        qrbox: { width: 250, height: 250 }
      },
      async (decodedText) => {
        await autoCheckinFromScan(decodedText);
      },
      () => {}
    );

    qrScannerRunning = true;
    showScanMessage("Scanner started. Point camera to QR code.", "success");

  } catch (error) {
    console.error("QR START ERROR:", error);
    showScanMessage("Failed to start QR scanner. Check camera permission.", "error");
  }
}


async function stopQrScanner() {
  try {
    if (qrScanner && qrScannerRunning) {
      await qrScanner.stop();
      await qrScanner.clear();
    }
  } catch (error) {
    console.error("QR STOP ERROR:", error);
  } finally {
    qrScannerRunning = false;
    qrScanner = null;
  }
}


async function scanUploadedQrImage() {
  if (typeof Html5Qrcode === "undefined") {
    showScanMessage("QR scanner library failed to load.", "error");
    return;
  }

  const file = qrImageInput?.files?.[0];

  if (!file) {
    showScanMessage("Please choose a QR image first.", "error");
    return;
  }

  try {
    await stopQrScanner();

    showScanMessage("Reading uploaded QR image...", "success");

    const imageScanner = new Html5Qrcode("reader");
    const decodedText = await imageScanner.scanFile(file, true);

    try {
      await imageScanner.clear();
    } catch (error) {}

    if (!decodedText) {
      showScanMessage("No QR code found in this image.", "error");
      playErrorBeep();
      return;
    }

    await autoCheckinFromScan(decodedText);

  } catch (error) {
    console.error("UPLOAD QR SCAN ERROR:", error);
    showScanMessage("Failed to read QR from image. Use a clear QR image.", "error");
    playErrorBeep();
  }
}


function bindQrControls() {
  startQrScanBtn?.addEventListener("click", async () => {
    await startQrScanner();
  });

  stopQrScanBtn?.addEventListener("click", async () => {
    await stopQrScanner();
    showScanMessage("Scanner stopped.", "success");
  });

  uploadQrImageBtn?.addEventListener("click", async () => {
    await scanUploadedQrImage();
  });

  qrImageInput?.addEventListener("change", () => {
    if (qrImageInput.files && qrImageInput.files[0]) {
      showScanMessage(`Selected image: ${qrImageInput.files[0].name}`, "success");
    }
  });
}


function bindLogout() {
  logoutBtn?.addEventListener("click", async (e) => {
    e.preventDefault();

    try {
      await stopQrScanner();
      await fetch("/api/auth/logout", {
        method: "GET"
      });
    } catch (error) {
      console.error("Logout error:", error);
    }

    logoutLocal();
  });
}


function showScanMessage(message, type) {
  if (!scanResult) return;

  scanResult.textContent = message;
  scanResult.classList.remove("success-message", "error-message");

  if (type === "success") {
    scanResult.classList.add("success-message");
  }

  if (type === "error") {
    scanResult.classList.add("error-message");
  }
}


function playSuccessBeep() {
  playBeep(880, 120);
}


function playErrorBeep() {
  playBeep(220, 220);
}


function playBeep(frequency, duration) {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(0.08, audioContext.currentTime);

    oscillator.start();

    setTimeout(() => {
      oscillator.stop();
      audioContext.close();
    }, duration);
  } catch (error) {}
}


document.addEventListener("DOMContentLoaded", async () => {
  const user = await authenticatePage();
  if (!user) return;

  bindSearch();
  bindTableActions();
  bindQrControls();
  bindLogout();

  await loadCheckinStatus();
});