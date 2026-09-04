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

        <span class="env-chip__status" :class="`env-chip__status--${statusTone}`" role="status">
          <EnvWaveIndicator :tone="statusTone" :ripple="connected" size="sm" />
          {{ connected ? "已连接" : "未连接" }}
        </span>
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
import { useTradeStore } from "@/stores";
import { pnlClass } from "../liveMap";
import EnvWaveIndicator from "./EnvWaveIndicator.vue";

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
  return String(gw.conn_status) === "CONNECTED" ? "ok" : "muted";
}

const envOptions = computed(() =>
  trade.gateways.map((gw) => {
    const key = String(gw.gateway_name || "");
    const short = String(gw.account_name || gw.gateway_name || "CTP");
    return {
      key,
      short,
      label: key || short,
      kind: gatewayKind(gw),
      tone: gatewayTone(gw),
    };
  }),
);

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
const connected = computed(() => String(selectedGwRow.value?.conn_status) === "CONNECTED");
const statusTone = computed(() => (connected.value ? "ok" : "muted"));

function formatMoney(value: number | null) {
  if (value === null || !Number.isFinite(value)) return "--";
  return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const fund = computed(() => {
  const rows = trade.funds.filter((row) => !selectedGw.value || row.gateway_name === selectedGw.value);
  const first = rows[0];
  if (!first) return { equity: null as number | null, available: null as number | null, margin: null as number | null, pnl: null as number | null };
  const equity = Number(first.balance);
  const available = Number(first.available);
  const frozen = Number(first.frozen);
  const positions = trade.positions.filter((pos) => !selectedGw.value || pos.gateway_name === selectedGw.value);
  return {
    equity: Number.isFinite(equity) ? equity : null,
    available: Number.isFinite(available) ? available : null,
    margin: Number.isFinite(equity) && Number.isFinite(available) ? equity - available : Number.isFinite(frozen) ? frozen : null,
    pnl: positions.reduce((sum, pos) => sum + (Number(pos.pnl) || 0), 0),
  };
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
  () => trade.gateways,
  (list) => {
    if (!selectedGw.value && list[0]) selectedGw.value = String(list[0].gateway_name);
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
});
</script>

<style scoped lang="scss">
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px 16px;
  min-height: 68px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--dash-border);
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.topbar-divider {
  width: 1px;
  height: 24px;
  background: color-mix(in srgb, var(--dash-border) 90%, transparent);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  color: #fff;
  background: linear-gradient(145deg, #1d4ed8, #3b82f6);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  gap: 2px;
}

.brand-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--dash-heading);
  letter-spacing: 0.02em;
}

.brand-en {
  font-size: 10px;
  color: var(--dash-text-muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.env-chip {
  --env-accent: var(--primary);
  --env-accent-soft: color-mix(in srgb, var(--primary) 14%, transparent);
  --env-accent-border: color-mix(in srgb, var(--primary) 34%, var(--dash-border));
  --env-pill-height: 26px;
  --env-pill-radius: 7px;

  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 6px 0 10px;
  border-radius: 10px;
  border: 1px solid var(--env-accent-border);
  background: var(--dash-surface-soft);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;

  &--simulation {
    background: linear-gradient(
      105deg,
      color-mix(in srgb, var(--primary) 10%, var(--dash-surface-soft)) 0%,
      var(--dash-surface-soft) 42%
    );
  }

  &--live {
    --env-accent: var(--danger);
    --env-accent-soft: color-mix(in srgb, var(--danger) 14%, transparent);
    --env-accent-border: color-mix(in srgb, var(--danger) 34%, var(--dash-border));
    background: linear-gradient(
      105deg,
      color-mix(in srgb, var(--danger) 10%, var(--dash-surface-soft)) 0%,
      var(--dash-surface-soft) 42%
    );
  }

  &:focus-within {
    border-color: color-mix(in srgb, var(--env-accent) 55%, var(--dash-border));
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      0 0 0 2px color-mix(in srgb, var(--env-accent) 16%, transparent);
  }
}

.env-chip__cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  min-width: 0;
}

.env-chip__cell:first-child {
  padding-left: 0;
}

.env-chip__caption {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--dash-text-muted);
  white-space: nowrap;
}

.env-chip__mode,
.env-chip__status {
  display: inline-flex;
  align-items: center;
  height: var(--env-pill-height);
  padding: 0 9px;
  border-radius: var(--env-pill-radius);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1;
  white-space: nowrap;
}

