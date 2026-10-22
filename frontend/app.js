// ==========================================================================
// JARVIS V2 — Intelligent Personal AI Operating Layer Client Controller
// ==========================================================================

const API_BASE = "";

// Global State
const state = {
  currentView: "dashboard",
  sidebarCollapsed: false,
  theme: "cyan",
  sfxEnabled: true,
  voiceOutputEnabled: true,
  isListening: false,
  isSpeaking: false,
  isProcessing: false,
  lastUtterance: "",
  activeChatSessionId: "session_default",
  chatHistory: [],
  pendingAuthorizations: [],
  workspaceFiles: [],
  memories: [],
  tools: [],
  latencyMs: 3,
  wsConnected: false
};

// Audio Synthesizer & Web Speech
let audioCtx = null;
let recognition = null;
let ws = null;
let coreCanvasAnimId = null;
let neuralReactor = null;

// ==========================================================================
// 1. Initialization & Lifecycle
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  loadStoredPreferences();
  initAudioContext();
  initNavigation();
  initTopNav();
  initGlobalHotkeys();
  initSpeechRecognition();
  initEventBusWebSocket();
  initVoiceOrbCanvas();
  
  // Initial Data Hydration
  refreshTelemetry();
  refreshPendingTasks();
  refreshWorkspaceFiles();
  refreshMemoryData();
  refreshToolsRegistry();
  
  // Background Telemetry Poller (every 10 seconds)
  setInterval(refreshTelemetry, 10000);
  setInterval(refreshPendingTasks, 12000);

  // Setup Chat & Composer
  setupChatHandlers();
  
  showToast("JARVIS V2 Operating Layer initialized. Systems nominal.", "info");
});

function loadStoredPreferences() {
  const savedTheme = localStorage.getItem("jarvis_theme") || "cyan";
  setThemeAccent(savedTheme);

  const savedSidebar = localStorage.getItem("jarvis_sidebar_collapsed");
  if (savedSidebar === "true") {
    toggleSidebar(true);
  }

  const savedSfx = localStorage.getItem("jarvis_sfx");
  if (savedSfx !== null) {
    state.sfxEnabled = savedSfx === "true";
    const sfxBtn = document.getElementById("toggle-sfx-btn");
    if (sfxBtn) sfxBtn.textContent = state.sfxEnabled ? "ENABLED" : "MUTED";
  }

  const savedName = localStorage.getItem("jarvis_user_name") || "Mahi";
  updateUserDisplayName(savedName);
}

function updateUserDisplayName(name) {
  const sidebarName = document.getElementById("sidebar-user-name");
  const sidebarAvatar = document.getElementById("sidebar-user-avatar");
  const greeting = document.getElementById("hero-greeting-text");
  const settingsInput = document.getElementById("settings-username-input");

  if (sidebarName) sidebarName.textContent = name;
  if (sidebarAvatar) sidebarAvatar.textContent = name.charAt(0).toUpperCase();
  if (greeting) greeting.textContent = `Welcome back, ${name}.`;
  if (settingsInput) settingsInput.value = name;
}

// ==========================================================================
// 2. Navigation & Workspace Switching
// ==========================================================================
function initNavigation() {
  const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const view = item.getAttribute("data-view");
      if (view) switchView(view);
    });
  });

  const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", () => toggleSidebar());
  }

  const mobileToggleBtn = document.getElementById("mobile-menu-toggle");
  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener("click", () => {
      const sidebar = document.getElementById("app-sidebar");
      sidebar?.classList.toggle("mobile-open");
    });
  }

  const brandHomeBtn = document.getElementById("brand-home-btn");
  if (brandHomeBtn) {
    brandHomeBtn.addEventListener("click", () => switchView("dashboard"));
  }

  const userProfileBtn = document.getElementById("user-profile-btn");
  if (userProfileBtn) {
    userProfileBtn.addEventListener("click", () => switchView("settings"));
  }
}

function switchView(viewName) {
  const validViews = ["dashboard", "chat", "voice", "tasks", "projects", "memory", "tools", "history", "settings"];
  if (!validViews.includes(viewName)) return;

  state.currentView = viewName;

  // Update Nav Items Active State
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    item.classList.toggle("active", item.getAttribute("data-view") === viewName);
  });

  // Update Workspace View Containers
  document.querySelectorAll(".workspace-view").forEach(view => {
    const isTarget = view.id === `view-${viewName}`;
    view.classList.toggle("active", isTarget);
  });

  // Update Breadcrumb Titles
  const breadcrumbMap = {
    dashboard: { title: "Command Dashboard", sub: "Neural Operating Overview & Real-Time Telemetry" },
    chat: { title: "AI Chat Workspace", sub: "Autonomous Multimodal Dialogue & Tool Execution" },
    voice: { title: "Voice Assistant", sub: "Hands-Free Speech Interaction with Quantum Holographic Core" },
    tasks: { title: "Tasks & Automation Center", sub: "Security Authorizations, Gatekeeper, and Background Services" },
    projects: { title: "Projects & Workspace Files", sub: "Sandboxed File Explorer (workspace_files/)" },
    memory: { title: "Long-Term Memory Store", sub: "Extracted Personal Preferences & Persistent Facts" },
    tools: { title: "Connected Tools Registry", sub: "3-Tier Classified Hardware, Browser, and Cognitive Tool Suite" },
    history: { title: "Activity History & Audit", sub: "Complete Chronological Record of System Directives" },
    settings: { title: "System Settings", sub: "Operator Preferences, Visual Themes, and API Connectors" }
  };

  const info = breadcrumbMap[viewName];
  if (info) {
    const titleEl = document.getElementById("breadcrumb-title");
    const subEl = document.getElementById("breadcrumb-sub");
    if (titleEl) titleEl.textContent = info.title;
    if (subEl) subEl.textContent = info.sub;
  }

  // Close mobile drawer if open
  document.getElementById("app-sidebar")?.classList.remove("mobile-open");

  playSynthesizedSound("click");

  // View-Specific Refreshes
  if (viewName === "projects") refreshWorkspaceFiles();
  if (viewName === "memory") refreshMemoryData();
  if (viewName === "tools") refreshToolsRegistry();
  if (viewName === "tasks") refreshPendingTasks();
  if (viewName === "history") renderActivityHistory();
}

function toggleSidebar(forceState = null) {
  const sidebar = document.getElementById("app-sidebar");
  if (!sidebar) return;

  if (forceState !== null) {
    state.sidebarCollapsed = forceState;
  } else {
    state.sidebarCollapsed = !state.sidebarCollapsed;
  }

  sidebar.classList.toggle("collapsed", state.sidebarCollapsed);
  localStorage.setItem("jarvis_sidebar_collapsed", state.sidebarCollapsed);
}

// ==========================================================================
// 3. Top Navigation & Global Hotkeys
// ==========================================================================
function initTopNav() {
  const searchInput = document.getElementById("global-search-input");
  if (searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && searchInput.value.trim()) {
        const query = searchInput.value.trim();
        searchInput.value = "";
        executeDirective(query);
      }
    });
  }

  const topMicBtn = document.getElementById("top-mic-btn");
  if (topMicBtn) {
    topMicBtn.addEventListener("click", () => {
      toggleVoiceAssistant();
    });
  }

  const topVisionBtn = document.getElementById("top-vision-btn");
  if (topVisionBtn) {
    topVisionBtn.addEventListener("click", openVisionModal);
  }

  const notificationsBtn = document.getElementById("notifications-btn");
  if (notificationsBtn) {
    notificationsBtn.addEventListener("click", () => {
      showToast("All telemetry channels active. 0 critical security alerts.", "info");
    });
  }
}

function initGlobalHotkeys() {
  window.addEventListener("keydown", (e) => {
    // Ctrl+K: Global Search Focus
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const search = document.getElementById("global-search-input");
      if (search) search.focus();
    }
    // Ctrl+B: Toggle Sidebar
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
      e.preventDefault();
      toggleSidebar();
    }
    // Escape: Close Modals
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.add("hidden"));
    }
  });
}

// ==========================================================================
// 4. Web Audio Synthesizer (Futuristic Sci-Fi Audio Cues)
// ==========================================================================
function initAudioContext() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) audioCtx = new AudioContext();
  }
}

