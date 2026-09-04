<template>
  <section class="card glass">
    <header class="card-head">
      <div>
        <h3>订阅合约行情</h3>
        <p>板块筛选 · 盘口简览 · 环境实时</p>
      </div>
      <el-radio-group v-model="sortKey" size="small" class="filter-bar sorts">
        <el-radio-button v-for="item in sortOptions" :key="item.k" :value="item.k">{{ item.l }}</el-radio-button>
      </el-radio-group>
    </header>
    <el-radio-group v-model="sector" size="small" class="filter-bar sectors">
      <el-radio-button v-for="item in contractSectors" :key="item.key" :value="item.key">{{ item.label }}</el-radio-button>
    </el-radio-group>
    <div class="quote-list">
      <article v-for="item in rows" :key="item.code" class="quote-row">
        <div class="left">
          <strong>{{ item.name }}</strong>
          <span>{{ item.code }}</span>
        </div>
        <div class="mid" :class="pnlClass(item.change)">{{ fmtPct(item.change) }}</div>
        <div class="book">
          <span class="bid">买 {{ fmtPriceOrDash(item.bid) }}</span>
          <span class="ask">卖 {{ fmtPriceOrDash(item.ask) }}</span>
        </div>
        <div class="vol">
          <span>量 {{ fmtVolume(item.vol) }}</span>
          <span>仓 {{ fmtVolume(item.oi) }}</span>
        </div>
      </article>
      <div v-if="!rows.length" class="quote-empty">暂无订阅行情，请到行情页订阅</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useMarketStore } from "@/stores";
import { contractSectors } from "../mockData";
import { finiteNumber, finitePrice, fmtPct, fmtPriceOrDash, fmtVolume, pnlClass, quoteAmplitude, quoteChangePct, quoteName, quoteSector } from "../liveMap";

const market = useMarketStore();
const sector = ref("all");
const sortKey = ref("subscription");
const sortOptions = [
  { k: "subscription", l: "订阅序" },
  { k: "change", l: "涨幅" },
  { k: "vol", l: "成交量" },
  { k: "oi", l: "持仓量" },
  { k: "amplitude", l: "振幅" },
];

onMounted(() => {
  market.loadTicks();
});

const rows = computed(() => {
  let list = Object.values(market.ticks).map((q, index) => {
    const code = String(q.symbol || "");
    return {
      code,
      name: quoteName(code, q.name),
      sector: quoteSector(code),
      change: quoteChangePct(q),
      vol: finiteNumber(q.volume),
      oi: finiteNumber(q.open_interest),
      amplitude: quoteAmplitude(q),
      bid: finitePrice(q.bid_price_1),
      ask: finitePrice(q.ask_price_1),
      subIndex: index,
    };
  });
  if (sector.value !== "all") list = list.filter((item) => item.sector === sector.value);
  if (sortKey.value === "subscription") list.sort((a, b) => a.subIndex - b.subIndex);
  else {
    const key = sortKey.value as "change" | "vol" | "oi" | "amplitude";
    list.sort((a, b) => (b[key] ?? Number.NEGATIVE_INFINITY) - (a[key] ?? Number.NEGATIVE_INFINITY));
  }
  return list;
});
</script>

<style scoped>
.card { border-radius: var(--dash-card-radius, 8px); padding: 14px; min-height: 0; display: flex; flex-direction: column; height: 100%; }
.card-head { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.card-head h3 { margin: 0; font-size: 14px; color: var(--dash-heading); }
.card-head p { margin: 4px 0 0; font-size: 11px; color: var(--dash-text-muted); }
.filter-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.sectors { margin-bottom: 8px; }
.sorts { justify-content: flex-end; }
.filter-bar :deep(.el-radio-button__inner) {
  border-radius: 999px;
  padding: 5px 11px;
  font-size: 11px;
  border-color: var(--dash-border);
  background: var(--dash-pill-bg);
  color: var(--dash-text-secondary);
  box-shadow: none;
}
.filter-bar :deep(.el-radio-button:first-child .el-radio-button__inner),
.filter-bar :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 999px;
}
.filter-bar :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: var(--dash-border-accent);
  color: var(--primary);
  background: var(--dash-primary-soft);
  box-shadow: none;
}
.quote-list { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.quote-empty { display: flex; align-items: center; justify-content: center; min-height: 72px; font-size: 12px; color: var(--dash-text-muted); }
.quote-row { display: grid; grid-template-columns: minmax(0, 1.2fr) 0.7fr 0.9fr 0.8fr; gap: 8px; align-items: center; padding: 8px 10px; border-radius: 10px; border: 1px solid var(--dash-border); background: var(--dash-surface); font-size: 11px; }
.left strong { display: block; font-size: 12px; color: var(--dash-heading); }
.left span { font-size: 10px; color: var(--dash-text-muted); }
.mid { font-weight: 600; font-variant-numeric: tabular-nums; }
.book, .vol { display: flex; flex-direction: column; gap: 2px; font-size: 10px; color: var(--dash-text-muted); }
</style>
