<template>
  <section class="chart-pane">
    <header class="chart-head">
      <div class="chart-title">
        <strong>{{ heading }}</strong>
        <span v-if="period === 'timeshare'" class="chart-src" :class="live ? 'live' : 'hist'">
          分时 · {{ live ? "SimNow 实时" : "历史交易日" }} · {{ sessionHint }}
        </span>
        <span v-else class="chart-src mock">{{ intervalLabel }} · 模拟K线（待对接 RQData）</span>
      </div>
      <div class="period-tabs">
        <button
          v-for="item in periods"
          :key="item.key"
          type="button"
          class="period-tab"
          :class="{ active: period === item.key }"
          @click="emit('update:period', item.key)"
        >
          {{ item.label }}
        </button>
      </div>
    </header>
    <div v-if="period === 'timeshare' && tradeDates.length" class="day-row">
      <button
        v-for="item in tradeDates"
        :key="item.date"
        type="button"
        class="day-tab"
        :class="{ active: tradeDate === item.date, dim: !item.has_data && !item.is_current }"
        @click="emit('update:tradeDate', item.date)"
      >
        {{ item.is_current ? "今日" : item.date.slice(5) }}
      </button>
    </div>
    <div class="chart-body">
      <div ref="el" class="chart-canvas" />
      <div v-if="emptyHint" class="chart-empty">{{ emptyHint }}</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { ChartPeriod, HistoryBar } from "../history";
import {
  timeshareAxisLabelText,
  timeshareAxisLabelVisible,
  timesharePriceRange,
  type TimesharePoint,
} from "../timeshare";

export type TradeDateOption = { date: string; is_current: boolean; has_data: boolean };

export type { ChartPeriod };

const periods: { key: ChartPeriod; label: string }[] = [
  { key: "timeshare", label: "分时" },
  { key: "1m", label: "1分" },
  { key: "5m", label: "5分" },
  { key: "15m", label: "15分" },
  { key: "30m", label: "30分" },
  { key: "60m", label: "60分" },
  { key: "1d", label: "日K" },
  { key: "1w", label: "周K" },
  { key: "1M", label: "月K" },
];

const props = defineProps<{
  period: ChartPeriod;
  heading: string;
  timeshare: TimesharePoint[];
  bars: HistoryBar[];
  emptyHint: string;
  preClose?: number | null;
  tradeDate?: string;
  tradeDates?: TradeDateOption[];
  live?: boolean;
  sessionHint?: string;
}>();

const emit = defineEmits<{
  "update:period": [value: ChartPeriod];
  "update:tradeDate": [value: string];
}>();

const tradeDates = computed(() => props.tradeDates || []);
const live = computed(() => props.live !== false);
const sessionHint = computed(() => props.sessionHint || "");

const el = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

const intervalLabel = computed(() => periods.find((p) => p.key === props.period)?.label || "");

function colors() {
  const style = el.value ? getComputedStyle(el.value) : getComputedStyle(document.documentElement);
  return {
    rise: style.getPropertyValue("--market-rise").trim() || "#ef5350",
    fall: style.getPropertyValue("--market-fall").trim() || "#26a69a",
    text: style.getPropertyValue("--dash-text-muted").trim() || "#64748b",
    line: style.getPropertyValue("--dash-border").trim() || "#e2e8f0",
    heading: style.getPropertyValue("--dash-heading").trim() || "#0f172a",
    avg: style.getPropertyValue("--primary").trim() || "#1677ff",
  };
}

function render() {
  if (!chart) return;
  const c = colors();
  if (props.period === "timeshare") {
    chart.setOption(timeshareOption(c), true);
    return;
  }
  chart.setOption(klineOption(c), true);
}

