(function () {
  const INACTIVITY_MINUTES = 15;
  const WARNING_SECONDS = 60;

  let warningShown = false;
  let logoutTimer = null;
  let warningTimer = null;

  async function hasActiveSession() {
    try {
      const res = await fetch("/api/auth/me", {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });

      return res.ok;
    } catch (error) {
      return false;
    }
  }

  function clearClientState() {
    localStorage.removeItem("current_user");
  }

  function logoutNow() {
    clearClientState();
    window.location.replace("/login");
  }

  async function serverLogoutSilently() {
    try {
      await fetch("/api/auth/logout", {
        method: "GET"
      });
    } catch (error) {
      console.error("SESSION LOGOUT ERROR:", error);
    }

    logoutNow();
  }

  function showWarning() {
    if (warningShown) return;
    warningShown = true;
    alert(`Session yako itaisha baada ya sekunde ${WARNING_SECONDS} za kutokutumia mfumo.`);
  }

  function resetTimers() {
    clearTimeout(logoutTimer);
    clearTimeout(warningTimer);
    warningShown = false;

    warningTimer = setTimeout(
      showWarning,
      (INACTIVITY_MINUTES * 60 * 1000) - (WARNING_SECONDS * 1000)
    );

    logoutTimer = setTimeout(
      serverLogoutSilently,
      INACTIVITY_MINUTES * 60 * 1000
    );
  }

  const events = [
    "mousemove",
    "mousedown",
    "keydown",
    "scroll",
    "touchstart",
    "click",
    "input"
  ];

  events.forEach((eventName) => {
    document.addEventListener(eventName, resetTimers, true);
  });

  async function initSessionGuard() {
    const active = await hasActiveSession();

    if (!active) {
      logoutNow();
      return;
    }

    resetTimers();
  }

  initSessionGuard();
})();