<template>
  <section class="card glass">
    <header class="card-head">
      <div>
        <h3>实时持仓监控</h3>
        <p>CTP 持仓 · 本机快照</p>
      </div>
      <span class="live-dot">LIVE</span>
    </header>
    <div class="table-wrap">
      <table class="positions-table">
        <thead>
          <tr>
            <th>合约</th>
            <th class="col-side">方向</th>
            <th class="col-qty">手数</th>
            <th class="col-avg">均价</th>
            <th class="col-pnl">浮盈</th>
            <th>冻结</th>
            <th>账户</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in rows" :key="`${item.code}-${item.side}-${item.gateway}`">
            <td class="col-contract">
              <strong>{{ item.name }}</strong>
              <small>{{ item.code }}</small>
            </td>
            <td class="col-side"><span class="side" :class="item.side === '多' ? 'long' : 'short'">{{ item.side }}</span></td>
            <td class="col-qty">{{ item.qty ?? "--" }}</td>
            <td class="col-avg">{{ fmtPriceOrDash(item.avgPrice) }}</td>
            <td class="col-pnl" :class="pnlClass(item.pnl)">{{ fmtSigned(item.pnl, 2) }}</td>
            <td class="col-num muted">{{ item.frozen ?? "--" }}</td>
            <td><code>{{ item.gateway }}</code></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!rows.length" class="table-empty">暂无持仓</div>
    </div>
    <footer class="card-foot">
      <span>多头盈亏 <em :class="pnlClass(summary.longPnl)">{{ fmtSigned(summary.longPnl, 2) }}</em></span>
      <span>空头盈亏 <em :class="pnlClass(summary.shortPnl)">{{ fmtSigned(summary.shortPnl, 2) }}</em></span>
      <span>最大浮亏风险 <em :class="pnlClass(summary.maxRisk)">{{ fmtSigned(summary.maxRisk, 2) }}</em></span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useMarketStore, useTradeStore } from "@/stores";
import { finiteNumber, finitePrice, fmtPriceOrDash, fmtSigned, pnlClass, positionSide, quoteName } from "../liveMap";

const trade = useTradeStore();
const market = useMarketStore();

const rows = computed(() =>
  trade.positions
    .map((p) => {
      const code = String(p.symbol || "");
      const qty = finiteNumber(p.volume);
      if (!code || qty === null || qty <= 0) return null;
      const tick = Object.values(market.ticks).find((t) => t.symbol === code);
      return {
        code,
        name: quoteName(code, tick?.name),
        side: positionSide(p.direction),
        qty,
        avgPrice: finitePrice(p.price),
        pnl: finiteNumber(p.pnl),
        frozen: finiteNumber(p.frozen),
        gateway: String(p.gateway_name || ""),
      };
    })
    .filter((row): row is NonNullable<typeof row> => !!row),
);

const summary = computed(() => {
  let longPnl: number | null = null;
  let shortPnl: number | null = null;
  let maxRisk: number | null = null;
  for (const item of rows.value) {
    if (item.pnl === null) continue;
    if (item.side === "多") longPnl = (longPnl ?? 0) + item.pnl;
    else shortPnl = (shortPnl ?? 0) + item.pnl;
    maxRisk = maxRisk === null ? item.pnl : Math.min(maxRisk, item.pnl);
  }
  return { longPnl, shortPnl, maxRisk };
});
</script>

<style scoped>
.card { border-radius: var(--dash-card-radius, 8px); padding: 14px; min-height: 0; display: flex; flex-direction: column; height: 100%; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.card-head h3 { margin: 0; font-size: 14px; color: var(--dash-heading); }
.card-head p { margin: 4px 0 0; font-size: 11px; color: var(--dash-text-muted); }
.live-dot { font-size: 10px; border-radius: 999px; padding: 2px 8px; }
.table-wrap { flex: 1; min-height: 0; overflow: auto; border-radius: 10px; border: 1px solid var(--dash-border); background: var(--dash-surface); }
.positions-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.table-empty { display: flex; align-items: center; justify-content: center; min-height: 72px; font-size: 12px; color: var(--dash-text-muted); }
thead { position: sticky; top: 0; z-index: 1; }
th, td {
  padding: 9px 8px;
  border-bottom: 1px solid var(--dash-border);
  text-align: center;
  white-space: nowrap;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}
th { font-weight: 500; color: var(--dash-text-muted); background: var(--dash-surface-soft); }
.col-contract strong, .col-contract small { display: block; text-align: center; overflow: hidden; text-overflow: ellipsis; }
.col-qty, .col-avg, .col-pnl { font-variant-numeric: tabular-nums; overflow: visible; }
.col-contract strong { color: var(--dash-heading); }
.col-contract small, .muted { color: var(--dash-text-muted); }
.side { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
code { font-size: 10px; color: var(--primary); }
.card-foot { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--dash-border); font-size: 11px; color: var(--dash-text-muted); }
.card-foot em { font-style: normal; font-weight: 600; }
</style>