function playSynthesizedSound(type) {
  if (!state.sfxEnabled) return;
  try {
    initAudioContext();
    if (!audioCtx) return;
    if (audioCtx.state === "suspended") audioCtx.resume();

    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === "click") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(1100, now);
      gain.gain.setValueAtTime(0.04, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
      osc.start(now);
      osc.stop(now + 0.04);
    } else if (type === "transmit") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(700, now);
      osc.frequency.exponentialRampToValueAtTime(1400, now + 0.09);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      osc.start(now);
      osc.stop(now + 0.1);
    } else if (type === "reply") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(800, now);
      osc.frequency.exponentialRampToValueAtTime(1200, now + 0.12);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
      osc.start(now);
      osc.stop(now + 0.15);
    } else if (type === "alert") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(220, now + 0.2);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);
    }
  } catch (e) {}
}

function toggleSFX() {
  state.sfxEnabled = !state.sfxEnabled;
  localStorage.setItem("jarvis_sfx", state.sfxEnabled);
  const sfxBtn = document.getElementById("toggle-sfx-btn");
  if (sfxBtn) sfxBtn.textContent = state.sfxEnabled ? "ENABLED" : "MUTED";
  playSynthesizedSound("click");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast-item toast-${type}`;
  
  const icon = type === "alert" ? "⚠️" : (type === "success" ? "✓" : "ℹ️");
  toast.innerHTML = `<span style="color: var(--accent-primary); font-weight:700;">${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.2s ease";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// ==========================================================================
// 5. Real-Time Telemetry & System Health
// ==========================================================================
async function refreshTelemetry() {
  const start = performance.now();
  try {
    const res = await fetch(`${API_BASE}/api/system/telemetry`);
    state.latencyMs = Math.round(performance.now() - start);

    if (res.ok) {
      const data = await res.json();
      updateTelemetryUI(data, state.latencyMs);
    }
  } catch (e) {
    const statusText = document.getElementById("status-text");
    const statusDot = document.getElementById("status-dot");
    if (statusText) statusText.textContent = "OFFLINE (Connecting...)";
    if (statusDot) {
      statusDot.style.background = "var(--status-rose)";
      statusDot.style.boxShadow = "0 0 8px var(--status-rose)";
    }
  }
}

function updateTelemetryUI(data, latency) {
  // Top Status Pill
  const statusText = document.getElementById("status-text");
  const statusDot = document.getElementById("status-dot");
  if (statusText) statusText.textContent = `SYSTEM ONLINE (${latency}ms)`;
  if (statusDot) {
    statusDot.style.background = "var(--status-emerald)";
    statusDot.style.boxShadow = "0 0 8px var(--status-emerald)";
  }

  // Battery Telemetry
  if (data.battery) {
    const batPct = data.battery.percentage || 100;
    const batStatus = data.battery.status || "Connected";
    const batValEl = document.getElementById("metric-battery-val");
    const batStatusEl = document.getElementById("metric-battery-status");
    const batBarEl = document.getElementById("metric-battery-bar");

    if (batValEl) batValEl.textContent = `${batPct}%`;
    if (batStatusEl) batStatusEl.textContent = batStatus;
    if (batBarEl) batBarEl.style.width = `${batPct}%`;
  }
}

// ==========================================================================
// 6. WebSocket EventBus Stream
// ==========================================================================
function initEventBusWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/events`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      state.wsConnected = true;
      const pill = document.getElementById("eventbus-live-pill");
      if (pill) {
        pill.textContent = "CONNECTED";
        pill.className = "pill-badge pill-emerald";
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleIncomingEvent(payload);
      } catch (e) {}
    };

    ws.onclose = () => {
      state.wsConnected = false;
      const pill = document.getElementById("eventbus-live-pill");
      if (pill) {
        pill.textContent = "RECONNECTING";
        pill.className = "pill-badge pill-amber";
      }
      setTimeout(initEventBusWebSocket, 4000);
    };
  } catch (e) {}
}

function handleIncomingEvent(event) {
  const stream = document.getElementById("dashboard-eventbus-stream");
  if (!stream) return;

  const item = document.createElement("div");
  item.className = "activity-item";

  const eventType = event.type || "EVENT";
  const data = event.data || {};
  const message = data.message || data.raw_input || JSON.stringify(data);

  item.innerHTML = `
    <span class="activity-badge">${eventType}</span>
    <span style="color: var(--text-secondary); word-break: break-word;">${message}</span>
  `;

  stream.insertBefore(item, stream.firstChild);
  if (stream.children.length > 15) {
    stream.removeChild(stream.lastChild);
  }

  // If confirmation is required, refresh pending tasks
  if (eventType === "CONFIRMATION_REQUIRED") {
    refreshPendingTasks();
    playSynthesizedSound("alert");
  }
}

// ==========================================================================
// 7. Core AI Directive Execution (Dashboard & Chat)
// ==========================================================================
function setupChatHandlers() {
  const heroForm = document.getElementById("hero-command-form");
  if (heroForm) {
    heroForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = document.getElementById("hero-command-input");
      if (input && input.value.trim()) {
        const text = input.value.trim();
        input.value = "";
        executeDirective(text);
      }
    });
  }

  const chatForm = document.getElementById("chat-form");
  const textarea = document.getElementById("user-input");
  
  if (chatForm && textarea) {
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
      }
    });

    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!textarea.value.trim()) return;
      const text = textarea.value.trim();
      textarea.value = "";
      textarea.style.height = "auto";
      executeDirective(text);
    });

    const composerMicBtn = document.getElementById("mic-btn");
    if (composerMicBtn) {
      composerMicBtn.addEventListener("click", () => {
        toggleVoiceAssistant();
      });
    }
  }

  const newChatBtn = document.getElementById("new-chat-btn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
      const stream = document.getElementById("chat-stream");
      if (stream) {
        stream.innerHTML = `
          <div class="chat-entry assistant-entry">
            <div class="entry-avatar">J</div>
            <div class="entry-bubble">
              <div class="entry-meta-header">
                <span class="jarvis-tag">// JARVIS CORE</span>
                <span>NEW DIALOGUE</span>
              </div>
              <p>Dialogue stream refreshed. How can I assist you now, Mahi?</p>
            </div>
          </div>
        `;
      }
      playSynthesizedSound("click");
      showToast("Started a new conversation session.", "info");
    });
  }

  const clearChatBtn = document.getElementById("clear-chat-btn");
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      document.getElementById("new-chat-btn")?.click();
    });
  }
}

function executeQuickAction(directive) {
  executeDirective(directive);
}

async function executeDirective(text) {
  if (!text || state.isProcessing) return;
  state.isProcessing = true;

  // Interrupt previous speech playback so user input takes immediate priority
  if (state.isSpeaking) {
    try { window.speechSynthesis.cancel(); } catch (e) {}
    state.isSpeaking = false;
  }

  playSynthesizedSound("transmit");

  // Ensure user sees the dialogue
  if (state.currentView !== "chat" && state.currentView !== "voice") {
    switchView("chat");
  }

  // Append user message
  appendUserMessage(text);

  // Update Recent Chats list on Dashboard
  recordDashboardActivity("USER", text);

  // Update Voice Live Box if in Voice view
  const voiceTranscript = document.getElementById("voice-live-transcript");
  if (voiceTranscript) {
    voiceTranscript.textContent = `"${text}"`;
  }
  setVoiceStageState("thinking");

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    playSynthesizedSound(data.pending_action ? "alert" : "reply");

    // Open targeted browser URL if directive requested navigation
    if (data.open_url) {
      try {
        window.currentOpenedMediaTab = window.open(data.open_url, "_blank");
      } catch (e) {
        console.warn("Could not open URL in new window:", e);
      }
    }

    // Handle tab / media closing
    const isCloseAction = 
      data.action === "close_tab" || 
      data.metadata?.action === "close_tab" ||
      data.tool_result?.output?.action === "close_tab" ||
      data.action === "close_media" ||
      (data.reply && data.reply.toLowerCase().includes("closed the current tab")) ||
      (data.reply && data.reply.toLowerCase().includes("closing current tab"));
    if (isCloseAction) {
      closeActiveMedia();
      try {
        window.focus();
      } catch (e) {}
    }

    appendAssistantMessage(data);
    recordDashboardActivity("JARVIS", data.reply);

    // Vocalize with Speech Synthesis
    if (data.reply) {
      state.lastUtterance = data.reply;
      speakJarvis(data.reply);
    } else {
      setVoiceStageState("idle");
    }

    // If pending action exists, refresh pending tasks
    if (data.pending_action) {
      triggerSecurityConfirmationModal(data.pending_action);
      refreshPendingTasks();
    }

  } catch (err) {
    playSynthesizedSound("alert");
    appendAssistantMessage({
      reply: `I encountered an issue executing that directive: ${err.message}. Please verify the backend connection.`,
      intent: "error"
    });
    setVoiceStageState("error");
    neuralReactor?.triggerError();
  } finally {
    state.isProcessing = false;
  }
}

function appendUserMessage(text) {
  const stream = document.getElementById("chat-stream");
  if (!stream) return;

  const entry = document.createElement("div");
  entry.className = "chat-entry user-entry";
  entry.innerHTML = `
    <div class="entry-avatar">M</div>
    <div class="entry-bubble">
      <div class="entry-meta-header">
        <span>MAHI</span>
        <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div>${escapeHtml(text)}</div>
    </div>
  `;
  stream.appendChild(entry);
  stream.scrollTop = stream.scrollHeight;
}

function appendAssistantMessage(data) {
  const stream = document.getElementById("chat-stream");
  if (!stream) return;

  const entry = document.createElement("div");
  entry.className = "chat-entry assistant-entry";

  const intentTag = data.intent ? `[INTENT: ${data.intent.toUpperCase()}]` : "";
  const formattedHtml = formatMarkdown(data.reply || "");

  let mediaHtml = "";
  if (data.video_id) {
    const videoUrl = data.open_url || `https://www.youtube.com/watch?v=${data.video_id}`;
    mediaHtml = `
      <div class="jarvis-embedded-media" id="active-jarvis-media">
        <div class="embedded-media-header">
          <span>▶ YOUTUBE AUDIO / VIDEO STREAM ACTIVE</span>
          <button type="button" class="media-close-badge" onclick="closeActiveMedia()" title="Close Player">✕ Close It</button>
        </div>
        <div class="embedded-media-frame-wrap">
          <iframe 
            src="https://www.youtube.com/embed/${data.video_id}?autoplay=1&enablejsapi=1" 
            title="JARVIS Stream" 
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen
          ></iframe>
        </div>
        <div class="embedded-media-actions">
          <a href="${videoUrl}" target="_blank" class="media-external-pill">
            ↗ Open in Full Tab
          </a>
          <button type="button" class="media-external-pill" onclick="closeActiveMedia()">
            ✕ Close Tab & Return to JARVIS
          </button>
        </div>
      </div>
    `;
  }

  entry.innerHTML = `
    <div class="entry-avatar">J</div>
    <div class="entry-bubble">
      <div class="entry-meta-header">
        <span class="jarvis-tag">// JARVIS</span>
        <span>${intentTag}</span>
      </div>
      <div class="message-body">
        ${formattedHtml}
        ${mediaHtml}
      </div>
      <div class="entry-toolbar">
        <button class="msg-action-btn" onclick="copyMessageText(this)">📋 Copy</button>
        <button class="msg-action-btn" onclick="speakJarvis('${encodeURIComponent(data.reply || '')}')">🔊 Speak</button>
      </div>
    </div>
  `;

  stream.appendChild(entry);
  stream.scrollTop = stream.scrollHeight;
}

