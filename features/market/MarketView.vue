<template>
  <div v-if="section === 'ticks'" class="page-shell">
    <div class="page-section">
      <h3 class="page-section-title">实时行情</h3>
      <p v-if="chStatusText" class="ch-status" :class="{ down: !market.clickhouse.ok }">{{ chStatusText }}</p>
      <el-table :data="tickRows" height="560">
        <el-table-column label="合约" min-width="140">
          <template #default="{ row }">
            <InstrumentCell :code="String(row.symbol || '')" :name="contractNameOf(market.contracts, String(row.symbol || ''), row.exchange) || row.name" />
          </template>
        </el-table-column>
        <el-table-column prop="last_price" label="最新" width="100" />
        <el-table-column prop="bid_price_1" label="买一" width="100" />
        <el-table-column prop="bid_volume_1" label="买量" width="80" />
        <el-table-column prop="ask_price_1" label="卖一" width="100" />
        <el-table-column prop="ask_volume_1" label="卖量" width="80" />
        <el-table-column prop="volume" label="成交量" />
        <el-table-column prop="gateway_name" label="账户" width="120" />
      </el-table>
    </div>
  </div>
  <div v-else class="equilibrix-dashboard market-terminal">
    <p v-if="chStatusText" class="ch-status" :class="{ down: !market.clickhouse.ok }">{{ chStatusText }}</p>
    <div class="market-grid">
      <ContractListPanel
        :contracts="market.contracts"
        :ticks="market.ticks"
        :selected-key="selectedKey"
        :subscribed-keys="market.subscribedKeys"
        @select="onPick"
        @search="onSearch"
        @subscribe="onSubscribe"
      />
      <QuoteChart
        v-model:period="period"
        v-model:trade-date="tradeDate"
        :heading="chartHeading"
        :timeshare="timesharePoints"
        :bars="bars"
        :empty-hint="emptyHint"
        :pre-close="preClose"
        :trade-dates="tradeDates"
        :live="viewingCurrent"
        :session-hint="sessionCaption"
      />
      <QuoteTape :contract="selected" :tick="selectedTick" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { useMarketStore, useTradeStore } from "@/stores";
import { contractNameOf, finitePrice, instrumentLabel } from "../workbench/liveMap";
import InstrumentCell from "@/components/InstrumentCell.vue";
import ContractListPanel from "./components/ContractListPanel.vue";
import QuoteChart from "./components/QuoteChart.vue";
import QuoteTape from "./components/QuoteTape.vue";
import { contractKey, exchangeLabel, type ContractRow } from "./contracts";
import { fetchHistoryBars, type ChartPeriod, type HistoryBar } from "./history";
import {
  aggregateTimeshare,
  currentTradeDate,
  recentTradeDates,
  sessionHint,
  type TimesharePoint,
} from "./timeshare";
import type { TradeDateOption } from "./components/QuoteChart.vue";

const route = useRoute();
const market = useMarketStore();
const trade = useTradeStore();

const selected = ref<ContractRow | null>(null);
const period = ref<ChartPeriod>("timeshare");
const bars = ref<HistoryBar[]>([]);
const barsLoading = ref(false);
const sessionLoading = ref(false);
const tradeDate = ref("");
const tradeDates = ref<TradeDateOption[]>([]);
const loadedTicks = ref<Record<string, unknown>[]>([]);
const historyKey = ref("");

const section = computed(() => String(route.params.section || "quotes"));
const tickRows = computed(() => Object.values(market.ticks));
const selectedKey = computed(() => contractKey(selected.value));

const selectedTick = computed(() => {
  if (!selected.value) return undefined;
  return market.latestTick(String(selected.value.symbol || ""), String(selected.value.exchange || ""));
});

const sessionKey = computed(() => selectedKey.value);
const selectedExchange = computed(() => String(selected.value?.exchange || ""));
const viewingCurrent = computed(() => {
  if (!tradeDate.value) return true;
  return tradeDate.value === currentTradeDate(selectedExchange.value);
});
const sessionCaption = computed(() => sessionHint(selectedExchange.value));
const sessionRows = computed(() => {
  const key = sessionKey.value;
  return key ? market.sessionTicks[key] || [] : [];
});

