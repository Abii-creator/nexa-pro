const loginForm = document.getElementById("loginForm");
const togglePassword = document.getElementById("togglePassword");
const passwordInput = document.getElementById("password");
const errorBox = document.getElementById("loginError");

togglePassword?.addEventListener("click", () => {
  passwordInput.type = passwordInput.type === "password" ? "text" : "password";
});

loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.textContent = "";

  const username = document.getElementById("username").value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    errorBox.textContent = "Username and password are required.";
    return;
  }

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errorBox.textContent = data.error || "Login failed";
      return;
    }

    if (data.user) {
      localStorage.setItem("current_user", JSON.stringify(data.user));
    } else {
      localStorage.removeItem("current_user");
    }

    window.location.href = data.redirect || "/dashboard";
  } catch (error) {
    errorBox.textContent = "Unable to connect to server.";
    console.error("LOGIN FETCH ERROR:", error);
  }
});