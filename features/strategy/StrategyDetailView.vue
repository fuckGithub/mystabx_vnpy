<template>
  <div v-loading="loading" class="page-shell strategy-detail">
    <header class="sd-header">
      <div class="sd-header__left">
        <el-button class="sd-back" link @click="goList">←</el-button>
        <h3 class="sd-title">{{ displayTitle }}</h3>
        <el-tag size="small" effect="plain" type="info">Python</el-tag>
        <el-tag v-if="source.store" size="small" effect="plain" :type="storeTagType">
          {{ storeLabel }}
        </el-tag>
      </div>
      <div class="sd-header__actions">
        <el-button size="small" :loading="compiling" :disabled="!auth.isAdmin" @click="compileSave">
          编译
        </el-button>
        <el-button size="small" :disabled="!auth.isAdmin" @click="settingsVisible = true">策略设置</el-button>
        <el-button size="small" @click="goBacktest">回测历史</el-button>
        <el-button size="small" @click="goBacktest">回测列表</el-button>
      </div>
    </header>

    <div class="sd-ide">
      <!-- Left: code editor -->
      <section class="sd-editor-pane">
        <div class="sd-editor-toolbar">
          <el-button size="small" text @click="varsVisible = true">变量</el-button>
          <el-button
            size="small"
            text
            type="primary"
            :loading="btRunning"
            :disabled="!auth.isAdmin"
            @click="runBacktest"
          >
            运行
          </el-button>
          <el-button size="small" text @click="showApiHint">API</el-button>
          <div class="sd-editor-toolbar__spacer" />
          <el-button size="small" text :disabled="!auth.isAdmin || !source.editable" @click="loadDefaultTemplate">
            默认模板
          </el-button>
          <el-button
            size="small"
            text
            type="primary"
            :loading="savingCode"
            :disabled="!auth.isAdmin || !source.editable"
            @click="saveSource"
          >
            保存
          </el-button>
          <button type="button" class="sd-zoom" title="放大" @click="zoomEditor(1)">＋</button>
          <button type="button" class="sd-zoom" title="缩小" @click="zoomEditor(-1)">－</button>
        </div>
        <div class="sd-editor-wrap">
          <div class="sd-gutter" aria-hidden="true">
            <span v-for="n in lineCount" :key="n">{{ n }}</span>
          </div>
          <textarea
            ref="codeInputRef"
            v-model="source.content"
            class="sd-code-area"
            :style="{ fontSize: editorFontSize + 'px' }"
            :readonly="!auth.isAdmin || !source.editable"
            spellcheck="false"
            wrap="off"
            @keydown.tab.prevent="onTab"
          />
        </div>
        <div class="sd-editor-foot">
          <span>{{ source.file_path || "—" }}</span>
          <span v-if="parentClass">父类 {{ parentClass }}</span>
        </div>
      </section>

      <!-- Right: backtest config + KPI + console -->
      <section class="sd-right">
        <div class="sd-bt-bar">
          <el-date-picker
            v-model="btRange"
            type="daterange"
            size="small"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="结束"
            class="sd-bt-dates"
          />
          <el-input-number
            v-model="btForm.capital"
            size="small"
            :min="1000"
            :step="10000"
            controls-position="right"
            class="sd-bt-capital"
          />
          <el-select v-model="btForm.interval" size="small" class="sd-bt-interval">
            <el-option label="分钟" value="1m" />
            <el-option label="小时" value="1h" />
            <el-option label="日线" value="d" />
          </el-select>
          <el-input v-model="btForm.vt_symbol" size="small" placeholder="合约" class="sd-bt-symbol" />
          <el-button
            type="primary"
            size="small"
            :loading="btRunning"
            :disabled="!auth.isAdmin"
            @click="runBacktest"
          >
            运行回测
          </el-button>
        </div>

        <div class="sd-kpi">
          <div v-for="item in kpiItems" :key="item.key" class="sd-kpi__item">
            <div class="sd-kpi__label">{{ item.label }}</div>
            <div class="sd-kpi__value" :class="kpiClass(item)">{{ item.display }}</div>
          </div>
        </div>

        <div class="sd-result-area">
          <template v-if="btHasResult && btDaily.length">
            <el-table :data="btDaily.slice(-30)" size="small" height="100%" class="sd-daily-table">
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="net_pnl" label="净盈亏" width="100" />
              <el-table-column prop="balance" label="结余" width="100" />
              <el-table-column prop="drawdown" label="回撤" width="100" />
            </el-table>
          </template>
          <div v-else class="sd-empty-hint">
            {{ btRunning ? "回测运行中…" : "请先运行回测，查看收益曲线与统计指标" }}
          </div>
        </div>

        <div class="sd-console-pane">
          <div class="sd-console-tabs">
            <button
              type="button"
              class="sd-console-tab"
              :class="{ 'is-active': consoleTab === 'logs' }"
              @click="consoleTab = 'logs'"
            >
              日志
            </button>
            <button
              type="button"
              class="sd-console-tab"
              :class="{ 'is-active': consoleTab === 'trades' }"
              @click="consoleTab = 'trades'"
            >
              成交
            </button>
            <button
              type="button"
              class="sd-console-tab"
              :class="{ 'is-active': consoleTab === 'vars' }"
              @click="consoleTab = 'vars'"
            >
              变量
            </button>
          </div>
          <div v-if="consoleTab === 'logs'" class="sd-console">
            <pre v-if="consoleLines.length">{{ consoleLines.join("\n") }}</pre>
            <pre v-else class="sd-console__empty">暂无日志 — 保存 / 编译 / 回测后将显示输出</pre>
          </div>
          <div v-else-if="consoleTab === 'trades'" class="sd-console sd-console--table">
            <el-table :data="btTrades" size="small" height="100%" empty-text="暂无回测成交">
              <el-table-column prop="datetime" label="时间" min-width="150" show-overflow-tooltip />
              <el-table-column prop="direction" label="方向" width="70" />
              <el-table-column prop="offset" label="开平" width="70" />
              <el-table-column prop="price" label="价格" width="80" />
              <el-table-column prop="volume" label="量" width="60" />
            </el-table>
          </div>
          <div v-else class="sd-console">
            <pre>{{ variablesText }}</pre>
          </div>
        </div>
      </section>
    </div>

    <el-dialog v-model="settingsVisible" title="策略设置" width="480px" destroy-on-close>
      <el-form label-width="100px" @submit.prevent>
        <el-form-item v-for="(val, key) in settingForm" :key="String(key)" :label="String(key)">
          <el-input v-model="settingForm[key]" size="small" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!auth.isAdmin" @click="saveSettings">保存参数</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="varsVisible" title="策略变量" size="360px">
      <pre class="sd-drawer-pre">{{ variablesText }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useAuthStore, useStrategyStore } from "@/stores";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const strategy = useStrategyStore();

