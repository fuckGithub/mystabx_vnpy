<template>
  <div v-loading="loading" class="page-shell strategy-detail">
    <header class="sd-header">
      <div class="sd-header__left">
        <el-button class="sd-back" link @click="goList">←</el-button>
        <span class="sd-title-prefix">策略模型</span>
        <span class="sd-title-sep">|</span>
        <h3 class="sd-title" :title="displayTitle">{{ displayTitle }}</h3>
        <el-tag size="small" effect="plain" type="info">{{ model?.class_name || "—" }}</el-tag>
        <el-tag size="small" effect="plain" type="success">
          {{ selectedVersionLabel }}
        </el-tag>
      </div>
      <nav class="sd-top-tabs" aria-label="模型视图">
        <button
          v-for="tab in topTabs"
          :key="tab.key"
          type="button"
          class="sd-top-tab"
          :class="{ 'is-active': mainTab === tab.key }"
          @click="setMainTab(tab.key)"
        >
          {{ tab.label }}
        </button>
        <el-select
          v-model="selectedVersionId"
          size="small"
          clearable
          placeholder="运行版本"
          class="sd-version-select"
          @change="onVersionPick"
        >
          <el-option label="当前草稿" :value="0" />
          <el-option
            v-for="v in versions"
            :key="v.id"
            :label="`${v.label || 'v' + v.version_no}`"
            :value="v.id"
          />
        </el-select>
        <el-button
          size="small"
          :loading="saving"
          :disabled="!auth.isAdmin"
          @click="saveDraft"
        >
          保存
        </el-button>
        <el-button
          size="small"
          type="primary"
          :loading="savingVersion"
          :disabled="!auth.isAdmin"
          @click="saveAsNewVersion"
        >
          保存为新版本
        </el-button>
      </nav>
    </header>

    <div class="sd-body">
      <aside v-if="showSubnav" class="sd-subnav">
        <button
          v-for="item in subnavItems"
          :key="item.key"
          type="button"
          class="sd-subnav__item"
          :class="{ 'is-active': subTab === item.key }"
          @click="setSubTab(item.key)"
        >
          <span class="sd-subnav__icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </aside>

      <!-- 回测 / 详情 -->
      <section v-if="mainTab === 'backtest' || mainTab === 'report'" class="sd-main">
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

        <div v-if="subTab === 'overview'" class="sd-panel-scroll">
          <div class="sd-kpi sd-kpi--wide">
            <div v-for="item in kpiItemsWide" :key="item.key" class="sd-kpi__item">
              <div class="sd-kpi__label">{{ item.label }}</div>
              <div class="sd-kpi__value" :class="kpiClass(item)">{{ item.display }}</div>
            </div>
          </div>
          <div class="sd-chart-placeholder">
            <template v-if="btHasResult && btDaily.length">
              <el-table :data="btDaily.slice(-60)" size="small" max-height="420" class="sd-daily-table">
                <el-table-column prop="date" label="日期" width="110" />
                <el-table-column prop="net_pnl" label="净盈亏" width="100" />
                <el-table-column prop="balance" label="结余" width="110" />
                <el-table-column prop="drawdown" label="回撤" width="100" />
              </el-table>
            </template>
            <div v-else class="sd-empty-hint">
              {{ btRunning ? "回测运行中…" : "请先运行回测；结果将写入本模型详情（绑定所选版本）" }}
            </div>
          </div>
          <div v-if="backtestRuns.length" class="sd-history">
            <h4>历史运行</h4>
            <el-table :data="backtestRuns.slice(0, 20)" size="small" max-height="220">
              <el-table-column prop="created_at" label="时间" width="170" />
              <el-table-column prop="status" label="状态" width="80" />
              <el-table-column prop="model_version_id" label="版本ID" width="90" />
              <el-table-column prop="note" label="备注" min-width="140" show-overflow-tooltip />
            </el-table>
          </div>
        </div>

        <div v-else-if="subTab === 'daily'" class="sd-panel-scroll">
          <el-table :data="btDaily" size="small" height="100%" empty-text="暂无每日结果">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="net_pnl" label="净盈亏" width="110" />
            <el-table-column prop="balance" label="结余" width="120" />
            <el-table-column prop="drawdown" label="回撤" width="110" />
          </el-table>
        </div>

        <div v-else-if="subTab === 'trades'" class="sd-panel-scroll">
          <el-table :data="btTrades" size="small" height="100%" empty-text="暂无回测成交">
            <el-table-column prop="datetime" label="时间" min-width="160" show-overflow-tooltip />
            <el-table-column prop="direction" label="方向" width="70" />
            <el-table-column prop="offset" label="开平" width="70" />
            <el-table-column prop="price" label="价格" width="90" />
            <el-table-column prop="volume" label="量" width="70" />
          </el-table>
        </div>

        <div v-else class="sd-panel-scroll sd-console-full">
          <pre v-if="consoleLines.length">{{ consoleLines.join("\n") }}</pre>
          <pre v-else class="sd-console__empty">暂无日志 — 保存 / 运行后将显示输出</pre>
        </div>
      </section>

      <!-- 模型编辑 = 代码 -->
      <section v-else-if="mainTab === 'code'" class="sd-ide">
        <section class="sd-editor-pane">
          <div class="sd-editor-toolbar">
            <el-tag size="small" effect="plain">{{ model?.parent_template || "CtaTemplate" }}</el-tag>
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
            <div class="sd-editor-toolbar__spacer" />
            <el-button size="small" text :disabled="!auth.isAdmin" @click="saveDraft">保存草稿</el-button>
            <el-button
              size="small"
              text
              type="primary"
              :loading="savingVersion"
              :disabled="!auth.isAdmin"
              @click="saveAsNewVersion"
            >
              保存为新版本
            </el-button>
            <button type="button" class="sd-zoom" title="放大" @click="zoomEditor(1)">＋</button>
            <button type="button" class="sd-zoom" title="缩小" @click="zoomEditor(-1)">－</button>
          </div>
          <div class="sd-editor-wrap">
            <div class="sd-gutter" aria-hidden="true">
              <span v-for="n in lineCount" :key="n">{{ n }}</span>
            </div>
            <textarea
              v-model="sourceContent"
              class="sd-code-area"
              :style="{ fontSize: editorFontSize + 'px' }"
              :readonly="!auth.isAdmin"
              spellcheck="false"
              wrap="off"
              @keydown.tab.prevent="onTab"
            />
          </div>
          <div class="sd-editor-foot">
            <span>MySQL · {{ model?.class_name }}</span>
            <span>普通保存不升版本</span>
          </div>
        </section>

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
          <div class="sd-console" :style="{ flexBasis: consoleHeightPct + '%' }">
            <div class="sd-console__head" @mousedown="startConsoleResize">运行日志</div>
            <pre v-if="consoleLines.length">{{ consoleLines.join("\n") }}</pre>
            <pre v-else class="sd-console__empty">点击「运行」：从库加载合约/参数/配置/源码并回测</pre>
          </div>
        </section>
      </section>

      <!-- 模型参数 -->
      <section v-else class="sd-settings">
        <el-form label-width="120px" class="sd-settings-form" style="max-width: 720px">
          <el-divider content-position="left">订阅合约</el-divider>
          <el-form-item label="合约 vt_symbol">
            <el-input v-model="btForm.vt_symbol" placeholder="rb2501.SHFE" />
          </el-form-item>
          <el-divider content-position="left">基础配置</el-divider>
          <el-form-item label="周期">
            <el-select v-model="baseConfig.interval" style="width: 200px">
              <el-option label="1m" value="1m" />
              <el-option label="1h" value="1h" />
              <el-option label="d" value="d" />
            </el-select>
          </el-form-item>
          <el-form-item label="初始资金">
            <el-input-number v-model="baseConfig.capital" :min="1000" :step="10000" />
          </el-form-item>
          <el-form-item label="手续费率">
            <el-input-number v-model="baseConfig.rate" :step="0.0001" :precision="6" />
          </el-form-item>
          <el-form-item label="滑点">
            <el-input-number v-model="baseConfig.slippage" :step="0.1" />
          </el-form-item>
          <el-form-item label="合约乘数">
            <el-input-number v-model="baseConfig.size" :min="1" :step="1" />
          </el-form-item>
          <el-form-item label="最小变动">
            <el-input-number v-model="baseConfig.pricetick" :step="0.1" />
          </el-form-item>
          <el-divider content-position="left">策略参数</el-divider>
          <el-form-item v-for="(val, key) in settingForm" :key="key" :label="String(key)">
            <el-input v-model="settingForm[key]" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" :disabled="!auth.isAdmin" @click="saveDraft">
              保存参数（不升版本）
            </el-button>
            <el-button
              type="success"
              :loading="savingVersion"
              :disabled="!auth.isAdmin"
              @click="saveAsNewVersion"
            >
              保存为新版本
            </el-button>
          </el-form-item>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { http } from "@/api";
