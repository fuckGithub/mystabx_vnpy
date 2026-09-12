export function pickInstrumentId(row: Record<string, unknown> | null | undefined): string {
  return String(row?.symbol ?? row?.instrumentId ?? row?.instrument ?? "").trim();
}

export function finiteNumber(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function finitePrice(v: unknown): number | null {
  const n = finiteNumber(v);
  return n === null || n === 0 ? null : n;
}

export function pnlClass(v: number | null | undefined) {
  if (v === null || v === undefined || v === 0) return "flat";
  return v > 0 ? "up" : "down";
}

export function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "--";
  if (v === 0) return digits > 0 ? (0).toFixed(digits) : "0";
  const abs = v.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return `${v > 0 ? "+" : ""}${abs}`;
}

export function fmtPriceOrDash(v: number | null | undefined): string {
  if (v === null || v === undefined) return "--";
  return v.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
}

export function fmtVolume(v: number | null | undefined): string {
  if (v === null || v === undefined) return "--";
  if (v >= 10_000) return `${(v / 10_000).toFixed(1)}万`;
  return v.toLocaleString("zh-CN");
}

export function positionSide(direction: unknown): "多" | "空" {
  const s = String(direction ?? "").trim().toLowerCase();
  if (s === "2" || s === "short" || s === "sell" || s === "空" || s === "s") return "空";
  return "多";
}

export function tradeSideLabel(direction: unknown, offset: unknown): string {
  const d = String(direction ?? "").trim().toLowerCase();
  const o = String(offset ?? "").trim().toLowerCase();
  const buy = d === "buy" || d === "1" || d === "long" || d === "买";
  const sell = d === "sell" || d === "2" || d === "short" || d === "卖";
  const dir = buy ? "买" : sell ? "卖" : "";
  let off = "";
  if (o === "open" || o === "0" || o === "开") off = "开";
  else if (o === "closetoday" || o === "平今") off = "平今";
  else if (o === "closeyesterday" || o === "平昨") off = "平昨";
  else if (o === "close" || o === "1" || o === "平") off = "平";
  if (dir && off) return `${dir}${off}`;
  return dir || off || "--";
}

export function orderStatusLabel(status: unknown): string {
  const s = String(status ?? "").trim().toUpperCase();
  if (s === "SUBMITTING" || s === "NOTTRADED" || s === "NOT_TRADED") return "报单";
  if (s === "PARTTRADED" || s === "PART_TRADED") return "部成";
  if (s === "ALLTRADED" || s === "ALL_TRADED") return "已成";
  if (s === "CANCELLED" || s === "CANCELED") return "已撤";
  if (s === "REJECTED") return "拒单";
  return s || "委托";
}

export function eventTimeText(ts: unknown): string {
  if (!ts) return "--";
  const raw = String(ts);
  const dt = new Date(raw.includes("T") ? raw : Number(ts));
  if (Number.isNaN(dt.getTime())) return raw.slice(11, 19) || "--";
  return dt.toLocaleTimeString("zh-CN", { hour12: false });
}

export function eventTimeMs(ts: unknown): number {
  if (!ts) return 0;
  const n = Number(ts);
  if (Number.isFinite(n) && n > 0) return n < 1e11 ? n * 1000 : n;
  const dt = new Date(String(ts));
  return Number.isNaN(dt.getTime()) ? 0 : dt.getTime();
}

export function quoteChangePct(tick: Record<string, unknown> | undefined): number | null {
  const last = finitePrice(tick?.last_price);
  const pre = finitePrice(tick?.pre_close);
  if (last === null || pre === null) return null;
  return (last - pre) / pre;
}

export function quoteAmplitude(tick: Record<string, unknown> | undefined): number | null {
  const high = finitePrice(tick?.high_price);
  const low = finitePrice(tick?.low_price);
  const pre = finitePrice(tick?.pre_close);
  if (high === null || low === null || pre === null) return null;
  return (high - low) / pre;
}

export function quoteName(code: string, name?: unknown) {
  const n = String(name ?? "").trim();
  return n || String(code || "").trim();
}

export function quoteCode(code: string) {
  return code;
}

/** Letter prefix of a futures symbol, e.g. T2609 → T, c2509 → C. */
export function productPrefixOf(code: string): string {
  const m = String(code || "").trim().match(/^([A-Za-z]+)/);
  return (m?.[1] || "").toUpperCase();
}