const loading = ref(false);
const savingCode = ref(false);
const compiling = ref(false);
const codeInputRef = ref<HTMLTextAreaElement | null>(null);
const instance = ref<Record<string, unknown> | null>(null);
const settingsVisible = ref(false);
const varsVisible = ref(false);
const consoleTab = ref<"logs" | "trades" | "vars">("logs");
const editorFontSize = ref(13);
const settingForm = reactive<Record<string, string>>({});

const btStats = ref<Record<string, unknown> | null>(null);
const btDaily = ref<Record<string, unknown>[]>([]);
const btTrades = ref<Record<string, unknown>[]>([]);
const btRunning = ref(false);
const btHasResult = ref(false);
const btRange = ref<[string, string] | null>(["2024-01-01", "2024-06-01"]);
const btForm = reactive({
  class_name: "",
  vt_symbol: "rb2501.SHFE",
  interval: "1m",
  capital: 1_000_000,
});

const source = reactive({
  content: "",
  file_path: "",
  editable: true,
  updated_at: "" as string | null,
  store: "" as string,
  is_default: false,
  parent_class: "" as string,
});

const name = computed(() => decodeURIComponent(String(route.params.name || "")));
const displayTitle = computed(() => String(instance.value?.strategy_name || name.value || "—"));
const parentClass = computed(() => source.parent_class || "EliteCtaTemplate");
const className = computed(() => String(instance.value?.class_name || btForm.class_name || ""));

const storeLabel = computed(() => {
  const s = source.store;
  if (s === "mysql_instance") return "MySQL·实例";
  if (s === "mysql") return "MySQL";
  if (s === "file") return "文件";
  if (s === "default") return "默认模板";
  return s || "";
});

const storeTagType = computed(() => {
  if (source.store?.startsWith("mysql")) return "success";
  if (source.store === "default") return "warning";
  return "info";
});

const lineCount = computed(() => Math.max(1, (source.content || "").split("\n").length));

