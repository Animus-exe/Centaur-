const API = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? "/api" : "http://localhost:8000");

const RETRYABLE_STATUSES = [502, 503, 504];
const MAX_RETRIES = 3;
const INITIAL_BACKOFF_MS = 500;

export async function getJSON(path) {
  let lastError;
  let delayMs = INITIAL_BACKOFF_MS;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const r = await fetch(`${API}${path}`);
      if (r.ok) return r.json();
      const retryable = RETRYABLE_STATUSES.includes(r.status);
      let msg = `HTTP ${r.status}`;
      try {
        const body = await r.json();
        if (body?.detail) msg += `: ${body.detail}`;
      } catch (_) {}
      lastError = new Error(msg);
      if (!retryable || attempt === MAX_RETRIES) throw lastError;
    } catch (err) {
      const isNetworkError = err?.name === "TypeError" && (err?.message?.includes("fetch") || err?.message?.includes("network"));
      lastError = err;
      if ((!isNetworkError && err?.message?.startsWith?.("HTTP")) || attempt === MAX_RETRIES) throw err;
    }
    await new Promise((r) => setTimeout(r, delayMs));
    delayMs = Math.min(delayMs * 2, 10000);
  }
  throw lastError;
}
