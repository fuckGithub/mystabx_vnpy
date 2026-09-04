<template>
  <el-row :gutter="16">
    <el-col :span="8">
      <h3>下单</h3>
      <OrderTicket :gateways="trade.gateways" />
    </el-col>
    <el-col :span="16">
      <h3>活动委托</h3>
      <el-table :data="trade.orders" height="420">
        <el-table-column prop="symbol" label="合约" width="100" />
        <el-table-column prop="direction" label="方向" width="80" />
        <el-table-column prop="offset" label="开平" width="80" />
        <el-table-column prop="price" label="价格" width="90" />
        <el-table-column prop="volume" label="量" width="70" />
        <el-table-column prop="traded" label="已成" width="70" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }"><StatusTag :text="String(row.status || '')" /></template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text type="danger" @click="cancel(row)">撤单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useTradeStore } from "@/stores";
import OrderTicket from "./OrderTicket.vue";
import StatusTag from "@/components/StatusTag.vue";

const trade = useTradeStore();

async function cancel(row: Record<string, unknown>) {
  await http.post("/api/orders/cancel", {
    vt_orderid: row.vt_orderid,
    gateway_name: row.gateway_name,
  });
  ElMessage.success("撤单已发送");
}
</script>

<style scoped>
h3 { margin: 0 0 12px; font-size: 14px; color: #c9d4de; }
</style>
