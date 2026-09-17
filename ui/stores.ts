import { defineStore } from "pinia";
import { computed, reactive, ref } from "vue";
import { clearTokens, fetchMe, getAccessToken, http, login as loginApi } from "./api";
import { mergeGatewayStatuses } from "./gatewayStatus";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Record<string, unknown> | null>(null);
  const ready = ref(false);

  const isLogin = computed(() => Boolean(user.value));
  const isAdmin = computed(() => Boolean(user.value?.is_admin));

  async function login(username: string, password: string) {
    const data = await loginApi(username, password);
    user.value = data.user;
    return data;
  }

  async function hydrate() {
    if (!getAccessToken()) {
      ready.value = true;
      return;
    }
    try {
      user.value = await fetchMe();
    } catch {
      clearTokens();
      user.value = null;
    } finally {
      ready.value = true;
    }
  }

  function logout() {
    clearTokens();
    user.value = null;
  }

  return { user, ready, isLogin, isAdmin, login, hydrate, logout };
});

function contractTickKey(tick: Record<string, unknown>): string {
  return `${String(tick.exchange || "").toUpperCase()}.${String(tick.symbol || "").toUpperCase()}`;
}

/** Keep distinct last_prices; datetime-only keys collapse a whole session to one snapshot. */
function tickSeriesId(tick: Record<string, unknown>): string {
  return `${tick.datetime ?? ""}|${tick.last_price ?? ""}|${tick.volume ?? ""}|${tick.last_volume ?? ""}`;
}

/**
 * SimNow sometimes freezes tick.datetime (or stamps a prior calendar day) while
 * last_price keeps moving. Bucketing by that stamp yields one minute → a flat
 * 分时 line. For live WS/OMS upserts, re-stamp when the exchange clock lags.
 */
