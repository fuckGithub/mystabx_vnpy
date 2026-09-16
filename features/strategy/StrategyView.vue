<template>
  <div class="page-shell">
    <div v-if="section === 'backtest'" class="page-list">
      <h3 class="page-section-title">CTA 回测</h3>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="依赖本地 bar / RQData。无历史数据时结果为空属正常（见 docs/09 阶段 B）。"
        style="margin-bottom: 12px"
      />
      <el-form class="page-query" label-width="96px" @submit.prevent>
        <el-form-item label="策略类">
          <el-select v-model="btForm.class_name" filterable style="width: 260px">
            <el-option v-for="c in btClasses" :key="c.class_name" :label="c.class_name" :value="c.class_name" />
          </el-select>
        </el-form-item>
        <el-form-item label="合约">
          <el-input v-model="btForm.vt_symbol" placeholder="rb2501.SHFE" style="width: 200px" />
        </el-form-item>
        <el-form-item label="周期">
          <el-input v-model="btForm.interval" style="width: 100px" />
        </el-form-item>
        <el-form-item label="开始">
          <el-input v-model="btForm.start" placeholder="2024-01-01" style="width: 140px" />
        </el-form-item>
        <el-form-item label="结束">
          <el-input v-model="btForm.end" placeholder="2024-06-01" style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="btRunning" :disabled="!auth.isAdmin" @click="runBacktest">运行回测</el-button>
          <el-button :icon="Refresh" @click="loadBacktestResult">刷新结果</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="strategy.backtestLogs" size="small" border max-height="180" empty-text="暂无回测日志" style="margin-bottom: 12px">
        <el-table-column prop="msg" label="日志" min-width="320" show-overflow-tooltip />
      </el-table>
      <el-descriptions v-if="btStats" title="统计" :column="3" border size="small">
        <el-descriptions-item v-for="(val, key) in btStats" :key="String(key)" :label="String(key)">
          {{ val }}
        </el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="尚无回测结果" />
    </div>

    <div v-else-if="section === 'stoporders'" class="page-list">
      <h3 class="page-section-title">停止单</h3>
      <el-table :data="strategy.stopOrders" border size="small" empty-text="暂无停止单">
        <el-table-column prop="stop_orderid" label="编号" min-width="140" show-overflow-tooltip />
        <el-table-column prop="strategy_name" label="策略" width="120" />
        <el-table-column prop="vt_symbol" label="合约" width="120" />
        <el-table-column prop="direction" label="方向" width="80" />
        <el-table-column prop="price" label="价格" width="90" />
        <el-table-column prop="volume" label="量" width="70" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="stopStatusType(row.status)">{{ row.status || "—" }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-else-if="section === 'logs'" class="page-list">
      <h3 class="page-section-title">策略日志</h3>
      <el-table :data="strategy.logs" border size="small" height="560" empty-text="暂无日志">
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="strategy_name" label="策略" width="140" />
        <el-table-column prop="level" label="级别" width="80" />
        <el-table-column prop="msg" label="内容" min-width="320" show-overflow-tooltip />
      </el-table>
    </div>

    <div v-else class="page-list">
      <h3 class="page-section-title">CTA 实例</h3>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="试用：管理员 → 添加策略选 DoubleMaStrategy → 填 vt_symbol（如 rb2501.SHFE）→ 初始化 → 启动。"
        description="首次接入或装依赖后需重启后端，前端硬刷新。"
        style="margin-bottom: 12px"
      />
      <div class="page-toolbar">
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openAdd">添加策略</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('init-all')">全部初始化</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('start-all')">全部启动</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('stop-all')">全部停止</el-button>
        <el-button :icon="Refresh" @click="strategy.refresh()">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="strategy.instances"
        border
        size="small"
        highlight-current-row
        style="width: 100%"
        empty-text="暂无策略实例"
      >
        <el-table-column prop="strategy_name" label="实例" min-width="120" show-overflow-tooltip />
        <el-table-column prop="class_name" label="策略类" min-width="130" show-overflow-tooltip />
        <el-table-column prop="vt_symbol" label="合约" width="130" show-overflow-tooltip />
        <el-table-column prop="gateway_name" label="账户" width="100" show-overflow-tooltip />
        <el-table-column label="inited" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.inited ? 'success' : 'info'">{{ row.inited ? "是" : "否" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="trading" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.trading ? 'success' : 'info'">{{ row.trading ? "是" : "否" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pos" label="仓位" width="70" align="center" />
        <el-table-column label="参数" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ formatMap(row.parameters) }}</template>
        </el-table-column>
        <el-table-column label="变量" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ formatMap(row.variables) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center" header-class-name="table-action-col" class-name="table-action-col">
          <template #default="{ row }">
            <span class="table-row-actions">
              <el-button type="primary" link :disabled="!auth.isAdmin" @click="act(row, 'init')">初始化</el-button>
              <el-button type="primary" link :disabled="!auth.isAdmin || !row.inited" @click="act(row, 'start')">启动</el-button>
              <el-button link :disabled="!auth.isAdmin" @click="act(row, 'stop')">停止</el-button>
              <el-button type="primary" link :disabled="!auth.isAdmin || row.trading" @click="openEdit(row)">编辑</el-button>
              <el-button type="danger" link :disabled="!auth.isAdmin || row.trading" @click="remove(row)">移除</el-button>
            </span>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog
        v-model="dialogVisible"
        :title="editingName ? '编辑策略参数' : '添加策略'"
        width="520px"
        class="page-dialog"
        align-center
        :close-on-click-modal="false"
        destroy-on-close
      >
        <el-form label-width="110px">
          <el-form-item v-if="!editingName" label="策略类">
            <el-select v-model="form.class_name" filterable style="width: 100%" @change="onClassChange">
              <el-option v-for="c in classes" :key="c.class_name" :label="c.class_name" :value="c.class_name" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="!editingName" label="实例名称">
            <el-input v-model="form.strategy_name" />
          </el-form-item>
          <el-form-item v-if="!editingName" label="合约 vt_symbol">
            <el-input v-model="form.vt_symbol" placeholder="rb2501.SHFE" />
            <p class="page-form-hint">格式：合约代码.交易所，如 rb2501.SHFE。添加后需「初始化」再「启动」。</p>
          </el-form-item>
          <el-form-item label="账户 gateway">
            <el-select v-model="form.setting.gateway_name" clearable filterable placeholder="可选" style="width: 100%">
              <el-option
                v-for="g in trade.gateways"
                :key="String(g.gateway_name)"
                :label="String(g.account_name || g.gateway_name)"
                :value="String(g.gateway_name)"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-for="(defVal, key) in paramSchema" :key="String(key)" :label="String(key)">
            <el-input-number
              v-if="typeof defVal === 'number'"
              v-model="form.setting[String(key)]"
              :controls="false"
              style="width: 100%"
            />
            <el-switch v-else-if="typeof defVal === 'boolean'" v-model="form.setting[String(key)]" />
            <el-input v-else-if="String(key) !== 'gateway_name'" v-model="form.setting[String(key)]" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveInstance">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { http } from "@/api";
import { useAuthStore, useStrategyStore, useTradeStore } from "@/stores";

const route = useRoute();
const auth = useAuthStore();
const strategy = useStrategyStore();
const trade = useTradeStore();
const section = computed(() => String(route.params.section || "cta"));

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const editingName = ref("");
const classes = ref<{ class_name: string; parameters: Record<string, unknown> }[]>([]);
const paramSchema = ref<Record<string, unknown>>({});
const form = reactive({
  class_name: "",
  strategy_name: "",
  vt_symbol: "",
  setting: {} as Record<string, unknown>,
});

const btClasses = ref<{ class_name: string; parameters: Record<string, unknown> }[]>([]);
const btRunning = ref(false);
const btStats = ref<Record<string, unknown> | null>(null);
const btForm = reactive({
  class_name: "",
  vt_symbol: "rb2501.SHFE",
  interval: "1m",
  start: "2024-01-01",
  end: "2024-06-01",
});

function formatMap(value: unknown) {
  if (!value || typeof value !== "object") return "—";
  return Object.entries(value as Record<string, unknown>)
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
}

function stopStatusType(status: unknown) {
  const s = String(status || "");
  if (s === "WAITING" || s === "等待中") return "warning";
  if (s === "TRIGGERED" || s === "已触发") return "success";
  return "info";
}

async function loadClasses() {
  const { data } = await http.get("/api/cta/strategies");
  classes.value = Array.isArray(data) ? data : [];
}

function onClassChange(name: string) {
  const found = classes.value.find((c) => c.class_name === name);
  const params = { ...(found?.parameters || {}) };
  delete params.gateway_name;
  paramSchema.value = params;
  form.setting = { ...params, gateway_name: form.setting.gateway_name || "" };
}

function openAdd() {
  editingName.value = "";
  form.class_name = classes.value[0]?.class_name || "";
  form.strategy_name = "";
  form.vt_symbol = "";
  form.setting = {};
  if (form.class_name) onClassChange(form.class_name);
  dialogVisible.value = true;
}

function openEdit(row: Record<string, unknown>) {
  editingName.value = String(row.strategy_name || "");
  form.class_name = String(row.class_name || "");
  const params = { ...((row.parameters as Record<string, unknown>) || {}) };
  paramSchema.value = Object.fromEntries(Object.entries(params).filter(([k]) => k !== "gateway_name"));
  form.setting = { ...params };
  dialogVisible.value = true;
}

async function saveInstance() {
  saving.value = true;
  try {
    if (editingName.value) {
      await http.patch(`/api/cta/instances/${encodeURIComponent(editingName.value)}`, { setting: form.setting });
      ElMessage.success("已更新参数");
    } else {
      if (!form.class_name || !form.strategy_name || !form.vt_symbol) {
        ElMessage.warning("请填写策略类 / 实例名 / 合约");
        return;
      }
      await http.post("/api/cta/instances", {
        class_name: form.class_name,
        strategy_name: form.strategy_name,
        vt_symbol: form.vt_symbol,
        setting: form.setting,
      });
      ElMessage.success("已添加策略实例");
    }
    dialogVisible.value = false;
    await strategy.refresh();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function act(row: Record<string, unknown>, action: string) {
  const name = String(row.strategy_name || "");
  try {
    await http.post(`/api/cta/instances/${encodeURIComponent(name)}/${action}`);
    ElMessage.success("已发送");
    await strategy.refresh();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "操作失败");
  }
}

async function remove(row: Record<string, unknown>) {
  const name = String(row.strategy_name || "");
  await ElMessageBox.confirm(`确认移除策略「${name}」？`, "移除策略", { type: "warning" });
  try {
    await http.delete(`/api/cta/instances/${encodeURIComponent(name)}`);
    ElMessage.success("已移除");
    await strategy.refresh();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "移除失败");
  }
}

async function batch(action: string) {
  await ElMessageBox.confirm(`确认执行「${action}」？`, "批量操作", { type: "warning" });
  try {
    await http.post(`/api/cta/instances/${action}`);
    ElMessage.success("已发送");
    await strategy.refresh();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "操作失败");
  }
}

async function loadBacktestClasses() {
  try {
    const { data } = await http.get("/api/backtest/strategies");
    btClasses.value = Array.isArray(data) ? data : [];
    if (!btForm.class_name && btClasses.value[0]) btForm.class_name = btClasses.value[0].class_name;
  } catch {
    btClasses.value = [];
  }
}

async function runBacktest() {
  btRunning.value = true;
  try {
    const { data } = await http.post("/api/backtest/run", { ...btForm, setting: {} });
    ElMessage.success(data?.note || "回测已启动");
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "启动失败");
  } finally {
    btRunning.value = false;
  }
}

async function loadBacktestResult() {
  try {
    const { data } = await http.get("/api/backtest/result");
    btStats.value = data?.statistics || null;
    if (data?.empty) ElMessage.info(data?.note || "暂无结果");
  } catch {
    btStats.value = null;
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await Promise.all([strategy.refresh(), loadClasses(), trade.refresh(), loadBacktestClasses()]);
  } finally {
    loading.value = false;
  }
});

watch(section, (s) => {
  if (s === "backtest") void loadBacktestResult();
  if (s === "cta" || !s) void strategy.refresh();
});
</script>
