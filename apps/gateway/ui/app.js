/* ── State ─────────────────────────────────────────────────────────────── */

let conversation = [];

const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const configBtn = document.getElementById("config-btn");
const configModal = document.getElementById("config-modal");
const configContent = document.getElementById("config-content");
const closeConfig = document.getElementById("close-config");

/* ── Helpers ──────────────────────────────────────────────────────────── */

function scrollBottom() {
  chatEl.parentElement.scrollTop = chatEl.parentElement.scrollHeight;
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
  div.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  chatEl.appendChild(div);
  scrollBottom();
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "message ai typing";
  div.id = "typing-indicator";
  div.innerHTML = `<div class="bubble"><span></span><span></span><span></span></div>`;
  chatEl.appendChild(div);
  scrollBottom();
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
  scrollBottom();
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
    addMessage("ai", data.reply);
  } catch (err) {
    removeTyping();
    showError("Network error — is the server running?");
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

/* ── Events ────────────────────────────────────────────────────────────── */

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendMessage(text);
});

/* ── Config modal ──────────────────────────────────────────────────────── */

configBtn.addEventListener("click", async () => {
  configContent.textContent = "Loading…";
  configModal.showModal();

  try {
    const resp = await fetch("/api/utils/config");
    if (!resp.ok) {
      configContent.textContent = `Error: ${resp.status} ${resp.statusText}`;
      return;
    }
    const data = await resp.json();
    configContent.textContent = JSON.stringify(data, null, 2);
  } catch {
    configContent.textContent = "Network error — is the utils service running?";
  }
});

closeConfig.addEventListener("click", () => configModal.close());
configModal.addEventListener("click", (e) => {
  if (e.target === configModal) configModal.close();
});
