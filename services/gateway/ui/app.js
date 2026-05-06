/* ── State ─────────────────────────────────────────────────────────────── */

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const configContent = document.getElementById("config-content");

let messageCount = 0;

/* ── Sidebar navigation ───────────────────────────────────────────────── */

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document
      .querySelectorAll(".nav-item")
      .forEach((n) => n.classList.remove("active"));
    item.classList.add("active");

    document
      .querySelectorAll(".view")
      .forEach((v) => v.classList.remove("active"));
    const view = document.getElementById(`view-${item.dataset.view}`);
    if (view) view.classList.add("active");

    if (item.dataset.view === "settings") {
      loadConfig();
    } else if (item.dataset.view === "chat") {
      inputEl.focus();
    }
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

/* ── Keyboard shortcut ────────────────────────────────────────────────── */

document.addEventListener("keydown", (e) => {
  // Cmd/Ctrl + . switches to Settings, Cmd/Ctrl + , switches to Chat
  if ((e.metaKey || e.ctrlKey) && e.key === ".") {
    e.preventDefault();
    document.querySelector('.nav-item[data-view="settings"]').click();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === ",") {
    e.preventDefault();
    document.querySelector('.nav-item[data-view="chat"]').click();
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