const instanceLogs = computed(() =>
  strategy.logs.filter((row) => String(row.strategy_name || "") === name.value),
);

const consoleLines = computed(() => {
  const lines: string[] = [];
  for (const row of instanceLogs.value) {
    const t = formatLogTime(row.time);
    const level = String(row.level || "INFO").toUpperCase();
    lines.push(`[${t}] - ${level} - ${String(row.msg || "")}`);
  }
  for (const row of strategy.backtestLogs) {
    lines.push(`[backtest] - INFO - ${String((row as { msg?: string }).msg || JSON.stringify(row))}`);
  }
  return lines;
});

const variablesText = computed(() => {
  const params = instance.value?.parameters;
  const vars = instance.value?.variables;
  return [
    "=== parameters ===",
    formatMap(params),
    "",
    "=== variables ===",
    formatMap(vars),
    "",
    `pos = ${instance.value?.pos ?? "—"}`,
    `vt_symbol = ${instance.value?.vt_symbol ?? "—"}`,
  ].join("\n");
});

const kpiItems = computed(() => {
  const s = btStats.value || {};
  return [
    { key: "total_return", label: "收益", value: s.total_return ?? s["总收益率"] },
    { key: "annual_return", label: "基准收益", value: s.annual_return ?? s["年化收益"] },
    { key: "return_drawdown_ratio", label: "Alpha", value: s.return_drawdown_ratio },
    { key: "beta", label: "Beta", value: s.beta },
    { key: "sharpe_ratio", label: "Sharpe", value: s.sharpe_ratio ?? s["夏普比率"] },
    { key: "max_ddpercent", label: "最大回撤", value: s.max_ddpercent ?? s.max_drawdown ?? s["最大回撤"] },
  ].map((item) => ({
    ...item,
    display: formatKpi(item.value),
  }));
});

let pollTimer: ReturnType<typeof setInterval> | null = null;

function formatMap(value: unknown) {
  if (!value || typeof value !== "object") return "—";
  return Object.entries(value as Record<string, unknown>)
    .map(([k, v]) => `${k} = ${v}`)
    .join("\n");
}

function formatLogTime(value: unknown) {
  const raw = String(value || "").trim();
  if (!raw) return "—";
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;
  return raw.length > 19 ? raw.slice(0, 19).replace("T", " ") : raw.replace("T", " ");
}

function formatKpi(val: unknown) {
  if (val == null || val === "") return "—";
  if (typeof val === "number" && Number.isFinite(val)) {
    if (Math.abs(val) < 10) return val.toFixed(4);
    return val.toFixed(2);
  }
  return String(val);
}

function kpiClass(item: { key: string; value: unknown }) {
  if (item.value == null || item.value === "") return "";
  const n = Number(item.value);
  if (!Number.isFinite(n)) return "";
  if (item.key === "max_ddpercent" || item.key === "max_drawdown") return n < 0 ? "is-neg" : "";
  if (n > 0) return "is-pos";
  if (n < 0) return "is-neg";
  return "";
}

function goList() {
  router.push("/strategy/cta");
}

function goBacktest() {
  router.push("/strategy/backtest");
}

function showApiHint() {
  ElMessage.info(`父类 ${parentClass.value}（core.strategy_shim）；源码存 MySQL，运行前动态编译`);
}

function zoomEditor(delta: number) {
  editorFontSize.value = Math.min(20, Math.max(11, editorFontSize.value + delta));
}

function onTab(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  source.content = `${source.content.slice(0, start)}    ${source.content.slice(end)}`;
  requestAnimationFrame(() => {
    el.selectionStart = el.selectionEnd = start + 4;
  });
}

function syncSettingForm() {
  const params = (instance.value?.parameters as Record<string, unknown>) || {};
  Object.keys(settingForm).forEach((k) => delete settingForm[k]);
  for (const [k, v] of Object.entries(params)) {
    settingForm[k] = String(v ?? "");
  }
}

async function loadInstance() {
  const n = name.value;
  if (!n) return;
  try {
    const { data } = await http.get(`/api/cta/instances/${encodeURIComponent(n)}`);
    instance.value = data;
    btForm.class_name = String(data?.class_name || "");
    if (data?.vt_symbol) btForm.vt_symbol = String(data.vt_symbol);
    syncSettingForm();
  } catch {
    const found = strategy.instances.find((r) => String(r.strategy_name) === n) || null;
    instance.value = found;
    if (found) {
      btForm.class_name = String(found.class_name || "");
      if (found.vt_symbol) btForm.vt_symbol = String(found.vt_symbol);
      syncSettingForm();
    } else {
      ElMessage.error("策略实例不存在");
    }
  }
}