import { useAuthStore, useStrategyStore } from "@/stores";

type MainTab = "backtest" | "report" | "code" | "settings";
type SubTab = "overview" | "daily" | "trades" | "logs";

type ModelRow = {
  id: number;
  code: string;
  name: string;
  class_name: string;
  parent_template: string;
  default_params: Record<string, unknown>;
  template_source?: string;
  vt_symbol?: string;
  base_config?: Record<string, unknown>;
  latest_version_id?: number | null;
};

type VersionRow = {
  id: number;
  version_no: number;
  label: string;
  note: string;
  params: Record<string, unknown>;
  template_source?: string;
};

const auth = useAuthStore();
const strategy = useStrategyStore();
const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const savingVersion = ref(false);
const model = ref<ModelRow | null>(null);
const versions = ref<VersionRow[]>([]);
const selectedVersionId = ref<number>(0);
const sourceContent = ref("");
const editorFontSize = ref(13);
const settingForm = reactive<Record<string, string>>({});
const baseConfig = reactive({
  interval: "1m",
  capital: 1_000_000,
  rate: 0,
  slippage: 0,
  size: 10,
  pricetick: 1,
});
const btRange = ref<[string, string] | null>(null);
const btForm = reactive({
  vt_symbol: "rb2501.SHFE",
  interval: "1m",
  capital: 1_000_000,
});
const btRunning = ref(false);
const btHasResult = ref(false);
const btStats = ref<Record<string, unknown> | null>(null);
const btDaily = ref<Record<string, unknown>[]>([]);
const btTrades = ref<Record<string, unknown>[]>([]);
const backtestRuns = ref<Record<string, unknown>[]>([]);
const consoleHeightPct = ref(38);
const localLogs = ref<string[]>([]);

