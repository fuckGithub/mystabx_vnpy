/** Aggregate SimNow ticks into one 交易日 timeshare (Asia/Shanghai session clock). */

export type TickLike = Record<string, unknown>;

export type SessionKind = "night" | "day" | "break";

export type TimesharePoint = {
  ts: number;
  label: string;
  axisKey: string;
  tradeDate: string;
  price: number | null;
  volume: number;
  avg: number | null;
  openInterest: number | null;
  session: SessionKind;
  dayStart?: boolean;
};

export type TimeshareSpan = "half" | "1" | "2" | "3" | "4" | "5";

export type ChartTradeMark = {
  index: number;
  label: "买" | "平" | "卖";
  price: number;
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

/**
 * Map an out-of-session clock onto the axis.
 * Critical: 15:00–21:00 (after day close, before night) must snap to 14:59,
 * never to night open 21:00 — otherwise one after-hours tick forward-fills a
 * flat line across the entire 夜盘+日盘 axis.
 */
function snapToSessionMinute(mins: number, windows: Window[]): number {
  if (!windows.length) return mins;
  if (inWindows(mins, windows)) return mins;
  for (let i = windows.length - 1; i >= 0; i -= 1) {
    if (mins >= windows[i].end) {
      const next = windows[i + 1];
      if (!next || mins < next.start) return windows[i].end - 1;
    }
  }
  if (mins < windows[0].start) return windows[0].start;
  return windows[windows.length - 1].end - 1;
}

/**
 * Live only: SimNow / OMS sometimes stamp a not-yet-elapsed axis minute
 * (e.g. 00:19 while wall clock is still 21:19). Plotting there leaves the
 * early 夜盘 empty and parks volume/MACD mid-panel. Pin those to "now".
 */
function liveBucketMinute(mins: number, nowMins: number, windows: Window[]): number {
  const snapped = inWindows(mins, windows) ? mins : snapToSessionMinute(mins, windows);
  if (slotElapsed(snapped, nowMins, windows)) return snapped;
  return snapToSessionMinute(nowMins, windows);
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

type MinuteBucket = { price: number; volume: number; notional: number; oi: number | null };

function tickOpenInterest(tick: TickLike): number | null {
  const n = Number(tick.open_interest ?? tick.openInterest);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function putBucket(
  buckets: Map<number, MinuteBucket>,
  mins: number,
  price: number,
  volume: number,
  oi: number | null,
) {
  const prev = buckets.get(mins);
  buckets.set(mins, {
    price,
    volume: (prev?.volume || 0) + volume,
    notional: (prev?.notional || 0) + price * volume,
    oi: oi ?? prev?.oi ?? null,
  });
}

function isPastSlot(mins: number, nowMins: number): boolean {
  const nightLate = mins >= 21 * 60;
  const nightEarly = mins < 3 * 60;
  if (nowMins >= 20 * 60 + 50) return nightLate && mins <= nowMins;
  if (nowMins < 3 * 60) return nightLate || (nightEarly && mins <= nowMins);
  if (nightLate || nightEarly) return true;
  return mins <= nowMins;
}

/** Elapsed axis minutes only — 夜盘 must not paint unused 日盘 slots. */
function slotElapsed(mins: number, nowMins: number, windows: Window[]): boolean {
  if (inWindows(nowMins, windows)) return isPastSlot(mins, nowMins);
  const hasNight = windows.some((w) => w.session === "night");
  if (!hasNight) {
    const lastEnd = windows[windows.length - 1]?.end ?? 0;
    const firstStart = windows[0]?.start ?? 0;
    if (nowMins >= lastEnd || nowMins < firstStart) return true;
    const next = windows.find((w) => nowMins < w.start);
    if (next) return mins < next.start;
    return true;
  }
  if (nowMins >= 15 * 60 && nowMins < 20 * 60 + 50) return true;
  if (nowMins >= 2 * 60 + 30 && nowMins < 9 * 60) return mins >= 21 * 60 || mins < 3 * 60;
  return isPastSlot(mins, nowMins);
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

function avgOf(price: number, cumVol: number, cumNotional: number): number {
  if (cumVol <= 0) return price;
  const raw = cumNotional / cumVol;
  if (raw > price * 5 || raw < price * 0.2) return price;
  return raw;
}

/**
 * Full 交易日 minute axis from 开盘 to 收盘. Ticks map onto HH:mm slots;
 * minutes before the first real last_price stay empty. After that, last
 * price carries only through elapsed minutes (live “now”), never across
 * unused 日盘 while still in 夜盘.
 */
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
  const buckets = new Map<number, MinuteBucket>();
  let prevCum = 0;
  const orphans: { price: number; volume: number; oi: number | null; dt: Date | null }[] = [];
  const nowMins = clockMinutes(new Date());
  const bucketMins = (mins: number) =>
    live ? liveBucketMinute(mins, nowMins, windows) : snapToSessionMinute(mins, windows);

  const sorted = ticks.map((tick, idx) => ({ tick, idx })).sort((a, b) => {
    const da = parseTickDate(a.tick.datetime)?.getTime() ?? 0;
    const db = parseTickDate(b.tick.datetime)?.getTime() ?? 0;
    if (da !== db) return da - db;
    return a.idx - b.idx;
  });

  for (const { tick } of sorted) {
    const price = tickLastPrice(tick);
    if (price === null) continue;
    const { delta, nextCum } = tickVolumeDelta(tick, prevCum);
    prevCum = nextCum;
    const oi = tickOpenInterest(tick);
    const dt = parseTickDate(tick.datetime);
    if (dt) {
      const mins = clockMinutes(dt);
      const inSession = inWindows(mins, windows);
      const inRange = dt.getTime() >= startMs && dt.getTime() < endMs;
      // inSession uses clock only — SimNow often stamps the wrong calendar day
      // but a valid session HH:mm; still plot those on today's axis.
      if (inSession || inRange) {
        putBucket(buckets, bucketMins(inSession ? mins : snapToSessionMinute(mins, windows)), price, delta, oi);
        continue;
      }
      // Live after-hours / mid-break quotes: pin to nearest session minute
      // (e.g. 17:xx → 14:59) so the curve keeps the latest last_price.
      if (live) {
        putBucket(buckets, bucketMins(mins), price, delta, oi);
        continue;
      }
    } else if (live) {
      putBucket(buckets, bucketMins(nowMins), price, delta, oi);
      continue;
    }
    orphans.push({ price, volume: delta, oi, dt });
  }

  if (buckets.size === 0 && orphans.length) {
    for (const row of orphans) {
      const clock = row.dt ? bucketMins(clockMinutes(row.dt)) : bucketMins(nowMins);
      putBucket(buckets, clock, row.price, row.volume, row.oi);
    }
  }

  // Live tape may only contribute one OMS snapshot — still anchor last_price at "now"
  // so 分时 is not blank while the right-hand quote panel updates.
  if (live && buckets.size === 0) {
    for (let i = sorted.length - 1; i >= 0; i -= 1) {
      const price = tickLastPrice(sorted[i].tick);
      if (price == null) continue;
      putBucket(buckets, bucketMins(nowMins), price, 0, tickOpenInterest(sorted[i].tick));
      break;
    }
  }
  const points: TimesharePoint[] = [];
  let lastPrice: number | null = null;
  let lastOi: number | null = null;
  let seenTick = false;
  let cumVol = 0;
  let cumNotional = 0;
  let prevSession: SessionKind | null = null;
  let markedStart = false;

  for (const win of windows) {
    if (prevSession === "night" && win.session === "day") {
      points.push({
        ts: -1,
        label: "\u2003",
        axisKey: `${tradeDate}|break`,
        tradeDate,
        price: null,
        volume: 0,
        avg: null,
        openInterest: null,
        session: "break",
      });
    }
    for (let m = win.start; m < win.end; m += 1) {
      const hit = buckets.get(m);
      if (hit) {
        lastPrice = hit.price;
        if (hit.oi != null) lastOi = hit.oi;
        seenTick = true;
        cumVol += hit.volume;
        cumNotional += hit.notional;
      }
      const elapsed = !live || slotElapsed(m, nowMins, windows);
      const price = hit ? lastPrice : seenTick && elapsed ? lastPrice : null;
      const dayStart = !markedStart;
      if (dayStart) markedStart = true;
      points.push({
        ts: m,
        label: formatHm(m),
        axisKey: `${tradeDate}|${m}`,
        tradeDate,
        price,
        volume: hit?.volume || 0,
        avg: price === null ? null : avgOf(price, cumVol, cumNotional),
        openInterest: price === null ? null : lastOi,
        session: win.session,
        dayStart,
      });
    }
    prevSession = win.session;
  }
  return points;
}

/** 半日: before 13:00 keep night + morning; after 13:00 keep afternoon only. */
export function sliceHalfDay(points: TimesharePoint[], now = new Date()): TimesharePoint[] {
  const wall = shanghaiWall(now);
  const afternoon = wall.hour * 60 + wall.minute >= 13 * 60;
  return points.filter((p) => {
    if (p.session === "break") return !afternoon;
    if (afternoon) return p.session === "day" && p.ts >= 13 * 60;
    return p.session === "night" || (p.session === "day" && p.ts < 13 * 60);
  });
}

/**
 * Live 分时: drop leading idle slots and unelapsed future slots so 价/量/MACD
 * start at the left edge of the pane instead of sitting mid-axis.
 */
export function focusLiveTimeshare(
  points: TimesharePoint[],
  exchange: string,
  now = new Date(),
): TimesharePoint[] {
  if (!points.length) return points;
  const windows = sessionWindows(exchange);
  const nowMins = clockMinutes(now);
  let first = -1;
  let last = -1;
  for (let i = 0; i < points.length; i += 1) {
    const p = points[i];
    if (p.session === "break") continue;
    if (!slotElapsed(p.ts, nowMins, windows)) continue;
    const active = p.price != null || (p.volume || 0) > 0;
    if (active && first < 0) first = i;
    if (first >= 0) last = i;
  }
  if (first < 0) {
    for (let i = 0; i < points.length; i += 1) {
      const p = points[i];
      if (p.session === "break") continue;
      if (!slotElapsed(p.ts, nowMins, windows)) continue;
      if (first < 0) first = i;
      last = i;
    }
    if (first < 0) return points;
  }
  const sliced = points.slice(first, last + 1);
  if (!sliced.length) return points;
  return sliced.map((p, i) => (i === 0 ? { ...p, dayStart: true } : p));
}

export function stitchTimeshareDays(
  days: { date: string; points: TimesharePoint[] }[],
): TimesharePoint[] {
  const out: TimesharePoint[] = [];
  days.forEach((day, i) => {
    if (i > 0 && day.points.length) {
      out.push({
        ts: -1,
        label: "\u2003",
        axisKey: `${day.date}|join`,
        tradeDate: day.date,
        price: null,
        volume: 0,
        avg: null,
        openInterest: null,
        session: "break",
      });
    }
    const pts = day.points.map((p, idx) => ({
      ...p,
      tradeDate: p.tradeDate || day.date,
      dayStart: idx === 0 || Boolean(p.dayStart),
      axisKey: p.axisKey || `${day.date}|${p.ts}|${idx}`,
    }));
    if (pts.length) pts[0] = { ...pts[0], dayStart: true };
    out.push(...pts);
  });
  return out;
}

export function timeshareTradeMarks(
  points: TimesharePoint[],
  trades: Record<string, unknown>[],
  symbol: string,
  exchange: string,
): ChartTradeMark[] {
  const wantSym = symbol.toUpperCase();
  const wantEx = exchange.toUpperCase();
  const indexByKey = new Map<string, number>();
  points.forEach((p, i) => {
    if (p.session === "break") return;
    indexByKey.set(`${p.tradeDate}|${p.ts}`, i);
  });
  const out: ChartTradeMark[] = [];
  for (const trade of trades) {
    if (String(trade.symbol || "").toUpperCase() !== wantSym) continue;
    const ex = String(trade.exchange || "").toUpperCase();
    if (ex && wantEx && ex !== wantEx) continue;
    const dt = parseTickDate(trade.datetime);
    if (!dt) continue;
    const mins = clockMinutes(dt);
    const td = currentTradeDate(exchange, dt);
    const snapped = snapToSessionMinute(mins, sessionWindows(exchange));
    const idx = indexByKey.get(`${td}|${mins}`) ?? indexByKey.get(`${td}|${snapped}`);
    if (idx == null) continue;
    const px = Number(trade.price);
    const price = Number.isFinite(px) && px > 0 ? px : points[idx]?.price;
    if (price == null) continue;
    out.push({ index: idx, label: tradeMarkLabel(trade), price });
  }
  return out;
}

function tradeMarkLabel(trade: Record<string, unknown>): "买" | "平" | "卖" {
  const o = String(trade.offset ?? "").toUpperCase();
  if (o.includes("CLOSE")) return "平";
  const d = String(trade.direction ?? "").toUpperCase();
  if (d === "SHORT" || d === "SELL" || d === "2") return "卖";
  return "买";
}

export function lastOpenInterest(points: TimesharePoint[]): number | null {
  for (let i = points.length - 1; i >= 0; i -= 1) {
    const oi = points[i].openInterest;
    if (oi != null && Number.isFinite(oi)) return oi;
  }
  return null;
}

export function sumVolume(points: TimesharePoint[]): number {
  return points.reduce((acc, p) => acc + (p.session === "break" ? 0 : p.volume || 0), 0);
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

function isMultiDay(points: TimesharePoint[]): boolean {
  const dates = new Set(points.map((p) => p.tradeDate).filter(Boolean));
  return dates.size > 1;
}

/** Clock text for the x-axis. Session names stay in the chart header, not on ticks. */
export function timeshareAxisLabelText(points: TimesharePoint[], index: number): string {
  const pt = points[index];
  if (!pt || pt.session === "break") return "";
  if (pt.dayStart && isMultiDay(points) && pt.tradeDate.length >= 10) return pt.tradeDate.slice(5);
  const next = points[index + 1];
  if (pt.session === "night" && next?.session === "break") return formatHm((pt.ts ?? 0) + 1);
  if (!next) return formatHm((pt.ts ?? 0) + 1);
  if (next.session !== "break") {
    const sequential = next.ts === pt.ts + 1 || (pt.ts === 24 * 60 - 1 && next.ts === 0);
    if (!sequential) {
      const endLabel = formatHm((pt.ts ?? 0) + 1);
      if (AXIS_LABELS.has(endLabel)) return endLabel;
    }
  }
  return pt.label;
}

/**
 * Sparse session clocks only (21:00, 22:00… 09:00, 10:30, 11:30, 13:30, 15:00).
 * Multi-day charts also label each 交易日 start (MM-DD).
 */
export function timeshareAxisLabelVisible(points: TimesharePoint[], index: number): boolean {
  const pt = points[index];
  if (!pt || pt.session === "break") return false;
  if (pt.dayStart && isMultiDay(points)) return true;
  const text = timeshareAxisLabelText(points, index);
  if (!AXIS_LABELS.has(text)) return false;
  for (let i = 0; i < index; i += 1) {
    if (points[i].tradeDate !== pt.tradeDate) continue;
    if (timeshareAxisLabelText(points, i) === text) return false;
  }
  return true;
}
