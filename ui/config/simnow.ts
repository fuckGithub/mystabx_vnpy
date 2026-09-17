/**
 * Frontend SimNow CTP defaults (offline / pre-API fallback).
 *
 * Canonical backend source: `mystabx/config/simnow.py`.
 * Prefer live values from `GET /api/admin/connect-defaults` when available;
 * keep this module in sync with the Python constants — do not redefine
 * fronts / broker / product defaults in feature views.
 */

/** Session-hours fronts (matches SIMNOW_SESSION). */
export const SIMNOW_SESSION = {
  td: "182.254.243.31:30001",
  md: "182.254.243.31:30011",
};

/** 7×24 fronts (matches SIMNOW_24H). */
export const SIMNOW_24H = {
  td: "182.254.243.31:40001",
  md: "182.254.243.31:40011",
};

/** Matches AUTO_FRONT_WINDOWS in mystabx/config/simnow.py */
export const AUTO_FRONT_WINDOWS =
  "交易时段 08:45–15:30（周一至周五）与夜盘 20:45–02:35" +
  "（周日夜盘至周五夜盘）；其余时间走 7×24。";

/** Matches SIMNOW_ACCOUNT_NAME */
export const SIMNOW_ACCOUNT_NAME = "SimNow";

/**
 * Offline auto-front hint before /api/admin/connect-defaults returns.
 * Shape matches API `auto` (+ windows). Default env = session fronts.
 */
export const FALLBACK_AUTO = {
  交易服务器: SIMNOW_SESSION.td,
  行情服务器: SIMNOW_SESSION.md,
  env: "session",
  label: "交易时段",
  windows: AUTO_FRONT_WINDOWS,
};

/**
 * Offline connect form defaults (matches SIMNOW_CONNECT_DEFAULTS + account name).
 * Never put InvestorID / password here.
 */
export const FALLBACK_DEFAULTS = {
  account_name: SIMNOW_ACCOUNT_NAME,
  用户名: "",
  密码: "",
  经纪商代码: "9999",
  产品名称: "simnow_client_test",
  授权编码: "0000000000000000",
  柜台环境: "实盘",
};

/** Matches interface.note from connect-defaults API */
export const SIMNOW_INTERFACE_NOTE =
  "本机仅打包实盘 CTP API，SimNow 走生产前置。";
