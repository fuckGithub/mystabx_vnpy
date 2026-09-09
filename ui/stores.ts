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

export const useMarketStore = defineStore("market", () => {
  const ticks = reactive<Record<string, Record<string, unknown>>>({});
  const sessionTicks = reactive<Record<string, Record<string, unknown>[]>>({});
  const contracts = ref<Record<string, unknown>[]>([]);

  function appendSessionTick(tick: Record<string, unknown>) {
    const key = contractTickKey(tick);
    if (!key.startsWith(".") && key.includes(".")) {
      const cutoff = Date.now() - 20 * 3600 * 1000;
      const list = (sessionTicks[key] ? [...sessionTicks[key]] : []).filter((row) => {
        const raw = String(row.datetime || "");
        const ms = Date.parse(raw);
        return Number.isNaN(ms) || ms >= cutoff;
      });
      const dt = String(tick.datetime || "");
      const last = list[list.length - 1];
      if (last && String(last.datetime || "") === dt && last.last_price === tick.last_price) {
        list[list.length - 1] = tick;
      } else {
        list.push(tick);
      }
      if (list.length > 24_000) list.splice(0, list.length - 24_000);
      sessionTicks[key] = list;
    }
  }

  function upsertTick(tick: Record<string, unknown>) {
    const key = `${tick.exchange}.${tick.symbol}.${tick.gateway_name}`;
    ticks[key] = tick;
    appendSessionTick(tick);
  }

  function latestTick(symbol: string, exchange: string): Record<string, unknown> | undefined {
    const want = `${exchange.toUpperCase()}.${symbol.toUpperCase()}`;
    return Object.values(ticks).find((tick) => contractTickKey(tick) === want);
  }

  function replaceSessionTicks(symbol: string, exchange: string, rows: Record<string, unknown>[]) {
    const key = `${exchange.toUpperCase()}.${symbol.toUpperCase()}`;
    const merged = new Map<string, Record<string, unknown>>();
    for (const row of [...(sessionTicks[key] || []), ...rows]) {
      merged.set(String(row.datetime || `${row.last_price}:${row.volume}`), row);
    }
    const sorted = [...merged.values()].sort((a, b) =>
      String(a.datetime || "").localeCompare(String(b.datetime || "")),
    );
    sessionTicks[key] = sorted;
    const last = sorted[sorted.length - 1];
    if (last) {
      const tickKey = `${last.exchange}.${last.symbol}.${last.gateway_name}`;
      ticks[tickKey] = last;
    }
  }

  async function loadContracts(q = "") {
    const { data } = await http.get("/api/contracts", { params: { q } });
    contracts.value = data;
    return data;
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
    return {
      ticks: rows as Record<string, unknown>[],
      trade_date: String(data?.trade_date || tradeDate || ""),
      is_current: isCurrent,
      clickhouse: String(data?.clickhouse || ""),
    };
  }

  async function loadTradeDates(symbol: string, exchange: string) {
    const { data } = await http.get("/api/market/trade-dates", { params: { symbol, exchange } });
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
  }

  return {
    ticks,
    sessionTicks,
    contracts,
    upsertTick,
    latestTick,
    loadContracts,
    loadTicks,
    loadSessionTicks,
    loadTradeDates,
    subscribeContract,
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