function closeActiveMedia() {
  const activeMedia = document.querySelectorAll(".jarvis-embedded-media");
  activeMedia.forEach(el => el.remove());
  if (window.currentOpenedMediaTab && !window.currentOpenedMediaTab.closed) {
    try {
      window.currentOpenedMediaTab.close();
      window.currentOpenedMediaTab = null;
    } catch (e) {}
  }
  showToast("Media closed. Returned to JARVIS.", "info");
}

function copyMessageText(btn) {
  const body = btn.closest(".entry-bubble")?.querySelector(".message-body");
  if (body) {
    navigator.clipboard.writeText(body.innerText).then(() => {
      showToast("Copied to clipboard.", "success");
    });
  }
}

function recordDashboardActivity(role, text) {
  const list = document.getElementById("dashboard-recent-chats");
  if (!list) return;

  const item = document.createElement("div");
  item.className = "activity-item";
  item.innerHTML = `
    <span class="activity-badge">${role}</span>
    <span style="color: var(--text-secondary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(text)}</span>
  `;
  list.insertBefore(item, list.firstChild);
  if (list.children.length > 8) list.removeChild(list.lastChild);
}

// ==========================================================================
// 8. Markdown Parser & Code Block Styler
// ==========================================================================
function formatMarkdown(text) {
  if (!text) return "";
  let out = escapeHtml(text);

  // Bold
  out = out.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  
  // Inline code
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Code Blocks
  out = out.replace(/```([a-zA-Z0-9_]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const language = lang || "code";
    return `
      <div class="code-block-wrap">
        <div class="code-block-header">
          <span>${language.toUpperCase()}</span>
          <button class="code-copy-btn" onclick="copyCodeBlock(this)">Copy Code</button>
        </div>
        <pre class="code-block-content"><code>${code}</code></pre>
      </div>
    `;
  });

  // Bullet items
  out = out.replace(/^\s*•\s*(.*?)$/gm, "<li>$1</li>");
  out = out.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

  // Newlines
  out = out.replace(/\n/g, "<br>");
  return out;
}

function copyCodeBlock(btn) {
  const code = btn.closest(".code-block-wrap")?.querySelector("code");
  if (code) {
    navigator.clipboard.writeText(code.innerText).then(() => {
      showToast("Code copied to clipboard.", "success");
    });
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==========================================================================
// 9. Voice Assistant & NEURAL REACTOR Visualization Engine
// ==========================================================================

class NeuralReactor {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    // Dimensions & High-DPI Scaling
    this.dpr = window.devicePixelRatio || 1;
    this.width = 380;
    this.height = 380;
    this.cx = 190;
    this.cy = 190;
    this.setupCanvasDimensions();

    // State Machine ("idle", "listening", "thinking", "responding", "error")
    this.currentState = "idle";
    this.manualState = null; // When selected via demo switcher
    this.thinkingProgress = 0.0; // 0.0 (Idle) -> 1.0 (Full Neural Recombination)
    this.respondingIntensity = 0.0;
    this.errorIntensity = 0.0;

    // Real Web Audio API & Microphone
    this.audioCtx = null;
    this.analyser = null;
    this.micStream = null;
    this.isMicActive = false;
    this.audioFreqData = null;
    this.audioLevel = 0.0; // Genuine microphone volume level: 0.0 to 1.0

    // Interactive Mouse Hover
    this.mouse = { x: -1000, y: -1000, isHovering: false, radius: 95 };
    this.setupMouseEvents();

    // Visual Elements: 210 Particles, 10 Glass Bubbles, Concentric Ripples
    this.particles = [];
    this.numParticles = 210;
    this.bubbles = [];
    this.numBubbles = 10;
    this.ripples = [];
    this.time = 0;
    this.animId = null;

    // Initialize systems
    this.initParticles();
    this.initBubbles();

    // Handle viewport resize
    window.addEventListener("resize", () => this.setupCanvasDimensions());

    // Start 60fps render loop
    this.startLoop();
  }

  setupCanvasDimensions() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width > 0 ? rect.width : 380;
    this.height = rect.height > 0 ? rect.height : 380;
    this.cx = this.width / 2;
    this.cy = this.height / 2;

    this.dpr = window.devicePixelRatio || 1;
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  setupMouseEvents() {
    if (!this.canvas) return;

    this.canvas.addEventListener("mousemove", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = e.clientX - rect.left;
      this.mouse.y = e.clientY - rect.top;
      this.mouse.isHovering = true;
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.mouse.isHovering = false;
      this.mouse.x = -1000;
      this.mouse.y = -1000;
    });

    this.canvas.addEventListener("click", () => {
      const clickX = this.mouse.x > 0 ? this.mouse.x : this.cx;
      const clickY = this.mouse.y > 0 ? this.mouse.y : this.cy;
      this.createRipple(clickX, clickY, 15, "rgba(0, 240, 255, 0.75)", 3.4);
    });
  }

  initParticles() {
    this.particles = [];
    const colors = [
      { r: 0, g: 240, b: 255 },     // Electric Cyan
      { r: 56, g: 189, b: 248 },    // Ice Blue
      { r: 192, g: 132, b: 252 },   // Electric Violet
      { r: 255, g: 255, b: 255 }     // Radiant White
    ];

    for (let i = 0; i < this.numParticles; i++) {
      const color = colors[Math.floor(Math.random() * colors.length)];
      const rand = Math.random();
      let baseRadius;
      if (rand < 0.28) {
        baseRadius = 36 + Math.random() * 32; // Core corona
      } else if (rand < 0.72) {
        baseRadius = 70 + Math.random() * 55; // Mid orbital belt
      } else {
        baseRadius = 125 + Math.random() * 45; // Outer halo
      }

      const baseAngle = Math.random() * Math.PI * 2;
      const speed = (0.005 + Math.random() * 0.012) * (Math.random() < 0.45 ? -1 : 1);

      this.particles.push({
        baseAngle,
        currentAngle: baseAngle,
        baseRadius,
        currentRadius: baseRadius,
        orbitSpeed: speed,
        x: this.cx + Math.cos(baseAngle) * baseRadius,
        y: this.cy + Math.sin(baseAngle) * baseRadius,
        vx: 0,
        vy: 0,
        size: 1.2 + Math.random() * 2.2,
        baseAlpha: 0.35 + Math.random() * 0.55,
        alpha: 0.5,
        color,
        seed: Math.random() * 100
      });
    }
  }

  initBubbles() {
    this.bubbles = [];
    for (let i = 0; i < this.numBubbles; i++) {
      const angle = (i / this.numBubbles) * Math.PI * 2;
      const radius = 72 + (i % 3) * 32 + Math.random() * 14;
      const speed = (0.007 + (i % 3) * 0.004) * (i % 2 === 0 ? 1 : -1);
      const size = 12 + Math.random() * 9;

      this.bubbles.push({
        angle,
        speed,
        baseRadius: radius,
        orbitRadius: radius,
        baseSize: size,
        size: size,
        x: this.cx + Math.cos(angle) * radius,
        y: this.cy + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        alpha: 0.85,
        wobblePhase: Math.random() * Math.PI * 2,
        isCyan: i % 2 === 0
      });
    }
  }

  async startMicrophone() {
    if (this.isMicActive) return true;
    try {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (!this.audioCtx) {
        this.audioCtx = new AudioCtxClass();
      }
      if (this.audioCtx.state === "suspended") {
        await this.audioCtx.resume();
      }

      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      const source = this.audioCtx.createMediaStreamSource(this.micStream);
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 128;
      this.analyser.smoothingTimeConstant = 0.75;
      source.connect(this.analyser);

      this.audioFreqData = new Uint8Array(this.analyser.frequencyBinCount);
      this.isMicActive = true;
      return true;
    } catch (err) {
      console.warn("Microphone access declined or unavailable:", err);
      this.isMicActive = false;
      this.audioLevel = 0.0;
      showToast("Microphone access not granted. Voice stage running in manual mode.", "info");
      return false;
    }
  }

  stopMicrophone() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(t => t.stop());
      this.micStream = null;
    }
    this.isMicActive = false;
    this.audioLevel = 0.0;
    this.updateAudioMeterUI(0);
  }

  updateAudioSpectralData() {
    if (!this.isMicActive || !this.analyser || !this.audioFreqData) {
      this.audioLevel = 0.0;
      this.updateAudioMeterUI(0);
      return;
    }

    this.analyser.getByteFrequencyData(this.audioFreqData);

    // Compute average intensity across voice speech spectrum (bins 1 to 24)
    let sum = 0;
    const count = Math.min(this.audioFreqData.length, 24);
    for (let i = 1; i <= count; i++) {
      sum += this.audioFreqData[i];
    }
    const instant = sum / (count * 255);

    // Exponential moving average for fluid responsiveness
    this.audioLevel = this.audioLevel * 0.72 + instant * 0.28;

    // Trigger acoustic sound ripples when sound reaches peak energy
    if (this.audioLevel > 0.16 && Math.random() < 0.28) {
      this.createRipple(this.cx, this.cy, 35, "rgba(0, 240, 255, 0.6)", 2.8);
    }

    this.updateAudioMeterUI(this.audioLevel);
  }

  updateAudioMeterUI(level) {
    const bar = document.getElementById("reactor-audio-bar");
    const db = document.getElementById("reactor-audio-db");
    if (bar) {
      const pct = Math.min(100, Math.round(level * 180));
      bar.style.width = `${pct}%`;
    }
    if (db) {
      if (level > 0.01) {
        const decibels = Math.round(-38 + level * 38);
        db.textContent = `${decibels} dB`;
      } else {
        db.textContent = "-- dB";
      }
    }
  }

  createRipple(x, y, radius, color, speed) {
    this.ripples.push({
      x,
      y,
      radius,
      maxRadius: 185,
      alpha: 0.8,
      speed: speed || 2.5,
      color: color || "rgba(0, 240, 255, 0.6)"
    });
  }

  triggerError() {
    this.manualState = "error";
    this.errorIntensity = 1.0;
    setTimeout(() => {
      if (this.manualState === "error") {
        this.manualState = null;
        const autoBtn = document.getElementById("btn-state-auto");
        document.querySelectorAll(".state-demo-btn").forEach(b => b.classList.remove("active"));
        if (autoBtn) autoBtn.classList.add("active");
        setVoiceStageState("idle");
      }
    }, 3500);
  }

  setDemoState(stateName) {
    if (stateName === "auto") {
      this.manualState = null;
      if (!state.isListening) {
        this.stopMicrophone();
      }
    } else {
      this.manualState = stateName;
      if (stateName === "listening") {
        this.startMicrophone();
      } else if (stateName === "error") {
        this.errorIntensity = 1.0;
      }
    }
  }

  getActiveState() {
    if (this.manualState) return this.manualState;
    if (state.isProcessing) return "thinking";
    if (state.isSpeaking) return "responding";
    if (state.isListening) return "listening";
    return "idle";
  }

  startLoop() {
    const render = () => {
      this.renderFrame();
      this.animId = requestAnimationFrame(render);
    };
    this.animId = requestAnimationFrame(render);
  }

  renderFrame() {
    this.time += 0.02;
    this.ctx.clearRect(0, 0, this.width, this.height);

    const activeState = this.getActiveState();
    this.currentState = activeState;
    this.updateAudioSpectralData();

    // Smooth transition interpolations
    if (activeState === "thinking") {
      this.thinkingProgress = Math.min(1.0, this.thinkingProgress + 0.035);
    } else {
      this.thinkingProgress = Math.max(0.0, this.thinkingProgress - 0.045);
    }

    if (activeState === "responding") {
      this.respondingIntensity = Math.min(1.0, this.respondingIntensity + 0.07);
      if (Math.random() < 0.07) {
        this.createRipple(this.cx, this.cy, 30, "rgba(56, 189, 248, 0.8)", 3.2);
      }
    } else {
      this.respondingIntensity = Math.max(0.0, this.respondingIntensity - 0.04);
    }

    if (activeState === "error") {
      this.errorIntensity = Math.min(1.0, this.errorIntensity + 0.1);
    } else {
      this.errorIntensity = Math.max(0.0, this.errorIntensity - 0.03);
    }

    // 1. Draw Acoustic Waves & Shockwave Ripples
    this.renderRipples();

    // 2. STATE B: Render Abstract Neural Network Synaptic Connections
    if (this.thinkingProgress > 0.15) {
      this.renderNeuralSynapses();
    }

    // 3. Render Translucent Glass Floating Bubbles
    this.renderBubbles();

    // 4. Render Micro-Particles with Additive Glow
    this.renderParticles();

    // 5. Render Central Radiant Energy Core
    this.renderCore();

    // Synchronize DOM Stage Badge
    this.syncStageBadge(activeState);
  }

  renderRipples() {
    for (let i = this.ripples.length - 1; i >= 0; i--) {
      const r = this.ripples[i];
      r.radius += r.speed;
      r.alpha = Math.max(0, (1 - r.radius / r.maxRadius) * 0.75);

      if (r.radius >= r.maxRadius || r.alpha <= 0.01) {
        this.ripples.splice(i, 1);
        continue;
      }

      this.ctx.beginPath();
      this.ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
      this.ctx.strokeStyle = r.color.replace(/[\d.]+\)$/, `${r.alpha})`);
      this.ctx.lineWidth = 1.4;
      this.ctx.stroke();
    }
  }

  renderNeuralSynapses() {
    const threshold = 46;
    const maxLinksPerParticle = 3;
    const ctx = this.ctx;

    ctx.save();
    ctx.lineWidth = 1.0;

    for (let i = 0; i < this.particles.length; i++) {
      let links = 0;
      const pi = this.particles[i];

      for (let j = i + 1; j < this.particles.length; j++) {
        if (links >= maxLinksPerParticle) break;
        const pj = this.particles[j];
        const dx = pi.x - pj.x;
        const dy = pi.y - pj.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < threshold * threshold) {
          const dist = Math.sqrt(distSq);
          const alpha = (1 - dist / threshold) * 0.65 * this.thinkingProgress;

          ctx.beginPath();
          ctx.moveTo(pi.x, pi.y);
          ctx.lineTo(pj.x, pj.y);
          ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
          ctx.stroke();

          // Flash glowing synaptic node at connection midpoint
          if (dist < 22 && Math.random() < 0.25) {
            ctx.fillStyle = `rgba(192, 132, 252, ${alpha * 1.2})`;
            ctx.fillRect((pi.x + pj.x) / 2 - 1, (pi.y + pj.y) / 2 - 1, 2, 2);
          }

          links++;
        }
      }
    }
    ctx.restore();
  }

  renderBubbles() {
    const ctx = this.ctx;

    for (let i = 0; i < this.bubbles.length; i++) {
      const b = this.bubbles[i];

      // Orbital rotation
      b.angle += b.speed;

      // Audio responsiveness (Listening State A)
      const micAudioScale = this.audioLevel * 18;
      const micRadiusOffset = this.audioLevel * 22;

      b.size = b.baseSize + Math.sin(this.time * 2.5 + b.wobblePhase) * 2.0 + micAudioScale;
      b.orbitRadius = b.baseRadius + micRadiusOffset;

      // Dissolution when thinking (Thinking State B)
      b.alpha = (1.0 - this.thinkingProgress) * 0.85;
      const effectiveSize = b.size * (1.0 - this.thinkingProgress * 0.65);

      if (b.alpha <= 0.02 || effectiveSize <= 1) continue;

      let targetX = this.cx + Math.cos(b.angle) * b.orbitRadius;
      let targetY = this.cy + Math.sin(b.angle) * b.orbitRadius;

      // Interactive Cursor Hover Repulsion
      if (this.mouse.isHovering) {
        const mdx = targetX - this.mouse.x;
        const mdy = targetY - this.mouse.y;
        const mdist = Math.hypot(mdx, mdy);
        if (mdist < this.mouse.radius && mdist > 1) {
          const force = (1 - mdist / this.mouse.radius) * 8.0;
          targetX += (mdx / mdist) * force;
          targetY += (mdy / mdist) * force;
        }
      }

      b.x += (targetX - b.x) * 0.15;
      b.y += (targetY - b.y) * 0.15;

      // Translucent Glass Fill
      const grad = ctx.createRadialGradient(
        b.x - effectiveSize * 0.3,
        b.y - effectiveSize * 0.3,
        2,
        b.x,
        b.y,
        effectiveSize
      );

      if (b.isCyan) {
        grad.addColorStop(0, `rgba(255, 255, 255, ${0.45 * b.alpha})`);
        grad.addColorStop(0.35, `rgba(0, 240, 255, ${0.22 * b.alpha})`);
        grad.addColorStop(1, `rgba(56, 189, 248, ${0.05 * b.alpha})`);
      } else {
        grad.addColorStop(0, `rgba(255, 255, 255, ${0.45 * b.alpha})`);
        grad.addColorStop(0.35, `rgba(168, 85, 247, ${0.22 * b.alpha})`);
        grad.addColorStop(1, `rgba(139, 92, 246, ${0.05 * b.alpha})`);
      }

      ctx.beginPath();
      ctx.arc(b.x, b.y, effectiveSize, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      // Refractive Outer Rim
      ctx.strokeStyle = b.isCyan
        ? `rgba(0, 240, 255, ${0.65 * b.alpha})`
        : `rgba(192, 132, 252, ${0.65 * b.alpha})`;
      ctx.lineWidth = 1.3;
      ctx.stroke();

      // Specular Highlight Arc
      ctx.beginPath();
      ctx.arc(b.x, b.y, effectiveSize * 0.72, -Math.PI * 0.85, -Math.PI * 0.3);
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.75 * b.alpha})`;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  }

  renderParticles() {
    const ctx = this.ctx;
    ctx.save();
    ctx.globalCompositeOperation = "lighter"; // Celestial additive blending

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // 1. STATE B: Particle Recombination Trajectories
      if (this.thinkingProgress > 0.05) {
        const dx = p.x - this.cx;
        const dy = p.y - this.cy;
        const dist = Math.hypot(dx, dy) || 1;
        const angle = Math.atan2(dy, dx);

        // Curved vortex swirl around core
        const swirlVx = -Math.sin(angle) * 2.8;
        const swirlVy = Math.cos(angle) * 2.8;

        // Harmonic curl noise
        const curlVx = Math.sin(p.seed + this.time * 2.2 + dy * 0.03) * 1.5;
        const curlVy = Math.cos(p.seed + this.time * 2.2 + dx * 0.03) * 1.5;

        // Centripetal containment pull
        const pull = (dist - 85) * -0.014;
        const pullVx = (dx / dist) * pull;
        const pullVy = (dy / dist) * pull;

        p.vx = p.vx * 0.88 + (swirlVx + curlVx + pullVx) * 0.12;
        p.vy = p.vy * 0.88 + (swirlVy + curlVy + pullVy) * 0.12;
        p.x += p.vx;
        p.y += p.vy;

      } else {
        // 2. Normal Celestial Orbit (Idle, Listening, Responding)
        p.currentAngle += p.orbitSpeed * (1 + this.audioLevel * 1.8);

        // Audio acoustic expansion in Listening state
        let r = p.baseRadius + Math.sin(this.time * 2.0 + p.seed) * 5 + (this.audioLevel * 22);

        // Wave release in Responding state
        if (this.respondingIntensity > 0) {
          r += Math.sin(this.time * 5.0 + p.seed) * 12 * this.respondingIntensity;
        }

        let targetX = this.cx + Math.cos(p.currentAngle) * r;
        let targetY = this.cy + Math.sin(p.currentAngle) * r;

        // Interactive Cursor Hover Deflection
        if (this.mouse.isHovering) {
          const mdx = targetX - this.mouse.x;
          const mdy = targetY - this.mouse.y;
          const mdist = Math.hypot(mdx, mdy);
          if (mdist < this.mouse.radius && mdist > 1) {
            const force = (1 - mdist / this.mouse.radius) * 7.0;
            targetX += (mdx / mdist) * force;
            targetY += (mdy / mdist) * force;
          }
        }

        // Smooth convergence when transitioning from Thinking back to Orbit
        p.x += (targetX - p.x) * 0.12;
        p.y += (targetY - p.y) * 0.12;
      }

      // Render glowing particle dot
      const alpha = p.baseAlpha * (0.8 + 0.2 * Math.sin(this.time * 3 + p.seed));
      const col = p.color;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${col.r}, ${col.g}, ${col.b}, ${alpha})`;
      ctx.fill();
    }

    ctx.restore();
  }

  renderCore() {
    const ctx = this.ctx;

    // Error Jitter Calculation
    let jitterX = 0;
    let jitterY = 0;
    if (this.errorIntensity > 0.05) {
      jitterX = (Math.random() - 0.5) * 6 * this.errorIntensity;
      jitterY = (Math.random() - 0.5) * 6 * this.errorIntensity;
    }

    const coreX = this.cx + jitterX;
    const coreY = this.cy + jitterY;

    // Dynamic Core Radius modulated by Active State
    let coreRadius = 32;

    if (this.currentState === "listening") {
      // Direct acoustic pulse from microphone
      coreRadius = 32 + (this.audioLevel * 32) + Math.sin(this.time * 4.0) * 3;
    } else if (this.currentState === "thinking") {
      // Energetic plasma vibration
      coreRadius = 33 + Math.sin(this.time * 6.0) * 5 + Math.cos(this.time * 14.0) * 2;
    } else if (this.currentState === "responding") {
      // Outward acoustic wave release
      coreRadius = 32 + Math.sin(this.time * 4.5) * 12 * this.respondingIntensity;
    } else if (this.currentState === "error") {
      coreRadius = 34 + Math.sin(this.time * 12.0) * 4;
    } else {
      // Standby gentle harmonic breathing
      coreRadius = 32 + Math.sin(this.time * 2.0) * 3;
    }

    // Outer Core Corona Glow
    const coronaGrad = ctx.createRadialGradient(
      coreX, coreY, 4,
      coreX, coreY, coreRadius * 2.2
    );

    if (this.errorIntensity > 0.3) {
      coronaGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
      coronaGrad.addColorStop(0.25, "rgba(244, 63, 94, 0.9)");
      coronaGrad.addColorStop(0.65, "rgba(225, 29, 72, 0.35)");
      coronaGrad.addColorStop(1, "transparent");
    } else if (this.thinkingProgress > 0.2) {
      coronaGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
      coronaGrad.addColorStop(0.25, "rgba(192, 132, 252, 0.9)");
      coronaGrad.addColorStop(0.65, "rgba(0, 240, 255, 0.4)");
      coronaGrad.addColorStop(1, "transparent");
    } else {
      coronaGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
      coronaGrad.addColorStop(0.25, "rgba(0, 240, 255, 0.85)");
      coronaGrad.addColorStop(0.65, "rgba(139, 92, 246, 0.3)");
      coronaGrad.addColorStop(1, "transparent");
    }

    ctx.beginPath();
    ctx.arc(coreX, coreY, coreRadius * 2.2, 0, Math.PI * 2);
    ctx.fillStyle = coronaGrad;
    ctx.fill();

    // Inner Radiant Star Core
    const innerGrad = ctx.createRadialGradient(
      coreX, coreY, 1,
      coreX, coreY, coreRadius
    );
    innerGrad.addColorStop(0, "#ffffff");
    innerGrad.addColorStop(0.4, this.errorIntensity > 0.3 ? "#f43f5e" : "#00f0ff");
    innerGrad.addColorStop(1, "transparent");

    ctx.beginPath();
    ctx.arc(coreX, coreY, coreRadius, 0, Math.PI * 2);
    ctx.fillStyle = innerGrad;
    ctx.fill();

    // Central focal spark
    ctx.beginPath();
    ctx.arc(coreX, coreY, 6, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
  }

  syncStageBadge(activeState) {
    const badge = document.getElementById("voice-stage-state-badge");
    if (!badge) return;

    let label = "SYSTEM STANDBY";
    let badgeClass = "idle";

    if (activeState === "listening") {
      label = "LISTENING";
      badgeClass = "listening";
    } else if (activeState === "thinking") {
      label = "THINKING (NEURAL RECOMBINATION)";
      badgeClass = "thinking";
    } else if (activeState === "responding") {
      label = "RESPONDING";
      badgeClass = "responding";
    } else if (activeState === "error") {
      label = "SECURITY ALERT / ERROR";
      badgeClass = "error";
    }

    if (badge.textContent !== label) {
      badge.textContent = label;
      badge.className = `voice-state-badge ${badgeClass}`;
    }
  }
}

// Speech Recognition Lifecycle
let speechDebounceTimer = null;
let lastHeardSpeech = "";

function commitVoiceDirective(rawTranscript) {
  if (speechDebounceTimer) {
    clearTimeout(speechDebounceTimer);
    speechDebounceTimer = null;
  }
  const text = (rawTranscript || lastHeardSpeech).trim();
  if (!text || state.isProcessing) return;

  // Interrupt active speech if user is speaking so user command takes priority
  if (state.isSpeaking) {
    try { window.speechSynthesis.cancel(); } catch (e) {}
    state.isSpeaking = false;
  }
  lastHeardSpeech = "";

  const liveEl = document.getElementById("voice-live-transcript");
  if (liveEl) {
    liveEl.textContent = `"${text}"`;
  }

  // Strip common wake-words if spoken
  const cleanCommand = text
    .replace(/^(?:hey\s+|hi\s+|hello\s+|ok\s+|okay\s+)?(?:jarvis|jarvi|computer)[,:\s]*/i, "")
    .trim();

  executeDirective(cleanCommand || text);
}

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("SpeechRecognition not supported in this browser environment.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = navigator.language || "en-US";

  recognition.onstart = () => {
    state.isListening = true;
    updateVoiceUIState(true);
    setVoiceStageState("listening");
  };

  recognition.onresult = (event) => {
    if (state.isProcessing) return;

    // Interrupt any active TTS vocalization when the user speaks
    if (state.isSpeaking) {
      try { window.speechSynthesis.cancel(); } catch (e) {}
      state.isSpeaking = false;
    }

    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const res = event.results[i];
      if (res.isFinal) {
        finalTranscript += res[0].transcript;
      } else {
        interimTranscript += res[0].transcript;
      }
    }

    const currentSpeech = (finalTranscript || interimTranscript).trim();
    if (!currentSpeech) return;

    lastHeardSpeech = currentSpeech;

    const liveEl = document.getElementById("voice-live-transcript");
    if (liveEl) {
      liveEl.textContent = `🎙️ Hearing: "${currentSpeech}"...`;
    }

    if (finalTranscript.trim()) {
      // Immediate commit when speech engine finalizes phrase
      commitVoiceDirective(finalTranscript.trim());
    } else {
      // Debounce commit interim speech if user pauses speaking
      if (speechDebounceTimer) clearTimeout(speechDebounceTimer);
      speechDebounceTimer = setTimeout(() => {
        if (lastHeardSpeech.trim() && !state.isProcessing) {
          commitVoiceDirective(lastHeardSpeech.trim());
        }
      }, 950);
    }
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    if (event.error === "no-speech") {
      return;
    }
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      state.isListening = false;
      updateVoiceUIState(false);
      setVoiceStageState("idle");
      showToast("Microphone access declined in browser settings. Please permit microphone permissions.", "alert");
    }
  };

  recognition.onend = () => {
    // If pending speech was buffered, commit before cycle reset
    if (lastHeardSpeech.trim() && !state.isProcessing) {
      commitVoiceDirective(lastHeardSpeech.trim());
    }

    // Keep continuous listening active if operator hasn't toggled off
    if (state.isListening && !state.isProcessing) {
      setTimeout(() => {
        if (state.isListening && !state.isProcessing) {
          try {
            recognition.start();
          } catch (e) {}
        }
      }, 200);
    } else if (!state.isProcessing) {
      state.isListening = false;
      updateVoiceUIState(false);
      setVoiceStageState("idle");
    }
  };
}

async function toggleVoiceAssistant() {
  try { window.speechSynthesis.cancel(); } catch (e) {}
  state.isSpeaking = false;

  if (state.isListening) {
    state.isListening = false;
    if (speechDebounceTimer) {
      clearTimeout(speechDebounceTimer);
      speechDebounceTimer = null;
    }
    lastHeardSpeech = "";
    if (recognition) {
      try { recognition.stop(); } catch (e) {}
    }
    neuralReactor?.stopMicrophone();
    updateVoiceUIState(false);
    setVoiceStageState("idle");
  } else {
    state.isListening = true;
    updateVoiceUIState(true);
    setVoiceStageState("listening");

    // Start Neural Reactor acoustic microphone analyser
    neuralReactor?.startMicrophone().catch(() => {});

    // Start Speech Recognition
    if (recognition) {
      try {
        recognition.start();
      } catch (e) {
        console.warn("SpeechRecognition start exception:", e);
      }
    } else {
      showToast("Speech Recognition not supported in this browser. Use text composer.", "alert");
    }
  }
}

function updateVoiceUIState(active) {
  const topMicBtn = document.getElementById("top-mic-btn");
  const compMicBtn = document.getElementById("mic-btn");
  const stageBtn = document.getElementById("voice-stage-toggle-btn");

  if (topMicBtn) topMicBtn.classList.toggle("active", active);
  if (compMicBtn) compMicBtn.classList.toggle("active", active);
  if (stageBtn) stageBtn.classList.toggle("active", active);
}

function setVoiceStageState(status) {
  const badge = document.getElementById("voice-stage-state-badge");
  if (badge) {
    badge.className = `voice-state-badge ${status}`;
    badge.textContent = status.toUpperCase();
  }

  if (status === "error") {
    neuralReactor?.triggerError();
  }
}

function speakJarvis(encodedText) {
  if (!("speechSynthesis" in window) || !state.voiceOutputEnabled) return;
  try { window.speechSynthesis.cancel(); } catch (e) {}

  const text = decodeURIComponent(encodedText)
    .replace(/[*_#`~]/g, "")
    .replace(/https?:\/\/\S+/g, "link")
    .replace(/<[^>]+>/g, "");

  if (!text.trim()) return;

  state.isSpeaking = true;
  setVoiceStageState("speaking");
  if (recognition && state.isListening) {
    try { recognition.stop(); } catch (e) {}
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.pitch = 0.95;

  const voices = window.speechSynthesis.getVoices();
  const jarvisVoice = voices.find(
    v => (v.name.includes("UK English") && v.name.includes("Male")) ||
         v.name.includes("Google UK English Male") ||
         v.name.includes("George") ||
         v.lang === "en-GB"
  ) || voices.find(v => v.lang.startsWith("en"));

  if (jarvisVoice) utterance.voice = jarvisVoice;

  if (window.speakingWatchdogTimer) {
    clearTimeout(window.speakingWatchdogTimer);
    window.speakingWatchdogTimer = null;
  }

  const resetSpeaking = () => {
    state.isSpeaking = false;
    setVoiceStageState("idle");
    if (window.speakingWatchdogTimer) {
      clearTimeout(window.speakingWatchdogTimer);
      window.speakingWatchdogTimer = null;
    }
  };

  utterance.onend = resetSpeaking;
  utterance.onerror = resetSpeaking;

  // Chromium watchdog: guarantees state.isSpeaking clears even if onend drops
  const wordCount = text.split(/\s+/).length;
  const estimatedDurationMs = Math.max(2500, (wordCount / 2.2) * 1000 + 1000);
  window.speakingWatchdogTimer = setTimeout(resetSpeaking, estimatedDurationMs);

  window.speechSynthesis.speak(utterance);
}

