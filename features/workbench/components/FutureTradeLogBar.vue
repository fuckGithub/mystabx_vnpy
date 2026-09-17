<template>
  <section class="log-bar glass">
    <header class="log-head">
      <div class="log-title">
        <h3>量化交易流水日志</h3>
        <p>订单与成交 · 本机实录</p>
      </div>
      <div class="log-filters">
        <el-select v-model="kindFilter" size="small" class="filter-select">
          <el-option label="全部流水" value="all" />
          <el-option label="只看成交" value="trade" />
          <el-option label="只看委托" value="order" />
        </el-select>
        <el-input v-model="codeFilter" size="small" placeholder="名称 / 代码" class="filter-input" clearable />
      </div>
    </header>
    <div class="log-scroll">
      <table v-if="pagedRows.length">
        <thead>
          <tr>
            <th>时间</th>
            <th>合约</th>
            <th>方向</th>
            <th>手数</th>
            <th>成交价</th>
            <th>账户</th>
            <th>类型</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pagedRows" :key="item.id">
            <td>{{ item.time }}</td>
            <td class="col-contract">
              <InstrumentCell :code="item.code" :name="item.name" />
            </td>
            <td>{{ item.side }}</td>
            <td>{{ item.qty ?? "--" }}</td>
            <td>{{ fmtPriceOrDash(item.price) }}</td>
            <td><code>{{ item.gateway }}</code></td>
            <td><span class="env" :class="item.kind === 'trade' ? 'live' : 'sim'">{{ item.kind === "trade" ? "成交" : "委托" }}</span></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="log-empty">暂无成交记录</div>
    </div>
    <footer class="log-pagination">
      <el-pagination
        v-model:current-page="current"
        v-model:page-size="size"
        :page-sizes="[10, 20, 50]"
        :total="filteredRows.length"
        :pager-count="5"
        background
        layout="total, sizes, prev, pager, next"
        size="small"
      />
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMarketStore, useTradeStore } from "@/stores";
import InstrumentCell from "@/components/InstrumentCell.vue";
import { contractNameOf, eventTimeMs, eventTimeText, finiteNumber, finitePrice, fmtPriceOrDash, instrumentLines, orderStatusLabel, tradeSideLabel } from "../liveMap";

const trade = useTradeStore();
const market = useMarketStore();
const kindFilter = ref("all");
const codeFilter = ref("");
const current = ref(1);
const size = ref(10);

const liveLogs = computed(() => {
  const trades = trade.trades.map((t) => {
    const code = String(t.symbol || "");
    const lines = instrumentLines(code, contractNameOf(market.contracts, code, t.exchange));
    return {
    id: `t-${t.tradeid}`,
    ts: eventTimeMs(t.datetime),
    time: eventTimeText(t.datetime),
    code: lines.code,
    name: lines.name,
    distinct: lines.distinct,
    side: tradeSideLabel(t.direction, t.offset),
    qty: finiteNumber(t.volume),
    price: finitePrice(t.price),
    gateway: String(t.gateway_name || ""),
    kind: "trade" as const,
  };
  });
  const orders = trade.orders.map((o) => {
    const code = String(o.symbol || "");
    const lines = instrumentLines(code, contractNameOf(market.contracts, code, o.exchange));
    return {
    id: `o-${o.vt_orderid || o.orderid}`,
    ts: eventTimeMs(o.datetime),
    time: eventTimeText(o.datetime),
    code: lines.code,
    name: lines.name,
    distinct: lines.distinct,
    side: `${tradeSideLabel(o.direction, o.offset)}·${orderStatusLabel(o.status)}`,
    qty: finiteNumber(o.volume),
    price: finitePrice(o.price),
    gateway: String(o.gateway_name || ""),
    kind: "order" as const,
  };
  });
  return [...trades, ...orders].sort((a, b) => b.ts - a.ts);
});

const filteredRows = computed(() =>
  liveLogs.value.filter((item) => {
    if (kindFilter.value !== "all" && item.kind !== kindFilter.value) return false;
    if (codeFilter.value) {
      const q = codeFilter.value.toUpperCase();
      if (!item.code.toUpperCase().includes(q) && !item.name.toUpperCase().includes(q)) return false;
    }
    return true;
  }),
);

watch([kindFilter, codeFilter, size], () => {
  current.value = 1;
});

const pagedRows = computed(() => {
  const start = (current.value - 1) * size.value;
  return filteredRows.value.slice(start, start + size.value);
});
</script>

<style scoped src="@/styles/future-trade-log.css"></style>
