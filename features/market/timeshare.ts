/** Aggregate SimNow ticks into one 交易日 timeshare (Asia/Shanghai session clock). */

export type TickLike = Record<string, unknown>;

export type SessionKind = "night" | "day" | "break";

export type TimesharePoint = {
  ts: number;
  label: string;
  price: number | null;
  volume: number;
  avg: number | null;
  session: SessionKind;
};

export type TimeshareOptions = {
  tradeDate?: string;
  live?: boolean;
};

const SH_TZ = "Asia/Shanghai";

type Ymd = { y: number; m: number; d: number };

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function ymdText(ymd: Ymd): string {
  return `${ymd.y}-${pad(ymd.m)}-${pad(ymd.d)}`;
}

function shanghaiWall(date = new Date()): Ymd & { hour: number; minute: number; second: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: SH_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const num = (type: string) => Number(parts.find((p) => p.type === type)?.value || 0);
  return {
    y: num("year"),
    m: num("month"),
    d: num("day"),
    hour: num("hour"),
    minute: num("minute"),
    second: num("second"),
  };
}

function shanghaiMs(y: number, m: number, d: number, hour: number, minute: number): number {
  return Date.parse(`${ymdText({ y, m, d })}T${pad(hour)}:${pad(minute)}:00+08:00`);
}

function parseYmd(raw?: string): Ymd | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(raw || "").trim());
  if (!m) return null;
  return { y: Number(m[1]), m: Number(m[2]), d: Number(m[3]) };
}

function addDays(ymd: Ymd, delta: number): Ymd {
  const dt = new Date(Date.UTC(ymd.y, ymd.m - 1, ymd.d + delta));
  return { y: dt.getUTCFullYear(), m: dt.getUTCMonth() + 1, d: dt.getUTCDate() };
}

function weekdayUtc(ymd: Ymd): number {
  return new Date(Date.UTC(ymd.y, ymd.m - 1, ymd.d)).getUTCDay();
}

function nextWeekday(ymd: Ymd): Ymd {
  let cur = ymd;
  while (weekdayUtc(cur) === 0 || weekdayUtc(cur) === 6) cur = addDays(cur, 1);
  return cur;
}

function prevWeekday(ymd: Ymd): Ymd {
  let cur = ymd;
  while (weekdayUtc(cur) === 0 || weekdayUtc(cur) === 6) cur = addDays(cur, -1);
  return cur;
}

function isCffex(exchange: string): boolean {
  const ex = exchange.toUpperCase();
  return ex === "CFFEX" || ex === "CFX";
}