// Initialize Neural Reactor Visualization
function initVoiceOrbCanvas() {
  neuralReactor = new NeuralReactor("voice-core-canvas");

  // Wire up state switcher demo buttons (For Hackathon Demonstration)
  const demoBtns = document.querySelectorAll(".state-demo-btn");
  demoBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const desiredState = btn.getAttribute("data-state");
      demoBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (neuralReactor) {
        neuralReactor.setDemoState(desiredState);
      }
    });
  });

  const stageBtn = document.getElementById("voice-stage-toggle-btn");
  if (stageBtn) {
    stageBtn.addEventListener("click", toggleVoiceAssistant);
  }

  const ttsBtn = document.getElementById("voice-tts-toggle-btn");
  if (ttsBtn) {
    ttsBtn.addEventListener("click", () => {
      state.voiceOutputEnabled = !state.voiceOutputEnabled;
      ttsBtn.innerHTML = `<span>🔊 Voice Audio: ${state.voiceOutputEnabled ? 'ON' : 'OFF'}</span>`;
      if (!state.voiceOutputEnabled) window.speechSynthesis?.cancel();
    });
  }

  const replayBtn = document.getElementById("voice-replay-btn");
  if (replayBtn) {
    replayBtn.addEventListener("click", () => {
      if (state.lastUtterance) speakJarvis(state.lastUtterance);
    });
  }
}