function tickBookKey(tick: Record<string, unknown>): string {
  return `${String(tick.exchange || "").toUpperCase()}.${String(tick.symbol || "").toUpperCase()}`;
}

function tickSeriesId(row: Record<string, unknown>): string {
  return `${row.datetime ?? ""}|${row.last_price ?? ""}|${row.volume ?? ""}|${row.last_volume ?? ""}`;
}

function mergeTickRows(...groups: Record<string, unknown>[][]): Record<string, unknown>[] {
  const merged = new Map<string, Record<string, unknown>>();
  for (const group of groups) {
    for (const row of group) {
      merged.set(tickSeriesId(row), row);
    }
  }
  return [...merged.values()];
}

function pricedTickCount(rows: Record<string, unknown>[]): number {
  return rows.filter((row) => finitePrice(row.last_price) != null).length;
}

/** Session API (memory + ClickHouse) plus live WS — 今日 used to ignore CH and keep one snapshot. */
const liveTicks = computed(() => {
  const key = sessionKey.value;
  if (!key) return [];
  const book = Object.values(market.ticks).filter((row) => tickBookKey(row) === key);
  return mergeTickRows(loadedTicks.value, sessionRows.value, book);
});

const timesharePoints = computed<TimesharePoint[]>(() => {
  if (!selected.value) return [];
  const ticks = viewingCurrent.value
    ? mergeTickRows(liveTicks.value, selectedTick.value ? [selectedTick.value] : [])
    : [...loadedTicks.value];
  return aggregateTimeshare(ticks, selectedExchange.value, {
    tradeDate: tradeDate.value || currentTradeDate(selectedExchange.value),
    live: viewingCurrent.value,
  });
});

const hasTimesharePrice = computed(() => timesharePoints.value.some((p) => p.price !== null));
const preClose = computed(() => finitePrice(selectedTick.value?.pre_close));

const chartHeading = computed(() => {
  if (!selected.value) return "选择合约查看分时";
  const code = String(selected.value.symbol || "");
  const label = instrumentLabel(code, selected.value.name, selectedTick.value?.name);
  return `${label}  ${exchangeLabel(selected.value.exchange)}`;
});

const emptyHint = computed(() => {
  if (!selected.value) return "点击左侧合约，默认打开当前交易时段分时图。";
  if (period.value !== "timeshare") {
    return barsLoading.value ? "正在加载模拟 K 线…" : bars.value.length ? "" : "暂无 K 线数据。";
  }
  if (sessionLoading.value && !hasTimesharePrice.value) {
    return viewingCurrent.value ? "正在订阅并等待 SimNow 分时 Tick…" : "正在从 ClickHouse 加载该交易日…";
  }
  if (!hasTimesharePrice.value) {
    if (!viewingCurrent.value) {
      return market.clickhouse.state === "down"
        ? "ClickHouse 未连接，历史交易日无法加载。今日分时仍可走内存实时。"
        : `${tradeDate.value} 暂无 Tick。连接行情后会写入本地 ClickHouse（保留 10 天）。`;
    }
    if (finitePrice(selectedTick.value?.last_price) != null) return "";
    return "暂无分时数据。请先连接行情通道并订阅该合约，分时由 SimNow 实时 Tick 聚合（非模拟）。";
  }
  return "";
});

const chStatusText = computed(() => {
  const ch = market.clickhouse;
  if (!ch.state) return "";
  const loc = ch.host ? `${ch.host}${ch.port ? `:${ch.port}` : ""}${ch.database ? ` / ${ch.database}` : ""}` : "";
  if (ch.ok) return `ClickHouse 可达${loc ? ` ${loc}` : ""}`;
  return `ClickHouse 不可达${loc ? ` ${loc}` : ""}（今日分时走内存，历史交易日不可查）`;
});

let healthTimer: ReturnType<typeof setInterval> | undefined;

onMounted(async () => {
  await Promise.allSettled([market.loadHealth(), market.loadContracts(), market.loadTicks(), trade.refresh()]);
  healthTimer = setInterval(() => {
    void market.loadHealth();
  }, 15_000);
});

onUnmounted(() => {
  if (healthTimer) clearInterval(healthTimer);
});

async function onSearch(keyword: string) {
  await market.loadContracts(keyword);
}