function parseTickDate(raw: unknown): Date | null {
  if (raw == null || raw === "") return null;
  if (typeof raw === "number") {
    const dt = new Date(raw < 1e12 ? raw * 1000 : raw);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }
  const text = String(raw).trim();
  if (!text) return null;
  if (/^\d+(\.\d+)?$/.test(text)) {
    const n = Number(text);
    const dt = new Date(n < 1e12 ? n * 1000 : n);
    return Number.isNaN(dt.getTime()) ? null : dt;
  }
  const iso = text.includes("T") ? text : text.replace(" ", "T");
  const withTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}+08:00`;
  const dt = new Date(withTz);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function tickLastPrice(tick: TickLike): number | null {
  return finitePrice(tick.last_price ?? tick.lastPrice);
}

function clockMinutes(date: Date): number {
  const wall = shanghaiWall(date);
  return wall.hour * 60 + wall.minute;
}

function formatHm(totalMin: number): string {
  const wrapped = ((totalMin % (24 * 60)) + 24 * 60) % (24 * 60);
  return `${pad(Math.floor(wrapped / 60))}:${pad(wrapped % 60)}`;
}

function formatHms(date: Date): string {
  const wall = shanghaiWall(date);
  return `${pad(wall.hour)}:${pad(wall.minute)}:${pad(wall.second)}`;
}

function clockHm(label: string): string {
  return label.length >= 5 ? label.slice(0, 5) : label;
}

type Window = { start: number; end: number; session: Exclude<SessionKind, "break"> };

function sessionWindows(exchange: string): Window[] {
  if (isCffex(exchange)) {
    return [
      { start: 9 * 60 + 30, end: 11 * 60 + 30, session: "day" },
      { start: 13 * 60, end: 15 * 60, session: "day" },
    ];
  }
  return [
    { start: 21 * 60, end: 24 * 60, session: "night" },
    { start: 0, end: 2 * 60 + 30, session: "night" },
    { start: 9 * 60, end: 10 * 60 + 15, session: "day" },
    { start: 10 * 60 + 30, end: 11 * 60 + 30, session: "day" },
    { start: 13 * 60 + 30, end: 15 * 60, session: "day" },
  ];
}

function inWindows(mins: number, windows: Window[]): boolean {
  return windows.some((w) => mins >= w.start && mins < w.end);
}

function sessionOfMinute(mins: number, windows: Window[]): Exclude<SessionKind, "break"> | null {
  const hit = windows.find((w) => mins >= w.start && mins < w.end);
  return hit ? hit.session : null;
}

/** Map an out-of-session clock (e.g. SimNow 17:30 after CFFEX close) onto the axis. */
function snapToSessionMinute(mins: number, windows: Window[]): number {
  if (!windows.length) return mins;
  if (inWindows(mins, windows)) return mins;
  if (mins < windows[0].start) return windows[0].start;
  for (let i = windows.length - 1; i >= 0; i -= 1) {
    if (mins >= windows[i].end) return windows[i].end - 1;
  }
  return windows[0].start;
}

function tickVolumeDelta(tick: TickLike, prevCum: number): { delta: number; nextCum: number } {
  const cum = Number(tick.volume);
  const lastVol = Number(tick.last_volume ?? tick.lastVolume);
  let delta = 0;
  let nextCum = prevCum;
  if (Number.isFinite(lastVol) && lastVol > 0) delta = lastVol;
  else if (Number.isFinite(cum) && cum >= prevCum) delta = cum - prevCum;
  if (Number.isFinite(cum) && cum > 0) nextCum = cum;
  return { delta: Math.max(0, delta), nextCum };
}

function finitePrice(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function currentTradeDate(exchange = "", now = new Date()): string {
  const wall = shanghaiWall(now);
  const mins = wall.hour * 60 + wall.minute;
  const ymd = { y: wall.y, m: wall.m, d: wall.d };
  const weekend = weekdayUtc(ymd) === 0 || weekdayUtc(ymd) === 6;
  if (isCffex(exchange)) return ymdText(weekend ? nextWeekday(ymd) : ymd);
  if (mins >= 20 * 60 + 50) return ymdText(nextWeekday(addDays(ymd, 1)));
  if (mins < 3 * 60) return ymdText(nextWeekday(ymd));
  return ymdText(weekend ? nextWeekday(ymd) : ymd);
}

export function recentTradeDates(n = 10, exchange = "", now = new Date()): string[] {
  const today = parseYmd(currentTradeDate(exchange, now));
  if (!today) return [];
  const out = [ymdText(today)];
  let cursor = addDays(today, -1);
  while (out.length < n) {
    const wd = weekdayUtc(cursor);
    if (wd !== 0 && wd !== 6) out.push(ymdText(cursor));
    cursor = addDays(cursor, -1);
    if (out.length > 0 && addDays(today, -40).y && out.length >= n) break;
    if (out.length > 20) break;
  }
  return out;
}

export function sessionHint(exchange: string): string {
  return isCffex(exchange) ? "日盘 09:30–11:30 | 13:00–15:00" : "夜盘 21:00–02:30 | 日盘 09:00–15:00";
}

export function sessionStartMs(exchange = "", tradeDate?: string): number {
  const ymd = parseYmd(tradeDate) || parseYmd(currentTradeDate(exchange));
  if (!ymd) return Date.now();
  if (isCffex(exchange)) return shanghaiMs(ymd.y, ymd.m, ymd.d, 9, 15);
  const prev = prevWeekday(addDays(ymd, -1));
  return shanghaiMs(prev.y, prev.m, prev.d, 21, 0);
}

function sessionEndMs(exchange: string, tradeDate?: string): number {
  const ymd = parseYmd(tradeDate) || parseYmd(currentTradeDate(exchange));
  if (!ymd) return Date.now();
  return shanghaiMs(ymd.y, ymd.m, ymd.d, 15, 15);
}

export function isSessionTick(tick: TickLike, exchange: string, tradeDate?: string): boolean {
  const dt = parseTickDate(tick.datetime);
  if (!dt) return true;
  const start = sessionStartMs(exchange, tradeDate);
  const end = sessionEndMs(exchange, tradeDate);
  const ms = dt.getTime();
  return ms >= start && ms < end;
}

type Vertex = {
  ts: number;
  label: string;
  price: number;
  volume: number;
  notional: number;
  session: Exclude<SessionKind, "break">;
};

function pushVertex(vertices: Vertex[], next: Vertex): void {
  const last = vertices[vertices.length - 1];
  if (last && last.label === next.label && last.price === next.price && last.session === next.session) {
    last.volume += next.volume;
    last.notional += next.notional;
    return;
  }
  vertices.push(next);
}

function avgOf(price: number, cumVol: number, cumNotional: number): number {
  if (cumVol <= 0) return price;
  const raw = cumNotional / cumVol;
  if (raw > price * 5 || raw < price * 0.2) return price;
  return raw;
}

/**
 * Polyline through session ticks in time order. Same-second quotes still keep
 * last_price changes; identical price+second is merged. Empty session minutes
 * are not invented — that was a flat fake curve.
 */
export function aggregateTimeshare(
  ticks: TickLike[],
  exchange: string,
  opts: TimeshareOptions = {},
): TimesharePoint[] {
  const tradeDate = opts.tradeDate || currentTradeDate(exchange);
  const windows = sessionWindows(exchange);
  const startMs = sessionStartMs(exchange, tradeDate);
  const endMs = sessionEndMs(exchange, tradeDate);
  let prevCum = 0;
  const orphans: { price: number; volume: number; dt: Date | null; idx: number }[] = [];
  const vertices: Vertex[] = [];

  const sorted = ticks.map((tick, idx) => ({ tick, idx })).sort((a, b) => {
    const da = parseTickDate(a.tick.datetime)?.getTime() ?? 0;
    const db = parseTickDate(b.tick.datetime)?.getTime() ?? 0;
    if (da !== db) return da - db;
    return a.idx - b.idx;
  });

  for (const { tick, idx } of sorted) {
    const price = tickLastPrice(tick);
    if (price === null) continue;
    const { delta, nextCum } = tickVolumeDelta(tick, prevCum);
    prevCum = nextCum;
    const dt = parseTickDate(tick.datetime);
    if (dt) {
      const mins = clockMinutes(dt);
      const inSession = inWindows(mins, windows);
      const inRange = dt.getTime() >= startMs && dt.getTime() < endMs;
      if (inSession || inRange) {
        const clock = inSession ? mins : snapToSessionMinute(mins, windows);
        const session = sessionOfMinute(clock, windows) || "day";
        pushVertex(vertices, {
          ts: clock,
          label: formatHms(dt),
          price,
          volume: delta,
          notional: price * delta,
          session,
        });
        continue;
      }
    }
    orphans.push({ price, volume: delta, dt, idx });
  }

  if (vertices.length === 0 && orphans.length) {
    for (const row of orphans) {
      const clock = row.dt
        ? snapToSessionMinute(clockMinutes(row.dt), windows)
        : windows[0]?.start ?? 21 * 60;
      const session = sessionOfMinute(clock, windows) || "night";
      const label = row.dt ? formatHms(row.dt) : `${formatHm(clock)}:${pad(row.idx % 60)}`;
      pushVertex(vertices, {
        ts: clock,
        label,
        price: row.price,
        volume: row.volume,
        notional: row.price * row.volume,
        session,
      });
    }
  }

  const points: TimesharePoint[] = [];
  let cumVol = 0;
  let cumNotional = 0;
  let prevSession: SessionKind | null = null;
  for (const v of vertices) {
    if (prevSession === "night" && v.session === "day") {
      points.push({
        ts: -1,
        label: "\u2003",
        price: null,
        volume: 0,
        avg: null,
        session: "break",
      });
    }
    cumVol += v.volume;
    cumNotional += v.notional;
    points.push({
      ts: v.ts,
      label: v.label,
      price: v.price,
      volume: v.volume,
      avg: avgOf(v.price, cumVol, cumNotional),
      session: v.session,
    });
    prevSession = v.session;
  }
  return points;
}

/** Y-axis from plotted prices only: 4% of span, or 0.25% of level when the series is flat. */
export function paddedPriceRange(values: number[]): { min?: number; max?: number } {
  const vals = values.filter((n) => Number.isFinite(n) && n > 0);
  if (!vals.length) return {};
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const mid = (lo + hi) / 2;
  const pad = Math.max((hi - lo) * 0.04, Math.abs(mid) * 0.0025, 0.01);
  return { min: lo - pad, max: hi + pad };
}

/**
 * Timeshare price axis from 现价, plus 均价 only when it is the same unit
 * (not turnover / VWAP blow-ups). Zeros, nulls, and 昨收 are ignored so a
 * flat last_price is not stretched to pre-close or a dummy 0–100000 range.
 */
export function timesharePriceRange(points: TimesharePoint[]): { min?: number; max?: number } {
  const prices: number[] = [];
  const avgs: number[] = [];
  for (const p of points) {
    if (p.session === "break") continue;
    if (p.price != null && p.price > 0) prices.push(p.price);
    if (p.avg != null && p.avg > 0) avgs.push(p.avg);
  }
  const vals = [...prices];
  if (prices.length) {
    const lo = Math.min(...prices);
    const hi = Math.max(...prices);
    for (const avg of avgs) {
      if (avg >= lo * 0.5 && avg <= hi * 2) vals.push(avg);
    }
  } else {
    vals.push(...avgs);
  }
  return paddedPriceRange(vals);
}

export const AXIS_LABELS = new Set([
  "21:00",
  "22:00",
  "23:00",
  "00:00",
  "01:00",
  "02:30",
  "09:00",
  "09:30",
  "10:15",
  "10:30",
  "11:30",
  "13:00",
  "13:30",
  "15:00",
]);

/** Clock text for the x-axis. Session names stay in the chart header, not on ticks. */
export function timeshareAxisLabelText(points: TimesharePoint[], index: number): string {
  const pt = points[index];
  if (!pt || pt.session === "break") return "";
  if (pt.session === "night" && points[index + 1]?.session === "break") {
    return formatHm((pt.ts ?? 0) + 1);
  }
  return clockHm(pt.label);
}

/**
 * Show sparse clock labels only. Skip the night/day join (「日盘」/09:00 glued to 01:00)
 * so the divider is a single vertical line.
 */
export function timeshareAxisLabelVisible(points: TimesharePoint[], index: number): boolean {
  const pt = points[index];
  if (!pt || pt.session === "break") return false;
  const text = timeshareAxisLabelText(points, index);
  if (!text) return false;
  const last = points.length - 1;
  const isEdge = index === 0 || index === last || (index === last - 1 && points[last]?.session === "break");
  if (!isEdge && !AXIS_LABELS.has(text)) return false;
  for (let i = 0; i < index; i += 1) {
    if (timeshareAxisLabelText(points, i) === text) return false;
  }
  const breakIdx = points.findIndex((p) => p.session === "break");
  if (breakIdx < 0) return true;
  if (index === breakIdx + 1) return false;
  if (index < breakIdx && text === "01:00") return false;
  return true;
}
