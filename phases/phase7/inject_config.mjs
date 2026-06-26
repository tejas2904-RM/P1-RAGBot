/** Write frontend config.js from API_BASE_URL (Vercel build). */
const apiBase = (process.env.API_BASE_URL || "").trim().replace(/\/$/, "");

if (process.env.VERCEL && !apiBase) {
  console.error(
    "ERROR: API_BASE_URL must be set in Vercel environment variables.\n" +
      "Use your Phase 6 Render API URL, e.g. https://m2-ragbot-api.onrender.com"
  );
  process.exit(1);
}

process.stdout.write(`window.__ENV__ = ${JSON.stringify({ API_BASE_URL: apiBase })};\n`);
