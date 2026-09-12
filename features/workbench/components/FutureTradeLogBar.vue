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

<style scoped>
.log-bar { border-radius: var(--dash-card-radius, 8px); padding: 12px 14px; height: 100%; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.log-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.log-head h3 { margin: 0; font-size: 13px; color: var(--dash-heading); }
.log-head p { margin: 2px 0 0; font-size: 11px; color: var(--dash-text-muted); }
.log-filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.filter-select { width: 128px; }
.filter-input { width: 120px; }
.log-scroll { flex: 1; min-height: 0; overflow: auto; }
.log-empty { display: flex; align-items: center; justify-content: center; min-height: 48px; font-size: 12px; color: var(--dash-text-muted); }
.log-pagination {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 8px;
  margin-top: 4px;
  border-top: 1px solid var(--dash-border);
}
.log-pagination :deep(.el-pagination) {
  flex-wrap: wrap;
  row-gap: 4px;
  --el-pagination-bg-color: transparent;
  --el-pagination-button-bg-color: var(--dash-surface-soft);
  --el-pagination-hover-color: var(--primary);
  --el-pagination-button-color: var(--dash-text-secondary);
}
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th, td { padding: 6px 8px; border-bottom: 1px solid var(--dash-border); text-align: left; white-space: nowrap; }
th { position: sticky; top: 0; color: var(--dash-text-muted); background: var(--dash-surface-soft); z-index: 1; }
code { font-size: 10px; color: var(--primary); }
.env { padding: 2px 6px; border-radius: 999px; font-size: 10px; }
</style>
