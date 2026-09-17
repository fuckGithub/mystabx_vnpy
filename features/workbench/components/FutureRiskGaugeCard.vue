<template>
  <section class="card glass">
    <header class="card-head">
      <div>
        <h3>实时风控压力仪表盘</h3>
        <p>资金占用 · 持仓集中度</p>
      </div>
      <div class="badges">
        <span class="risk-badge" :class="{ off: !riskEnabled }">{{ riskEnabled ? "风控运行中" : "风控已关闭" }}</span>
        <el-button size="small" class="lock-btn" :type="blockNewPositions ? 'danger' : 'default'" plain @click="blockNewPositions = !blockNewPositions">
          {{ blockNewPositions ? "禁开新仓" : "允许开仓" }}
        </el-button>
      </div>
    </header>
    <div class="gauge-grid">
      <article v-for="item in gauges" :key="item.key" class="gauge-card" :class="{ flash: item.value >= item.danger && riskEnabled }">
        <div class="gauge-ring" :style="gaugeStyle(item.value, item.warn, item.danger)">
          <div class="gauge-inner"><strong>{{ (item.value * 100).toFixed(0) }}%</strong></div>
        </div>
        <p>{{ item.label }}</p>
        <small>警戒 {{ (item.warn * 100).toFixed(0) }}% · 危险 {{ (item.danger * 100).toFixed(0) }}%</small>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useTradeStore } from "@/stores";
import { pickFunds } from "../liveMap";

const trade = useTradeStore();
const riskEnabled = ref(true);
const blockNewPositions = ref(false);

const gauges = computed(() => {
  const selected = String(trade.activeGatewayName || "");
  const fund = pickFunds(trade.funds, selected, trade.gateways.find((gw) => String(gw.gateway_name) === selected))[0];
  const equity = Number(fund?.balance) || 0;
  const available = Number(fund?.available) || 0;
  const usage = equity > 0 ? Math.min(1, Math.max(0, (equity - available) / equity)) : 0;
  const positions = trade.positions.filter((p) => !selected || p.gateway_name === selected);
  const volumes = positions.map((p) => Number(p.volume) || 0);
  const totalVol = volumes.reduce((a, b) => a + b, 0);
  const maxVol = volumes.reduce((a, b) => Math.max(a, b), 0);
  const concentrate = totalVol > 0 ? maxVol / totalVol : 0;
  const pnls = positions.map((p) => Number(p.pnl) || 0);
  const loss = pnls.filter((v) => v < 0).reduce((a, b) => a + b, 0);
  const dailyLoss = equity > 0 ? Math.min(1, Math.abs(loss) / equity) : 0;
  return [
    { key: "fundUsage", label: "资金使用率", value: usage, warn: 0.7, danger: 0.9 },
    { key: "dailyLoss", label: "单日最大亏损阈值", value: dailyLoss, warn: 0.6, danger: 0.85 },
    { key: "singleContract", label: "单合约持仓上限", value: concentrate, warn: 0.65, danger: 0.8 },
    { key: "volatility", label: "波动率风险指数", value: Math.min(1, dailyLoss * 1.2 + usage * 0.3), warn: 0.55, danger: 0.75 },
  ];
});

function gaugeStyle(value: number, warn: number, danger: number) {
  const pct = Math.round(value * 100);
  const color = value >= danger ? "var(--danger)" : value >= warn ? "var(--warning)" : "var(--success)";
  return { background: `conic-gradient(${color} ${pct}%, var(--dash-gauge-track) ${pct}% 100%)` };
}
</script>

<style scoped src="@/styles/future-risk-gauge.css"></style>
