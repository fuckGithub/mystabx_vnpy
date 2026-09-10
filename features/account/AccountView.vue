<template>
  <div class="page-shell">
    <div v-if="section === 'funds'" class="page-section">
      <h3 class="page-section-title">资金</h3>
      <el-table :data="trade.funds" height="560">
        <el-table-column prop="accountid" label="账号" />
        <el-table-column prop="balance" label="权益" />
        <el-table-column prop="frozen" label="冻结" />
        <el-table-column prop="available" label="可用" />
        <el-table-column prop="gateway_name" label="网关" />
      </el-table>
    </div>

    <div v-else-if="section === 'positions'" class="page-section">
      <h3 class="page-section-title">持仓</h3>
      <el-table :data="trade.positions" height="560">
        <el-table-column label="合约" min-width="140">
          <template #default="{ row }">
            <InstrumentCell :code="String(row.symbol || '')" :name="nameOf(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="direction" label="方向" />
        <el-table-column prop="volume" label="数量" />
        <el-table-column prop="price" label="均价" />
        <el-table-column prop="pnl" label="浮盈" />
        <el-table-column prop="gateway_name" label="网关" />
      </el-table>
    </div>

    <div v-else-if="section === 'trades'" class="page-section">
      <h3 class="page-section-title">成交</h3>
      <el-table :data="trade.trades" height="560">
        <el-table-column label="合约" min-width="140">
          <template #default="{ row }">
            <InstrumentCell :code="String(row.symbol || '')" :name="nameOf(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="direction" label="方向" />
        <el-table-column prop="offset" label="开平" />
        <el-table-column prop="price" label="价格" />
        <el-table-column prop="volume" label="数量" />
        <el-table-column prop="gateway_name" label="网关" />
      </el-table>
    </div>

    <div v-else class="page-section">
      <h3 class="page-section-title">账户连接</h3>
      <el-table :data="trade.gateways" height="560">
        <el-table-column prop="gateway_name" label="网关" />
        <el-table-column prop="account_name" label="名称" />
        <el-table-column label="环境" width="100">
          <template #default="{ row }">{{ row.front_label || "—" }}</template>
        </el-table-column>
        <el-table-column label="交易前置" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row["交易服务器"] || "—" }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="168" align="center">
          <template #default="{ row }">
            <ChannelStatusPair :row="row" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" class-name="table-action-col">
          <template #default="{ row }">
            <span class="table-row-actions">
              <el-button size="small" type="primary" @click="connect(row)">连接</el-button>
              <el-button size="small" :loading="testingId === row.id" @click="testConnect(row)">测试联通</el-button>
              <el-button size="small" @click="disconnect(row)">断开</el-button>
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useMarketStore, useTradeStore } from "@/stores";
import { contractNameOf } from "../workbench/liveMap";
import ChannelStatusPair from "@/components/ChannelStatusPair.vue";
import InstrumentCell from "@/components/InstrumentCell.vue";

const route = useRoute();
const trade = useTradeStore();
const market = useMarketStore();
const section = computed(() => String(route.params.section || "gateways"));

function nameOf(row: Record<string, unknown>) {
  return contractNameOf(market.contracts, String(row.symbol || ""), row.exchange);
}
const testingId = ref<number | null>(null);

async function connect(row: Record<string, unknown>) {
  await http.post(`/api/gateways/${row.id}/connect`);
  ElMessage.success(`正在连接 ${row.gateway_name}`);
  trade.setActiveGateway(String(row.gateway_name || ""));
  await trade.refresh();
}

async function testConnect(row: Record<string, unknown>) {
  const id = Number(row.id);
  testingId.value = id;
  try {
    const { data } = await http.post(`/api/gateways/${id}/test-connect`);
    ElMessage[data.ok ? "success" : data.reachable ? "warning" : "error"](data.summary || "联通测试完成");
    if (data.ok) trade.setActiveGateway(String(data.gateway_name || row.gateway_name || ""));
    await trade.refresh();
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "联通测试失败");
  } finally {
    testingId.value = null;
  }
}

async function disconnect(row: Record<string, unknown>) {
  await http.post(`/api/gateways/${row.id}/disconnect`);
  ElMessage.success(`已断开 ${row.gateway_name}`);
  await trade.refresh();
}
</script>
