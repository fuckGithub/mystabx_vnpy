import type { Component } from "vue";
import {
  Box,
  Connection,
  Cpu,
  DataLine,
  Document,
  EditPen,
  HomeFilled,
  List,
  Notebook,
  SetUp,
  Setting,
  Tickets,
  TrendCharts,
  User,
  Wallet,
} from "@element-plus/icons-vue";

export type NavItem = {
  path: string;
  title: string;
  icon: Component;
  home?: boolean;
  admin?: boolean;
};

export const topMenus: NavItem[] = [
  { path: "/workbench", title: "工作台", icon: HomeFilled, home: true },
  { path: "/market/ticks", title: "市场行情", icon: DataLine },
  { path: "/trade/order", title: "交易下单", icon: Tickets },
  { path: "/strategy/cta", title: "策略模型", icon: Cpu },
  { path: "/account/gateways", title: "资金持仓", icon: Wallet },
  { path: "/admin/users", title: "系统管理", icon: Setting, admin: true },
];

export const sidebars: Record<string, NavItem[]> = {
  market: [
    { path: "/market/ticks", title: "实时行情", icon: TrendCharts },
    { path: "/market/quotes", title: "行情中心", icon: List },
  ],
  trade: [
    { path: "/trade/order", title: "下单面板", icon: EditPen },
    { path: "/trade/orders", title: "委托列表", icon: Document },
  ],
  strategy: [
    { path: "/strategy/cta", title: "CTA实例", icon: Cpu },
    { path: "/strategy/logs", title: "策略日志", icon: Notebook },
    { path: "/strategy/stoporders", title: "停止单", icon: List },
    { path: "/strategy/backtest", title: "回测", icon: TrendCharts },
  ],
  account: [
    { path: "/account/gateways", title: "账户连接", icon: Connection },
    { path: "/account/funds", title: "资金账户", icon: Wallet },
    { path: "/account/positions", title: "持仓明细", icon: Box },
    { path: "/account/trades", title: "成交记录", icon: Notebook },
  ],
  admin: [
    { path: "/admin/users", title: "用户管理", icon: User },
    { path: "/admin/accounts", title: "通道配置", icon: SetUp },
  ],
};

export function moduleKeyFromPath(path: string): string {
  if (path.startsWith("/market")) return "market";
  if (path.startsWith("/trade")) return "trade";
  if (path.startsWith("/strategy")) return "strategy";
  if (path.startsWith("/account")) return "account";
  if (path.startsWith("/admin")) return "admin";
  return "";
}

export function topActivePath(path: string): string {
  if (path === "/workbench" || path.startsWith("/workbench/")) return "/workbench";
  const first = sidebars[moduleKeyFromPath(path)]?.[0];
  return first?.path ?? path;
}
