const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Project mode SSE: POST /api/project/stream, body { idea: string }.
 * Events: { type, data } — status | decomposition | stats | token | error | done
 */
export function getApiBase() {
  return API_URL.replace(/\/$/, "");
}

/**
 * @param {string} idea
 * @param {object} handlers
 * @param {(msg: string) => void} [handlers.onStatus]
 * @param {(data: object) => void} [handlers.onDecomposition]
 * @param {(stats: object) => void} [handlers.onStats]
 * @param {(chunk: string) => void} [handlers.onToken]
 * @param {() => void} [handlers.onDone]
 * @param {(err: string) => void} [handlers.onError]
 * @param {(status: number, text: string) => void} [handlers.onHttpError]
 */
export async function streamProject(idea, handlers) {
  const url = `${getApiBase()}/api/project/stream`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea }),
  });

  if (!response.ok) {
    const text = await response.text();
    if (handlers.onHttpError) {
      handlers.onHttpError(response.status, text);
    } else {
      handlers.onError?.(`HTTP ${response.status}`);
    }
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    handlers.onError?.("No response body");
    handlers.onDone?.();
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let sawDone = false;

  const processBuffer = () => {
    for (;;) {
      const idx = buffer.indexOf("\n\n");
      if (idx === -1) break;
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      for (const line of raw.split("\n")) {
        const t = line.trim();
        if (!t.startsWith("data:")) continue;
        const payload = t.slice(5).trim();
        if (!payload) continue;
        let event;
        try {
          event = JSON.parse(payload);
        } catch {
          continue;
        }
        const { type, data } = event;
        if (type === "status" && data != null) {
          handlers.onStatus?.(String(data));
        } else if (type === "decomposition" && data != null) {
          handlers.onDecomposition?.(data);
        } else if (type === "stats" && data != null) {
          handlers.onStats?.(data);
        } else if (type === "token" && data != null) {
          handlers.onToken?.(String(data));
        } else if (type === "error" && data != null) {
          handlers.onError?.(String(data));
        } else if (type === "done") {
          sawDone = true;
          handlers.onDone?.();
        }
      }
    }
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        if (buffer.trim()) {
          buffer += "\n\n";
          processBuffer();
        }
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      processBuffer();
    }
    if (!sawDone) {
      handlers.onDone?.();
    }
  } catch (e) {
    handlers.onError?.(e?.message || "Stream failed");
    if (!sawDone) {
      handlers.onDone?.();
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // ignore
    }
  }
}
