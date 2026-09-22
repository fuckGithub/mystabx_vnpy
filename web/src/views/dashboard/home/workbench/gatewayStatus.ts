export function loginStatusOf(row: Record<string, unknown> | undefined | null): string {
  return String(row?.login_status ?? row?.td_status ?? row?.trade_status ?? "DISCONNECTED");
}

export function quoteStatusOf(row: Record<string, unknown> | undefined | null): string {
  return String(row?.quote_status ?? row?.md_status ?? "DISCONNECTED");
}

export function isStatusOk(status: string): boolean {
  return status === "CONNECTED";
}

export function isStatusConnecting(status: string): boolean {
  return status === "CONNECTING";
}

export function statusTone(status: string): "ok" | "warn" | "muted" {
  if (isStatusOk(status)) return "ok";
  if (isStatusConnecting(status)) return "warn";
  return "muted";
}

export function loginLabel(status: string): string {
  if (status === "CONNECTED") return "已登录";
  if (status === "CONNECTING") return "登录中";
  return "未登录";
}

export function quoteLabel(status: string): string {
  if (status === "CONNECTED") return "已连接";
  if (status === "CONNECTING") return "连接中";
  return "未连接";
}

const CONN_TOKENS = new Set(["CONNECTED", "CONNECTING", "DISCONNECTED"]);

function firstStatus(...values: unknown[]): string | undefined {
  for (const value of values) {
    const text = value == null ? "" : String(value);
    if (CONN_TOKENS.has(text)) return text;
  }
  return undefined;
}

export function mergeGatewayStatuses(
  prev: Record<string, unknown> | undefined,
  data: Record<string, unknown>,
): {
  login_status: string;
  td_status: string;
  trade_status: string;
  quote_status: string;
  md_status: string;
  conn_status: string;
} {
  const login =
    firstStatus(data.login_status, data.td_status, data.trade_status) ??
    firstStatus(prev?.login_status, prev?.td_status, prev?.trade_status) ??
    "DISCONNECTED";
  const quote =
    firstStatus(data.quote_status, data.md_status) ??
    firstStatus(prev?.quote_status, prev?.md_status) ??
    "DISCONNECTED";
  const derived =
    login === "CONNECTED" && quote === "CONNECTED"
      ? "CONNECTED"
      : login === "DISCONNECTED" && quote === "DISCONNECTED"
        ? "DISCONNECTED"
        : "CONNECTING";
  const conn = firstStatus(data.conn_status, data.status) ?? derived;
  return {
    login_status: login,
    td_status: login,
    trade_status: login,
    quote_status: quote,
    md_status: quote,
    conn_status: conn,
  };
}
