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
              <InstrumentCell :code="item.code" :name="item.name" />
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
import InstrumentCell from "@/components/InstrumentCell.vue";
import { contractNameOf, finiteNumber, finitePrice, fmtPriceOrDash, fmtSigned, instrumentLines, pnlClass, positionSide } from "../liveMap";

const trade = useTradeStore();
const market = useMarketStore();

const rows = computed(() => {
  const selected = String(trade.activeGatewayName || "");
  return trade.positions
    .filter((p) => !selected || p.gateway_name === selected)
    .map((p) => {
      const code = String(p.symbol || "");
      const qty = finiteNumber(p.volume);
      if (!code || qty === null || qty <= 0) return null;
      const tick = Object.values(market.ticks).find((t) => t.symbol === code);
      const lines = instrumentLines(code, contractNameOf(market.contracts, code, p.exchange), tick?.name);
      return {
        code: lines.code,
        name: lines.name,
        distinct: lines.distinct,
        side: positionSide(p.direction),
        qty,
        avgPrice: finitePrice(p.price),
        pnl: finiteNumber(p.pnl),
        frozen: finiteNumber(p.frozen),
        gateway: String(p.gateway_name || ""),
      };
    })
    .filter((row): row is NonNullable<typeof row> => !!row);
});

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

<style scoped src="@/styles/future-positions.css"></style>