/** Fallback product names when ContractData.name is missing. Exact letter-prefix match. */
const PRODUCT_PREFIX_NAMES: Record<string, string> = {
  T: "十年国债",
  TF: "五年国债",
  TS: "二年国债",
  TL: "三十年国债",
  IF: "沪深300",
  IH: "上证50",
  IC: "中证500",
  IM: "中证1000",
  C: "玉米",
};

export function productNameFromCode(code: string): string {
  const prefix = productPrefixOf(code);
  return prefix ? PRODUCT_PREFIX_NAMES[prefix] || "" : "";
}

/** ContractData.name from `/api/contracts`, matched by symbol (and exchange when given). */
export function contractNameOf(
  contracts: Array<Record<string, unknown>>,
  symbol: string,
  exchange?: unknown,
): string {
  const sym = String(symbol || "").trim().toUpperCase();
  if (!sym) return "";
  const ex = String(exchange || "").trim().toUpperCase();
  let fallback = "";
  for (const row of contracts) {
    if (String(row.symbol || "").toUpperCase() !== sym) continue;
    const name = String(row.name ?? "").trim();
    if (ex && String(row.exchange || "").toUpperCase() === ex) return name;
    if (!fallback) fallback = name;
  }
  return fallback;
}

export function instrumentLines(code: string, ...candidates: unknown[]) {
  const symbol = String(code || "").trim();
  const symbolUpper = symbol.toUpperCase();
  let resolved = "";
  for (const candidate of candidates) {
    const name = String(candidate ?? "").trim();
    if (name && name.toUpperCase() !== symbolUpper) {
      resolved = name;
      break;
    }
  }
  if (!resolved) resolved = productNameFromCode(symbol);
  const name = resolved || symbol;
  const distinct = Boolean(symbol) && name.toUpperCase() !== symbolUpper;
  return { name: distinct ? name : symbol, code: symbol, distinct };
}

export function instrumentLabel(code: string, ...candidates: unknown[]) {
  const lines = instrumentLines(code, ...candidates);
  return lines.distinct ? `${lines.name} ${lines.code}` : lines.code;
}

export function pickFunds(
  funds: Record<string, unknown>[],
  gatewayName: string,
  gatewayRow?: Record<string, unknown> | null,
): Record<string, unknown>[] {
  if (!funds.length) return [];
  if (!gatewayName) return funds;
  const exact = funds.filter((row) => String(row.gateway_name || "") === gatewayName);
  if (exact.length) return exact;
  const connect = (gatewayRow?.connect || {}) as Record<string, unknown>;
  const investor = String(connect["用户名"] || gatewayRow?.accountid || "").trim();
  if (investor) {
    const byInvestor = funds.filter((row) => String(row.accountid || "") === investor);
    if (byInvestor.length) return byInvestor;
  }
  const byAccountId = funds.filter((row) => String(row.accountid || "") === gatewayName);
  if (byAccountId.length) return byAccountId;
  return funds.length === 1 ? [...funds] : [];
}

export function accountMetrics(
  fundRow: Record<string, unknown> | undefined,
  positions: Record<string, unknown>[],
) {
  if (!fundRow) {
    return { equity: null as number | null, available: null as number | null, margin: null as number | null, pnl: null as number | null };
  }
  const equity = finiteNumber(fundRow.balance);
  const available = finiteNumber(fundRow.available);
  const marginDirect = finiteNumber(fundRow.margin);
  const frozen = finiteNumber(fundRow.frozen);
  const closeProfit = finiteNumber(fundRow.close_profit);
  const positionProfit = finiteNumber(fundRow.position_profit);
  const posPnl = positions.reduce((sum, pos) => sum + (finiteNumber(pos.pnl) || 0), 0);
  const pnl =
    closeProfit != null || positionProfit != null ? (closeProfit || 0) + (positionProfit || 0) : posPnl;
  const margin =
    marginDirect != null
      ? marginDirect
      : equity != null && available != null
        ? Math.max(0, equity - available)
        : frozen;
  return { equity, available, margin, pnl };
}

export function quoteSector(code: string) {
  const c = code.toUpperCase();
  if (c.startsWith("CU") || c.startsWith("AU") || c.startsWith("AG") || c.startsWith("AL")) return "metal";
  if (c.startsWith("RB") || c.startsWith("I") || c.startsWith("HC")) return "black";
  if (c.startsWith("SA") || c.startsWith("TA") || c.startsWith("MA")) return "chem";
  if (c.startsWith("IF") || c.startsWith("IH") || c.startsWith("IC") || c.startsWith("IM")) return "index";
  if (c.startsWith("M") || c.startsWith("C") || c.startsWith("A")) return "agri";
  return "other";
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "--";
  if (v === 0) return "0.00%";
  return `${v > 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}