async function loadSource() {
  const n = name.value;
  if (!n) return;
  try {
    const { data } = await http.get(`/api/cta/instances/${encodeURIComponent(n)}/source`);
    applySource(data);
  } catch {
    // Fallback: class source or template
    const cn = className.value || "UserStrategy";
    try {
      const { data } = await http.get(`/api/cta/strategies/${encodeURIComponent(cn)}/source`);
      applySource(data);
    } catch {
      const { data } = await http.get("/api/cta/strategies/template", { params: { class_name: cn } });
      applySource(data);
    }
  }
}

function applySource(data: Record<string, unknown> | undefined) {
  if (!data) return;
  source.content = String(data.content ?? "");
  source.file_path = String(data.file_path ?? "");
  source.editable = data.editable !== false;
  source.updated_at = (data.updated_at as string) ?? null;
  source.store = String(data.store ?? "");
  source.is_default = Boolean(data.is_default);
  source.parent_class = String(
    (data as { parent_class?: string }).parent_class ||
      (data as { parent?: { parent_class?: string } }).parent?.parent_class ||
      "EliteCtaTemplate",
  );
}

async function loadDefaultTemplate() {
  const cn = className.value || "UserStrategy";
  const { data } = await http.get("/api/cta/strategies/template", { params: { class_name: cn } });
  applySource(data);
  ElMessage.success("已载入默认模板（未保存）");
}

async function saveSource() {
  const n = name.value;
  if (!n) return;
  savingCode.value = true;
  try {
    const { data } = await http.put(`/api/cta/instances/${encodeURIComponent(n)}/source`, {
      content: source.content,
      reload: true,
    });
    source.store = String(data?.store ?? "mysql_instance");
    source.updated_at = data?.updated_at ?? source.updated_at;
    source.is_default = false;
    ElMessage.success(data?.reloaded ? "已保存到 MySQL 并热加载" : "已保存到 MySQL");
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    savingCode.value = false;
  }
}

async function compileSave() {
  compiling.value = true;
  try {
    await saveSource();
  } finally {
    compiling.value = false;
  }
}

async function saveSettings() {
  const n = name.value;
  const setting: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(settingForm)) {
    const num = Number(v);
    setting[k] = v.trim() !== "" && Number.isFinite(num) && String(num) === v.trim() ? num : v;
  }
  try {
    await http.patch(`/api/cta/instances/${encodeURIComponent(n)}`, { setting });
    ElMessage.success("参数已更新");
    settingsVisible.value = false;
    await loadInstance();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存参数失败");
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

async function runBacktest() {
  if (!auth.isAdmin) return;
  const cn = className.value;
  if (!cn) {
    ElMessage.warning("缺少策略类名");
    return;
  }
  const [start, end] = btRange.value || [];
  if (!start || !end) {
    ElMessage.warning("请选择回测区间");
    return;
  }
  // Persist editor before run so DB is authoritative
  if (source.content.trim() && source.editable) {
    try {
      await http.put(`/api/cta/instances/${encodeURIComponent(name.value)}/source`, {
        content: source.content,
        reload: true,
      });
      source.store = "mysql_instance";
      source.is_default = false;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      ElMessage.error(err.response?.data?.detail || "保存源码失败，已取消回测");
      return;
    }
  }
  btRunning.value = true;
  consoleTab.value = "logs";
  try {
    const { data } = await http.post("/api/backtest/run", {
      class_name: cn,
      vt_symbol: btForm.vt_symbol,
      interval: btForm.interval,
      start,
      end,
      capital: btForm.capital,
      setting: {},
      strategy_name: name.value,
    });
    ElMessage.success(data?.note || "回测已启动");
    startPolling();
  } catch (e: unknown) {
    btRunning.value = false;
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "启动回测失败");
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    await loadBacktest();
    if (!btRunning.value) stopPolling();
  }, 1500);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function refreshAll() {
  loading.value = true;
  try {
    await Promise.all([strategy.refresh(), loadInstance()]);
    await loadSource();
    await loadBacktest();
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void refreshAll();
});

onUnmounted(() => stopPolling());

watch(
  () => route.params.name,
  () => {
    void refreshAll();
  },
);
</script>

<style scoped src="@/styles/strategy-detail.css"></style>
