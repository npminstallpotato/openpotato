/* ── Theme ──────────────────────────────────────────────────────────────── */

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  const checkbox = document.getElementById("theme-checkbox");
  if (checkbox) {
    checkbox.checked = theme === "dark";
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  setTheme(current === "dark" ? "light" : "dark");
}

// Restore saved theme on load
const savedTheme = localStorage.getItem("theme") || "light";
setTheme(savedTheme);

// Wire up toggle — use checkbox change event for reliable state sync
const checkbox = document.getElementById("theme-checkbox");
if (checkbox) {
  checkbox.addEventListener("change", (e) => {
    setTheme(e.target.checked ? "dark" : "light");
  });
}

/* ── State ─────────────────────────────────────────────────────────────── */

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
let messageCount = 0;

/* ── Settings / Config ────────────────────────────────────────────────── */

const settingsForm = document.getElementById("settings-form");
const settingsStatus = document.getElementById("settings-status");
const saveBtn = document.getElementById("settings-save-btn");
const restoreBtn = document.getElementById("settings-restore-btn");
const cancelBtn = document.getElementById("settings-cancel-btn");
const modelInput = document.getElementById("setting-model");
const baseUrlInput = document.getElementById("setting-base-url");
const apiKeyInput = document.getElementById("setting-api-key");

let initialSettings = {};

/* ── Router ────────────────────────────────────────────────────────────── */

function getViewFromPath(path) {
  if (path === "/settings") return "settings";
  return "chat"; // default — also covers "/" and "/chat"
}

function navigateTo(view) {
  const path = view === "settings" ? "/settings" : "/chat";
  history.pushState({ view }, "", path);
  renderView(view);
}

function renderView(view) {
  // Update nav items
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.view === view);
  });

  // Update views
  document.querySelectorAll(".view").forEach((v) => {
    v.classList.toggle("active", v.id === `view-${view}`);
  });

  // Side effects per view
  if (view === "settings") {
    loadSettings();
  } else if (view === "chat") {
    inputEl.focus();
  }
}

/* ── Initial route ────────────────────────────────────────────────────── */

// Redirect "/" → "/chat"
if (window.location.pathname === "/") {
  history.replaceState({ view: "chat" }, "", "/chat");
}

const initialView = getViewFromPath(window.location.pathname);
renderView(initialView);

/* ── Browser navigation (back/forward) ────────────────────────────────── */

window.addEventListener("popstate", () => {
  const view = getViewFromPath(window.location.pathname);
  renderView(view);
});

/* ── Sidebar navigation ───────────────────────────────────────────────── */

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    navigateTo(item.dataset.view);
  });
});

/* ── Helpers ──────────────────────────────────────────────────────────── */

function scrollToBottom() {
  chatEl.scrollTo({ top: chatEl.scrollHeight, behavior: "smooth" });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/* ── Render message ───────────────────────────────────────────────────── */

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.style.animationDelay = "0s";
  div.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  chatEl.appendChild(div);
  messageCount++;
  scrollToBottom();
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "message ai typing";
  div.id = "typing-indicator";
  div.innerHTML = `<div class="bubble"><span></span><span></span><span></span></div>`;
  chatEl.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function showError(msg) {
  const div = document.createElement("div");
  div.className = "message error";
  div.innerHTML = `<div class="bubble">${escapeHtml(msg)}</div>`;
  chatEl.appendChild(div);
  scrollToBottom();
}

/* ── Chat ──────────────────────────────────────────────────────────────── */

async function sendMessage(text) {
  addMessage("user", text);
  showTyping();
  sendBtn.disabled = true;

  try {
    const resp = await fetch("/api/llm/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_name: "test" }),
    });

    removeTyping();

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showError(err.detail || `Server error (${resp.status})`);
      return;
    }

    const data = await resp.json();
    addMessage("ai", data.result || "No response text");
  } catch (err) {
    removeTyping();
    showError("Network error — is the server running?");
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

/* ── Events ───────────────────────────────────────────────────────────── */

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendMessage(text);
});

/* ── Keyboard shortcuts ───────────────────────────────────────────────── */

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === ".") {
    e.preventDefault();
    navigateTo("settings");
  }
  if ((e.metaKey || e.ctrlKey) && e.key === ",") {
    e.preventDefault();
    navigateTo("chat");
  }
});

function getCurrentSettings() {
  return {
    LLM_MODEL: modelInput.value.trim(),
    LLM_BASE_URL: baseUrlInput.value.trim(),
    LLM_API_KEY: apiKeyInput.value.trim(),
  };
}

