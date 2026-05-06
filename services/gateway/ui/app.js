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
const configContent = document.getElementById("config-content");

let messageCount = 0;

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
    loadConfig();
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
      body: JSON.stringify({ message: text }),
    });

    removeTyping();

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showError(err.detail || `Server error (${resp.status})`);
      return;
    }

    const data = await resp.json();
    const textBlock = data.content.find((b) => b.type === "text");
    addMessage("ai", textBlock ? textBlock.text : "No response text");
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

/* ── Settings / Config ────────────────────────────────────────────────── */

async function loadConfig() {
  configContent.textContent = "Loading…";

  try {
    const resp = await fetch("/api/config");
    if (!resp.ok) {
      configContent.textContent = `Error: ${resp.status} ${resp.statusText}`;
      return;
    }
    const data = await resp.json();
    configContent.textContent = JSON.stringify(data, null, 2);
  } catch {
    configContent.textContent = "Network error — is the server running?";
  }
}