const topTabs: { key: MainTab; label: string }[] = [
  { key: "code", label: "模型编辑" },
  { key: "settings", label: "模型参数" },
  { key: "backtest", label: "策略回测" },
  { key: "report", label: "详情分析" },
];

const subnavItems: { key: SubTab; label: string; icon: string }[] = [
  { key: "overview", label: "结果概览", icon: "概" },
  { key: "daily", label: "每日明细", icon: "日" },
  { key: "trades", label: "成交记录", icon: "成" },
  { key: "logs", label: "运行日志", icon: "志" },
];

const modelId = computed(() => Number(route.params.id || 0));
const displayTitle = computed(() => model.value?.name || "—");
const selectedVersionLabel = computed(() => {
  if (!selectedVersionId.value) return "当前草稿";
  const v = versions.value.find((x) => x.id === selectedVersionId.value);
  return v ? v.label || `v${v.version_no}` : `版本#${selectedVersionId.value}`;
});

const mainTab = computed<MainTab>(() => {
  const raw = String(route.query.tab || "code").toLowerCase();
  if (raw === "backtest" || raw === "bt") return "backtest";
  if (raw === "settings" || raw === "params") return "settings";
  if (raw === "report" || raw === "analysis") return "report";
  return "code";
});

const subTab = computed<SubTab>(() => {
  const raw = String(route.query.sub || "overview").toLowerCase();
  if (raw === "daily" || raw === "trades" || raw === "logs") return raw;
  return "overview";
});

