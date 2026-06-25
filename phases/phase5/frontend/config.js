// Local default — same-origin API (Phase 5 FastAPI on :8000).
// Vercel build overwrites this via phases/phase7/inject_config.py.
window.__ENV__ = window.__ENV__ || {};
window.__ENV__.API_BASE_URL = "";