async function onPick(row: ContractRow) {
  void market.loadHealth();
  selected.value = row;
  period.value = "timeshare";
  loadedTicks.value = [];
  historyKey.value = "";
  const next = currentTradeDate(String(row.exchange || ""));
  tradeDate.value = next;
  await ensureSubscribed(row);
  await refreshTradeDates(row);
  await refreshSession(row, next);
  if (pricedTickCount(loadedTicks.value) < 2) {
    const fallback = tradeDates.value.find((d) => d.has_data && d.date !== next);
    if (fallback) {
      tradeDate.value = fallback.date;
      await refreshSession(row, fallback.date);
    }
  }
}

async function onSubscribe(row?: ContractRow) {
  const target = row || selected.value;
  if (!target) {
    ElMessage.warning("请先在列表中选择要订阅的合约");
    return;
  }
  await ensureSubscribed(target, true);
}

async function ensureSubscribed(row: ContractRow, notify = false) {
  const key = contractKey(row);
  const live = market.latestTick(String(row.symbol || ""), String(row.exchange || ""));
  const gateway = String(
    row.gateway_name || live?.gateway_name || trade.activeGatewayName || trade.gateways[0]?.gateway_name || "",
  );
  if (!gateway) {
    ElMessage.warning("没有可用账户，无法订阅行情");
    return;
  }
  if (market.subscribedKeys[key]) {
    if (notify) ElMessage.info("该合约已订阅");
    return;
  }
  try {
    await market.subscribeContract(gateway, String(row.symbol || ""), String(row.exchange || ""));
    if (notify) ElMessage.success(`已订阅 ${row.symbol}`);
  } catch {
    ElMessage.error(`订阅 ${row.symbol} 失败，请确认行情通道已连接`);
  }
  try {
    await market.loadTicks();
  } catch {
    /* latest OMS tick is optional; live WS still merges */
  }
}

async function refreshTradeDates(row: ContractRow) {
  const fallback = recentTradeDates(10, String(row.exchange || "")).map((date, i) => ({
    date,
    is_current: i === 0,
    has_data: i === 0,
  }));
  try {
    const data = await market.loadTradeDates(String(row.symbol || ""), String(row.exchange || ""));
    tradeDates.value = data.dates || fallback;
    if (!tradeDate.value && data.current) tradeDate.value = data.current;
  } catch {
    tradeDates.value = fallback;
  }
}

async function refreshSession(row: ContractRow, date = tradeDate.value) {
  sessionLoading.value = true;
  try {
    const result = await market.loadSessionTicks(String(row.symbol || ""), String(row.exchange || ""), date);
    loadedTicks.value = result.ticks || [];
    historyKey.value = result.is_current
      ? ""
      : `${String(row.exchange || "").toUpperCase()}.${String(row.symbol || "").toUpperCase()}.${result.trade_date}`;
  } catch {
    /* keep WS ticks already in store */
  } finally {
    sessionLoading.value = false;
  }
}

async function loadBars() {
  if (!selected.value || period.value === "timeshare") {
    bars.value = [];
    return;
  }
  barsLoading.value = true;
  try {
    const result = await fetchHistoryBars({
      symbol: String(selected.value.symbol || ""),
      exchange: String(selected.value.exchange || ""),
      interval: period.value,
    });
    bars.value = result.bars;
  } catch {
    bars.value = [];
    ElMessage.warning("K 线暂为模拟数据；RQData 尚未对接");
  } finally {
    barsLoading.value = false;
  }
}

watch(period, () => {
  void loadBars();
});

watch(selectedKey, () => {
  if (period.value !== "timeshare") void loadBars();
});

watch(tradeDate, (next, prev) => {
  if (!selected.value || !next || next === prev) return;
  void refreshSession(selected.value, next);
});
</script>

<style src="@/styles/equilibrix-dashboard.css"></style>

<style scoped>
.ch-status {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-color-success);
}
.ch-status.down {
  color: var(--el-color-warning);
}
.market-terminal {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 10px 12px;
  box-sizing: border-box;
}
.market-grid {
  display: grid;
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr) minmax(196px, 236px);
  gap: 8px;
  flex: 1;
  min-height: 0;
}
@media (max-width: 1100px) {
  .market-grid {
    grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
  }
  .market-grid > :last-child {
    grid-column: 1 / -1;
    height: auto;
  }
}
</style>
