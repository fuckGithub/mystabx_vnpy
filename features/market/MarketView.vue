<template>
  <div>
    <div class="bar">
      <el-input v-model="keyword" placeholder="搜索合约代码 / 名称" clearable style="width: 280px" @change="search" />
      <el-select v-model="gateway" placeholder="账户" style="width: 180px">
        <el-option v-for="gw in trade.gateways" :key="String(gw.gateway_name)" :label="String(gw.gateway_name)" :value="String(gw.gateway_name)" />
      </el-select>
      <el-button type="primary" :disabled="!selected || !gateway" @click="subscribe">订阅选中</el-button>
    </div>
    <el-table :data="market.contracts" height="240" highlight-current-row @current-change="onPick">
      <el-table-column prop="symbol" label="代码" width="120" />
      <el-table-column prop="exchange" label="交易所" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="pricetick" label="跳价" width="80" />
      <el-table-column prop="gateway_name" label="账户" width="120" />
    </el-table>
    <h3>实时行情</h3>
    <el-table :data="tickRows" height="320">
      <el-table-column prop="symbol" label="合约" width="120" />
      <el-table-column prop="last_price" label="最新" width="100" />
      <el-table-column prop="bid_price_1" label="买一" width="100" />
      <el-table-column prop="bid_volume_1" label="买量" width="80" />
      <el-table-column prop="ask_price_1" label="卖一" width="100" />
      <el-table-column prop="ask_volume_1" label="卖量" width="80" />
      <el-table-column prop="volume" label="成交量" />
      <el-table-column prop="gateway_name" label="账户" width="120" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useMarketStore, useTradeStore } from "@/stores";

const market = useMarketStore();
const trade = useTradeStore();
const keyword = ref("");
const gateway = ref("");
const selected = ref<Record<string, unknown> | null>(null);

const tickRows = computed(() => Object.values(market.ticks));

onMounted(async () => {
  await market.loadContracts();
  if (trade.gateways[0]) gateway.value = String(trade.gateways[0].gateway_name);
});

function onPick(row: Record<string, unknown> | null) {
  selected.value = row;
  if (row?.gateway_name) gateway.value = String(row.gateway_name);
}

async function search() {
  await market.loadContracts(keyword.value);
}

async function subscribe() {
  if (!selected.value) return;
  await http.post("/api/market/subscribe", {
    gateway_name: gateway.value,
    symbol: selected.value.symbol,
    exchange: selected.value.exchange,
  });
  ElMessage.success(`已订阅 ${selected.value.symbol}`);
}
</script>

<style scoped>
.bar { display: flex; gap: 12px; margin-bottom: 12px; }
h3 { margin: 16px 0 8px; font-size: 14px; color: #c9d4de; }
</style>
