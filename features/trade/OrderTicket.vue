<template>
  <el-form label-width="72px" class="ticket">
    <el-form-item label="账户">
      <el-select v-model="form.gateway_name">
        <el-option v-for="gw in gateways" :key="String(gw.gateway_name)" :label="String(gw.gateway_name)" :value="String(gw.gateway_name)" />
      </el-select>
    </el-form-item>
    <el-form-item label="合约">
      <el-input v-model="form.symbol" />
    </el-form-item>
    <el-form-item label="交易所">
      <el-input v-model="form.exchange" />
    </el-form-item>
    <el-form-item label="方向">
      <el-radio-group v-model="form.direction">
        <el-radio label="LONG">买</el-radio>
        <el-radio label="SHORT">卖</el-radio>
      </el-radio-group>
    </el-form-item>
    <el-form-item label="开平">
      <el-select v-model="form.offset">
        <el-option label="开" value="OPEN" />
        <el-option label="平" value="CLOSE" />
        <el-option label="平今" value="CLOSETODAY" />
      </el-select>
    </el-form-item>
    <el-form-item label="价格">
      <el-input-number v-model="form.price" :step="1" />
    </el-form-item>
    <el-form-item label="数量">
      <el-input-number v-model="form.volume" :min="1" :step="1" />
    </el-form-item>
    <el-button type="primary" @click="confirmSend">下单</el-button>
  </el-form>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { http } from "@/api";

const props = defineProps<{ gateways: Record<string, unknown>[] }>();
const form = reactive({
  gateway_name: String(props.gateways[0]?.gateway_name || ""),
  symbol: "",
  exchange: "SHFE",
  direction: "LONG",
  offset: "OPEN",
  type: "LIMIT",
  price: 0,
  volume: 1,
});

async function confirmSend() {
  await ElMessageBox.confirm(
    `${form.direction} ${form.offset} ${form.exchange}.${form.symbol} × ${form.volume} @ ${form.price}`,
    "确认下单",
    { type: "warning" },
  );
  const { data } = await http.post("/api/orders", form);
  ElMessage.success(`已提交 ${data.vt_orderid}`);
}
</script>

<style scoped>
.ticket { max-width: 320px; }
</style>