// ==========================================================================
// 10. Tasks & Security Confirmation Modal (Phase 8)
// ==========================================================================
async function refreshPendingTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/tasks/pending`);
    if (res.ok) {
      const data = await res.json();
      state.pendingAuthorizations = data.pending || [];
      renderPendingTasksUI(state.pendingAuthorizations);
    }
  } catch (e) {}
}

function renderPendingTasksUI(pendingList) {
  const container = document.getElementById("pending-tasks-container");
  const badge = document.getElementById("pending-tasks-badge");
  
  if (badge) {
    badge.textContent = pendingList.length;
    badge.style.display = pendingList.length > 0 ? "inline-block" : "none";
  }

  if (!container) return;

  if (pendingList.length === 0) {
    container.innerHTML = `
      <div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 24px 0;">
        No pending authorizations requiring approval. All systems secure.
      </div>
    `;
    return;
  }

  container.innerHTML = pendingList.map(task => `
    <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: var(--radius-md); padding: 14px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
      <div>
        <div style="font-weight: 700; color: #fbbf24; font-size: 13px;">${task.tool_name} (Action ID: ${task.action_id})</div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${task.description}</div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="resolveConfirmation('${task.action_id}', true)">Authorize</button>
        <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="resolveConfirmation('${task.action_id}', false)">Reject</button>
      </div>
    </div>
  `).join("");
}

function triggerSecurityConfirmationModal(pending) {
  const modal = document.getElementById("confirmation-modal");
  const descEl = document.getElementById("modal-action-description");
  const detailsEl = document.getElementById("modal-action-details");
  const approveBtn = document.getElementById("modal-approve-btn");
  const rejectBtn = document.getElementById("modal-reject-btn");

  if (!modal) return;

  if (descEl) descEl.textContent = pending.description;
  if (detailsEl) {
    detailsEl.innerHTML = `
      <strong>TOOL:</strong> ${pending.tool}<br>
      <strong>RISK LEVEL:</strong> ${pending.risk}<br>
      <strong>ACTION ID:</strong> ${pending.action_id}
    `;
  }

  approveBtn.onclick = () => resolveConfirmation(pending.action_id, true);
  rejectBtn.onclick = () => resolveConfirmation(pending.action_id, false);

  modal.classList.remove("hidden");
  playSynthesizedSound("alert");
}

async function resolveConfirmation(actionId, approved) {
  document.getElementById("confirmation-modal")?.classList.add("hidden");
  try {
    const res = await fetch(`${API_BASE}/chat/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_id: actionId, approved: approved })
    });
    const result = await res.json();
    showToast(result.message, approved ? "success" : "info");
    refreshPendingTasks();
  } catch (e) {
    showToast(`Confirmation error: ${e.message}`, "alert");
  }
}

