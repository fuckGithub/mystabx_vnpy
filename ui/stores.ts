import { defineStore } from "pinia";
import { computed, reactive, ref } from "vue";
import { clearTokens, fetchMe, getAccessToken, http, login as loginApi } from "./api";

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

export const useMarketStore = defineStore("market", () => {
  const ticks = reactive<Record<string, Record<string, unknown>>>({});
  const contracts = ref<Record<string, unknown>[]>([]);

  function upsertTick(tick: Record<string, unknown>) {
    const key = `${tick.exchange}.${tick.symbol}.${tick.gateway_name}`;
    ticks[key] = tick;
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

  return { ticks, contracts, upsertTick, loadContracts, loadTicks };
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
    const status = String(data.status ?? data.conn_status ?? "DISCONNECTED");
    const index = gateways.value.findIndex((row) => String(row.gateway_name) === name);
    if (index >= 0) {
      gateways.value[index] = {
        ...gateways.value[index],
        ...data,
        gateway_name: name,
        conn_status: status,
      };
      return true;
    }
    gateways.value = [
      {
        gateway_name: name,
        account_name: data.account_name || name,
        conn_status: status,
        ...data,
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
    funds.value = f.data;
    gateways.value = g.data;
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