const showSubnav = computed(() => mainTab.value === "backtest" || mainTab.value === "report");
const lineCount = computed(() => Math.max(1, (sourceContent.value || "").split("\n").length));

const consoleLines = computed(() => {
  const lines = [...localLogs.value];
  for (const row of strategy.backtestLogs) {
    lines.push(`[backtest] ${String((row as { msg?: string }).msg || JSON.stringify(row))}`);
  }
  return lines;
});

function buildKpi(keys: { key: string; label: string; aliases?: string[] }[]) {
  const s = btStats.value || {};
  return keys.map((item) => {
    let value: unknown = s[item.key];
    if ((value == null || value === "") && item.aliases) {
      for (const a of item.aliases) {
        if (s[a] != null && s[a] !== "") {
          value = s[a];
          break;
        }
      }
    }
    return { key: item.key, label: item.label, value, display: formatKpi(value) };
  });
}

const kpiItems = computed(() =>
  buildKpi([
    { key: "total_return", label: "收益", aliases: ["总收益率"] },
    { key: "annual_return", label: "年化", aliases: ["年化收益"] },
    { key: "sharpe_ratio", label: "Sharpe", aliases: ["夏普比率"] },
    { key: "max_ddpercent", label: "最大回撤", aliases: ["max_drawdown", "最大回撤"] },
  ]),
);

const kpiItemsWide = computed(() =>
  buildKpi([
    { key: "total_return", label: "总收益率", aliases: ["总收益率"] },
    { key: "annual_return", label: "年化收益", aliases: ["年化收益"] },
    { key: "max_ddpercent", label: "最大回撤", aliases: ["max_drawdown", "最大回撤"] },
    { key: "sharpe_ratio", label: "夏普比率", aliases: ["夏普比率"] },
    { key: "total_net_pnl", label: "总盈亏", aliases: ["总盈亏"] },
    { key: "total_trade_count", label: "总成交笔数", aliases: ["总成交次数"] },
  ]),
);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let resizeStartY = 0;
let resizeStartPct = 38;
let rightColEl: HTMLElement | null = null;

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
  if (item.key.includes("drawdown") || item.key.includes("ddpercent")) return n < 0 ? "is-neg" : "";
  if (n > 0) return "is-pos";
  if (n < 0) return "is-neg";
  return "";
}

function goList() {
  router.push("/strategy/models");
}

function setMainTab(tab: MainTab) {
  const q: Record<string, string> = { ...route.query } as Record<string, string>;
  q.tab = tab;
  if (tab === "backtest" || tab === "report") {
    if (!q.sub) q.sub = "overview";
  } else {
    delete q.sub;
  }
  router.replace({ path: route.path, query: q });
}

function setSubTab(sub: SubTab) {
  router.replace({
    path: route.path,
    query: { ...route.query, tab: mainTab.value === "backtest" ? "backtest" : "report", sub },
  });
}

function zoomEditor(delta: number) {
  editorFontSize.value = Math.min(20, Math.max(11, editorFontSize.value + delta));
}

function onTab(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  const start = el.selectionStart;
  const end = el.selectionEnd;
  sourceContent.value = `${sourceContent.value.slice(0, start)}    ${sourceContent.value.slice(end)}`;
  requestAnimationFrame(() => {
    el.selectionStart = el.selectionEnd = start + 4;
  });
}

function syncSettingForm(params: Record<string, unknown>) {
  Object.keys(settingForm).forEach((k) => delete settingForm[k]);
  for (const [k, v] of Object.entries(params || {})) {
    settingForm[k] = String(v ?? "");
  }
}

function collectParams(): Record<string, unknown> {
  const setting: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(settingForm)) {
    const num = Number(v);
    setting[k] = v.trim() !== "" && Number.isFinite(num) && String(num) === v.trim() ? num : v;
  }
  return setting;
}

