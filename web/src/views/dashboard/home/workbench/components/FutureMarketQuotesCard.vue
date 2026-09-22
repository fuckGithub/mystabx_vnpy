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
          <InstrumentCell :code="item.code" :name="item.name" />
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
import { useMarketStore } from '../stores';
import InstrumentCell from './InstrumentCell.vue';
import { contractSectors } from "../mockData";
import { contractNameOf, finiteNumber, finitePrice, fmtPct, fmtPriceOrDash, fmtVolume, instrumentLines, pnlClass, quoteAmplitude, quoteChangePct, quoteSector } from "../liveMap";

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
  void market.loadTicks();
  if (!market.contracts.length) void market.loadContracts();
});

const rows = computed(() => {
  let list = Object.values(market.ticks).map((q, index) => {
    const code = String(q.symbol || "");
    const lines = instrumentLines(code, contractNameOf(market.contracts, code, q.exchange), q.name);
    return {
      code: lines.code,
      name: lines.name,
      distinct: lines.distinct,
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

<style scoped src="../styles/future-market-quotes.css"></style>