.env-chip__mode {
  color: var(--env-accent);
  background: var(--env-accent-soft);
  border: 1px solid color-mix(in srgb, var(--env-accent) 26%, transparent);
}

.env-chip__sep {
  width: 1px;
  height: 18px;
  background: color-mix(in srgb, var(--dash-border) 88%, transparent);
  flex-shrink: 0;
}

.env-chip__select {
  width: auto;
  min-width: 92px;
}

.env-chip__select :deep(.el-select__wrapper) {
  min-height: var(--env-pill-height) !important;
  height: var(--env-pill-height);
  padding: 0 8px 0 9px;
  gap: 6px;
  background: var(--env-accent-soft) !important;
  border: 1px solid color-mix(in srgb, var(--env-accent) 26%, transparent) !important;
  box-shadow: none !important;
  border-radius: var(--env-pill-radius);
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease;
}

.env-chip__select :deep(.el-select__wrapper:hover),
.env-chip__select :deep(.el-select__wrapper.is-hovering) {
  background: color-mix(in srgb, var(--env-accent) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--env-accent) 38%, transparent) !important;
  box-shadow: none !important;
}

.env-chip__select :deep(.el-select__wrapper.is-focused) {
  background: color-mix(in srgb, var(--env-accent) 18%, transparent) !important;
  border-color: color-mix(in srgb, var(--env-accent) 48%, transparent) !important;
  box-shadow: none !important;
}

.env-chip__select :deep(.el-select__selection) {
  min-height: calc(var(--env-pill-height) - 2px);
  align-items: center;
}

.env-chip__select :deep(.el-select__selected-item) {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1;
  color: var(--dash-heading);
}

.env-chip__select :deep(.el-select__suffix) {
  display: flex;
  align-items: center;
  height: 100%;
}

.env-chip__select :deep(.el-select__caret),
.env-chip__select :deep(.el-icon) {
  font-size: 12px;
  width: 12px;
  height: 12px;
  color: color-mix(in srgb, var(--dash-text-muted) 80%, var(--env-accent));
  transition: color 0.18s ease, transform 0.18s ease;
}

.env-chip__select :deep(.el-select__wrapper:hover .el-select__caret),
.env-chip__select :deep(.el-select__wrapper:hover .el-icon),
.env-chip__select :deep(.el-select__wrapper.is-focused .el-select__caret),
.env-chip__select :deep(.el-select__wrapper.is-focused .el-icon) {
  color: var(--env-accent);
}