function applyModel(data: ModelRow, keepVersion = false) {
  model.value = data;
  sourceContent.value = String(data.template_source || "");
  btForm.vt_symbol = String(data.vt_symbol || "rb2501.SHFE");
  const cfg = (data.base_config || {}) as Record<string, number | string>;
  baseConfig.interval = String(cfg.interval || "1m");
  baseConfig.capital = Number(cfg.capital ?? 1_000_000);
  baseConfig.rate = Number(cfg.rate ?? 0);
  baseConfig.slippage = Number(cfg.slippage ?? 0);
  baseConfig.size = Number(cfg.size ?? 10);
  baseConfig.pricetick = Number(cfg.pricetick ?? 1);
  btForm.interval = baseConfig.interval;
  btForm.capital = baseConfig.capital;
  syncSettingForm(data.default_params || {});
  if (!keepVersion) selectedVersionId.value = 0;
}

async function loadModel() {
  const id = modelId.value;
  if (!id) return;
  loading.value = true;
  try {
    const [{ data }, verRes, btRes] = await Promise.all([
      http.get(`/api/cta/models/${id}`),
      http.get(`/api/cta/models/${id}/versions`),
      http.get(`/api/cta/models/${id}/backtests`),
    ]);
    applyModel(data);
    versions.value = Array.isArray(verRes.data) ? verRes.data : [];
    backtestRuns.value = Array.isArray(btRes.data) ? btRes.data : [];
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "加载模型失败");
  } finally {
    loading.value = false;
  }
}

function onVersionPick(vid: number | null) {
  if (!vid) {
    if (model.value) applyModel(model.value);
    return;
  }
  const v = versions.value.find((x) => x.id === vid);
  if (!v) return;
  sourceContent.value = String(v.template_source || sourceContent.value);
  syncSettingForm(v.params || {});
  localLogs.value.push(`[info] 已载入版本 ${v.label || "v" + v.version_no}（未自动保存）`);
}

async function saveDraft(): Promise<boolean> {
  const id = modelId.value;
  if (!id) return false;
  saving.value = true;
  try {
    const { data } = await http.put(`/api/cta/models/${id}/draft`, {
      template_source: sourceContent.value,
      params: collectParams(),
      vt_symbol: btForm.vt_symbol,
      base_config: {
        interval: baseConfig.interval,
        capital: baseConfig.capital,
        rate: baseConfig.rate,
        slippage: baseConfig.slippage,
        size: baseConfig.size,
        pricetick: baseConfig.pricetick,
      },
    });
    applyModel(data, true);
    localLogs.value.push("[ok] 草稿已保存（版本号未变）");
    ElMessage.success("已保存草稿（未升版本）");
    return true;
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存失败");
    return false;
  } finally {
    saving.value = false;
  }
}

async function saveAsNewVersion() {
  const id = modelId.value;
  if (!id) return;
  let note = "";
  try {
    const { value } = await ElMessageBox.prompt("版本备注（可选）", "保存为新版本", {
      confirmButtonText: "保存",
      cancelButtonText: "取消",
      inputPlaceholder: "例如：调整均线窗口",
    });
    note = value || "";
  } catch {
    return;
  }
  savingVersion.value = true;
  try {
    // Persist draft first so version snapshot matches editor
    await http.put(`/api/cta/models/${id}/draft`, {
      template_source: sourceContent.value,
      params: collectParams(),
      vt_symbol: btForm.vt_symbol,
      base_config: { ...baseConfig },
    });
    const { data } = await http.post(`/api/cta/models/${id}/versions`, {
      params: collectParams(),
      template_source: sourceContent.value,
      note,
    });
    ElMessage.success(`已创建 ${data?.label || "新版本"}`);
    localLogs.value.push(`[ok] 已保存为新版本 ${data?.label || ""}`);
    await loadModel();
    if (data?.id) selectedVersionId.value = Number(data.id);
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存版本失败");
  } finally {
    savingVersion.value = false;
  }
}

