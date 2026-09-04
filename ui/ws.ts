import { getAccessToken } from "./api";
import { useMarketStore, useTradeStore } from "./stores";

type Handler = (msg: { type: string; data: Record<string, unknown> }) => void;

let socket: WebSocket | null = null;
let pingTimer: number | undefined;
let retry = 0;
const listeners = new Set<Handler>();

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/ws`;
}

function dispatch(msg: { type: string; data: Record<string, unknown> }) {
  const market = useMarketStore();
  const trade = useTradeStore();
  if (msg.type === "tick") market.upsertTick(msg.data);
  if (msg.type === "order") trade.upsertBy(trade.orders, msg.data, "vt_orderid");
  if (msg.type === "trade") trade.upsertBy(trade.trades, msg.data, "tradeid");
  if (msg.type === "position") trade.upsertBy(trade.positions, msg.data, "symbol");
  if (msg.type === "account") trade.upsertBy(trade.funds, msg.data, "accountid");
  if (msg.type === "gateway") {
    const gw = trade.gateways.find((row) => row.gateway_name === msg.data.gateway_name);
    if (gw) gw.conn_status = msg.data.status;
  }
  listeners.forEach((fn) => fn(msg));
}

export function connectWs() {
  const token = getAccessToken();
  if (!token) return;
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  socket = new WebSocket(wsUrl());
  socket.addEventListener("open", () => {
    retry = 0;
    socket?.send(JSON.stringify({ type: "auth", data: { token } }));
    pingTimer = window.setInterval(() => {
      socket?.send(JSON.stringify({ type: "ping", data: {} }));
    }, 15000);
  });
  socket.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    dispatch(msg);
    if (msg.type === "auth_ok") {
      socket?.send(JSON.stringify({ type: "subscribe", data: { topics: ["tick", "order", "trade", "position", "account", "gateway", "log"] } }));
      useTradeStore().refresh();
    }
  });
  socket.addEventListener("close", () => {
    window.clearInterval(pingTimer);
    socket = null;
    const wait = Math.min(15000, 500 * 2 ** retry);
    retry += 1;
    window.setTimeout(connectWs, wait);
  });
}

export function disconnectWs() {
  window.clearInterval(pingTimer);
  retry = 99;
  socket?.close();
  socket = null;
}

export function onMessage(handler: Handler) {
  listeners.add(handler);
  return () => listeners.delete(handler);
}

export function sendWs(type: string, data: Record<string, unknown> = {}) {
  socket?.send(JSON.stringify({ type, data }));
}
