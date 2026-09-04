<template>
  <div class="page-shell page-grid">
    <div class="page-panel">
      <h3 class="page-section-title">下单</h3>
      <OrderTicket :gateways="trade.gateways" />
    </div>
    <div class="page-panel">
      <h3 class="page-section-title">活动委托</h3>
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
        <el-table-column label="操作" width="90" class-name="table-action-col">
          <template #default="{ row }">
            <el-button text type="danger" @click="cancel(row)">撤单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
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
