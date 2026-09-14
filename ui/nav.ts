import type { Component } from "vue";
import {
  Box,
  Connection,
  Cpu,
  DataAnalysis,
  DataBoard,
  DataLine,
  Document,
  EditPen,
  Files,
  Grid,
  HomeFilled,
  Histogram,
  List,
  Monitor,
  Notebook,
  Opportunity,
  SetUp,
  Setting,
  Share,
  Tickets,
  TrendCharts,
  User,
  VideoCamera,
  Wallet,
  Warning,
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
  { path: "/account/gateways", title: "资金持仓", icon: Wallet },
  { path: "/apps/overview", title: "策略应用", icon: Cpu },
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
  account: [
    { path: "/account/gateways", title: "账户连接", icon: Connection },
    { path: "/account/funds", title: "资金账户", icon: Wallet },
    { path: "/account/positions", title: "持仓明细", icon: Box },
    { path: "/account/trades", title: "成交记录", icon: Notebook },
  ],
  apps: [
    { path: "/apps/overview", title: "应用总览", icon: Grid },
    { path: "/apps/cta", title: "CTA自动交易", icon: Opportunity },
    { path: "/apps/backtester", title: "CTA回测研究", icon: DataAnalysis },
    { path: "/apps/spread", title: "价差套利", icon: Share },
    { path: "/apps/option", title: "期权波动率", icon: Histogram },
    { path: "/apps/portfolio", title: "组合策略", icon: DataBoard },
    { path: "/apps/algo", title: "算法委托", icon: Cpu },
    { path: "/apps/script", title: "脚本策略", icon: Document },
    { path: "/apps/paper", title: "本地仿真", icon: Monitor },
    { path: "/apps/recorder", title: "行情记录", icon: VideoCamera },
    { path: "/apps/datamanager", title: "历史数据", icon: Files },
    { path: "/apps/risk", title: "事前风控", icon: Warning },
    { path: "/apps/rpc", title: "RPC服务器", icon: Connection },
    { path: "/apps/chart", title: "实时K线", icon: TrendCharts },
    { path: "/apps/portfolio_mgr", title: "组合管理", icon: DataBoard },
    { path: "/apps/excelrtd", title: "EXCEL RTD", icon: Grid },
    { path: "/apps/webtrader", title: "Web服务器", icon: Monitor },
  ],
  admin: [
    { path: "/admin/users", title: "用户管理", icon: User },
    { path: "/admin/accounts", title: "通道配置", icon: SetUp },
  ],
};

export function moduleKeyFromPath(path: string): string {
  if (path.startsWith("/market")) return "market";
  if (path.startsWith("/trade")) return "trade";
  if (path.startsWith("/account")) return "account";
  if (path.startsWith("/apps")) return "apps";
  if (path.startsWith("/admin")) return "admin";
  return "";
}

export function topActivePath(path: string): string {
  if (path === "/workbench" || path.startsWith("/workbench/")) return "/workbench";
  const first = sidebars[moduleKeyFromPath(path)]?.[0];
  return first?.path ?? path;
}
