/** Chinese titles for CTA strategy classes (UI labels; API may also send display_name). */

const TITLE_ZH: Record<string, string> = {
  TurtleSignalStrategy: "海龟交易信号策略",
  DualThrustStrategy: "双推力策略",
  BollChannelStrategy: "布林带通道策略",
  AtrRsiStrategy: "ATR-RSI策略",
  KingKeltnerStrategy: "肯特纳通道策略",
  MultiSignalStrategy: "多信号策略",
  MultiTimeframeStrategy: "多周期策略",
  TestStrategy: "测试策略",
  DoubleMaStrategy: "双均线策略",
  RumiStrategy: "RUMI均线偏差策略",
};

function titleZh(className: string): string {
  const name = (className || "").trim();
  if (!name) return "";
  if (TITLE_ZH[name]) return TITLE_ZH[name];
  const spaced = name
    .replace(/([a-z\d])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/\s+Strategy$/, "")
    .trim();
  return spaced ? `${spaced}策略` : name;
}

/** 「中文名 (ClassName)」; unknown classes stay readable without crashing. */
export function strategyDisplayName(className: string, apiDisplay?: string | null): string {
  const name = (className || "").trim();
  if (!name) return "";
  if (apiDisplay && String(apiDisplay).trim()) return String(apiDisplay).trim();
  const title = titleZh(name);
  if (title === name) return name;
  return `${title} (${name})`;
}
