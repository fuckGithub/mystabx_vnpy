<template>
  <div v-loading="loading" class="page-shell strategy-detail">
    <div class="strategy-detail__header">
      <div class="strategy-detail__title-row">
        <el-button link type="primary" @click="goList">← 返回列表</el-button>
        <h3 class="strategy-detail__title">
          {{ displayTitle }}
          <el-button
            link
            type="primary"
            :icon="EditPen"
            :disabled="!auth.isAdmin || !!instance?.trading"
            title="重命名实例"
            @click="renameInstance"
          />
        </h3>
        <el-tag size="small" type="info">Python</el-tag>
        <el-tag v-if="instance?.trading" size="small" type="success">交易中</el-tag>
        <el-tag v-else-if="instance?.inited" size="small" type="warning">已初始化</el-tag>
        <el-tag v-else size="small">未初始化</el-tag>
      </div>
      <div class="strategy-detail__meta">
        <span>策略类：{{ classLabel }}</span>
        <span>合约：{{ instance?.vt_symbol || "—" }}</span>
        <span>账户：{{ instance?.gateway_name || "—" }}</span>
        <span>源码：{{ instance?.file_path || "—" }}</span>
        <span v-if="btMeta">
          回测：{{ btMeta.start || "?" }} 到 {{ btMeta.end || "?" }}
          · 资金 {{ btMeta.capital ?? "—" }}
          · {{ btMeta.interval || "—" }}
          · {{ btRunning ? "运行中" : btHasResult ? "有结果" : "暂无结果" }}
        </span>
      </div>
      <div class="strategy-detail__actions">
        <el-button size="small" type="primary" :disabled="!auth.isAdmin" @click="act('init')">初始化</el-button>
        <el-button size="small" type="primary" :disabled="!auth.isAdmin || !instance?.inited" @click="act('start')">启动</el-button>
        <el-button size="small" :disabled="!auth.isAdmin" @click="act('stop')">停止</el-button>
        <el-button size="small" :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <div class="strategy-detail__body">
      <aside class="strategy-detail__aside">
        <el-menu :default-active="pane" @select="onSelectPane">
          <el-menu-item v-for="item in primaryPanes" :key="item.key" :index="item.key">
            {{ item.label }}
          </el-menu-item>
          <div class="strategy-detail__aside-sep" />
          <el-menu-item v-for="item in metricPanes" :key="item.key" :index="item.key">
            {{ item.label }}
          </el-menu-item>
        </el-menu>
      </aside>

      <main class="strategy-detail__main">
        <!-- 收益概述 -->
        <section v-if="pane === 'overview'" class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">收益概述</h4>
          <el-descriptions v-if="btStats && Object.keys(btStats).length" :column="3" border size="small">
            <el-descriptions-item v-for="(val, key) in btStats" :key="String(key)" :label="String(key)">
              {{ val }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无回测统计（可在「策略回测」运行后查看）" />
          <div class="strategy-detail__live">
            <h5>实盘状态</h5>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="仓位">{{ instance?.pos ?? "—" }}</el-descriptions-item>
              <el-descriptions-item label="参数">{{ formatMap(instance?.parameters) }}</el-descriptions-item>
              <el-descriptions-item label="变量">{{ formatMap(instance?.variables) }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </section>

        <!-- 交易详情 -->
        <section v-else-if="pane === 'trades'" class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">交易详情</h4>
          <el-table :data="btTrades" border size="small" empty-text="暂无回测成交（跑完回测后显示）">
            <el-table-column prop="datetime" label="时间" min-width="160" show-overflow-tooltip />
            <el-table-column prop="vt_symbol" label="合约" width="120" />
            <el-table-column prop="direction" label="方向" width="80" />
            <el-table-column prop="offset" label="开平" width="80" />
            <el-table-column prop="price" label="价格" width="90" />
            <el-table-column prop="volume" label="数量" width="80" />
          </el-table>
        </section>

        <!-- 每日持仓 -->
        <section v-else-if="pane === 'daily'" class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">每日持仓</h4>
          <el-table :data="btDaily" border size="small" empty-text="暂无每日结果">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="close_price" label="收盘" width="100" />
            <el-table-column prop="net_pnl" label="净盈亏" width="110" />
            <el-table-column prop="balance" label="结余" width="110" />
            <el-table-column prop="drawdown" label="回撤" width="110" />
          </el-table>
        </section>

        <!-- 日志输出 -->
        <section v-else-if="pane === 'logs'" class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">日志输出</h4>
          <el-table :data="instanceLogs" border size="small" max-height="480" empty-text="暂无该实例日志">
            <el-table-column label="时间" width="168">
              <template #default="{ row }">{{ formatLogTime(row.time) }}</template>
            </el-table-column>
            <el-table-column prop="level" label="级别" width="88" />
            <el-table-column prop="msg" label="内容" min-width="320" show-overflow-tooltip />
          </el-table>
          <el-divider content-position="left">回测日志</el-divider>
          <el-table :data="strategy.backtestLogs" border size="small" max-height="240" empty-text="暂无回测日志">
            <el-table-column prop="msg" label="内容" min-width="320" show-overflow-tooltip />
          </el-table>
        </section>

        <!-- 性能分析 -->
        <section v-else-if="pane === 'perf'" class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">性能分析</h4>
          <el-descriptions v-if="btStats && Object.keys(btStats).length" :column="2" border size="small">
            <el-descriptions-item v-for="key in perfKeys" :key="key" :label="key">
              {{ btStats[key] ?? "—" }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无性能数据" />
        </section>

        <!-- 策略代码 -->
        <section v-else-if="pane === 'code'" class="strategy-detail__panel strategy-detail__code">
          <div class="strategy-detail__code-toolbar">
            <h4 class="strategy-detail__panel-title">策略代码</h4>
            <span class="strategy-detail__code-path">{{ source.file_path || "—" }}</span>
            <el-button size="small" :icon="Refresh" @click="loadSource">重新加载</el-button>
            <el-button
              size="small"
              type="primary"
              :loading="savingCode"
              :disabled="!auth.isAdmin || !source.editable"
              @click="saveSource"
            >
              保存并热加载
            </el-button>
          </div>
          <el-alert
            v-if="source.editable === false"
            type="warning"
            :closable="false"
            show-icon
            title="内置策略只读；仅项目 strategies/ 下的源码可编辑。"
            style="margin-bottom: 8px"
          />
          <el-input
            v-model="source.content"
            type="textarea"
            :rows="28"
            class="strategy-detail__editor"
            :readonly="!auth.isAdmin || !source.editable"
            spellcheck="false"
          />
        </section>

        <!-- 指标表（占位 / 从统计取标量） -->
        <section v-else class="strategy-detail__panel">
          <h4 class="strategy-detail__panel-title">{{ currentMetricLabel }}</h4>
          <el-table :data="metricTableRows" border size="small" empty-text="暂无滚动指标数据（后续接回测序列）">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="m1" label="1个月" />
            <el-table-column prop="m3" label="3个月" />
            <el-table-column prop="m6" label="6个月" />
            <el-table-column prop="m12" label="12个月" />
          </el-table>
          <p v-if="metricScalar != null" class="strategy-detail__scalar">
            当前回测统计：{{ currentMetricLabel }} = <strong>{{ metricScalar }}</strong>
          </p>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { EditPen, Refresh } from "@element-plus/icons-vue";
import { http } from "@/api";
import { useAuthStore, useStrategyStore } from "@/stores";
import { strategyDisplayName } from "./strategyNames";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const strategy = useStrategyStore();

const loading = ref(false);
const savingCode = ref(false);
const instance = ref<Record<string, unknown> | null>(null);
const pane = ref(String(route.query.pane || "overview"));

const btStats = ref<Record<string, unknown> | null>(null);
const btDaily = ref<Record<string, unknown>[]>([]);
const btTrades = ref<Record<string, unknown>[]>([]);
const btRunning = ref(false);
const btHasResult = ref(false);
const btMeta = ref<Record<string, unknown> | null>(null);

const source = reactive({
  content: "",
  file_path: "",
  editable: false,
  updated_at: "" as string | null,
});

const primaryPanes = [
  { key: "overview", label: "收益概述" },
  { key: "trades", label: "交易详情" },
  { key: "daily", label: "每日持仓" },
  { key: "logs", label: "日志输出" },
  { key: "perf", label: "性能分析" },
  { key: "code", label: "策略代码" },
];

const metricPanes = [
  { key: "ret_strategy", label: "策略收益", statKey: "total_return" },
  { key: "ret_bench", label: "基准收益", statKey: "annual_return" },
  { key: "alpha", label: "阿尔法", statKey: "return_drawdown_ratio" },
  { key: "beta", label: "贝塔", statKey: "" },
  { key: "sharpe", label: "夏普比率", statKey: "sharpe_ratio" },
  { key: "maxdd", label: "最大回撤", statKey: "max_drawdown" },
];

const perfKeys = [
  "total_return",
  "annual_return",
  "max_drawdown",
  "max_ddpercent",
  "sharpe_ratio",
  "return_drawdown_ratio",
  "total_net_pnl",
  "daily_net_pnl",
];

const name = computed(() => decodeURIComponent(String(route.params.name || "")));

const displayTitle = computed(() => String(instance.value?.strategy_name || name.value || "—"));

const classLabel = computed(() =>
  strategyDisplayName(
    String(instance.value?.class_name || ""),
    String(instance.value?.display_name || "") || null,
  ),
);

const instanceLogs = computed(() =>
  strategy.logs.filter((row) => String(row.strategy_name || "") === name.value),
);

const currentMetric = computed(() => metricPanes.find((p) => p.key === pane.value));
const currentMetricLabel = computed(() => currentMetric.value?.label || pane.value);
const metricScalar = computed(() => {
  const key = currentMetric.value?.statKey;
  if (!key || !btStats.value) return null;
  return btStats.value[key] ?? null;
});
const metricTableRows = computed(() => [] as { date: string; m1: string; m3: string; m6: string; m12: string }[]);

function formatMap(value: unknown) {
  if (!value || typeof value !== "object") return "—";
  return Object.entries(value as Record<string, unknown>)
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
}

function formatLogTime(value: unknown) {
  const raw = String(value || "").trim();
  if (!raw) return "—";
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;
  return raw.length > 19 ? raw.slice(0, 19).replace("T", " ") : raw.replace("T", " ");
}

function goList() {
  router.push("/strategy/cta");
}

function onSelectPane(key: string) {
  pane.value = key;
  router.replace({ query: { ...route.query, pane: key } });
  if (key === "code") void loadSource();
  if (key === "trades" || key === "daily" || key === "overview" || key === "perf") void loadBacktest();
}

async function loadInstance() {
  const n = name.value;
  if (!n) return;
  try {
    const { data } = await http.get(`/api/cta/instances/${encodeURIComponent(n)}`);
    instance.value = data;
  } catch {
    const found = strategy.instances.find((r) => String(r.strategy_name) === n) || null;
    instance.value = found;
    if (!found) ElMessage.error("策略实例不存在");
  }
}

async function loadSource() {
  const className = String(instance.value?.class_name || "").trim();
  if (!className) {
    source.content = "";
    return;
  }
  try {
    const { data } = await http.get(`/api/cta/strategies/${encodeURIComponent(className)}/source`);
    source.content = String(data?.content ?? "");
    source.file_path = String(data?.file_path ?? "");
    source.editable = Boolean(data?.editable);
    source.updated_at = data?.updated_at ?? null;
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    source.content = "";
    source.editable = false;
    ElMessage.error(err.response?.data?.detail || "读取源码失败");
  }
}

async function saveSource() {
  const className = String(instance.value?.class_name || "").trim();
  if (!className) return;
  savingCode.value = true;
  try {
    const { data } = await http.put(`/api/cta/strategies/${encodeURIComponent(className)}/source`, {
      content: source.content,
      reload: true,
    });
    source.file_path = String(data?.file_path ?? source.file_path);
    source.updated_at = data?.updated_at ?? source.updated_at;
    ElMessage.success(data?.reloaded ? "已保存并热加载策略类" : "已保存");
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    savingCode.value = false;
  }
}

async function loadBacktest() {
  try {
    const [statusRes, resultRes, tradesRes] = await Promise.all([
      http.get("/api/backtest/status"),
      http.get("/api/backtest/result"),
      http.get("/api/backtest/trades"),
    ]);
    btRunning.value = Boolean(statusRes.data?.running);
    btHasResult.value = Boolean(statusRes.data?.has_result);
    btStats.value = (resultRes.data?.statistics as Record<string, unknown>) || null;
    btDaily.value = Array.isArray(resultRes.data?.daily_results) ? resultRes.data.daily_results : [];
    btTrades.value = Array.isArray(tradesRes.data) ? tradesRes.data : [];
    btMeta.value = btHasResult.value
      ? { start: "—", end: "—", capital: "—", interval: "—" }
      : null;
  } catch {
    btStats.value = null;
    btDaily.value = [];
    btTrades.value = [];
  }
}

async function refreshAll() {
  loading.value = true;
  try {
    await Promise.all([strategy.refresh(), loadInstance(), loadBacktest()]);
    if (pane.value === "code") await loadSource();
  } finally {
    loading.value = false;
  }
}

async function act(action: string) {
  const n = name.value;
  try {
    await http.post(`/api/cta/instances/${encodeURIComponent(n)}/${action}`);
    ElMessage.success("已发送");
    await loadInstance();
    await strategy.refresh();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "操作失败");
  }
}

async function renameInstance() {
  if (!auth.isAdmin) return;
  try {
    const { value } = await ElMessageBox.prompt("输入新的实例名称", "重命名策略实例", {
      inputValue: name.value,
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputPattern: /\S+/,
      inputErrorMessage: "名称不能为空",
    });
    const newName = String(value || "").trim();
    if (!newName || newName === name.value) return;
    const { data } = await http.post(`/api/cta/instances/${encodeURIComponent(name.value)}/rename`, {
      strategy_name: newName,
    });
    ElMessage.success("已重命名");
    await strategy.refresh();
    router.replace(`/strategy/detail/${encodeURIComponent(String(data?.strategy_name || newName))}`);
  } catch (e: unknown) {
    if (e === "cancel" || e === "close") return;
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "重命名失败");
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await Promise.all([strategy.refresh(), loadInstance(), loadBacktest()]);
    if (pane.value === "code") await loadSource();
  } finally {
    loading.value = false;
  }
});