function settingsChanged() {
  const current = getCurrentSettings();
  return (
    current.LLM_MODEL !== initialSettings.LLM_MODEL ||
    current.LLM_BASE_URL !== initialSettings.LLM_BASE_URL ||
    current.LLM_API_KEY !== initialSettings.LLM_API_KEY
  );
}

function updateSaveButton() {
  const changed = settingsChanged();
  saveBtn.disabled = !changed;
  saveBtn.style.opacity = changed ? "" : "0.45";
}

async function loadSettings() {
  settingsStatus.textContent = "";
  settingsStatus.className = "settings-status";
  try {
    const resp = await fetch("/api/settings");
    if (!resp.ok) {
      settingsStatus.textContent = `Error loading settings (${resp.status})`;
      settingsStatus.className = "settings-status error";
      return;
    }
    const data = await resp.json();
    modelInput.value = data.LLM_MODEL || "";
    baseUrlInput.value = data.LLM_BASE_URL || "";
    apiKeyInput.value = data.LLM_API_KEY || "";
    initialSettings = getCurrentSettings();
    updateSaveButton();
  } catch {
    settingsStatus.textContent = "Network error — is the server running?";
    settingsStatus.className = "settings-status error";
  }
}

async function saveSettings(e) {
  e.preventDefault();

  saveBtn.blur();
  if (!confirm("Save these settings?")) return;

  saveBtn.disabled = true;
  restoreBtn.disabled = true;
  cancelBtn.disabled = true;
  settingsStatus.textContent = "";
  settingsStatus.className = "settings-status";

  const payload = getCurrentSettings();

  try {
    const resp = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      settingsStatus.textContent = err.detail || `Error saving (${resp.status})`;
      settingsStatus.className = "settings-status error";
      saveBtn.disabled = false;
      return;
    }
    settingsStatus.textContent = "Settings saved successfully";
    settingsStatus.className = "settings-status success";
    initialSettings = getCurrentSettings();
    updateSaveButton();
  } catch {
    settingsStatus.textContent = "Network error — is the server running?";
    settingsStatus.className = "settings-status error";
    saveBtn.disabled = false;
  } finally {
    restoreBtn.disabled = false;
    cancelBtn.disabled = false;
  }
}

async function restoreDefaults() {
  restoreBtn.blur();
  if (!confirm("Restore default settings? This will overwrite your current values.")) return;

  saveBtn.disabled = true;
  restoreBtn.disabled = true;
  cancelBtn.disabled = true;
  settingsStatus.textContent = "";
  settingsStatus.className = "settings-status";

  try {
    // Fetch defaults from settings.example.json via Util API
    const defResp = await fetch("/api/settings/defaults");
    if (!defResp.ok) {
      settingsStatus.textContent = "Error fetching defaults";
      settingsStatus.className = "settings-status error";
      saveBtn.disabled = false;
      return;
    }
    const defaults = await defResp.json();

    // Restore by saving the defaults
    const resp = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(defaults),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      settingsStatus.textContent = err.detail || `Error restoring (${resp.status})`;
      settingsStatus.className = "settings-status error";
      saveBtn.disabled = false;
      return;
    }

    // Update form fields from fetched defaults
    modelInput.value = defaults.LLM_MODEL || "";
    baseUrlInput.value = defaults.LLM_BASE_URL || "";
    apiKeyInput.value = defaults.LLM_API_KEY || "";
    initialSettings = getCurrentSettings();
    updateSaveButton();

    settingsStatus.textContent = "Defaults restored";
    settingsStatus.className = "settings-status success";
  } catch {
    settingsStatus.textContent = "Network error — is the server running?";
    settingsStatus.className = "settings-status error";
    saveBtn.disabled = false;
  } finally {
    restoreBtn.disabled = false;
    cancelBtn.disabled = false;
  }
}

async function cancelEdits() {
  cancelBtn.blur();
  settingsStatus.textContent = "";
  settingsStatus.className = "settings-status";
  if (!settingsChanged() || confirm("Discard unsaved changes?")) {
    restoreBtn.disabled = true;
    cancelBtn.disabled = true;
    await loadSettings();
    restoreBtn.disabled = false;
    cancelBtn.disabled = false;
  }
}

if (settingsForm) {
  settingsForm.addEventListener("submit", saveSettings);
  restoreBtn.addEventListener("click", restoreDefaults);
  cancelBtn.addEventListener("click", cancelEdits);
  [modelInput, baseUrlInput, apiKeyInput].forEach((input) => {
    input.addEventListener("input", updateSaveButton);
  });
}
