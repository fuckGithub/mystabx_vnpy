/** Chinese labels for CTA strategy / model parameter keys. */
const PARAM_LABEL_ZH: Record<string, string> = {
  vt_symbol: "合约",
  fast_window: "快线周期",
  slow_window: "慢线周期",
  fixed_size: "固定手数",
  entry_window: "入场窗口",
  exit_window: "出场窗口",
  atr_window: "ATR 周期",
  atr_multiplier: "ATR 倍数",
  rsi_window: "RSI 周期",
  rsi_entry: "RSI 入场阈值",
  rsi_exit: "RSI 出场阈值",
  rsi_signal: "RSI 信号阈值",
  rsi_level: "RSI 水平",
  boll_window: "布林带周期",
  boll_dev: "布林带标准差",
  boll_length: "布林带长度",
  cci_window: "CCI 周期",
  cci_level: "CCI 水平",
  trailing_percent: "跟踪止损比例",
  trailing_long: "多头跟踪止损",
  trailing_short: "空头跟踪止损",
  price_add: "加价跳数",
  donchian_window: "唐奇安通道周期",
  channel_length: "通道长度",
  window: "周期窗口",
  N: "周期 N",
  k1: "上轨系数 K1",
  k2: "下轨系数 K2",
  bar_window: "K线窗口",
  bar_interval: "K线周期",
  bar_buffer: "K线缓冲",
  capital: "初始资金",
  rate: "手续费率",
  slippage: "滑点",
  size: "合约乘数",
  pricetick: "最小变动价位",
  interval: "周期",
};

/** Prefer dictionary; otherwise turn snake_case into readable Chinese-friendly text. */
export function paramLabelZh(key: string): string {
  const k = String(key || "").trim();
  if (!k) return "—";
  if (PARAM_LABEL_ZH[k]) return PARAM_LABEL_ZH[k];
  const lower = k.toLowerCase();
  if (PARAM_LABEL_ZH[lower]) return PARAM_LABEL_ZH[lower];
  return k
    .replace(/_/g, " ")
    .replace(/\bwindow\b/gi, "周期")
    .replace(/\bsize\b/gi, "手数")
    .replace(/\blength\b/gi, "长度")
    .replace(/\bmultiplier\b/gi, "倍数")
    .replace(/\bpercent\b/gi, "比例")
    .replace(/\bentry\b/gi, "入场")
    .replace(/\bexit\b/gi, "出场")
    .replace(/\bfast\b/gi, "快")
    .replace(/\bslow\b/gi, "慢")
    .replace(/\bfixed\b/gi, "固定")
    .trim();
}
