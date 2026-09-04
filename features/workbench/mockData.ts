export const topBarBrand = {
  icon: "衍",
  text: "Stabx",
  en: "simnow",
};

export const riskGauges = [
  { key: "fundUsage", label: "资金使用率", value: 0, warn: 0.7, danger: 0.9 },
  { key: "dailyLoss", label: "单日最大亏损阈值", value: 0, warn: 0.6, danger: 0.85 },
  { key: "singleContract", label: "单合约持仓上限", value: 0, warn: 0.65, danger: 0.8 },
  { key: "volatility", label: "波动率风险指数", value: 0, warn: 0.55, danger: 0.75 },
];

export const contractSectors = [
  { key: "all", label: "全部" },
  { key: "black", label: "黑色系" },
  { key: "agri", label: "农产品" },
  { key: "chem", label: "化工" },
  { key: "index", label: "股指" },
  { key: "metal", label: "贵金属" },
];

function padDate(y: number, m: number, d: number) {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function buildCalendarEvents(year: number, month: number) {
  const events: Record<string, { delivery: string[]; macro: string[]; strategy: string[]; fee: boolean; closed: boolean }> = {};
  const daysInMonth = new Date(year, month, 0).getDate();
  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = padDate(year, month, day);
    const entry = { delivery: [] as string[], macro: [] as string[], strategy: [] as string[], fee: false, closed: false };
    if (day % 11 === 0) entry.delivery.push("沪铜");
    if (day % 13 === 0) entry.delivery.push("烧碱");
    if (day % 17 === 0) entry.macro.push("CPI");
    if (day % 19 === 0) entry.macro.push("PMI");
    if (day % 7 === 0) entry.strategy.push("趋势Alpha");
    if (day % 9 === 0) entry.fee = true;
    if (day % 6 === 0 || day % 7 === 0) entry.closed = true;
    if (entry.delivery.length || entry.macro.length || entry.strategy.length || entry.fee || entry.closed) {
      events[date] = entry;
    }
  }
  return events;
}

export const tradeCalExchanges = [
  { value: "SHFE", label: "上期所" },
  { value: "DCE", label: "大商所" },
  { value: "CFFEX", label: "中金所" },
  { value: "CZCE", label: "郑商所" },
  { value: "INE", label: "能源中心" },
];

export const calendarDayDetail = {
  delivery: [
    { contract: "cu", name: "沪铜", exchange: "上期所", daysLeft: 3 },
  ],
  sessions: [
    { label: "日盘", time: "09:00 – 10:15 / 10:30 – 11:30 / 13:30 – 15:00" },
    { label: "夜盘", time: "21:00 – 23:00 / 01:00" },
  ],
  macroEvents: [{ name: "关注 SimNow 交易时段", countdown: "--", impact: "中" }],
  strategies: [],
  backtestCompare: { lastYear: 0, twoYearsAgo: 0, avg: 0 },
};