// ==========================================================================
// 11. Projects & Workspace Files Explorer (Phase 8)
// ==========================================================================
async function refreshWorkspaceFiles() {
  const grid = document.getElementById("workspace-files-grid");
  if (!grid) return;

  try {
    const res = await fetch(`${API_BASE}/api/workspace/files`);
    if (res.ok) {
      const data = await res.json();
      state.workspaceFiles = data.files || [];
      renderWorkspaceFilesGrid(state.workspaceFiles);
    }
  } catch (e) {}
}

function renderWorkspaceFilesGrid(files) {
  const grid = document.getElementById("workspace-files-grid");
  if (!grid) return;

  if (files.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; color: var(--text-muted); text-align: center; padding: 40px;">
        Workspace is empty. Create a file or capture a screenshot to populate workspace_files/.
      </div>
    `;
    return;
  }

  grid.innerHTML = files.map(f => {
    const isImg = /\.(png|jpe?g|webp|gif)$/i.test(f.name);
    const icon = isImg ? "🖼️" : (f.name.endsWith(".py") ? "🐍" : (f.name.endsWith(".txt") ? "📝" : "📄"));
    const sizeKb = (f.size_bytes / 1024).toFixed(1);

    return `
      <div class="file-card-item" onclick="openFilePreviewModal('${encodeURIComponent(f.name)}', ${isImg})">
        <div class="file-card-icon">${icon}</div>
        <div class="file-card-name" title="${f.name}">${f.name}</div>
        <div class="file-card-meta">${sizeKb} KB • Workspace File</div>
      </div>
    `;
  }).join("");
}

async function openFilePreviewModal(encodedName, isImg) {
  const name = decodeURIComponent(encodedName);
  const modal = document.getElementById("file-modal");
  const title = document.getElementById("file-modal-title");
  const body = document.getElementById("file-modal-body");

  if (!modal || !body) return;

  title.textContent = `File: ${name}`;

  if (isImg) {
    body.innerHTML = `
      <div style="text-align: center; padding: 10px;">
        <img src="${API_BASE}/chat/file-content?path=${encodeURIComponent('workspace_files/' + name)}" style="max-width: 100%; max-height: 400px; border-radius: var(--radius-md); box-shadow: 0 4px 20px rgba(0,0,0,0.5);" />
      </div>
    `;
    modal.classList.remove("hidden");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/workspace/file?name=${encodeURIComponent(name)}`);
    const data = await res.json();
    const content = data.content || "Empty file";
    body.innerHTML = `
      <pre style="background: #060910; padding: 14px; border-radius: var(--radius-md); font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #e2e8f0; max-height: 380px; overflow: auto; white-space: pre-wrap;">${escapeHtml(content)}</pre>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px;">
        <button class="btn-danger" onclick="deleteWorkspaceFile('${encodeURIComponent(name)}')">Delete File</button>
      </div>
    `;
    modal.classList.remove("hidden");
  } catch (e) {
    showToast(`Could not read file: ${e.message}`, "alert");
  }
}

