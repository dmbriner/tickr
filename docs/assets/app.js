const BACKEND_URL = (window.TICKR_BACKEND_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "tickr_token";
const AUTH_MODE_KEY = "tickr_auth_mode";

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

function getAuthMode() {
  return window.localStorage.getItem(AUTH_MODE_KEY) || "login";
}

function setAuthMode(mode) {
  window.localStorage.setItem(AUTH_MODE_KEY, mode);
}

function getApiUrl(path) {
  if (!BACKEND_URL) {
    throw new Error("Missing backend URL.");
  }
  return `${BACKEND_URL}${path}`;
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

  const response = await fetch(getApiUrl(path), {
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

function setModeUi(mode) {
  const isSignup = mode === "signup";
  const loginModeButton = document.getElementById("login-mode-button");
  const signupModeButton = document.getElementById("signup-mode-button");
  const confirmField = document.getElementById("confirm-password-field");
  const submitButton = document.getElementById("auth-submit");
  const passwordInput = document.getElementById("password");
  const confirmInput = document.getElementById("confirm-password");

  if (loginModeButton) {
    loginModeButton.className = isSignup ? "button secondary" : "button primary";
  }
  if (signupModeButton) {
    signupModeButton.className = isSignup ? "button primary" : "button secondary";
  }
  if (confirmField) {
    confirmField.hidden = !isSignup;
  }
  if (submitButton) {
    submitButton.textContent = isSignup ? "Create Account" : "Sign In";
  }
  if (passwordInput) {
    passwordInput.autocomplete = isSignup ? "new-password" : "current-password";
  }
  if (confirmInput) {
    confirmInput.required = isSignup;
    if (!isSignup) {
      confirmInput.value = "";
    }
  }
}

function setAuthFeedback({ error = "", success = "" } = {}) {
  const errorNode = document.getElementById("login-error");
  const successNode = document.getElementById("login-success");

  if (errorNode) {
    errorNode.textContent = error;
    errorNode.hidden = !error;
  }
  if (successNode) {
    successNode.textContent = success;
    successNode.hidden = !success;
  }
}

async function handleAuthSubmit(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const mode = getAuthMode();
  const email = form.email.value.trim();
  const password = form.password.value;
  const confirmPassword = form.confirmPassword ? form.confirmPassword.value : "";

  setAuthFeedback();

  if (!BACKEND_URL || BACKEND_URL.includes("your-railway-app")) {
    setAuthFeedback({ error: "Set your Railway backend URL in docs/assets/config.js before using auth." });
    return;
  }

  if (mode === "signup" && password !== confirmPassword) {
    setAuthFeedback({ error: "Passwords do not match." });
    return;
  }

  try {
    const response = await fetch(getApiUrl(`/api/auth/${mode === "signup" ? "signup" : "login"}`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || !payload.access_token) {
      setAuthFeedback({ error: payload.detail || "Unable to authenticate." });
      return;
    }

    setToken(payload.access_token);
    setAuthFeedback({
      success: mode === "signup" ? "Account created. Redirecting..." : "Signed in. Redirecting...",
    });
    redirectTo("./app.html");
  } catch {
    setAuthFeedback({ error: "Network error. Please try again." });
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
  const profilesCountNode = document.getElementById("private-profiles-count");
  const analysesCountNode = document.getElementById("private-analyses-count");

  try {
    const [meResponse, profilesResponse, analysesResponse] = await Promise.all([
      authFetch("/api/auth/me"),
      authFetch("/api/me/api-profiles"),
      authFetch("/api/me/analyses"),
    ]);
    if (!meResponse || !profilesResponse || !analysesResponse) {
      return;
    }

    const mePayload = await meResponse.json().catch(() => ({}));
    const profilesPayload = await profilesResponse.json().catch(() => []);
    const analysesPayload = await analysesResponse.json().catch(() => []);

    if (!meResponse.ok) {
      errorNode.textContent = mePayload.detail || "Unable to verify session.";
      errorNode.hidden = false;
      statusNode.textContent = "Session unavailable.";
      return;
    }

    statusNode.textContent = "Signed in.";
    emailNode.textContent = mePayload.email || "";
    okNode.textContent = "true";
    profilesCountNode.textContent = String(Array.isArray(profilesPayload) ? profilesPayload.length : 0);
    analysesCountNode.textContent = String(Array.isArray(analysesPayload) ? analysesPayload.length : 0);
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
  const loginModeButton = document.getElementById("login-mode-button");
  const signupModeButton = document.getElementById("signup-mode-button");
  const mode = getAuthMode();

  setModeUi(mode);

  if (loginModeButton) {
    loginModeButton.addEventListener("click", () => {
      setAuthMode("login");
      setAuthFeedback();
      setModeUi("login");
    });
  }

  if (signupModeButton) {
    signupModeButton.addEventListener("click", () => {
      setAuthMode("signup");
      setAuthFeedback();
      setModeUi("signup");
    });
  }

  if (form) {
    form.addEventListener("submit", handleAuthSubmit);
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
