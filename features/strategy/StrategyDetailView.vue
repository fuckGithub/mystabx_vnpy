<template>
  <div v-loading="loading" class="page-shell strategy-detail">
    <!-- JoinQuant-style header -->
    <header class="sd-header">
      <div class="sd-header__top">
        <div class="sd-header__title-wrap">
          <el-button class="sd-back" link type="primary" @click="goList">←</el-button>
          <h3 class="sd-title">{{ displayTitle }}</h3>
          <el-button
            class="sd-edit"
            link
            :icon="EditPen"
            :disabled="!auth.isAdmin || !!instance?.trading"
            title="重命名实例"
            @click="renameInstance"
          />
          <el-tag size="small" type="primary" effect="plain" class="sd-lang">Python</el-tag>
        </div>
        <div class="sd-header__actions">
          <el-button
            size="small"
            class="sd-btn-sim"
            :disabled="!auth.isAdmin || !instance?.inited || !!instance?.trading"
            @click="act('start')"
          >
            模拟交易
          </el-button>
          <el-button size="small" type="primary" @click="goBacktest">回测分析</el-button>
          <el-button size="small" :disabled="!auth.isAdmin" @click="act('init')">初始化</el-button>
          <el-button size="small" :disabled="!auth.isAdmin" @click="act('stop')">停止</el-button>
          <el-button size="small" :icon="Refresh" @click="refreshAll">刷新</el-button>
        </div>
      </div>
      <div class="sd-header__meta">
        <span class="sd-meta-item">
          <em>设置：</em>
          {{ settingsLine }}
        </span>
        <span class="sd-meta-item sd-meta-status">
          <em>状态：</em>
          <span class="sd-status-dot" :class="statusDotClass" />
          {{ statusLine }}
        </span>
      </div>
    </header>

    <div class="sd-body">
      <aside class="sd-aside">
        <nav class="sd-nav">
          <button
            v-for="item in primaryPanes"
            :key="item.key"
            type="button"
            class="sd-nav__item"
            :class="{ 'is-active': pane === item.key }"
            @click="onSelectPane(item.key)"
          >
            {{ item.label }}
          </button>
          <div class="sd-nav__sep" />
          <button
            v-for="item in metricPanes"
            :key="item.key"
            type="button"
            class="sd-nav__item sd-nav__item--metric"
            :class="{ 'is-active': pane === item.key }"
            @click="onSelectPane(item.key)"
          >
            {{ item.label }}
          </button>
        </nav>
      </aside>

      <main class="sd-main">
        <!-- 收益概述 -->
        <section v-if="pane === 'overview'" class="sd-panel">
          <h4 class="sd-panel__title">收益概述</h4>
          <el-descriptions
            v-if="btStats && Object.keys(btStats).length"
            :column="3"
            border
            size="small"
            class="sd-desc"
          >
            <el-descriptions-item v-for="(val, key) in btStats" :key="String(key)" :label="String(key)">
              {{ val }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无回测统计（可在「策略回测」运行后查看）" />
          <div class="sd-live">
            <h5>实盘状态</h5>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="仓位">{{ instance?.pos ?? "—" }}</el-descriptions-item>
              <el-descriptions-item label="参数">{{ formatMap(instance?.parameters) }}</el-descriptions-item>
              <el-descriptions-item label="变量">{{ formatMap(instance?.variables) }}</el-descriptions-item>
              <el-descriptions-item label="合约">{{ instance?.vt_symbol || "—" }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </section>

        <!-- 交易详情 -->
        <section v-else-if="pane === 'trades'" class="sd-panel">
          <h4 class="sd-panel__title">交易详情</h4>
          <el-table
            :data="btTrades"
            stripe
            border
            size="small"
            class="sd-table"
            empty-text="暂无回测成交（跑完回测后显示）"
          >
            <el-table-column prop="datetime" label="时间" min-width="160" show-overflow-tooltip />
            <el-table-column prop="vt_symbol" label="合约" width="120" />
            <el-table-column prop="direction" label="方向" width="80" />
            <el-table-column prop="offset" label="开平" width="80" />
            <el-table-column prop="price" label="价格" width="90" />
            <el-table-column prop="volume" label="数量" width="80" />
          </el-table>
        </section>

        <!-- 每日持仓&收益 -->
        <section v-else-if="pane === 'daily'" class="sd-panel">
          <h4 class="sd-panel__title">每日持仓&收益</h4>
          <el-table :data="btDaily" stripe border size="small" class="sd-table" empty-text="暂无每日结果">
            <el-table-column prop="date" label="日期" width="120" sortable />
            <el-table-column prop="close_price" label="收盘" width="100" />
            <el-table-column prop="net_pnl" label="净盈亏" width="110" />
            <el-table-column prop="balance" label="结余" width="110" />
            <el-table-column prop="drawdown" label="回撤" width="110" />
          </el-table>
        </section>

        <!-- 日志输出 — dark console -->
        <section v-else-if="pane === 'logs'" class="sd-panel">
          <h4 class="sd-panel__title">日志输出</h4>
          <div class="sd-console" tabindex="0">
            <pre v-if="consoleLines.length">{{ consoleLines.join("\n") }}</pre>
            <pre v-else class="sd-console__empty">暂无该实例或回测日志</pre>
          </div>
        </section>

        <!-- 性能分析 -->
        <section v-else-if="pane === 'perf'" class="sd-panel">
          <h4 class="sd-panel__title">性能分析</h4>
          <el-descriptions
            v-if="btStats && Object.keys(btStats).length"
            :column="2"
            border
            size="small"
            class="sd-desc"
          >
            <el-descriptions-item v-for="key in perfKeys" :key="key" :label="key">
              {{ btStats[key] ?? "—" }}
            </el-descriptions-item>
          </el-descriptions>
          <div v-else class="sd-console sd-console--hint">
            <pre>暂无性能数据。完成回测后可在此查看夏普、回撤等统计。</pre>
          </div>
        </section>

        <!-- 策略代码 -->
        <section v-else-if="pane === 'code'" class="sd-panel sd-code">
          <div class="sd-code__head">
            <h4 class="sd-panel__title">策略代码</h4>
            <span class="sd-code__path">{{ source.file_path || "—" }}</span>
            <div class="sd-code__btns">
              <el-button size="small" :disabled="!auth.isAdmin || !source.editable" @click="startEditCode">
                编写代码
              </el-button>
              <el-button size="small" :loading="loadingSource" @click="restoreCode">恢复代码</el-button>
              <el-button
                size="small"
                type="primary"
                :loading="savingCode"
                :disabled="!auth.isAdmin || !source.editable || !codeEditing"
                @click="saveSource"
              >
                保存并热加载
              </el-button>
            </div>
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
            ref="codeInputRef"
            v-model="source.content"
            type="textarea"
            :rows="22"
            class="sd-editor"
            :readonly="!auth.isAdmin || !source.editable || !codeEditing"
            spellcheck="false"
          />
          <div class="sd-code-history">
            <h5 class="sd-code-history__title">代码变更记录</h5>
            <el-table :data="codeHistoryRows" stripe border size="small" empty-text="暂无变更记录">
              <el-table-column prop="time" label="操作时间" width="180" />
              <el-table-column prop="method" label="操作方式" width="120" />
              <el-table-column prop="note" label="备注" min-width="200" />
              <el-table-column prop="code" label="代码" width="100" />
            </el-table>
          </div>
        </section>

        <!-- 滚动指标表 -->
        <section v-else class="sd-panel">
          <h4 class="sd-panel__title">{{ currentMetricLabel }}</h4>
          <el-table
            :data="metricTableRows"
            stripe
            border
            size="small"
            class="sd-table"
            empty-text="暂无滚动指标序列（后续接回测月度序列）"
          >
            <el-table-column prop="date" label="日期" width="120" sortable />
            <el-table-column prop="m1" label="1个月" align="center" />
            <el-table-column prop="m3" label="3个月" align="center" />
            <el-table-column prop="m6" label="6个月" align="center" />
            <el-table-column prop="m12" label="12个月" align="center" />
          </el-table>
          <p v-if="metricScalar != null" class="sd-scalar">
            当前回测统计：{{ currentMetricLabel }} =
            <strong>{{ formatMetric(metricScalar) }}</strong>
          </p>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
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
const loadingSource = ref(false);
const savingCode = ref(false);
const codeEditing = ref(false);
const codeInputRef = ref<{ focus?: () => void } | null>(null);
const instance = ref<Record<string, unknown> | null>(null);
const pane = ref(String(route.query.pane || "overview"));

const btStats = ref<Record<string, unknown> | null>(null);
const btDaily = ref<Record<string, unknown>[]>([]);
const btTrades = ref<Record<string, unknown>[]>([]);
const btRunning = ref(false);
const btHasResult = ref(false);

const source = reactive({
  content: "",
  file_path: "",
  editable: false,
  updated_at: "" as string | null,
});

/** Stub only — no JoinQuant history API */
const codeHistoryRows = ref<{ time: string; method: string; note: string; code: string }[]>([]);

const primaryPanes = [
  { key: "overview", label: "收益概述" },
  { key: "trades", label: "交易详情" },
  { key: "daily", label: "每日持仓&收益" },
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
  { key: "sortino", label: "索提诺比率", statKey: "" },
  { key: "info", label: "信息比率", statKey: "" },
  { key: "vol", label: "波动率", statKey: "" },
  { key: "vol_bench", label: "基准波动率", statKey: "" },
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

const consoleLines = computed(() => {
  const lines: string[] = [];
  for (const row of instanceLogs.value) {
    const t = formatLogTime(row.time);
    const level = String(row.level || "INFO").toUpperCase();
    const msg = String(row.msg || "");
    lines.push(`[${t}] - ${level} - ${msg}`);
  }
  for (const row of strategy.backtestLogs) {
    const msg = String((row as { msg?: string }).msg || JSON.stringify(row));
    lines.push(`[backtest] - INFO - ${msg}`);
  }
  return lines;
});

const settingsLine = computed(() => {
  const start = dateFromDaily(btDaily.value, "first");
  const end = dateFromDaily(btDaily.value, "last");
  const capital =
    (btStats.value?.capital as string | number | undefined) ??
    (instance.value?.parameters as Record<string, unknown> | undefined)?.capital ??
    "—";
  const interval =
    String((instance.value as { interval?: string } | null)?.interval || "").trim() || "—";
  const symbol = String(instance.value?.vt_symbol || "—");
  const range = start && end ? `${start} 到 ${end}` : "暂无回测区间";
  const capText = capital === "—" ? "资金 —" : `¥ ${capital}`;
  return `${range}，${capText}，${interval} · ${classLabel.value} · ${symbol}`;
});

const statusLine = computed(() => {
  if (btRunning.value) return "回测运行中";
  if (btHasResult.value) return "回测完成";
  if (instance.value?.trading) return "交易中（模拟）";
  if (instance.value?.inited) return "已初始化，待启动";
  return "未初始化";
});

const statusDotClass = computed(() => {
  if (btRunning.value) return "is-running";
  if (btHasResult.value || instance.value?.trading) return "is-ok";
  if (instance.value?.inited) return "is-warn";
  return "is-idle";
});

const currentMetric = computed(() => metricPanes.find((p) => p.key === pane.value));
const currentMetricLabel = computed(() => currentMetric.value?.label || pane.value);
const metricScalar = computed(() => {
  const key = currentMetric.value?.statKey;
  if (!key || !btStats.value) return null;
  return btStats.value[key] ?? null;
});
const metricTableRows = computed(
  () => [] as { date: string; m1: string; m3: string; m6: string; m12: string }[],
);

function dateFromDaily(rows: Record<string, unknown>[], which: "first" | "last") {
  if (!rows.length) return "";
  const row = which === "first" ? rows[0] : rows[rows.length - 1];
  const raw = row?.date ?? row?.Date;
  if (!raw) return "";
  return String(raw).slice(0, 10);
}

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

function formatMetric(val: unknown) {
  if (val == null || val === "") return "—";
  if (typeof val === "number" && Number.isFinite(val)) return val.toFixed(4);
  return String(val);
}

function goList() {
  router.push("/strategy/cta");
}

function goBacktest() {
  router.push("/strategy/backtest");
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
  loadingSource.value = true;
  try {
    const { data } = await http.get(`/api/cta/strategies/${encodeURIComponent(className)}/source`);
    source.content = String(data?.content ?? "");
    source.file_path = String(data?.file_path ?? "");
    source.editable = Boolean(data?.editable);
    source.updated_at = data?.updated_at ?? null;
    codeEditing.value = false;
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    source.content = "";
    source.editable = false;
    ElMessage.error(err.response?.data?.detail || "读取源码失败");
  } finally {
    loadingSource.value = false;
  }
}

async function startEditCode() {
  if (!auth.isAdmin || !source.editable) return;
  if (!source.content) await loadSource();
  codeEditing.value = true;
  await nextTick();
  codeInputRef.value?.focus?.();
}

async function restoreCode() {
  await loadSource();
  ElMessage.success("已从磁盘恢复代码");
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
    codeEditing.value = false;
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

<style scoped src="@/styles/strategy-detail.css"></style>
