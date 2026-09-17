<template>
  <section class="chart-pane">
    <header class="chart-toolbar">
      <nav class="period-tabs" aria-label="周期">
        <button
          v-for="item in mainPeriods"
          :key="item.key"
          type="button"
          class="period-tab"
          :class="{ active: period === item.key }"
          @click="emit('update:period', item.key)"
        >
          {{ item.label }}
        </button>
        <el-dropdown trigger="click" @command="onMorePeriod">
          <button type="button" class="period-tab more" :class="{ active: moreActive }">
            更多<span class="caret">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="item in morePeriods" :key="item.key" :command="item.key">
                {{ item.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button type="button" class="period-tab ghost" title="叠加对比将在后续版本提供" disabled>同列</button>
        <el-popover placement="bottom-end" :width="220" trigger="click">
          <template #reference>
            <button type="button" class="period-tab icon" title="图表设置">⚙</button>
          </template>
          <div class="chart-settings">
            <p>MACD 参数</p>
            <div class="setting-row">
              <label>DIFF</label>
              <el-input-number v-model="macdFast" size="small" :min="2" :max="40" />
            </div>
            <div class="setting-row">
              <label>DEA</label>
              <el-input-number v-model="macdSlow" size="small" :min="3" :max="60" />
            </div>
            <div class="setting-row">
              <label>MACD</label>
              <el-input-number v-model="macdSignal" size="small" :min="2" :max="30" />
            </div>
          </div>
        </el-popover>
      </nav>
      <div class="chart-meta">
        <strong>{{ heading }}</strong>
        <span v-if="period === 'timeshare'" class="chart-src" :class="live ? 'live' : 'hist'">
          {{ live ? "SimNow 实时" : "历史交易日" }} · {{ sessionHint }}
        </span>
        <span v-else class="chart-src mock">{{ intervalLabel }} · 模拟K线（待对接 RQData）</span>
      </div>
    </header>
    <div v-if="period === 'timeshare'" class="span-row">
      <el-select :model-value="daySpan" size="small" class="span-select" @update:model-value="onSpan">
        <el-option v-for="item in spanOptions" :key="item.key" :label="item.label" :value="item.key" />
      </el-select>
    </div>
    <div class="chart-body">
      <div class="pane-caption vol">
        <el-select v-model="overlayKind" size="small" class="overlay-select">
          <el-option label="持仓量" value="oi" />
          <el-option label="成交量" value="volume" />
        </el-select>
        <span>持仓量 <b>{{ oiText }}</b></span>
        <span>成交量 <b>{{ volText }}</b></span>
      </div>
      <div class="pane-caption macd">
        MACD({{ macdFast }},{{ macdSlow }},{{ macdSignal }})
        <small>{{ macdHint }}</small>
      </div>
      <div ref="el" class="chart-canvas" />
      <div v-if="emptyHint" class="chart-empty">{{ emptyHint }}</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { ChartPeriod, HistoryBar } from "../history";
import { computeMacd, lastMacdLabel } from "../macd";
import {
  lastOpenInterest,
  paddedPriceRange,
  sumVolume,
  timeshareAxisLabelText,
  timeshareAxisLabelVisible,
  timesharePriceRange,
  type ChartTradeMark,
  type TimesharePoint,
  type TimeshareSpan,
} from "../timeshare";

export type TradeDateOption = { date: string; is_current: boolean; has_data: boolean };

export type { ChartPeriod, TimeshareSpan };

const mainPeriods: { key: ChartPeriod; label: string }[] = [
  { key: "timeshare", label: "分时" },
  { key: "1d", label: "日K" },
  { key: "1m", label: "1分" },
  { key: "5m", label: "5分" },
  { key: "15m", label: "15分" },
];

const morePeriods: { key: ChartPeriod; label: string }[] = [
  { key: "30m", label: "30分" },
  { key: "60m", label: "60分" },
  { key: "1w", label: "周K" },
  { key: "1M", label: "月K" },
];

const spanOptions: { key: TimeshareSpan; label: string }[] = [
  { key: "half", label: "半日" },
  { key: "1", label: "当日" },
  { key: "2", label: "二日" },
  { key: "3", label: "三日" },
  { key: "4", label: "四日" },
  { key: "5", label: "五日" },
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
  daySpan?: TimeshareSpan;
  marks?: ChartTradeMark[];
}>();

const emit = defineEmits<{
  "update:period": [value: ChartPeriod];
  "update:tradeDate": [value: string];
  "update:daySpan": [value: TimeshareSpan];
}>();

const live = computed(() => props.live !== false);
const sessionHint = computed(() => props.sessionHint || "");
const daySpan = computed(() => props.daySpan || "1");
const marks = computed(() => props.marks || []);

const el = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

const overlayKind = ref<"oi" | "volume">("oi");
const macdFast = ref(12);
const macdSlow = ref(26);
const macdSignal = ref(9);

const moreActive = computed(() => morePeriods.some((p) => p.key === props.period));
const intervalLabel = computed(() => {
  const all = [...mainPeriods, ...morePeriods];
  return all.find((p) => p.key === props.period)?.label || "";
});

const oiText = computed(() => formatQty(lastOpenInterest(props.timeshare) ?? lastBarOi()));
const volText = computed(() => {
  if (props.period === "timeshare") return formatQty(sumVolume(props.timeshare));
  return formatQty(props.bars.reduce((acc, b) => acc + (Number(b.volume) || 0), 0));
});

const macdHint = computed(() => {
  const closes =
    props.period === "timeshare"
      ? props.timeshare.map((p) => (p.session === "break" ? null : p.price))
      : props.bars.map((b) => b.close);
  return lastMacdLabel(computeMacd(closes, macdFast.value, macdSlow.value, macdSignal.value));
});

function lastBarOi(): number | null {
  for (let i = props.bars.length - 1; i >= 0; i -= 1) {
    const n = Number(props.bars[i].open_interest);
    if (Number.isFinite(n) && n >= 0) return n;
  }
  return null;
}

function formatQty(n: number | null): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return String(Math.round(n));
}

function onMorePeriod(key: ChartPeriod) {
  emit("update:period", key);
}

function onSpan(value: string | number) {
  emit("update:daySpan", String(value) as TimeshareSpan);
}

function klinePriceRange(bars: HistoryBar[]) {
  const vals: number[] = [];
  for (const b of bars) {
    for (const v of [b.open, b.high, b.low, b.close]) {
      const n = Number(v);
      if (Number.isFinite(n) && n > 0) vals.push(n);
    }
  }
  return paddedPriceRange(vals);
}

function colors() {
  const style = el.value ? getComputedStyle(el.value) : getComputedStyle(document.documentElement);
  return {
    rise: style.getPropertyValue("--market-rise").trim() || "#ef5350",
    fall: style.getPropertyValue("--market-fall").trim() || "#26a69a",
    text: style.getPropertyValue("--dash-text-muted").trim() || "#64748b",
    line: style.getPropertyValue("--dash-border").trim() || "#e8edf2",
    heading: style.getPropertyValue("--dash-heading").trim() || "#0f172a",
    price: "#3b7ddd",
    avg: "#e67e22",
    oi: "#1f2937",
    dif: "#e67e22",
    dea: "#8b5cf6",
  };
}

let axisKey = "";

function chartAxisKey(): string {
  if (props.period !== "timeshare") {
    return `k:${props.period}:${props.bars.length}:${macdFast.value}:${macdSlow.value}:${macdSignal.value}:${overlayKind.value}`;
  }
  const ts = props.timeshare;
  return `t:${daySpan.value}:${props.tradeDate || ""}:${ts.length}:${ts[0]?.axisKey || ""}:${macdFast.value}:${overlayKind.value}`;
}

function render() {
  if (!chart) return;
  const c = colors();
  axisKey = chartAxisKey();
  // Always replace axes/series so OI/volume scales never merge onto the price pane.
  const opts = { notMerge: true as const, lazyUpdate: false as const };
  if (props.period === "timeshare") {
    chart.setOption(timeshareOption(c), opts);
    return;
  }
  chart.setOption(klineOption(c), opts);
}

/** Price / volume / MACD panes; mid band (≈52–62%) holds time labels + 持仓量 caption. */
const grids = [
  { left: 56, right: 56, top: 10, height: "42%" },
  { left: 56, right: 56, top: "62%", height: "12%" },
  { left: 56, right: 56, top: "80%", height: "14%" },
];

function stackedXAxis(labels: string[], formatter?: (value: string, i: number) => string, interval?: (i: number) => boolean) {
  const base = {
    type: "category" as const,
    data: labels,
    boundaryGap: false,
    axisTick: { show: false },
    axisLine: { lineStyle: { color: colors().line } },
    splitLine: { show: true, lineStyle: { color: colors().line, type: "solid" as const, opacity: 0.7 } },
  };
  // Time labels sit under the price pane (bottom of grid 0), above the 持仓量 caption — not on grid 1.
  const timeLabel = {
    show: true,
    color: colors().text,
    fontSize: 10,
    hideOverlap: true,
    margin: 6,
    interval: interval ?? "auto",
    formatter: formatter || ((v: string) => v),
  };
  return [
    { ...base, gridIndex: 0, position: "bottom" as const, axisLabel: timeLabel },
    { ...base, gridIndex: 1, axisLabel: { show: false } },
    { ...base, gridIndex: 2, axisLabel: { show: false } },
  ];
}

/** Keep price-pane series on price scale — reject OI/volume magnitude leaks. */
function clampPriceSeries(values: Array<number | null>, ref: number): Array<number | null> {
  const anchor = ref > 0 ? ref : [...values].reverse().find((v) => v != null && v > 0) || 0;
  if (!(anchor > 0)) return values.map(() => null);
  return values.map((v) => {
    if (v == null || !Number.isFinite(v) || v <= 0) return null;
    if (v > anchor * 20 || v < anchor * 0.05) return null;
    return v;
  });
}

function formatAxisPrice(v: number): string {
  if (!Number.isFinite(v)) return "";
  const abs = Math.abs(v);
  if (abs >= 1e4) return abs >= 1e8 ? `${(v / 1e8).toFixed(2)}亿` : String(Math.round(v));
  if (abs >= 100) return v.toFixed(0);
  if (abs >= 10) return v.toFixed(1);
  return v.toFixed(2);
}

function markSeries(labels: string[], c: ReturnType<typeof colors>): echarts.SeriesOption | null {
  if (!marks.value.length) return null;
  const colorOf = (label: string) => (label === "平" ? c.price : c.rise);
  return {
    name: "成交",
    type: "scatter",
    xAxisIndex: 0,
    yAxisIndex: 0,
    symbolSize: 1,
    data: marks.value.map((m) => ({
      value: [labels[m.index], m.price],
      name: m.label,
      itemStyle: { color: colorOf(m.label) },
      label: {
        show: true,
        formatter: m.label,
        color: "#fff",
        fontSize: 10,
        backgroundColor: colorOf(m.label),
        padding: [1, 4],
        borderRadius: 2,
        offset: [0, -10],
      },
    })),
    tooltip: { show: false },
    z: 8,
  };
}

function timeshareOption(c: ReturnType<typeof colors>): echarts.EChartsOption {
  const labels = props.timeshare.map((p) => p.axisKey);
  const rawPrices = props.timeshare.map((p) => (p.session === "break" ? null : p.price));
  const rawAvgs = props.timeshare.map((p) => (p.session === "break" ? null : p.avg));
  const last =
    [...rawPrices].reverse().find((v) => v !== null) ?? props.preClose ?? 0;
  const ref = props.preClose && props.preClose > 0 ? props.preClose : last;
  const prices = clampPriceSeries(rawPrices, ref || last);
  const avgs = clampPriceSeries(rawAvgs, ref || last);
  const vols = props.timeshare.map((p, i) => {
    const prev = [...prices].slice(0, i).reverse().find((v) => v != null);
    const px = prices[i];
    const up = px != null && prev != null ? px >= prev : true;
    return {
      value: p.session === "break" ? null : p.volume > 0 ? p.volume : null,
      itemStyle: { color: up ? c.rise : c.fall },
    };
  });
  const oi = props.timeshare.map((p) => (p.session === "break" ? null : p.openInterest));
  const overlay =
    overlayKind.value === "oi" ? oi : props.timeshare.map((p) => (p.session === "break" ? null : p.volume));
  const lastIdx = (() => {
    let volIdx = -1;
    let priceIdx = -1;
    for (let i = 0; i < prices.length; i += 1) {
      if (prices[i] != null) priceIdx = i;
      if ((props.timeshare[i]?.volume || 0) > 0) volIdx = i;
    }
    return priceIdx >= 0 ? priceIdx : volIdx;
  })();
  const yRange = timesharePriceRange(
    props.timeshare.map((p, i) => ({
      ...p,
      price: prices[i],
      avg: avgs[i],
    })),
  );
  const minP = yRange.min ?? (last > 0 ? last * 0.99 : 0);
  const maxP = yRange.max ?? (last > 0 ? last * 1.01 : 1);
  const minPct = ref ? ((minP - ref) / ref) * 100 : -1;
  const maxPct = ref ? ((maxP - ref) / ref) * 100 : 1;
  const macd = computeMacd(prices, macdFast.value, macdSlow.value, macdSignal.value);
  const scatter = markSeries(labels, c);
  return {
    animation: false,
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross", label: { show: false } },
      formatter: (items: unknown) => {
        const list = Array.isArray(items) ? items : [];
        const first = list[0] as { dataIndex?: number } | undefined;
        const idx = first?.dataIndex ?? 0;
        const pt = props.timeshare[idx];
        if (!pt || pt.session === "break") return "";
        const price = prices[idx] == null ? "—" : String(prices[idx]);
        const avg = avgs[idx] == null ? "—" : String(Number(avgs[idx]).toFixed(2));
        const pct =
          prices[idx] != null && ref ? `${(((prices[idx]! - ref) / ref) * 100).toFixed(2)}%` : "—";
        const oiVal = pt.openInterest == null ? "—" : formatQty(pt.openInterest);
        return `${pt.tradeDate} ${pt.label}<br/>现价 ${price}（${pct}）<br/>均价 ${avg}<br/>量 ${pt.volume}<br/>仓 ${oiVal}`;
      },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: grids,
    xAxis: stackedXAxis(
      labels,
      (_value: string, i: number) => timeshareAxisLabelText(props.timeshare, i),
      (i: number) => timeshareAxisLabelVisible(props.timeshare, i),
    ),
    yAxis: [
      {
        gridIndex: 0,
        position: "left",
        min: minP,
        max: maxP,
        scale: false,
        splitLine: { lineStyle: { color: c.line } },
        axisLabel: { color: c.text, fontSize: 10, formatter: formatAxisPrice },
      },
      {
        gridIndex: 0,
        position: "right",
        min: minPct,
        max: maxPct,
        scale: false,
        splitLine: { show: false },
        axisLabel: {
          color: c.text,
          fontSize: 10,
          formatter: (v: number) => `${v.toFixed(2)}%`,
        },
      },
      {
        gridIndex: 1,
        position: "left",
        scale: true,
        splitLine: { show: false },
        axisLabel: { show: false },
      },
      {
        gridIndex: 1,
        position: "right",
        scale: true,
        splitLine: { show: false },
        axisLabel: {
          color: c.text,
          fontSize: 10,
          formatter: (v: number) => formatQty(v),
        },
      },
      {
        gridIndex: 2,
        position: "right",
        scale: true,
        splitLine: { lineStyle: { color: c.line, type: "dashed" } },
        axisLabel: { color: c.text, fontSize: 10 },
      },
    ],
    series: [
      {
        name: "现价",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: prices,
        showSymbol: lastIdx >= 0,
        symbolSize: (_v: unknown, params: { dataIndex?: number }) => (params.dataIndex === lastIdx ? 6 : 0),
        connectNulls: false,
        lineStyle: { width: 1.4, color: c.price },
        itemStyle: { color: c.price },
        z: 3,
        markLine: ref
          ? {
              silent: true,
              symbol: "none",
              data: [{ yAxis: ref, lineStyle: { type: "dashed", color: c.text, width: 1 } }],
              label: { show: false },
            }
          : undefined,
      },
      {
        name: "均价",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: avgs,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.1, color: c.avg },
        z: 2,
      },
      {
        name: "涨跌幅",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 1,
        data: prices.map((p) => (p == null || !ref ? null : ((p - ref) / ref) * 100)),
        showSymbol: false,
        lineStyle: { width: 0, opacity: 0 },
        tooltip: { show: false },
        silent: true,
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: vols,
        barWidth: "60%",
      },
      {
        name: overlayKind.value === "oi" ? "持仓量" : "成交量线",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 3,
        data: overlay,
        showSymbol: false,
        connectNulls: true,
        lineStyle: { width: 1.1, color: c.oi },
      },
      {
        name: "MACD",
        type: "bar",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => ({
          value: p.hist,
          itemStyle: { color: (p.hist || 0) >= 0 ? c.rise : c.fall },
        })),
        barWidth: "50%",
      },
      {
        name: "DIFF",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => p.dif),
        showSymbol: false,
        lineStyle: { width: 1, color: c.dif },
      },
      {
        name: "DEA",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => p.dea),
        showSymbol: false,
        lineStyle: { width: 1, color: c.dea },
      },
      ...(scatter ? [scatter] : []),
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
    value: b.volume > 0 ? b.volume : null,
    itemStyle: { color: b.close >= (props.bars[i - 1]?.close ?? b.open) ? c.rise : c.fall },
  }));
  const oi = props.bars.map((b) => b.open_interest ?? null);
  const overlay = overlayKind.value === "oi" ? oi : props.bars.map((b) => b.volume);
  const yRange = klinePriceRange(props.bars);
  const closes = props.bars.map((b) => b.close);
  const macd = computeMacd(closes, macdFast.value, macdSlow.value, macdSignal.value);
  const last = closes[closes.length - 1] || 0;
  const ref = props.preClose && props.preClose > 0 ? props.preClose : last;
  const minP = yRange.min ?? (last > 0 ? last * 0.99 : 0);
  const maxP = yRange.max ?? (last > 0 ? last * 1.01 : 1);
  const minPct = ref ? ((minP - ref) / ref) * 100 : -1;
  const maxPct = ref ? ((maxP - ref) / ref) * 100 : 1;
  return {
    animation: false,
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", axisPointer: { type: "cross", label: { show: false } } },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: grids,
    xAxis: stackedXAxis(labels),
    yAxis: [
      {
        gridIndex: 0,
        position: "left",
        min: minP,
        max: maxP,
        scale: false,
        splitLine: { lineStyle: { color: c.line } },
        axisLabel: { color: c.text, fontSize: 10, formatter: formatAxisPrice },
      },
      {
        gridIndex: 0,
        position: "right",
        min: minPct,
        max: maxPct,
        scale: false,
        splitLine: { show: false },
        axisLabel: { color: c.text, fontSize: 10, formatter: (v: number) => `${v.toFixed(2)}%` },
      },
      { gridIndex: 1, position: "left", scale: true, splitLine: { show: false }, axisLabel: { show: false } },
      {
        gridIndex: 1,
        position: "right",
        scale: true,
        splitLine: { show: false },
        axisLabel: { color: c.text, fontSize: 10, formatter: (v: number) => formatQty(v) },
      },
      {
        gridIndex: 2,
        position: "right",
        scale: true,
        splitLine: { lineStyle: { color: c.line, type: "dashed" } },
        axisLabel: { color: c.text, fontSize: 10 },
      },
    ],
    series: [
      {
        type: "candlestick",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ohlc,
        itemStyle: {
          color: c.rise,
          color0: c.fall,
          borderColor: c.rise,
          borderColor0: c.fall,
        },
      },
      {
        name: "涨跌幅",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 1,
        data: closes.map((p) => (!ref ? null : ((p - ref) / ref) * 100)),
        showSymbol: false,
        lineStyle: { width: 0, opacity: 0 },
        tooltip: { show: false },
        silent: true,
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: vols,
      },
      {
        name: overlayKind.value === "oi" ? "持仓量" : "成交量线",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 3,
        data: overlay,
        showSymbol: false,
        lineStyle: { width: 1.1, color: c.oi },
      },
      {
        name: "MACD",
        type: "bar",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => ({
          value: p.hist,
          itemStyle: { color: (p.hist || 0) >= 0 ? c.rise : c.fall },
        })),
      },
      {
        name: "DIFF",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => p.dif),
        showSymbol: false,
        lineStyle: { width: 1, color: c.dif },
      },
      {
        name: "DEA",
        type: "line",
        xAxisIndex: 2,
        yAxisIndex: 4,
        data: macd.map((p) => p.dea),
        showSymbol: false,
        lineStyle: { width: 1, color: c.dea },
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
  axisKey = "";
  ro?.disconnect();
  chart?.dispose();
  chart = null;
});

watch(
  () => [
    props.period,
    props.timeshare,
    props.bars,
    props.preClose,
    props.tradeDate,
    props.daySpan,
    props.marks,
    overlayKind.value,
    macdFast.value,
    macdSlow.value,
    macdSignal.value,
  ],
  () => render(),
  { deep: true },
);
</script>

<style scoped src="@/styles/quote-chart.css"></style>
