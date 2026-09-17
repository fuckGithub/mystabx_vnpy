<template>
  <header class="topbar glass">
    <div class="topbar-left">
      <div class="brand">
        <span class="brand-icon">{{ brand.icon }}</span>
        <div class="brand-copy">
          <span class="brand-text">{{ brand.text }}</span>
          <span class="brand-en">{{ brand.en }}</span>
        </div>
      </div>
      <span class="topbar-divider" aria-hidden="true" />
      <div class="env-chip" :class="`env-chip--${selectedEnvKind}`">
        <div class="env-chip__cell">
          <span class="env-chip__caption">交易环境</span>
          <span class="env-chip__mode" :class="`env-chip__mode--${selectedEnvKind}`">
            {{ selectedEnvKind === "live" ? "实盘" : "仿真" }}
          </span>
        </div>

        <span class="env-chip__sep" aria-hidden="true" />

        <div class="env-chip__cell">
          <span class="env-chip__caption">通道</span>
          <el-select
            v-model="selectedGw"
            size="small"
            class="env-chip__select"
            popper-class="future-env-select-popper"
            :teleported="true"
            :suffix-icon="ArrowDown"
            placeholder="账户"
          >
            <el-option-group v-for="group in envOptionGroups" :key="group.key" :label="group.label">
              <el-option
                v-for="item in group.options"
                :key="item.key"
                :label="item.short"
                :value="item.key"
              >
                <div class="env-option">
                  <span class="env-option__dot" :class="`env-option__dot--${item.tone}`" />
                  <span class="env-option__body">
                    <span class="env-option__title">{{ item.short }}</span>
                    <span class="env-option__desc">{{ item.label }}</span>
                  </span>
                  <span class="env-option__tag" :class="`env-option__tag--${item.kind}`">
                    {{ item.kind === "live" ? "实盘" : "仿真" }}
                  </span>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </div>

        <span class="env-chip__sep" aria-hidden="true" />

        <div class="env-chip__statuses" role="status">
          <span class="env-chip__status" :class="`env-chip__status--${loginTone}`">
            <EnvWaveIndicator :tone="loginTone" :ripple="loginOk" size="sm" />
            账号 {{ loginText }}
          </span>
          <span class="env-chip__status" :class="`env-chip__status--${quoteTone}`">
            <EnvWaveIndicator :tone="quoteTone" :ripple="quoteOk" size="sm" />
            行情 {{ quoteText }}
          </span>
        </div>
      </div>
    </div>

    <div class="metrics-row">
      <div v-for="metric in metrics" :key="metric.label" class="metric" :class="metric.tone">
        <span class="metric-label">{{ metric.label }}</span>
        <strong class="metric-value">{{ metric.value }}</strong>
      </div>
    </div>

    <div class="topbar-right">
      <el-button
        size="small"
        class="pill action"
        :class="{ active: riskEnabled }"
        :type="riskEnabled ? 'primary' : 'default'"
        plain
        @click="riskEnabled = !riskEnabled"
      >
        风控 {{ riskEnabled ? "ON" : "OFF" }}
      </el-button>
      <el-button size="small" class="pill action danger" type="danger" plain :loading="flattening" @click="onFlatten">
        一键清仓
      </el-button>
      <span class="clock">{{ nowText }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { ArrowDown } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { http } from "@/api";
import { isSseOpen } from "@/sse";
import { useTradeStore } from "@/stores";
import { pnlClass, pickFunds, accountMetrics } from "../liveMap";
import EnvWaveIndicator from "./EnvWaveIndicator.vue";
import {
  isStatusOk,
  loginLabel,
  loginStatusOf,
  quoteLabel,
  quoteStatusOf,
  statusTone,
} from "@/gatewayStatus";

defineProps<{
  brand: { icon: string; text: string; en: string };
}>();

const trade = useTradeStore();
const riskEnabled = ref(true);
const flattening = ref(false);
const selectedGw = ref("");
const nowText = ref("");
let clockTimer: ReturnType<typeof setInterval> | null = null;

function gatewayKind(gw: Record<string, unknown>) {
  const blob = `${gw.gateway_name ?? ""} ${gw.account_name ?? ""}`.toLowerCase();
  if (blob.includes("live") || blob.includes("实盘")) return "live";
  return "simulation";
}

function gatewayTone(gw: Record<string, unknown>) {
  return statusTone(loginStatusOf(gw));
}

function preferGateway(current: Record<string, unknown> | undefined, next: Record<string, unknown>) {
  if (!current) return next;
  const curOk = isStatusOk(loginStatusOf(current));
  const nextOk = isStatusOk(loginStatusOf(next));
  if (nextOk && !curOk) return next;
  if (nextOk === curOk && Number(next.id || 0) < Number(current.id || 0)) return next;
  return current;
}

function gatewayDedupeKey(gw: Record<string, unknown>) {
  const connect = (gw.connect || {}) as Record<string, unknown>;
  const investor = String(connect["用户名"] || "").trim();
  if (investor) return `uid:${investor}`;
  const name = String(gw.account_name || "").trim() || String(gw.gateway_name || "");
  return `user:${gw.user_id ?? ""}:${name}`;
}

const envOptions = computed(() => {
  const unique = new Map<string, Record<string, unknown>>();
  const preferred = String(trade.activeGatewayName || "");
  for (const gw of trade.gateways) {
    const key = gatewayDedupeKey(gw);
    const existing = unique.get(key);
    if (preferred && String(gw.gateway_name || "") === preferred) {
      unique.set(key, gw);
      continue;
    }
    if (existing && preferred && String(existing.gateway_name || "") === preferred) continue;
    unique.set(key, preferGateway(existing, gw));
  }
  return [...unique.values()].map((gw) => {
    const key = String(gw.gateway_name || "");
    const short = String(gw.account_name || gw.gateway_name || "CTP");
    const env = String(gw.front_label || "");
    return {
      key,
      short,
      label: env ? `${key} · ${env}` : key || short,
      kind: gatewayKind(gw),
      tone: gatewayTone(gw),
    };
  });
});

const envOptionGroups = computed(() =>
  [
    { key: "simulation", label: "仿真" },
    { key: "live", label: "实盘" },
  ]
    .map((group) => ({
      ...group,
      options: envOptions.value.filter((item) => item.kind === group.key),
    }))
    .filter((group) => group.options.length > 0),
);

const selectedMeta = computed(() => envOptions.value.find((item) => item.key === selectedGw.value));
const selectedEnvKind = computed(() => selectedMeta.value?.kind ?? "simulation");
const selectedGwRow = computed(() => trade.gateways.find((gw) => String(gw.gateway_name) === selectedGw.value));
const loginState = computed(() => loginStatusOf(selectedGwRow.value));
const quoteState = computed(() => quoteStatusOf(selectedGwRow.value));
const loginOk = computed(() => isStatusOk(loginState.value));
const quoteOk = computed(() => isStatusOk(quoteState.value));
const loginTone = computed(() => statusTone(loginState.value));
const quoteTone = computed(() => statusTone(quoteState.value));
const loginText = computed(() => loginLabel(loginState.value));
const quoteText = computed(() => quoteLabel(quoteState.value));
const connected = computed(() => loginOk.value);

function formatMoney(value: number | null) {
  if (value === null || !Number.isFinite(value)) return "--";
  return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const fund = computed(() => {
  const rows = pickFunds(trade.funds, selectedGw.value, selectedGwRow.value);
  const positions = trade.positions.filter((pos) => !selectedGw.value || pos.gateway_name === selectedGw.value);
  return accountMetrics(rows[0], positions);
});

const metrics = computed(() => {
  const data = fund.value;
  const pnlTone = pnlClass(data.pnl);
  const ret = data.equity && data.pnl != null && data.equity !== 0 ? data.pnl / data.equity : null;
  return [
    { label: "账户总权益", value: formatMoney(data.equity) },
    { label: "可用资金", value: formatMoney(data.available) },
    { label: "持仓保证金", value: formatMoney(data.margin) },
    { label: "当日盈亏", value: formatMoney(data.pnl), tone: pnlTone },
    { label: "总收益率", value: ret === null ? "--" : `${(ret * 100).toFixed(2)}%`, tone: pnlTone },
  ];
});

watch(
  [envOptions, () => trade.activeGatewayName],
  ([list, preferred]) => {
    if (!list.length) return;
    const preferredKey = String(preferred || "");
    if (preferredKey && list.some((item) => item.key === preferredKey)) {
      selectedGw.value = preferredKey;
      return;
    }
    const connectedItem = list.find((item) => item.tone === "ok");
    if (!selectedGw.value || !list.some((item) => item.key === selectedGw.value)) {
      selectedGw.value = (connectedItem || list[0]).key;
      return;
    }
    const current = list.find((item) => item.key === selectedGw.value);
    if (current && current.tone !== "ok" && connectedItem) {
      selectedGw.value = connectedItem.key;
    }
  },
  { immediate: true },
);

watch(selectedGw, (name) => {
  if (name) trade.setActiveGateway(name);
});

let fundPoll: ReturnType<typeof setTimeout> | null = null;
let fundTries = 0;

async function syncChannelFunds() {
  if (!selectedGw.value || !connected.value) return;
  if (fund.value.equity != null) return;
  const row = selectedGwRow.value;
  if (!row?.id) return;
  try {
    const { data } = await http.post(`/api/gateways/${row.id}/query`);
    for (const acc of data?.accounts || []) trade.upsertFund(acc);
  } catch {
    /* SSE 会在账户回报到达后补齐 */
  }
}

watch(
  [connected, selectedGw],
  () => {
    if (fundPoll) {
      clearTimeout(fundPoll);
      fundPoll = null;
    }
    fundTries = 0;
    if (!connected.value || fund.value.equity != null) return;
    const tick = () => {
      if (!connected.value || fund.value.equity != null || fundTries >= 8) return;
      if (isSseOpen() && fundTries >= 2) return;
      fundTries += 1;
      void syncChannelFunds().then(() => {
        if (connected.value && fund.value.equity == null && fundTries < 8) {
          fundPoll = setTimeout(tick, 3000);
        }
      });
    };
    fundPoll = setTimeout(tick, isSseOpen() ? 2500 : 800);
  },
  { immediate: true },
);

async function onFlatten() {
  try {
    await ElMessageBox.confirm("将撤销可撤挂单。持仓平仓请到交易页手工处理。确认继续？", "一键清仓", {
      type: "warning",
      confirmButtonText: "确认撤单",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  flattening.value = true;
  try {
    const open = trade.orders.filter((row) => {
      if (selectedGw.value && row.gateway_name !== selectedGw.value) return false;
      const s = String(row.status || "");
      return s === "NOT_TRADED" || s === "PART_TRADED" || s === "SUBMITTING";
    });
    for (const row of open) {
      await http.post("/api/orders/cancel", { vt_orderid: row.vt_orderid, gateway_name: row.gateway_name });
    }
    ElMessage.success(`已发送撤单 ${open.length} 笔`);
    await trade.refresh();
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : "撤单失败");
  } finally {
    flattening.value = false;
  }
}

function tickClock() {
  nowText.value = new Date().toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

onMounted(() => {
  tickClock();
  clockTimer = setInterval(tickClock, 1000);
});
onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer);
  if (fundPoll) clearTimeout(fundPoll);
});
</script>

<style scoped lang="scss" src="@/styles/future-top-bar.scss"></style>

<style lang="scss" src="@/styles/future-top-bar-global.scss"></style>
