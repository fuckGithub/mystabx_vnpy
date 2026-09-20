<template>
  <div class="equilibrix-dashboard market-terminal">
    <p v-if="chStatusText" class="ch-status" :class="{ down: !market.clickhouse.ok }">{{ chStatusText }}</p>

    <div v-if="isLiveQuotes && !listContracts.length" class="market-empty">
      <h3 class="market-empty__title">暂无已订阅合约</h3>
      <p class="market-empty__desc">
        实时行情只展示已订阅合约的盘口与分时。请先到行情中心浏览全部合约并订阅。
      </p>
      <el-button type="primary" @click="goQuotesCenter">去行情中心订阅</el-button>
    </div>

    <div v-else class="market-grid">
      <ContractListPanel
        :contracts="listContracts"
        :ticks="market.ticks"
        :selected-key="selectedKey"
        :subscribed-keys="market.subscribedKeys"
        :variant="isLiveQuotes ? 'live' : 'center'"
        :allow-subscribe="!isLiveQuotes"
        :allow-unsubscribe="!isLiveQuotes"
        :empty-text="listEmptyText"
        @select="onPick"
        @search="onSearch"
        @subscribe="onSubscribe"
        @unsubscribe="onUnsubscribe"
      />
      <QuoteChart
        v-model:period="period"
        v-model:trade-date="tradeDate"
        v-model:day-span="daySpan"
        :heading="chartHeading"
        :timeshare="timesharePoints"
        :bars="bars"
        :empty-hint="emptyHint"
        :pre-close="preClose"
        :trade-dates="tradeDates"
        :live="viewingCurrent"
        :session-hint="sessionCaption"
        :marks="chartMarks"
      />
      <QuoteTape :contract="selected" :tick="selectedTick" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useMarketStore, useTradeStore } from "@/stores";
import { finitePrice, instrumentLabel } from "../workbench/liveMap";
import ContractListPanel from "./components/ContractListPanel.vue";
import QuoteChart from "./components/QuoteChart.vue";
import QuoteTape from "./components/QuoteTape.vue";
import { contractKey, exchangeLabel, type ContractRow } from "./contracts";
import { fetchHistoryBars, type ChartPeriod, type HistoryBar } from "./history";
import {
  aggregateTimeshare,
  currentTradeDate,
  focusLiveTimeshare,
  recentTradeDates,
  sessionHint,
  sliceHalfDay,
  stitchTimeshareDays,
  timeshareTradeMarks,
  type TimesharePoint,
  type TimeshareSpan,
} from "./timeshare";
import type { TradeDateOption } from "./components/QuoteChart.vue";

const route = useRoute();
const router = useRouter();
const market = useMarketStore();
const trade = useTradeStore();

const selected = ref<ContractRow | null>(null);
const period = ref<ChartPeriod>("timeshare");
const daySpan = ref<TimeshareSpan>("1");
const bars = ref<HistoryBar[]>([]);
const barsLoading = ref(false);
const barsHint = ref("");
const sessionLoading = ref(false);
const tradeDate = ref("");
const tradeDates = ref<TradeDateOption[]>([]);
const loadedTicks = ref<Record<string, unknown>[]>([]);
const ticksByDate = ref<Record<string, Record<string, unknown>[]>>({});
const historyKey = ref("");

const section = computed(() => String(route.params.section || "ticks"));
/** 实时行情：仅已订阅；行情中心：全市场 */
const isLiveQuotes = computed(() => section.value === "ticks");

const allContracts = computed(() => market.contracts as ContractRow[]);
const listContracts = computed(() => {
  if (!isLiveQuotes.value) return allContracts.value;
  const byKey = new Map<string, ContractRow>();
  for (const row of allContracts.value) {
    const key = contractKey(row);
    if (key && market.subscribedKeys[key]) byKey.set(key, row);
  }
  // Restored MySQL subscription rows must appear even before OMS contract query returns.
  for (const sub of market.subscriptions) {
    const row = sub as ContractRow;
    const key = contractKey(row);
    if (!key || byKey.has(key)) continue;
    byKey.set(key, {
      symbol: row.symbol,
      exchange: row.exchange,
      name: row.name || "",
      gateway_name: row.gateway_name,
      vt_symbol: row.vt_symbol || `${row.symbol}.${row.exchange}`,
    });
  }
  return [...byKey.values()];
});

const listEmptyText = computed(() =>
  isLiveQuotes.value
    ? "暂无已订阅合约。请到行情中心订阅后再回来查看。"
    : "暂无合约。请先连接行情通道，合约查询成功后将按交易所 / 品种列出。",
);

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

