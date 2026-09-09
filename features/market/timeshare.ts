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

function shanghaiWall(date = new Date()): Ymd & { hour: number; minute: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: SH_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const num = (type: string) => Number(parts.find((p) => p.type === type)?.value || 0);
  return { y: num("year"), m: num("month"), d: num("day"), hour: num("hour"), minute: num("minute") };
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
  if (!raw) return null;
  const text = String(raw);
  const dt = new Date(text.includes("T") ? text : Number(text));
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function clockMinutes(date: Date): number {
  const wall = shanghaiWall(date);
  return wall.hour * 60 + wall.minute;
}

function formatHm(totalMin: number): string {
  const wrapped = ((totalMin % (24 * 60)) + 24 * 60) % (24 * 60);
  return `${pad(Math.floor(wrapped / 60))}:${pad(wrapped % 60)}`;
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

function isPastSlot(mins: number, nowMins: number): boolean {
  const nightLate = mins >= 21 * 60;
  const nightEarly = mins < 3 * 60;
  if (nowMins >= 20 * 60 + 50) return nightLate && mins <= nowMins;
  if (nowMins < 3 * 60) return nightLate || (nightEarly && mins <= nowMins);
  if (nightLate || nightEarly) return true;
  return mins <= nowMins;
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

export function aggregateTimeshare(
  ticks: TickLike[],
  exchange: string,
  opts: TimeshareOptions = {},
): TimesharePoint[] {
  const tradeDate = opts.tradeDate || currentTradeDate(exchange);
  const live = opts.live !== false && tradeDate === currentTradeDate(exchange);
  const windows = sessionWindows(exchange);
  const startMs = sessionStartMs(exchange, tradeDate);
  const endMs = sessionEndMs(exchange, tradeDate);
  const buckets = new Map<number, { price: number; volume: number; turnover: number }>();
  let prevCum = 0;

  const sorted = [...ticks].sort((a, b) => {
    const da = parseTickDate(a.datetime)?.getTime() ?? 0;
    const db = parseTickDate(b.datetime)?.getTime() ?? 0;
    return da - db;
  });

  for (const tick of sorted) {
    const dt = parseTickDate(tick.datetime);
    if (!dt) continue;
    const ms = dt.getTime();
    if (ms < startMs || ms >= endMs) continue;
    const price = finitePrice(tick.last_price);
    if (price === null) continue;
    const mins = clockMinutes(dt);
    if (!inWindows(mins, windows)) continue;

    const cum = Number(tick.volume);
    const lastVol = Number(tick.last_volume);
    let delta = 0;
    if (Number.isFinite(lastVol) && lastVol > 0) delta = lastVol;
    else if (Number.isFinite(cum) && cum >= prevCum) delta = cum - prevCum;
    if (Number.isFinite(cum) && cum > 0) prevCum = cum;

    const turnover = Number(tick.turnover);
    const prev = buckets.get(mins);
    buckets.set(mins, {
      price,
      volume: (prev?.volume || 0) + Math.max(0, delta),
      turnover: Number.isFinite(turnover) ? turnover : prev?.turnover || 0,
    });
  }

  const nowMins = clockMinutes(new Date());
  const points: TimesharePoint[] = [];
  let lastPrice: number | null = null;
  let cumVol = 0;
  let cumTurnover = 0;
  let prevSession: SessionKind | null = null;

  for (const win of windows) {
    if (prevSession === "night" && win.session === "day") {
      points.push({
        ts: -1,
        label: "日盘",
        price: null,
        volume: 0,
        avg: null,
        session: "break",
      });
    }
    for (let m = win.start; m < win.end; m += 1) {
      const hit = buckets.get(m);
      if (hit) {
        lastPrice = hit.price;
        cumVol += hit.volume;
        if (hit.turnover > 0) cumTurnover = hit.turnover;
      }
      const pastOrNow = !live || isPastSlot(m, nowMins);
      const price = hit || (pastOrNow && lastPrice !== null) ? lastPrice : null;
      const avg = cumVol > 0 && cumTurnover > 0 ? cumTurnover / cumVol : lastPrice;
      points.push({
        ts: m,
        label: formatHm(m),
        price,
        volume: hit?.volume || 0,
        avg: price === null ? null : avg,
        session: win.session,
      });
    }
    prevSession = win.session;
  }
  return points;
}

export const AXIS_LABELS = new Set([
  "21:00",
  "22:00",
  "23:00",
  "00:00",
  "01:00",
  "02:30",
  "日盘",
  "09:00",
  "09:30",
  "10:15",
  "10:30",
  "11:30",
  "13:00",
  "13:30",
  "15:00",
]);