async function loadBacktest() {
  try {
    const [statusRes, resultRes, tradesRes] = await Promise.all([
      http.get("/api/backtest/status"),
      http.get("/api/backtest/result"),
      http.get("/api/backtest/trades"),
    ]);
    const wasRunning = btRunning.value;
    btRunning.value = Boolean(statusRes.data?.running);
    btHasResult.value = Boolean(statusRes.data?.has_result);
    btStats.value = (resultRes.data?.statistics as Record<string, unknown>) || null;
    btDaily.value = Array.isArray(resultRes.data?.daily_results) ? resultRes.data.daily_results : [];
    btTrades.value = Array.isArray(tradesRes.data) ? tradesRes.data : [];
    if (wasRunning && !btRunning.value && modelId.value) {
      try {
        await http.post("/api/backtest/persist-result", null, {
          params: {
            model_id: modelId.value,
            model_version_id: selectedVersionId.value || model.value?.latest_version_id || undefined,
          },
        });
        localLogs.value.push("[ok] 回测结果已写入模型详情");
        const { data } = await http.get(`/api/cta/models/${modelId.value}/backtests`);
        backtestRuns.value = Array.isArray(data) ? data : [];
      } catch {
        /* best-effort */
      }
    }
  } catch {
    btStats.value = null;
    btDaily.value = [];
    btTrades.value = [];
  }
}

async function runBacktest() {
  if (!auth.isAdmin || !modelId.value) return;
  const [start, end] = btRange.value || [];
  if (!start || !end) {
    ElMessage.warning("请选择回测区间");
    return;
  }
  // Save draft so DB has latest 合约/参数/配置/源码 before run loads them
  const ok = await saveDraft();
  if (!ok) return;
  btRunning.value = true;
  localLogs.value.push("[run] 从 MySQL 加载合约/参数/基础配置/源码并启动回测…");
  try {
    const { data } = await http.post("/api/backtest/run", {
      model_id: modelId.value,
      model_version_id: selectedVersionId.value > 0 ? selectedVersionId.value : undefined,
      start,
      end,
      // UI overrides for this run session
      vt_symbol: btForm.vt_symbol,
      interval: btForm.interval,
      capital: btForm.capital,
    });
    ElMessage.success(data?.note || "回测已启动");
    localLogs.value.push(
      `[run] class=${data?.class_name} symbol=${data?.vt_symbol} version=${data?.run_context?.version_label || "draft"}`,
    );
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

function startConsoleResize(e: MouseEvent) {
  const target = e.currentTarget as HTMLElement | null;
  rightColEl = target?.parentElement || null;
  if (!rightColEl) return;
  resizeStartY = e.clientY;
  resizeStartPct = consoleHeightPct.value;
  window.addEventListener("mousemove", onConsoleResize);
  window.addEventListener("mouseup", stopConsoleResize);
}

function onConsoleResize(e: MouseEvent) {
  if (!rightColEl) return;
  const h = rightColEl.getBoundingClientRect().height || 1;
  const deltaPct = ((resizeStartY - e.clientY) / h) * 100;
  consoleHeightPct.value = Math.min(60, Math.max(22, resizeStartPct + deltaPct));
}

function stopConsoleResize() {
  window.removeEventListener("mousemove", onConsoleResize);
  window.removeEventListener("mouseup", stopConsoleResize);
  rightColEl = null;
}

watch(modelId, () => {
  loadModel();
});

onMounted(async () => {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 1);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  btRange.value = [fmt(start), fmt(end)];
  await loadModel();
  await loadBacktest();
});

onUnmounted(() => {
  stopPolling();
  stopConsoleResize();
});
</script>

<style scoped src="@/styles/strategy-detail.css"></style>
<style scoped>
.sd-version-select {
  width: 140px;
  margin-right: 8px;
}
.sd-history {
  margin-top: 16px;
}
.sd-history h4 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
}
.sd-settings {
  flex: 1;
  overflow: auto;
  padding: 16px 20px;
}
</style>
