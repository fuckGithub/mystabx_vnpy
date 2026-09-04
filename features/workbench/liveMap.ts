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
  return n || code;
}

export function quoteCode(code: string) {
  return code;
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