function closeFileModal() {
  document.getElementById("file-modal")?.classList.add("hidden");
}

function openCreateFileModal() {
  const modal = document.getElementById("file-modal");
  const title = document.getElementById("file-modal-title");
  const body = document.getElementById("file-modal-body");

  if (!modal || !body) return;

  title.textContent = "Create New Workspace File";
  body.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <input type="text" class="search-input-pill" id="new-file-name" placeholder="Filename (e.g. notes.txt, script.py)..." style="border-radius: var(--radius-md);" />
      <textarea class="search-input-pill" id="new-file-content" placeholder="File content..." rows="8" style="border-radius: var(--radius-md); font-family: 'JetBrains Mono', monospace; resize: vertical;"></textarea>
      <div style="display: flex; justify-content: flex-end; gap: 8px;">
        <button class="btn-secondary" onclick="closeFileModal()">Cancel</button>
        <button class="btn-primary" onclick="submitCreateWorkspaceFile()">Save File</button>
      </div>
    </div>
  `;
  modal.classList.remove("hidden");
}

async function submitCreateWorkspaceFile() {
  const nameInput = document.getElementById("new-file-name");
  const contentInput = document.getElementById("new-file-content");
  if (!nameInput || !nameInput.value.trim()) return;

  try {
    const res = await fetch(`${API_BASE}/api/workspace/file`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: nameInput.value.trim(), content: contentInput.value })
    });
    const data = await res.json();
    closeFileModal();
    showToast(data.message || "File saved successfully.", "success");
    refreshWorkspaceFiles();
  } catch (e) {
    showToast(`Error creating file: ${e.message}`, "alert");
  }
}

async function deleteWorkspaceFile(encodedName) {
  const name = decodeURIComponent(encodedName);
  try {
    const res = await fetch(`${API_BASE}/api/workspace/file?name=${encodeURIComponent(name)}`, {
      method: "DELETE"
    });
    const data = await res.json();
    closeFileModal();
    showToast(data.message || "File deleted.", "info");
    refreshWorkspaceFiles();
  } catch (e) {
    showToast(`Error deleting file: ${e.message}`, "alert");
  }
}

// ==========================================================================
// 12. Memory & Connected Tools Data
// ==========================================================================
async function refreshMemoryData() {
  try {
    const res = await fetch(`${API_BASE}/chat/memory`);
    if (res.ok) {
      const data = await res.json();
      state.memories = data.memories || [];
      renderMemoryUI(state.memories);
    }
  } catch (e) {}
}

function renderMemoryUI(memories) {
  const list = document.getElementById("memory-facts-list");
  const count = document.getElementById("memory-count");
  if (count) count.textContent = memories.length;

  if (!list) return;

  if (memories.length === 0) {
    list.innerHTML = `
      <div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 24px;">
        No facts stored in long-term memory. Add a preference above or instruct JARVIS to remember something.
      </div>
    `;
    return;
  }

  list.innerHTML = memories.map(m => `
    <div class="memory-fact-card">
      <div>
        <div style="color: var(--text-highlight); font-weight: 500; font-size: 13px;">${escapeHtml(m.fact)}</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Recorded ${new Date(m.timestamp * 1000).toLocaleString()}</div>
      </div>
    </div>
  `).join("");
}

document.getElementById("add-memory-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("new-memory-input");
  if (!input || !input.value.trim()) return;

  try {
    await fetch(`${API_BASE}/chat/memory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fact: input.value.trim() })
    });
    input.value = "";
    showToast("Memory committed to long-term memory store.", "success");
    refreshMemoryData();
  } catch (e) {
    showToast(`Error saving memory: ${e.message}`, "alert");
  }
});

