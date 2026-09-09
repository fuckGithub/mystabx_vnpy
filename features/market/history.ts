import { http } from "@/api";

/** Historical K-line source. Flip to rqdata after the backend RQData plug-in is wired. */
export type HistorySource = "mock" | "rqdata";
export type BarInterval = "1m" | "5m" | "15m" | "30m" | "60m" | "1d" | "1w" | "1M";
export type ChartPeriod = "timeshare" | BarInterval;

export const HISTORY_SOURCE: HistorySource = "mock";

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
};

export async function fetchHistoryBars(params: {
  symbol: string;
  exchange: string;
  interval: BarInterval;
  source?: HistorySource;
}): Promise<HistoryBarsResult> {
  const source = params.source ?? HISTORY_SOURCE;
  const { data } = await http.get<HistoryBarsResult>("/api/market/bars", {
    params: {
      symbol: params.symbol,
      exchange: params.exchange,
      interval: params.interval,
      source,
    },
  });
  return data;
}