/** Cap client-side tapes so live WS + history cannot re-inflate to 10k+ rows. */
function downsampleToMinute(ticks: Record<string, unknown>[]): Record<string, unknown>[] {
  if (ticks.length <= 1500) return ticks;
  const buckets = new Map<string, Record<string, unknown>>();
  for (const row of ticks) {
    const raw = String(row.datetime || "");
    const key = raw.length >= 16 ? raw.slice(0, 16) : raw || tickSeriesId(row);
    const prev = buckets.get(key);
    if (!prev) {
      buckets.set(key, { ...row, last_volume: 0 });
      continue;
    }
    const next = { ...row, last_volume: 0 };
    const prevVol = Number(prev.volume);
    const nextVol = Number(next.volume);
    if (Number.isFinite(prevVol) && (!Number.isFinite(nextVol) || prevVol > nextVol)) {
      next.volume = prev.volume;
    }
    buckets.set(key, next);
  }
  return [...buckets.values()];
}

/** Session API (memory + ClickHouse) plus live WS — 今日 used to ignore CH and keep one snapshot. */
const liveTicks = computed(() => {
  const key = sessionKey.value;
  if (!key) return [];
  const book = Object.values(market.ticks).filter((row) => tickBookKey(row) === key);
  return mergeTickRows(loadedTicks.value, sessionRows.value, book);
});

function spanCount(span: TimeshareSpan): number {
  return span === "half" ? 1 : Number(span) || 1;
}

const spanDates = computed(() => {
  const n = spanCount(daySpan.value);
  const dates = tradeDates.value.map((d) => d.date);
  const start = dates.indexOf(tradeDate.value);
  const window = (start >= 0 ? dates.slice(start, start + n) : dates.slice(0, n)).filter(Boolean);
  return [...window].reverse();
});

function ticksForDate(date: string): Record<string, unknown>[] {
  const current = currentTradeDate(selectedExchange.value);
  if (date === current) {
    return downsampleToMinute(
      mergeTickRows(
        ticksByDate.value[date] || [],
        liveTicks.value,
        selectedTick.value ? [selectedTick.value] : [],
      ),
    );
  }
  if (date === tradeDate.value) return downsampleToMinute(mergeTickRows(ticksByDate.value[date] || [], loadedTicks.value));
  return downsampleToMinute(ticksByDate.value[date] || []);
}

const timesharePoints = computed<TimesharePoint[]>(() => {
  if (!selected.value) return [];
  const ex = selectedExchange.value;
  const days = spanDates.value.map((date) => ({
    date,
    points: aggregateTimeshare(ticksForDate(date), ex, {
      tradeDate: date,
      live: date === currentTradeDate(ex),
    }),
  }));
  const priced = days.filter((d) => d.points.some((p) => p.price != null));
  const stitched = stitchTimeshareDays(priced.length ? priced : days.slice(-1));
  const scoped = daySpan.value === "half" ? sliceHalfDay(stitched) : stitched;
  if (viewingCurrent.value && daySpan.value !== "half" && spanCount(daySpan.value) === 1) {
    return focusLiveTimeshare(scoped, ex);
  }
  return scoped;
});

const chartMarks = computed(() => {
  if (!selected.value) return [];
  return timeshareTradeMarks(
    timesharePoints.value,
    trade.trades,
    String(selected.value.symbol || ""),
    selectedExchange.value,
  );
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
    if (barsLoading.value) return "正在加载本地 K 线…";
    if (bars.value.length) return "";
    return barsHint.value || "本地暂无 K 线。请先订阅合约，等待 Tick 归集后再查看。";
  }
  if (sessionLoading.value && !hasTimesharePrice.value) {
    return viewingCurrent.value ? "正在加载分时 Tick…" : "正在从 ClickHouse 加载该交易日…";
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
  await Promise.allSettled([
    market.loadHealth(),
    market.loadContracts(),
    market.loadSubscriptions(),
    market.loadTicks(),
    trade.refresh(),
  ]);
  healthTimer = setInterval(() => {
    void market.loadHealth();
  }, 15_000);
  ensureSelectionInList();
});

onUnmounted(() => {
  if (healthTimer) clearInterval(healthTimer);
});

function goQuotesCenter() {
  void router.push("/market/quotes");
}