function withLiveTickStamp(tick: Record<string, unknown>): Record<string, unknown> {
  const raw = tick.datetime;
  if (raw == null || raw === "") {
    return { ...tick, datetime: new Date().toISOString() };
  }
  let ms = 0;
  if (typeof raw === "number") {
    ms = raw < 1e12 ? raw * 1000 : raw;
  } else {
    const text = String(raw).trim();
    if (/^\d+(\.\d+)?$/.test(text)) {
      const n = Number(text);
      ms = n < 1e12 ? n * 1000 : n;
    } else {
      const iso = text.includes("T") ? text : text.replace(" ", "T");
      const withTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}+08:00`;
      ms = Date.parse(withTz);
    }
  }
  if (!Number.isFinite(ms)) {
    return { ...tick, datetime: new Date().toISOString() };
  }
  const lagSec = (Date.now() - ms) / 1000;
  // >2 min behind (frozen / wrong day) or >1 min ahead (clock skew)
  if (lagSec > 120 || lagSec < -60) {
    return { ...tick, datetime: new Date().toISOString() };
  }
  return tick;
}

export type ClickHouseHealth = {
  ok: boolean;
  state: string;
  host: string;
  port: number;
  database: string;
  error: string;
};

export const useMarketStore = defineStore("market", () => {
  const ticks = reactive<Record<string, Record<string, unknown>>>({});
  const sessionTicks = reactive<Record<string, Record<string, unknown>[]>>({});
  const contracts = ref<Record<string, unknown>[]>([]);
  const subscribedKeys = ref<Record<string, true>>({});
  const subscriptions = ref<Record<string, unknown>[]>([]);
  const clickhouse = reactive<ClickHouseHealth>({
    ok: false,
    state: "",
    host: "",
    port: 0,
    database: "",
    error: "",
  });

  function applyClickhouse(
    data: { ok?: boolean; state?: string; host?: string; port?: number; database?: string; error?: string } | string,
  ) {
    if (typeof data === "string") {
      const state = data || "";
      clickhouse.state = state;
      clickhouse.ok = state === "ok";
      if (state === "ok") clickhouse.error = "";
      return;
    }
    if (data.ok === undefined && data.state === undefined) {
      return;
    }
    const state = String(data.state || (data.ok ? "ok" : "down"));
    clickhouse.ok = Boolean(data.ok ?? state === "ok");
    clickhouse.state = state;
    if (data.host) clickhouse.host = String(data.host);
    if (data.port) clickhouse.port = Number(data.port);
    if (data.database) clickhouse.database = String(data.database);
    clickhouse.error = data.error ? String(data.error) : "";
  }

  async function loadHealth() {
    try {
      const { data } = await http.get("/health");
      const ch = data?.clickhouse;
      if (ch && typeof ch === "object") applyClickhouse(ch);
      else if (typeof ch === "string" && ch) applyClickhouse(ch);
    } catch {
      applyClickhouse({ ok: false, state: "down" });
    }
    return clickhouse;
  }

  function appendSessionTick(tick: Record<string, unknown>) {
    const key = contractTickKey(tick);
    if (!key.startsWith(".") && key.includes(".")) {
      const prev = sessionTicks[key] ? [...sessionTicks[key]] : [];
      const seen = new Set<string>();
      const list: Record<string, unknown>[] = [];
      for (const row of prev) {
        const id = tickSeriesId(row);
        if (seen.has(id)) continue;
        seen.add(id);
        list.push(row);
      }
      const id = tickSeriesId(tick);
      const last = list[list.length - 1];
      if (last && tickSeriesId(last) === id) {
        list[list.length - 1] = tick;
      } else if (!seen.has(id)) {
        list.push(tick);
        seen.add(id);
      }
      if (list.length > 80_000) list.splice(0, list.length - 80_000);
      sessionTicks[key] = list;
    }
  }

  function markSubscribed(symbol: string, exchange: string) {
    const key = `${String(exchange || "").toUpperCase()}.${String(symbol || "").toUpperCase()}`;
    if (!key.includes(".") || key.startsWith(".") || key.endsWith(".")) return;
    if (subscribedKeys.value[key]) return;
    subscribedKeys.value = { ...subscribedKeys.value, [key]: true };
  }

  function unmarkSubscribed(symbol: string, exchange: string) {
    const key = `${String(exchange || "").toUpperCase()}.${String(symbol || "").toUpperCase()}`;
    if (!subscribedKeys.value[key]) return;
    const next = { ...subscribedKeys.value };
    delete next[key];
    subscribedKeys.value = next;
  }

  /** Tick 入账不得视为订阅：仅显式 subscribeContract（或退订对称清理）改 subscribedKeys。 */
  function upsertTick(tick: Record<string, unknown>) {
    const live = withLiveTickStamp(tick);
    const key = `${live.exchange}.${live.symbol}.${live.gateway_name}`;
    ticks[key] = live;
    appendSessionTick(live);
  }

  function latestTick(symbol: string, exchange: string): Record<string, unknown> | undefined {
    const want = `${exchange.toUpperCase()}.${symbol.toUpperCase()}`;
    return Object.values(ticks).find((tick) => contractTickKey(tick) === want);
  }

  function replaceSessionTicks(symbol: string, exchange: string, rows: Record<string, unknown>[]) {
    const key = `${exchange.toUpperCase()}.${symbol.toUpperCase()}`;
    const merged = new Map<string, Record<string, unknown>>();
    for (const row of [...(sessionTicks[key] || []), ...rows]) {
      const live = withLiveTickStamp(row);
      merged.set(tickSeriesId(live), live);
    }
    const sorted = [...merged.values()].sort((a, b) =>
      String(a.datetime || "").localeCompare(String(b.datetime || "")),
    );
    sessionTicks[key] = sorted;
    const last = sorted[sorted.length - 1];
    if (last) {
      const stamped = withLiveTickStamp(last);
      const tickKey = `${stamped.exchange}.${stamped.symbol}.${stamped.gateway_name}`;
      ticks[tickKey] = stamped;
    }
  }

  function applySubscriptions(rows: Record<string, unknown>[]) {
    subscriptions.value = rows;
    const next: Record<string, true> = {};
    for (const row of rows) {
      const key = `${String(row.exchange || "").toUpperCase()}.${String(row.symbol || "").toUpperCase()}`;
      if (!key.includes(".") || key.startsWith(".") || key.endsWith(".")) continue;
      next[key] = true;
    }
    subscribedKeys.value = next;
  }

  async function loadSubscriptions() {
    try {
      const { data } = await http.get("/api/market/subscriptions");
      applySubscriptions(Array.isArray(data) ? data : []);
    } catch {
      applySubscriptions([]);
    }
    return subscriptions.value;
  }

  async function loadContracts(q = "") {
    const { data } = await http.get("/api/contracts", { params: { q } });
    contracts.value = Array.isArray(data) ? data : [];
    return contracts.value;
  }

  async function loadTicks() {
    const { data } = await http.get("/api/ticks");
    for (const tick of data) upsertTick(tick);
    return data;
  }

  async function loadSessionTicks(symbol: string, exchange: string, tradeDate?: string) {
    const { data } = await http.get("/api/market/session-ticks", {
      params: { symbol, exchange, ...(tradeDate ? { trade_date: tradeDate } : {}) },
    });
    const rows = Array.isArray(data) ? data : Array.isArray(data?.ticks) ? data.ticks : [];
    const isCurrent = Array.isArray(data) ? true : Boolean(data?.is_current ?? !tradeDate);
    if (isCurrent) replaceSessionTicks(symbol, exchange, rows);
    if (data?.clickhouse) applyClickhouse(String(data.clickhouse));
    return {
      ticks: rows as Record<string, unknown>[],
      trade_date: String(data?.trade_date || tradeDate || ""),
      is_current: isCurrent,
      clickhouse: String(data?.clickhouse || ""),
    };
  }

  async function loadTradeDates(symbol: string, exchange: string) {
    const { data } = await http.get("/api/market/trade-dates", { params: { symbol, exchange } });
    if (data?.clickhouse) applyClickhouse(String(data.clickhouse));
    return data as {
      current: string;
      clickhouse: string;
      dates: { date: string; is_current: boolean; has_data: boolean }[];
    };
  }

  async function subscribeContract(gatewayName: string, symbol: string, exchange: string) {
    await http.post("/api/market/subscribe", {
      gateway_name: gatewayName,
      symbol,
      exchange,
    });
    markSubscribed(symbol, exchange);
    void loadSubscriptions();
  }

  async function unsubscribeContract(gatewayName: string, symbol: string, exchange: string) {
    await http.post("/api/market/unsubscribe", {
      gateway_name: gatewayName,
      symbol,
      exchange,
    });
    unmarkSubscribed(symbol, exchange);
    void loadSubscriptions();
  }

  return {
    ticks,
    sessionTicks,
    contracts,
    subscriptions,
    subscribedKeys,
    clickhouse,
    applyClickhouse,
    upsertTick,
    markSubscribed,
    unmarkSubscribed,
    applySubscriptions,
    latestTick,
    loadHealth,
    loadContracts,
    loadSubscriptions,
    loadTicks,
    loadSessionTicks,
    loadTradeDates,
    subscribeContract,
    unsubscribeContract,
  };
});

export const useTradeStore = defineStore("trade", () => {
  const orders = ref<Record<string, unknown>[]>([]);
  const trades = ref<Record<string, unknown>[]>([]);
  const positions = ref<Record<string, unknown>[]>([]);
  const funds = ref<Record<string, unknown>[]>([]);
  const gateways = ref<Record<string, unknown>[]>([]);
  const activeGatewayName = ref("");

  function upsertBy<T extends Record<string, unknown>>(list: T[], item: T, key: string) {
    const index = list.findIndex((row) => row[key] === item[key] && row.gateway_name === item.gateway_name);
    if (index >= 0) list[index] = item;
    else list.unshift(item);
  }

  function upsertFund(item: Record<string, unknown>) {
    upsertBy(funds.value, item, "accountid");
  }

  function setActiveGateway(name: string) {
    if (name) activeGatewayName.value = name;
  }

  function upsertGateway(data: Record<string, unknown>) {
    const name = String(data.gateway_name || "");
    if (!name) return false;
    const index = gateways.value.findIndex((row) => String(row.gateway_name) === name);
    const prev = index >= 0 ? gateways.value[index] : undefined;
    const statuses = mergeGatewayStatuses(prev, data);
    if (index >= 0) {
      gateways.value[index] = {
        ...prev,
        ...data,
        ...statuses,
        gateway_name: name,
      };
      return true;
    }
    gateways.value = [
      {
        gateway_name: name,
        account_name: data.account_name || name,
        ...data,
        ...statuses,
      },
      ...gateways.value,
    ];
    return false;
  }

  async function refresh() {
    const [o, t, p, f, g] = await Promise.all([
      http.get("/api/orders"),
      http.get("/api/trades"),
      http.get("/api/positions"),
      http.get("/api/accounts"),
      http.get("/api/gateways"),
    ]);
    orders.value = o.data;
    trades.value = t.data;
    positions.value = p.data;
    const nextFunds = Array.isArray(f.data) ? f.data : [];
    // Empty GET must not wipe a later WS/query snapshot (connect race).
    funds.value = nextFunds.length ? nextFunds : funds.value;
    const rows = Array.isArray(g.data) ? g.data : [];
    gateways.value = rows.map((row: Record<string, unknown>) => ({
      ...row,
      ...mergeGatewayStatuses(undefined, row),
    }));
  }

  return {
    orders,
    trades,
    positions,
    funds,
    gateways,
    activeGatewayName,
    upsertBy,
    upsertFund,
    upsertGateway,
    setActiveGateway,
    refresh,
  };
});

export const useStrategyStore = defineStore("strategy", () => {
  const instances = ref<Record<string, unknown>[]>([]);
  const stopOrders = ref<Record<string, unknown>[]>([]);
  const logs = ref<Record<string, unknown>[]>([]);
  const backtestLogs = ref<Record<string, unknown>[]>([]);

  function upsertStrategy(item: Record<string, unknown>) {
    const name = String(item.strategy_name || "");
    if (!name) return;
    const index = instances.value.findIndex((row) => String(row.strategy_name) === name);
    if (index >= 0) instances.value[index] = { ...instances.value[index], ...item };
    else instances.value = [item, ...instances.value];
  }

  function upsertStopOrder(item: Record<string, unknown>) {
    const id = String(item.stop_orderid || "");
    if (!id) return;
    const index = stopOrders.value.findIndex((row) => String(row.stop_orderid) === id);
    if (index >= 0) stopOrders.value[index] = item;
    else stopOrders.value = [item, ...stopOrders.value];
  }

  function upsertLog(item: Record<string, unknown>) {
    logs.value = [item, ...logs.value].slice(0, 500);
  }

  function upsertBacktestLog(item: Record<string, unknown>) {
    backtestLogs.value = [item, ...backtestLogs.value].slice(0, 500);
  }

  async function refresh() {
    const [i, s] = await Promise.all([http.get("/api/cta/instances"), http.get("/api/cta/stop-orders")]);
    instances.value = Array.isArray(i.data) ? i.data : [];
    stopOrders.value = Array.isArray(s.data) ? s.data : [];
  }

  return {
    instances,
    stopOrders,
    logs,
    backtestLogs,
    upsertStrategy,
    upsertStopOrder,
    upsertLog,
    upsertBacktestLog,
    refresh,
  };
});
