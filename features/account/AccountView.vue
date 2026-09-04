<template>
  <div>
    <h3>账户连接</h3>
    <el-table :data="trade.gateways">
      <el-table-column prop="gateway_name" label="网关" />
      <el-table-column prop="account_name" label="名称" />
      <el-table-column label="状态">
        <template #default="{ row }"><StatusTag :text="String(row.conn_status || 'DISCONNECTED')" /></template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="connect(row)">连接</el-button>
          <el-button size="small" @click="disconnect(row)">断开</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3>资金</h3>
    <el-table :data="trade.funds">
      <el-table-column prop="accountid" label="账号" />
      <el-table-column prop="balance" label="权益" />
      <el-table-column prop="frozen" label="冻结" />
      <el-table-column prop="available" label="可用" />
      <el-table-column prop="gateway_name" label="网关" />
    </el-table>

    <h3>持仓</h3>
    <el-table :data="trade.positions">
      <el-table-column prop="symbol" label="合约" />
      <el-table-column prop="direction" label="方向" />
      <el-table-column prop="volume" label="数量" />
      <el-table-column prop="price" label="均价" />
      <el-table-column prop="pnl" label="浮盈" />
      <el-table-column prop="gateway_name" label="网关" />
    </el-table>

    <h3>成交</h3>
    <el-table :data="trade.trades">
      <el-table-column prop="symbol" label="合约" />
      <el-table-column prop="direction" label="方向" />
      <el-table-column prop="offset" label="开平" />
      <el-table-column prop="price" label="价格" />
      <el-table-column prop="volume" label="数量" />
      <el-table-column prop="gateway_name" label="网关" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useTradeStore } from "@/stores";
import StatusTag from "@/components/StatusTag.vue";

const trade = useTradeStore();

async function connect(row: Record<string, unknown>) {
  await http.post(`/api/gateways/${row.id}/connect`);
  ElMessage.success(`正在连接 ${row.gateway_name}`);
  await trade.refresh();
}

async function disconnect(row: Record<string, unknown>) {
  await http.post(`/api/gateways/${row.id}/disconnect`);
  ElMessage.success(`已断开 ${row.gateway_name}`);
  await trade.refresh();
}
</script>

<style scoped>
h3 { margin: 18px 0 8px; font-size: 14px; color: #c9d4de; }
</style>
