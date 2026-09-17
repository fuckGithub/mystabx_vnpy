<template>
  <aside class="tape">
    <header class="tape-head">
      <strong>{{ title }}</strong>
      <span>{{ subtitle }}</span>
    </header>
    <dl class="tape-grid">
      <div class="tape-cell wide">
        <dt>最新</dt>
        <dd :class="chgClass">{{ fmtPriceOrDash(last) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>涨跌</dt>
        <dd :class="chgClass">{{ fmtSigned(changeAbs) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>涨幅</dt>
        <dd :class="chgClass">{{ fmtPct(changePct) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>买一</dt>
        <dd class="bid">{{ fmtPriceOrDash(bid) }}<small>×{{ fmtVolume(bidVol) }}</small></dd>
      </div>
      <div class="tape-cell">
        <dt>卖一</dt>
        <dd class="ask">{{ fmtPriceOrDash(ask) }}<small>×{{ fmtVolume(askVol) }}</small></dd>
      </div>
      <div class="tape-cell">
        <dt>成交</dt>
        <dd>{{ fmtVolume(vol) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>持仓</dt>
        <dd>{{ fmtVolume(oi) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>开盘</dt>
        <dd>{{ fmtPriceOrDash(open) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>最高</dt>
        <dd class="up">{{ fmtPriceOrDash(high) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>最低</dt>
        <dd class="down">{{ fmtPriceOrDash(low) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>昨收</dt>
        <dd>{{ fmtPriceOrDash(pre) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>涨停</dt>
        <dd class="up">{{ fmtPriceOrDash(limitUp) }}</dd>
      </div>
      <div class="tape-cell">
        <dt>跌停</dt>
        <dd class="down">{{ fmtPriceOrDash(limitDown) }}</dd>
      </div>
    </dl>
    <div class="book">
      <div class="book-head">盘口</div>
      <ul class="book-side asks">
        <li v-for="row in askRows" :key="row.label" class="book-row ask">
          <span class="book-label">{{ row.label }}</span>
          <span class="book-price">{{ fmtPriceOrDash(row.price) }}</span>
          <span class="book-vol">{{ fmtVolume(row.volume) }}</span>
        </li>
      </ul>
      <ul class="book-side bids">
        <li v-for="row in bidRows" :key="row.label" class="book-row bid">
          <span class="book-label">{{ row.label }}</span>
          <span class="book-price">{{ fmtPriceOrDash(row.price) }}</span>
          <span class="book-vol">{{ fmtVolume(row.volume) }}</span>
        </li>
      </ul>
    </div>
    <p v-if="!tick" class="tape-hint">选中合约后展示盘口；数据来自 SimNow 实时 Tick。</p>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { finiteNumber, finitePrice, fmtPct, fmtPriceOrDash, fmtSigned, fmtVolume, instrumentLines, pnlClass, quoteChangePct } from "../../workbench/liveMap";
import { exchangeLabel } from "../contracts";

const props = defineProps<{
  contract: Record<string, unknown> | null;
  tick?: Record<string, unknown>;
}>();

const lines = computed(() => {
  if (!props.contract) return null;
  const code = String(props.contract.symbol || "");
  return instrumentLines(code, props.contract.name, props.tick?.name);
});
const title = computed(() => lines.value?.name || "未选合约");
const subtitle = computed(() => {
  if (!lines.value) return "点击左侧列表";
  const ex = exchangeLabel(props.contract?.exchange);
  return lines.value.code ? `${lines.value.code} · ${ex}` : ex;
});

const last = computed(() => finitePrice(props.tick?.last_price));
const pre = computed(() => finitePrice(props.tick?.pre_close));
const changePct = computed(() => quoteChangePct(props.tick));
const changeAbs = computed(() => {
  if (last.value === null || pre.value === null) return null;
  return last.value - pre.value;
});
const chgClass = computed(() => pnlClass(changePct.value));
const bid = computed(() => finitePrice(props.tick?.bid_price_1));
const ask = computed(() => finitePrice(props.tick?.ask_price_1));
const bidVol = computed(() => finiteNumber(props.tick?.bid_volume_1));
const askVol = computed(() => finiteNumber(props.tick?.ask_volume_1));

const ASK_LABELS = ["卖五", "卖四", "卖三", "卖二", "卖一"] as const;
const BID_LABELS = ["买一", "买二", "买三", "买四", "买五"] as const;

function bookLevel(side: "bid" | "ask", level: number) {
  const tick = props.tick;
  const price = finitePrice(tick?.[`${side}_price_${level}`]);
  const volume = finiteNumber(tick?.[`${side}_volume_${level}`]);
  return {
    price,
    volume: price === null || volume === 0 ? null : volume,
  };
}

const askRows = computed(() =>
  ASK_LABELS.map((label, i) => ({ label, ...bookLevel("ask", 5 - i) })),
);
const bidRows = computed(() =>
  BID_LABELS.map((label, i) => ({ label, ...bookLevel("bid", i + 1) })),
);
const vol = computed(() => finiteNumber(props.tick?.volume));
const oi = computed(() => finiteNumber(props.tick?.open_interest));
const open = computed(() => finitePrice(props.tick?.open_price));
const high = computed(() => finitePrice(props.tick?.high_price));
const low = computed(() => finitePrice(props.tick?.low_price));
const limitUp = computed(() => finitePrice(props.tick?.limit_up));
const limitDown = computed(() => finitePrice(props.tick?.limit_down));
</script>

<style scoped src="@/styles/quote-tape.css"></style>
