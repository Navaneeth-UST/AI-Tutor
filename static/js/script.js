const thread = document.getElementById("thread");
const composer = document.getElementById("composer");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");
const ledgerList = document.getElementById("ledger-list");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function addUserEntry(text) {
  const el = document.createElement("div");
  el.className = "entry user";
  el.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  thread.appendChild(el);
  scrollToBottom();
}

function addTypingIndicator() {
  const el = document.createElement("div");
  el.className = "entry tutor";
  el.id = "typing-indicator";
  el.innerHTML = `<div class="bubble"><span class="typing">thinking through your answer…</span></div>`;
  thread.appendChild(el);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function addTutorEntry(data) {
  const { reply, phase, user_said, correction } = data;
  const el = document.createElement("div");
  el.className = "entry tutor";

  const tagLabel = {
    eliciting: "Asking you first",
    correcting: "Correcting the margin",
    reinforcing: "Checking it stuck",
    mastered: "Looking solid",
  }[phase] || "Tutor";

  let annotationHtml = "";
  if (correction) {
    const isAffirm = phase === "mastered";
    annotationHtml = `
      <div class="annotation ${isAffirm ? "affirm" : ""}">
        ${user_said ? `<p class="you-said">You said: <span>"${escapeHtml(user_said)}"</span></p>` : ""}
        <p class="correction">${escapeHtml(correction)}</p>
      </div>`;
  }

  el.innerHTML = `
    <span class="phase-tag ${phase}">${tagLabel}</span>
    <div class="bubble">${escapeHtml(reply)}</div>
    ${annotationHtml}
  `;
  thread.appendChild(el);
  scrollToBottom();
}

function scrollToBottom() {
  thread.scrollTop = thread.scrollHeight;
}

function renderLedger(ledger) {
  const entries = Object.entries(ledger || {});
  if (entries.length === 0) {
    ledgerList.innerHTML = `<li class="ledger-empty">Nothing opened yet — ask your first question.</li>`;
    return;
  }
  ledgerList.innerHTML = entries
    .map(([term, mastery]) => `
      <li class="ledger-item">
        <div class="term-row">
          <span class="term-name">${escapeHtml(term)}</span>
          <span class="term-pct">${mastery}%</span>
        </div>
        <div class="ledger-bar-track">
          <div class="ledger-bar-fill" style="width: ${mastery}%;"></div>
        </div>
      </li>
    `)
    .join("");
}

async function sendMessage(message) {
  addUserEntry(message);
  addTypingIndicator();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    removeTypingIndicator();

    if (!res.ok) {
      addTutorEntry({
        reply: data.error || "Something went wrong reaching the tutor model.",
        phase: "eliciting",
        user_said: "",
        correction: "",
      });
      return;
    }

    addTutorEntry(data);
    renderLedger(data.ledger);
  } catch (err) {
    removeTypingIndicator();
    addTutorEntry({
      reply: "Network hiccup — couldn't reach the server. Try again.",
      phase: "eliciting",
      user_said: "",
      correction: "",
    });
  } finally {
    sendBtn.disabled = false;
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendMessage(message);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

resetBtn.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  thread.innerHTML = `
    <div class="entry system-entry">
      <p class="system-line">
        Fresh notebook. Ask about any AI or software term —
        <span class="hint">token</span>, <span class="hint">REST</span>,
        <span class="hint">race condition</span>, <span class="hint">gradient descent</span> —
        anything. I won't define it right away. I'll ask what you already think it means first,
        then correct the margin.
      </p>
    </div>`;
  renderLedger({});
});