watch(
  () => route.params.name,
  () => {
    void refreshAll();
  },
);
</script>

<style scoped>
.strategy-detail__header {
  margin-bottom: 12px;
}
.strategy-detail__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.strategy-detail__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.strategy-detail__meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.strategy-detail__actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.strategy-detail__body {
  display: flex;
  gap: 0;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  overflow: hidden;
}
.strategy-detail__aside {
  width: 168px;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
}
.strategy-detail__aside :deep(.el-menu) {
  border-right: none;
  background: transparent;
}
.strategy-detail__aside :deep(.el-menu-item) {
  height: 40px;
  line-height: 40px;
  font-size: 13px;
}
.strategy-detail__aside-sep {
  height: 1px;
  margin: 8px 12px;
  background: var(--el-border-color-lighter);
}
.strategy-detail__main {
  flex: 1;
  min-width: 0;
  padding: 16px;
  overflow: auto;
}
.strategy-detail__panel-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}
.strategy-detail__live {
  margin-top: 20px;
}
.strategy-detail__live h5 {
  margin: 0 0 8px;
  font-size: 14px;
}
.strategy-detail__code-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.strategy-detail__code-toolbar .strategy-detail__panel-title {
  margin: 0;
  margin-right: auto;
}
.strategy-detail__code-path {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.strategy-detail__editor :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
}
.strategy-detail__scalar {
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
