import { getAccessToken } from "./api";
import { dispatch } from "./ws";

let source: EventSource | null = null;
let retryTimer: number | undefined;
let retry = 0;
let stopped = false;

function sseUrl(): string {
  const token = encodeURIComponent(getAccessToken());
  return `/api/sse?token=${token}`;
}

function applyRaw(raw: string) {
  try {
    const msg = JSON.parse(raw) as { type: string; data: Record<string, unknown> };
    if (msg && typeof msg.type === "string") dispatch(msg);
  } catch {
    /* ignore malformed frames */
  }
}

export function connectSse() {
  const token = getAccessToken();
  if (!token) return;
  stopped = false;
  if (source && source.readyState !== EventSource.CLOSED) return;

  source = new EventSource(sseUrl());
  source.addEventListener("snapshot", (event) => applyRaw((event as MessageEvent).data));
  source.addEventListener("gateway", (event) => applyRaw((event as MessageEvent).data));
  source.addEventListener("account", (event) => applyRaw((event as MessageEvent).data));
  source.addEventListener("open", () => {
    retry = 0;
  });
  source.addEventListener("error", () => {
    source?.close();
    source = null;
    if (stopped || !getAccessToken()) return;
    const wait = Math.min(15000, 500 * 2 ** retry);
    retry += 1;
    window.clearTimeout(retryTimer);
    retryTimer = window.setTimeout(connectSse, wait);
  });
}

export function disconnectSse() {
  stopped = true;
  window.clearTimeout(retryTimer);
  retryTimer = undefined;
  retry = 0;
  source?.close();
  source = null;
}

export function isSseOpen() {
  return source?.readyState === EventSource.OPEN;
}