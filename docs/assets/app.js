const BACKEND_URL = "https://YOUR-RAILWAY-APP-URL";
const TOKEN_KEY = "tickr_token";

function setCurrentYear() {
  const year = String(new Date().getFullYear());
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = year;
  });
}

function redirectTo(path) {
  window.location.href = path;
}

function getToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    redirectTo("./login.html");
    return null;
  }

  return response;
}

async function handleLoginSubmit(event) {
  event.preventDefault();

  const errorNode = document.getElementById("login-error");
  const form = event.currentTarget;
  const email = form.email.value.trim();
  const password = form.password.value;

  errorNode.hidden = true;
  errorNode.textContent = "";

  try {
    const response = await fetch(`${BACKEND_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || !payload.access_token) {
      errorNode.textContent = payload.detail || "Unable to sign in.";
      errorNode.hidden = false;
      return;
    }

    setToken(payload.access_token);
    redirectTo("./app.html");
  } catch {
    errorNode.textContent = "Network error. Please try again.";
    errorNode.hidden = false;
  }
}

async function loadPrivateState() {
  if (!getToken()) {
    redirectTo("./login.html");
    return;
  }

  const statusNode = document.getElementById("app-status");
  const errorNode = document.getElementById("app-error");
  const stateNode = document.getElementById("private-state");
  const emailNode = document.getElementById("private-email");
  const okNode = document.getElementById("private-ok");

  try {
    const response = await authFetch("/api/private");
    if (!response) {
      return;
    }

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      errorNode.textContent = payload.detail || "Unable to verify session.";
      errorNode.hidden = false;
      statusNode.textContent = "Session unavailable.";
      return;
    }

    statusNode.textContent = "Signed in.";
    emailNode.textContent = payload.email || "";
    okNode.textContent = payload.ok ? "true" : "false";
    stateNode.hidden = false;
  } catch {
    errorNode.textContent = "Network error. Please try again.";
    errorNode.hidden = false;
    statusNode.textContent = "Session unavailable.";
  }
}

function logout() {
  clearToken();
  redirectTo("./index.html");
}

function initLoginPage() {
  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("submit", handleLoginSubmit);
  }
}

function initAppPage() {
  const logoutButton = document.getElementById("logout-button");
  if (logoutButton) {
    logoutButton.addEventListener("click", logout);
  }
  void loadPrivateState();
}

function initPage() {
  setCurrentYear();

  const page = document.body.dataset.page;
  if (page === "login") {
    initLoginPage();
    return;
  }
  if (page === "app") {
    initAppPage();
  }
}

document.addEventListener("DOMContentLoaded", initPage);
