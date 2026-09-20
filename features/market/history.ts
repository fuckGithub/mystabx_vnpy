import { http } from "@/api";

/** Historical K-line source. Charts always request local MySQL replay. */
export type HistorySource = "local" | "mock" | "rqdata";
export type BarInterval = "1m" | "5m" | "15m" | "30m" | "60m" | "1d" | "1w" | "1M";
export type ChartPeriod = "timeshare" | BarInterval;

/** Production charts never request mock; empty local stays empty. */
export const HISTORY_SOURCE: HistorySource = "local";

export type HistoryBar = {
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  open_interest?: number;
};

export type HistoryBarsResult = {
  source: HistorySource;
  symbol: string;
  exchange: string;
  interval: BarInterval;
  bars: HistoryBar[];
  empty?: boolean;
  hint?: string;
};

export async function fetchHistoryBars(params: {
  symbol: string;
  exchange: string;
  interval: BarInterval;
  source?: HistorySource;
}): Promise<HistoryBarsResult> {
  // Charts always request local MySQL; ignore any caller mock/rqdata intent.
  void params.source;
  const { data } = await http.get<HistoryBarsResult>("/api/market/bars", {
    params: {
      symbol: params.symbol,
      exchange: params.exchange,
      interval: params.interval,
      source: HISTORY_SOURCE,
    },
  });
  return data;
}