.env-chip__status {
  gap: 6px;
  margin-right: 2px;
  cursor: default;
  pointer-events: none;
  user-select: none;
  color: var(--dash-text-secondary);
  background: color-mix(in srgb, var(--dash-surface) 55%, transparent);
  border: 1px solid color-mix(in srgb, var(--dash-border) 70%, transparent);

  :deep(.env-wave) {
    color: currentColor;
  }

  &--ok {
    color: color-mix(in srgb, var(--success) 72%, #86efac);
    background: color-mix(in srgb, var(--success) 9%, var(--dash-surface-soft));
    border-color: color-mix(in srgb, var(--success) 16%, transparent);
  }

  &--bad {
    color: color-mix(in srgb, var(--danger) 78%, #fecaca);
    background: color-mix(in srgb, var(--danger) 9%, var(--dash-surface-soft));
    border-color: color-mix(in srgb, var(--danger) 16%, transparent);
  }

  &--warn {
    color: color-mix(in srgb, var(--warning) 78%, #fde68a);
    background: color-mix(in srgb, var(--warning) 9%, var(--dash-surface-soft));
    border-color: color-mix(in srgb, var(--warning) 16%, transparent);
  }

  &--muted {
    color: var(--dash-text-muted);
    background: color-mix(in srgb, var(--dash-surface) 60%, transparent);
    border-color: color-mix(in srgb, var(--dash-border) 80%, transparent);
  }
}

.metrics-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  flex-wrap: nowrap;
  min-width: 0;
  overflow-x: auto;
}

.metric {
  text-align: center;
  flex: 0 0 auto;
}

.metric-label {
  display: block;
  font-size: 11px;
  color: var(--dash-text-muted);
  margin-bottom: 2px;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--dash-heading);
  font-variant-numeric: tabular-nums;
}

.metric.up .metric-value {
  color: var(--price-up, var(--market-rise));
}

.metric.down .metric-value {
  color: var(--price-down, var(--market-fall));
}

.metric.flat .metric-value {
  color: var(--price-flat, var(--dash-text-muted));
}

.pill {
  border-radius: 8px;
  font-weight: 600;
}

.pill.action.active {
  border-color: var(--dash-border-accent);
  background: var(--dash-primary-soft);
  color: var(--primary);
}

.pill.action.danger {
  border-color: color-mix(in srgb, var(--danger) 35%, var(--dash-border));
  color: var(--danger);

  &:hover {
    background: color-mix(in srgb, var(--danger) 10%, transparent);
    border-color: color-mix(in srgb, var(--danger) 48%, var(--dash-border));
  }
}

.clock {
  font-size: 12px;
  color: var(--dash-text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  letter-spacing: 0.02em;
}

@media (max-width: 1080px) {
  .topbar {
    grid-template-columns: auto minmax(0, 1fr);
    grid-template-areas:
      "brand right"
      "metrics metrics";
  }

  .topbar-left {
    grid-area: brand;
  }

  .metrics-row {
    grid-area: metrics;
    justify-content: flex-start;
  }

  .topbar-right {
    grid-area: right;
    overflow-x: auto;
  }
}
</style>

<style lang="scss">
.future-env-select-popper {
  --primary: #1677ff;
  --success: #52c41a;
  --warning: #faad14;
  --danger: #ff4d4f;
  --dash-surface: #ffffff;
  --dash-border: #e2e8f0;
  --dash-text: #334155;
  --dash-text-muted: #64748b;
  --dash-heading: #0f172a;

  min-width: 268px !important;
  padding: 6px !important;
  border-radius: 10px !important;
  border: 1px solid var(--dash-border) !important;
  background: var(--dash-surface) !important;
  box-shadow:
    0 1px 0 rgba(15, 23, 42, 0.03) inset,
    0 12px 28px rgba(15, 23, 42, 0.12) !important;

  .el-select-dropdown__wrap {
    background: transparent;
  }

  .el-select-group__title {
    padding: 8px 10px 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--dash-text-muted);
  }

  .el-select-group__wrap:not(:last-of-type)::after {
    display: block;
    margin: 6px 10px 8px;
    border-top: 1px solid var(--dash-border);
    content: "";
  }

  .el-select-dropdown__item {
    height: auto;
    min-height: 42px;
    padding: 8px 10px;
    line-height: 1.2;
    border-radius: 8px;
    margin: 2px 0;
    color: var(--dash-text);
  }

  .el-select-dropdown__item:hover,
  .el-select-dropdown__item.hover {
    background: color-mix(in srgb, var(--primary) 10%, transparent) !important;
  }

  .el-select-dropdown__item.is-selected {
    font-weight: 600;
    background: color-mix(in srgb, var(--primary) 14%, transparent) !important;
    color: var(--dash-heading);
  }

  .el-select-dropdown__item.is-disabled {
    opacity: 0.5;
  }
}

html.dark .future-env-select-popper,
[data-theme="dark"] .future-env-select-popper {
  --primary: #60a5fa;
  --success: #4ade80;
  --warning: #fbbf24;
  --danger: #f87171;
  --dash-surface: #121a27;
  --dash-border: rgba(148, 163, 184, 0.14);
  --dash-text: #e2e8f0;
  --dash-text-muted: #94a3b8;
  --dash-heading: #f8fafc;

  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.04) inset,
    0 16px 36px rgba(0, 0, 0, 0.38) !important;
}

.env-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;

  &__dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 18%, transparent);

    &--ok {
      background: var(--success, #4ade80);
      color: var(--success, #4ade80);
    }

    &--bad {
      background: var(--danger, #f87171);
      color: var(--danger, #f87171);
    }

    &--warn {
      background: var(--warning, #fbbf24);
      color: var(--warning, #fbbf24);
    }

    &--muted {
      background: var(--dash-text-muted, #94a3b8);
      color: var(--dash-text-muted, #94a3b8);
      box-shadow: none;
    }
  }

  &__body {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  &__title {
    font-size: 13px;
    font-weight: 600;
    color: var(--dash-heading, var(--el-text-color-primary));
  }

  &__desc {
    font-size: 11px;
    color: var(--dash-text-muted, var(--el-text-color-secondary));
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__tag {
    flex-shrink: 0;
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;

    &--simulation {
      color: var(--primary, #60a5fa);
      background: color-mix(in srgb, var(--primary, #60a5fa) 14%, transparent);
    }

    &--live {
      color: var(--danger, #f87171);
      background: color-mix(in srgb, var(--danger, #f87171) 14%, transparent);
    }
  }
}
</style>