function timeshareOption(c: ReturnType<typeof colors>): echarts.EChartsOption {
  const labels = props.timeshare.map((p) => p.label);
  const prices = props.timeshare.map((p) => (p.session === "break" ? null : p.price));
  const avgs = props.timeshare.map((p) => (p.session === "break" ? null : p.avg));
  const vols = props.timeshare.map((p) => (p.session === "break" ? 0 : p.volume));
  const last = [...prices].reverse().find((v) => v !== null) ?? props.preClose ?? 0;
  const lastIdx = prices.reduce((acc, v, i) => (v != null ? i : acc), -1);
  const ref = props.preClose && props.preClose > 0 ? props.preClose : last;
  const yRange = timesharePriceRange(props.timeshare, props.preClose);
  const breakIdx = props.timeshare.findIndex((p) => p.session === "break");
  const nightEnd = breakIdx > 0 ? labels[breakIdx - 1] : "";
  const dayStart = breakIdx >= 0 && breakIdx + 1 < labels.length ? labels[breakIdx + 1] : "";
  const markArea =
    nightEnd && dayStart
      ? {
          silent: true,
          label: { show: false },
          data: [
            [
              { xAxis: labels[0], itemStyle: { color: "rgba(99, 102, 241, 0.06)" } },
              { xAxis: nightEnd },
            ],
            [
              { xAxis: dayStart, itemStyle: { color: "rgba(14, 165, 233, 0.05)" } },
              { xAxis: labels[labels.length - 1] },
            ],
          ],
        }
      : undefined;
  const sessionLine =
    breakIdx >= 0
      ? {
          silent: true,
          symbol: "none",
          lineStyle: { type: "solid", color: c.text, width: 1, opacity: 0.45 },
          label: { show: false },
          data: [{ xAxis: labels[breakIdx] }],
        }
      : undefined;
  return {
    animation: false,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      formatter: (items: unknown) => {
        const list = Array.isArray(items) ? items : [];
        const first = list[0] as { dataIndex?: number; axisValue?: string } | undefined;
        const idx = first?.dataIndex ?? 0;
        const pt = props.timeshare[idx];
        if (!pt || pt.session === "break") return "夜盘 / 日盘";
        const sess = pt.session === "night" ? "夜盘" : "日盘";
        const price = pt.price == null ? "—" : String(pt.price);
        const avg = pt.avg == null ? "—" : String(Number(pt.avg).toFixed(2));
        return `${sess} ${pt.label}<br/>现价 ${price}<br/>均价 ${avg}<br/>量 ${pt.volume}`;
      },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 48, right: 16, top: 16, height: "62%" },
      { left: 48, right: 16, top: "76%", height: "16%" },
    ],
    xAxis: [
      {
        type: "category",
        data: labels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: c.line } },
        axisLabel: {
          color: c.text,
          fontSize: 10,
          hideOverlap: true,
          interval: (i: number) => timeshareAxisLabelVisible(props.timeshare, i),
          formatter: (_value: string, i: number) => timeshareAxisLabelText(props.timeshare, i),
        },
        axisTick: { show: false },
      },
      {
        type: "category",
        gridIndex: 1,
        data: labels,
        boundaryGap: false,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: c.line } },
      },
    ],
    yAxis: [
      {
        scale: true,
        min: yRange.min,
        max: yRange.max,
        splitLine: { lineStyle: { color: c.line, type: "dashed" } },
        axisLabel: { color: c.text, fontSize: 10 },
      },
      {
        gridIndex: 1,
        splitLine: { show: false },
        axisLabel: { color: c.text, fontSize: 10 },
      },
    ],
    series: [
      {
        name: "现价",
        type: "line",
        data: prices,
        showSymbol: lastIdx >= 0,
        symbolSize: (_v: unknown, params: { dataIndex?: number }) =>
          params.dataIndex === lastIdx ? 7 : 0,
        connectNulls: true,
        lineStyle: { width: 1.4, color: last >= ref ? c.rise : c.fall },
        itemStyle: { color: last >= ref ? c.rise : c.fall },
        markArea,
        markLine: {
          silent: true,
          symbol: "none",
          data: [
            ...(ref
              ? [{ yAxis: ref, lineStyle: { type: "dashed", color: c.text, width: 1 }, label: { formatter: "昨收", color: c.text, fontSize: 10 } }]
              : []),
            ...(sessionLine ? sessionLine.data.map((d) => ({ ...d, lineStyle: sessionLine.lineStyle, label: sessionLine.label })) : []),
          ],
        },
      },
      {
        name: "均价",
        type: "line",
        data: avgs,
        showSymbol: false,
        connectNulls: true,
        lineStyle: { width: 1, color: c.avg, opacity: 0.75 },
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: vols,
        itemStyle: { color: c.avg },
      },
    ],
  };
}

