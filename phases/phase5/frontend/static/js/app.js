const el = {
  appShell: document.querySelector(".app-shell"),
  chatView: document.getElementById("chat-view"),
  heroSection: document.getElementById("hero-section"),
  title: document.getElementById("app-title"),
  greetingText: document.getElementById("greeting-text"),
  disclaimerBanner: document.getElementById("disclaimer-banner"),
  footerDisclaimer: document.getElementById("footer-disclaimer"),
  welcome: document.getElementById("welcome-message"),
  exampleList: document.getElementById("example-list"),
  statusBanner: document.getElementById("status-banner"),
  form: document.getElementById("chat-form"),
  input: document.getElementById("query-input"),
  charCount: document.getElementById("char-count"),
  submitBtn: document.getElementById("submit-btn"),
  submitSpinner: document.getElementById("submit-spinner"),
  responsePanel: document.getElementById("response-panel"),
  responseBody: document.getElementById("response-body"),
  responseMeta: document.getElementById("response-meta"),
  responseSource: document.getElementById("response-source"),
  sourceLink: document.getElementById("source-link"),
  sourceLinkText: document.getElementById("source-link-text"),
  responseUpdated: document.getElementById("response-updated"),
  newChatBtn: document.getElementById("new-chat-btn"),
  sidebarToggle: document.getElementById("sidebar-toggle"),
};

const QUICK_ACTION_ICONS = {
  expense: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  lock: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="currentColor" stroke-width="1.5"/></svg>`,
  benchmark: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M3 3v18h18M7 16l4-4 4 4 5-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  default: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/><path d="M12 8v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
};

function getTimeGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function pickQuickActionIcon(text) {
  const lower = text.toLowerCase();
  if (lower.includes("expense")) return QUICK_ACTION_ICONS.expense;
  if (lower.includes("lock-in") || lower.includes("lock in")) return QUICK_ACTION_ICONS.lock;
  if (lower.includes("benchmark")) return QUICK_ACTION_ICONS.benchmark;
  return QUICK_ACTION_ICONS.default;
}

function shortLabel(text) {
  if (text.toLowerCase().includes("expense ratio")) return "Expense ratio";
  if (text.toLowerCase().includes("lock-in")) return "Lock-in period";
  if (text.toLowerCase().includes("benchmark")) return "Benchmark index";
  if (text.length <= 28) return text;
  return `${text.slice(0, 25)}…`;
}

function showStatus(message) {
  el.statusBanner.textContent = message;
  el.statusBanner.classList.remove("status-banner--hidden");
  el.statusBanner.classList.add("status-banner--warning");
}

function hideStatus() {
  el.statusBanner.classList.add("status-banner--hidden");
}

function updateCharCount() {
  const length = el.input.value.length;
  el.charCount.textContent = `${length} / 500`;
}

function autoResizeInput() {
  el.input.style.height = "auto";
  el.input.style.height = `${Math.min(el.input.scrollHeight, 160)}px`;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function renderExamples(questions) {
  el.exampleList.innerHTML = "";
  questions.forEach((item) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-action";
    button.title = item.text;
    button.innerHTML = `<span class="quick-action__icon">${pickQuickActionIcon(item.text)}</span><span>${shortLabel(item.text)}</span>`;
    button.addEventListener("click", () => {
      el.input.value = item.text;
      updateCharCount();
      autoResizeInput();
      el.input.focus();
      askQuestion(item.text);
    });
    li.appendChild(button);
    el.exampleList.appendChild(li);
  });
}

function resetChat() {
  el.input.value = "";
  updateCharCount();
  autoResizeInput();
  el.responsePanel.classList.add("response--hidden");
  el.responsePanel.classList.remove("response-thread--success", "response-thread--refusal");
  el.chatView.classList.remove("chat-view--has-response");
  el.input.focus();
}

function renderResponse(payload) {
  el.chatView.classList.add("chat-view--has-response");
  el.responsePanel.classList.remove("response--hidden", "response-thread--success", "response-thread--refusal");
  el.responsePanel.classList.toggle("response-thread--refusal", payload.refused);
  el.responsePanel.classList.toggle("response-thread--success", !payload.refused && payload.success);

  const body = payload.answer_body || payload.answer;
  el.responseBody.textContent = body;

  const hasMeta = Boolean(payload.source_url || payload.last_updated);
  el.responseMeta.classList.toggle("response__meta--hidden", !hasMeta);

  if (payload.source_url) {
    el.responseSource.classList.remove("response__meta--hidden");
    el.sourceLink.href = payload.source_url;
    el.sourceLinkText.textContent = payload.source_url;
  } else {
    el.responseSource.classList.add("response__meta--hidden");
  }

  if (payload.last_updated) {
    el.responseUpdated.classList.remove("response__meta--hidden");
    el.responseUpdated.innerHTML = `<span class="response-thread__label">Updated</span><span>Last updated from sources: ${payload.last_updated}</span>`;
  } else {
    el.responseUpdated.classList.add("response__meta--hidden");
  }

  el.responsePanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setLoading(isLoading) {
  el.submitBtn.disabled = isLoading;
  el.submitBtn.classList.toggle("composer__send--loading", isLoading);
  el.submitSpinner.classList.toggle("composer__spinner--hidden", !isLoading);
}

async function askQuestion(query) {
  const trimmed = query.trim();
  if (!trimmed) {
    return;
  }

  setLoading(true);
  try {
    const payload = await fetchJson("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: trimmed }),
    });
    renderResponse(payload);
  } catch (error) {
    el.chatView.classList.add("chat-view--has-response");
    el.responsePanel.classList.remove("response--hidden", "response-thread--success");
    el.responsePanel.classList.add("response-thread--refusal");
    el.responseBody.textContent =
      "Something went wrong while processing your question. Please try again.";
    el.responseMeta.classList.add("response__meta--hidden");
    console.error(error);
  } finally {
    setLoading(false);
  }
}

async function bootstrap() {
  el.greetingText.textContent = getTimeGreeting();

  try {
    const [meta, health] = await Promise.all([
      fetchJson("/api/v1/meta"),
      fetchJson("/health"),
    ]);

    document.title = meta.title;
    el.title.textContent = meta.title;
    el.disclaimerBanner.textContent = meta.disclaimer;
    el.footerDisclaimer.textContent = meta.disclaimer;
    el.welcome.textContent = meta.welcome_message;
    renderExamples(meta.example_questions);

    if (!health.index_ready) {
      showStatus(
        "The knowledge index is not ready. Run the Phase 2 indexing pipeline before asking questions."
      );
      el.submitBtn.disabled = true;
    } else {
      hideStatus();
    }
  } catch (error) {
    showStatus("Unable to load assistant configuration. Is the API server running?");
    console.error(error);
  }
}

el.form.addEventListener("submit", (event) => {
  event.preventDefault();
  askQuestion(el.input.value);
});

el.input.addEventListener("input", () => {
  updateCharCount();
  autoResizeInput();
});

el.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    askQuestion(el.input.value);
  }
});

el.newChatBtn.addEventListener("click", resetChat);

el.sidebarToggle.addEventListener("click", () => {
  el.appShell.classList.toggle("app-shell--sidebar-collapsed");
});

updateCharCount();
autoResizeInput();
bootstrap();