async function clearAllMemories() {
  if (!confirm("Are you sure you want to purge all stored long-term memory?")) return;
  try {
    await fetch(`${API_BASE}/chat/memory`, { method: "DELETE" });
    showToast("Long-term memory cleared.", "info");
    refreshMemoryData();
  } catch (e) {}
}

async function refreshToolsRegistry() {
  try {
    const res = await fetch(`${API_BASE}/api/tools`);
    if (res.ok) {
      state.tools = await res.json();
      renderToolsUI(state.tools);
    }
  } catch (e) {}
}

function renderToolsUI(tools) {
  const grid = document.getElementById("tools-cards-grid");
  if (!grid) return;

  grid.innerHTML = tools.map(t => {
    const riskPill = t.risk === "high" ? "pill-rose" : (t.risk === "medium" ? "pill-amber" : "pill-emerald");
    return `
      <div class="glass-card tool-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <strong style="color: var(--accent-primary); font-family: 'JetBrains Mono', monospace; font-size: 13px;">${t.name}</strong>
          <span class="pill-badge ${riskPill}">${t.risk.toUpperCase()}</span>
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4;">${escapeHtml(t.description || "")}</div>
        <div style="margin-top: auto; padding-top: 10px; border-top: var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">Category: ${t.category || "General"}</span>
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="switchView('chat'); executeDirective('Test tool ${t.name}')">Test</button>
        </div>
      </div>
    `;
  }).join("");
}

// ==========================================================================
// 13. Activity History Audit
// ==========================================================================
async function renderActivityHistory() {
  const list = document.getElementById("history-audit-list");
  if (!list) return;

  try {
    const res = await fetch(`${API_BASE}/api/history`);
    const data = await res.json();
    const history = data.history || [];

    if (history.length === 0) {
      list.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 24px;">No directives recorded yet in this sliding window.</div>`;
      return;
    }

    list.innerHTML = history.map(item => `
      <div class="activity-item">
        <span class="activity-badge">${item.role.toUpperCase()}</span>
        <span style="color: var(--text-secondary); word-break: break-word;">${escapeHtml(item.content)}</span>
      </div>
    `).join("");
  } catch (e) {}
}

function exportHistoryLog() {
  fetch(`${API_BASE}/api/history`)
    .then(r => r.json())
    .then(data => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `jarvis_audit_${Date.now()}.json`;
      a.click();
      showToast("Audit log exported.", "success");
    });
}

function clearHistoryLog() {
  showToast("History window cleared.", "info");
  document.getElementById("history-audit-list").innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 24px;">History cleared.</div>`;
}

// ==========================================================================
// 14. Theme & Appearance Controls (Phase 2 & Phase 7)
// ==========================================================================
function setThemeAccent(themeName) {
  state.theme = themeName;
  document.body.setAttribute("data-theme", themeName);
  localStorage.setItem("jarvis_theme", themeName);

  document.querySelectorAll(".theme-swatch-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("title").toLowerCase().includes(themeName));
  });
}

document.getElementById("settings-username-input")?.addEventListener("change", (e) => {
  const newName = e.target.value.trim() || "Mahi";
  localStorage.setItem("jarvis_user_name", newName);
  updateUserDisplayName(newName);
  showToast(`Operator display name set to ${newName}.`, "success");
});

// ==========================================================================
// 15. Optical Vision Modal Analysis
// ==========================================================================
function openVisionModal() {
  document.getElementById("vision-modal")?.classList.remove("hidden");
}

function closeVisionModal() {
  document.getElementById("vision-modal")?.classList.add("hidden");
}

async function submitVisionAnalysis() {
  const fileInput = document.getElementById("vision-file-input");
  const promptInput = document.getElementById("vision-prompt-input");
  const resultBox = document.getElementById("vision-result-box");
  const analyzeBtn = document.getElementById("vision-analyze-btn");

  if (!fileInput?.files[0]) {
    alert("Please select an image file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("prompt", promptInput?.value || "Describe this image in detail.");

  analyzeBtn.textContent = "Analyzing Visual Feed...";
  analyzeBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/vision/analyze`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    resultBox.style.display = "block";
    resultBox.innerHTML = `<strong>Analysis:</strong><br>${escapeHtml(data.analysis || "Processed.")}`;
    showToast("Vision analysis completed.", "success");
  } catch (e) {
    showToast(`Vision analysis error: ${e.message}`, "alert");
  } finally {
    analyzeBtn.textContent = "Analyze Image";
    analyzeBtn.disabled = false;
  }
}