function klineOption(c: ReturnType<typeof colors>): echarts.EChartsOption {
  const labels = props.bars.map((b) => {
    const raw = String(b.datetime || "");
    return raw.length >= 16 ? raw.slice(5, 16).replace("T", " ") : raw;
  });
  const ohlc = props.bars.map((b) => [b.open, b.close, b.low, b.high]);
  const vols = props.bars.map((b, i) => ({
    value: b.volume,
    itemStyle: { color: b.close >= (props.bars[i - 1]?.close ?? b.open) ? c.rise : c.fall },
  }));
  return {
    animation: false,
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 48, right: 16, top: 16, height: "62%" },
      { left: 48, right: 16, top: "76%", height: "16%" },
    ],
    xAxis: [
      {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: c.line } },
        axisLabel: { color: c.text, fontSize: 10 },
        axisTick: { show: false },
      },
      {
        type: "category",
        gridIndex: 1,
        data: labels,
        axisLabel: { show: false },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: c.line } },
      },
    ],
    yAxis: [
      {
        scale: true,
        splitLine: { lineStyle: { color: c.line, type: "dashed" } },
        axisLabel: { color: c.text, fontSize: 10 },
      },
      {
        gridIndex: 1,
        splitLine: { show: false },
        axisLabel: { color: c.text, fontSize: 10 },
      },
    ],
    series: [
      {
        type: "candlestick",
        data: ohlc,
        itemStyle: {
          color: c.rise,
          color0: c.fall,
          borderColor: c.rise,
          borderColor0: c.fall,
        },
      },
      {
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: vols,
      },
    ],
  };
}

onMounted(async () => {
  await nextTick();
  if (!el.value) return;
  chart = echarts.init(el.value);
  render();
  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
  chart = null;
});

watch(
  () => [props.period, props.timeshare, props.bars, props.preClose, props.tradeDate],
  () => render(),
  { deep: true },
);
</script>

<style scoped>
.chart-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: var(--dash-surface);
  border: 1px solid var(--dash-border);
  border-radius: var(--dash-card-radius, 8px);
  box-shadow: var(--dash-shadow);
}
.chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 10px 0;
}
.chart-title { min-width: 0; }
.chart-title strong {
  display: block;
  font-size: 14px;
  color: var(--dash-heading);
}
.chart-src {
  font-size: 10px;
  color: var(--dash-text-muted);
}
.chart-src.live { color: var(--success); }
.chart-src.hist { color: var(--dash-text-muted); }
.chart-src.mock { color: var(--warning); }
.period-tabs { display: flex; flex-wrap: wrap; gap: 4px; }
.day-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 10px 0;
}
.day-tab {
  padding: 2px 7px;
  border: 1px solid var(--dash-border);
  border-radius: 999px;
  background: var(--dash-pill-bg);
  color: var(--dash-text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.day-tab.active {
  border-color: var(--dash-border-accent);
  background: var(--dash-primary-soft);
  color: var(--primary);
}
.day-tab.dim { opacity: 0.55; }
.period-tab {
  padding: 3px 8px;
  border: 1px solid var(--dash-border);
  border-radius: 999px;
  background: var(--dash-pill-bg);
  color: var(--dash-text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.period-tab.active {
  border-color: var(--dash-border-accent);
  background: var(--dash-primary-soft);
  color: var(--primary);
}
.chart-body {
  position: relative;
  flex: 1;
  min-height: 0;
}
.chart-canvas { width: 100%; height: 100%; }
.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  font-size: 13px;
  line-height: 1.6;
  color: var(--dash-text-muted);
  pointer-events: none;
}
</style>