function ensureSelectionInList() {
  const list = listContracts.value;
  if (!list.length) {
    selected.value = null;
    return;
  }
  const key = selectedKey.value;
  if (key && list.some((row) => contractKey(row) === key)) return;
  void onPick(list[0]);
}

async function onSearch(keyword: string) {
  await market.loadContracts(keyword);
}

async function onPick(row: ContractRow) {
  void market.loadHealth();
  selected.value = row;
  period.value = "timeshare";
  loadedTicks.value = [];
  ticksByDate.value = {};
  historyKey.value = "";
  const next = currentTradeDate(String(row.exchange || ""));
  tradeDate.value = next;
  await refreshTradeDates(row);
  // Always stay on the current 交易日 for live quotes. Falling back to a
  // historical day when today still has <2 ticks made the tape look live
  // while 分时 froze on a sparse/flat history series.
  await refreshSession(row, next);
  await ensureSpanTicks(row);
}

async function onSubscribe(row?: ContractRow) {
  const target = row || selected.value;
  if (!target) {
    ElMessage.warning("请先在列表中选择要订阅的合约");
    return;
  }
  await ensureSubscribed(target, true);
}

async function onUnsubscribe(row: ContractRow) {
  const live = market.latestTick(String(row.symbol || ""), String(row.exchange || ""));
  const gateway = String(
    row.gateway_name || live?.gateway_name || trade.activeGatewayName || trade.gateways[0]?.gateway_name || "",
  );
  if (!gateway) {
    ElMessage.warning("没有可用账户，无法退订行情");
    return;
  }
  try {
    await market.unsubscribeContract(gateway, String(row.symbol || ""), String(row.exchange || ""));
    ElMessage.success(`已退订 ${row.symbol}`);
    // 行情中心仍保留选中行；实时行情列表会丢掉该合约时再重选
    if (isLiveQuotes.value && selectedKey.value === contractKey(row)) ensureSelectionInList();
  } catch {
    ElMessage.error(`退订 ${row.symbol} 失败`);
  }
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
    const storedDate = result.trade_date || date;
    ticksByDate.value = { ...ticksByDate.value, [storedDate]: result.ticks || [] };
    historyKey.value = result.is_current
      ? ""
      : `${String(row.exchange || "").toUpperCase()}.${String(row.symbol || "").toUpperCase()}.${result.trade_date}`;
  } catch {
    /* keep WS ticks already in store */
  } finally {
    sessionLoading.value = false;
  }
}

async function ensureSpanTicks(row: ContractRow) {
  const extra = spanDates.value.filter((date) => date && date !== tradeDate.value);
  if (!extra.length) return;
  sessionLoading.value = true;
  try {
    const updates: Record<string, Record<string, unknown>[]> = { ...ticksByDate.value };
    await Promise.all(
      extra.map(async (date) => {
        try {
          const result = await market.loadSessionTicks(String(row.symbol || ""), String(row.exchange || ""), date);
          updates[result.trade_date || date] = result.ticks || [];
        } catch {
          updates[date] = updates[date] || [];
        }
      }),
    );
    ticksByDate.value = updates;
  } finally {
    sessionLoading.value = false;
  }
}

async function loadBars() {
  if (!selected.value || period.value === "timeshare") {
    bars.value = [];
    barsHint.value = "";
    return;
  }
  barsLoading.value = true;
  barsHint.value = "";
  try {
    const result = await fetchHistoryBars({
      symbol: String(selected.value.symbol || ""),
      exchange: String(selected.value.exchange || ""),
      interval: period.value,
      source: "local",
    });
    bars.value = result.bars || [];
    if (!bars.value.length) {
      barsHint.value =
        result.hint ||
        "本地暂无 K 线。请先订阅该合约，系统会从 ClickHouse Tick 归集到 MySQL 后供回放。";
      ElMessage.info(barsHint.value);
    }
  } catch {
    bars.value = [];
    barsHint.value = "加载本地 K 线失败，请确认后端与 MySQL 可用。";
    ElMessage.warning(barsHint.value);
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
  void refreshSession(selected.value, next).then(() => {
    if (selected.value) void ensureSpanTicks(selected.value);
  });
});

watch(daySpan, () => {
  if (selected.value) void ensureSpanTicks(selected.value);
});

watch(section, () => {
  ensureSelectionInList();
});

watch(
  () => Object.keys(market.subscribedKeys).sort().join("|"),
  () => {
    if (isLiveQuotes.value) ensureSelectionInList();
  },
);
</script>

<style src="@/styles/equilibrix-dashboard.css"></style>

<style scoped src="@/styles/market-view.css"></style>
