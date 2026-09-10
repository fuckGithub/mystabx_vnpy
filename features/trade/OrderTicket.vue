<template>
  <el-form label-width="72px" class="ticket">
    <el-form-item label="账户">
      <el-select v-model="form.gateway_name">
        <el-option v-for="gw in gateways" :key="String(gw.gateway_name)" :label="String(gw.gateway_name)" :value="String(gw.gateway_name)" />
      </el-select>
    </el-form-item>
    <el-form-item label="合约">
      <el-select
        v-model="picked"
        filterable
        clearable
        allow-create
        default-first-option
        placeholder="名称 / 代码"
        @change="onPick"
      >
        <el-option
          v-for="item in contractOptions"
          :key="item.key"
          :label="item.label"
          :value="item.key"
        />
      </el-select>
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
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { http } from "@/api";
import { useMarketStore } from "@/stores";
import { instrumentLabel } from "../workbench/liveMap";

const props = defineProps<{ gateways: Record<string, unknown>[] }>();
const market = useMarketStore();
const picked = ref("");
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

const contractOptions = computed(() =>
  market.contracts
    .map((row) => {
      const symbol = String(row.symbol || "").trim();
      const exchange = String(row.exchange || "").trim();
      if (!symbol) return null;
      const name = String(row.name || "").trim();
      return {
        key: exchange ? `${exchange}.${symbol}` : symbol,
        symbol,
        exchange,
        name,
        label: instrumentLabel(symbol, name),
      };
    })
    .filter((row): row is NonNullable<typeof row> => !!row),
);

onMounted(() => {
  if (!market.contracts.length) void market.loadContracts();
});

function onPick(value: string) {
  const key = String(value || "").trim();
  const hit = contractOptions.value.find((item) => item.key === key);
  if (hit) {
    form.symbol = hit.symbol;
    if (hit.exchange) form.exchange = hit.exchange;
    return;
  }
  const dot = key.lastIndexOf(".");
  if (dot > 0) {
    form.exchange = key.slice(0, dot);
    form.symbol = key.slice(dot + 1);
    return;
  }
  form.symbol = key;
}

async function confirmSend() {
  const hit = contractOptions.value.find(
    (item) => item.symbol === form.symbol && (!item.exchange || item.exchange === form.exchange),
  );
  await ElMessageBox.confirm(
    `${form.direction} ${form.offset} ${instrumentLabel(form.symbol, hit?.name)} × ${form.volume} @ ${form.price}`,
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
