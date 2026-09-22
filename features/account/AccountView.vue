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

    <div v-else class="page-list">
      <h3 class="page-section-title">账户连接</h3>
      <el-form class="page-query" :inline="true" @submit.prevent="applyQuery">
        <el-form-item>
          <el-input
            v-model="keyword"
            placeholder="网关 / 名称 / 环境 / 前置"
            clearable
            style="width: 240px"
            @keyup.enter="applyQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="applyQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table
        :data="pagedGateways"
        border
        size="small"
        highlight-current-row
        style="width: 100%"
        empty-text="暂无账户连接"
      >
        <el-table-column prop="gateway_name" label="网关" width="110" show-overflow-tooltip />
        <el-table-column prop="account_name" label="名称" min-width="120" show-overflow-tooltip />
        <el-table-column label="环境" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.auto_front === false ? 'warning' : 'info'">
              {{ row.front_label || "—" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="交易前置" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ row["交易服务器"] || "—" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="188" align="center">
          <template #default="{ row }">
            <ChannelStatusPair :row="row" />
          </template>
        </el-table-column>
        <el-table-column label="自动连接" width="88" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="Boolean(row.auto_connect)"
              @change="(value) => setAutoConnect(row, value)"
            />
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="300"
          align="center"
          header-class-name="table-action-col"
          class-name="table-action-col"
        >
          <template #default="{ row }">
            <span class="table-row-actions channel-row-actions">
              <el-button size="small" text type="success" :icon="Connection" @click="connect(row)">
                连接
              </el-button>
              <el-button
                size="small"
                text
                type="primary"
                :icon="Aim"
                :loading="testingId === row.id"
                @click="testConnect(row)"
              >
                测试
              </el-button>
              <el-button size="small" text type="warning" :icon="SwitchButton" @click="disconnect(row)">
                断开
              </el-button>
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="page-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="filteredGateways.length"
          :page-sizes="[10, 20, 50]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          size="small"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Aim, Connection, Refresh, Search, SwitchButton } from "@element-plus/icons-vue";
import { http } from "@/api";
import { useMarketStore, useTradeStore } from "@/stores";
import { contractNameOf } from "../workbench/liveMap";
import ChannelStatusPair from "@/components/ChannelStatusPair.vue";
import InstrumentCell from "@/components/InstrumentCell.vue";

const route = useRoute();
const trade = useTradeStore();
const market = useMarketStore();
const section = computed(() => String(route.params.section || "gateways"));

const keyword = ref("");
const appliedKeyword = ref("");
const page = ref(1);
const pageSize = ref(10);

const filteredGateways = computed(() => {
  const q = appliedKeyword.value.trim().toLowerCase();
  const rows = trade.gateways;
  if (!q) return rows;
  return rows.filter((row) =>
    [row.gateway_name, row.account_name, row.front_label, row["交易服务器"]]
      .join(" ")
      .toLowerCase()
      .includes(q),
  );
});

const pagedGateways = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filteredGateways.value.slice(start, start + pageSize.value);
});

function clampPage() {
  const maxPage = Math.max(1, Math.ceil(filteredGateways.value.length / pageSize.value) || 1);
  if (page.value > maxPage) page.value = maxPage;
}

function applyQuery() {
  appliedKeyword.value = keyword.value;
  page.value = 1;
}

function resetQuery() {
  keyword.value = "";
  appliedKeyword.value = "";
  page.value = 1;
}

watch([filteredGateways, pageSize], clampPage);

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

async function setAutoConnect(row: Record<string, unknown>, value: string | number | boolean) {
  const enabled = Boolean(value);
  try {
    await http.post(`/api/gateways/${row.id}/auto-connect`, { auto_connect: enabled });
    row.auto_connect = enabled;
    ElMessage.success(enabled ? "已开启进程启动时自动连接" : "已关闭启动自连（断线重连仍在连接后生效）");
    await trade.refresh();
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "自动连接设置失败");
  }
}
</script>
