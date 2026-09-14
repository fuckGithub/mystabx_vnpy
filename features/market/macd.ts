/** MACD(fast, slow, signal) from close series. Nulls are skipped until the first valid close. */

export type MacdPoint = {
  dif: number | null;
  dea: number | null;
  hist: number | null;
};

function emaNext(prev: number | null, value: number, period: number): number {
  const k = 2 / (period + 1);
  if (prev == null) return value;
  return value * k + prev * (1 - k);
}

export function computeMacd(
  closes: (number | null | undefined)[],
  fast = 12,
  slow = 26,
  signal = 9,
): MacdPoint[] {
  const f = Math.max(1, Math.floor(fast));
  const s = Math.max(f + 1, Math.floor(slow));
  const sig = Math.max(1, Math.floor(signal));
  let emaFast: number | null = null;
  let emaSlow: number | null = null;
  let emaSignal: number | null = null;
  let seeded = 0;
  const out: MacdPoint[] = [];
  for (const raw of closes) {
    const close = Number(raw);
    if (!Number.isFinite(close) || close <= 0) {
      out.push({ dif: null, dea: null, hist: null });
      continue;
    }
    emaFast = emaNext(emaFast, close, f);
    emaSlow = emaNext(emaSlow, close, s);
    seeded += 1;
    if (seeded < s) {
      out.push({ dif: null, dea: null, hist: null });
      continue;
    }
    const dif = emaFast - emaSlow;
    emaSignal = emaNext(emaSignal, dif, sig);
    const dea = emaSignal;
    out.push({
      dif,
      dea,
      hist: (dif - dea) * 2,
    });
  }
  return out;
}

export function lastMacdLabel(points: MacdPoint[]): string {
  for (let i = points.length - 1; i >= 0; i -= 1) {
    const p = points[i];
    if (p.dif == null || p.dea == null || p.hist == null) continue;
    return `MACD ${p.hist.toFixed(2)}  DIFF ${p.dif.toFixed(2)}  DEA ${p.dea.toFixed(2)}`;
  }
  return "";
}
