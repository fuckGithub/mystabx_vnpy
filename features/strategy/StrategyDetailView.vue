<template>
  <div v-loading="loading" class="page-shell strategy-detail">
    <header class="sd-header">
      <div class="sd-header__left">
        <el-button class="sd-back" link @click="goList">←</el-button>
        <span class="sd-title-prefix">策略详情</span>
        <span class="sd-title-sep">|</span>
        <template v-if="renaming">
          <el-input
            ref="renameInputRef"
            v-model="renameDraft"
            size="small"
            class="sd-rename-input"
            maxlength="64"
            @keydown.enter.prevent="commitRename"
            @keydown.esc.prevent="cancelRename"
          />
          <el-button size="small" type="primary" :loading="renamingBusy" @click="commitRename">确定</el-button>
          <el-button size="small" @click="cancelRename">取消</el-button>
        </template>
        <template v-else>
          <h3 class="sd-title" :title="displayTitle" @dblclick="startRename">{{ displayTitle }}</h3>
          <el-button
            v-if="auth.isAdmin"
            size="small"
            text
            type="primary"
            class="sd-rename-btn"
            @click="startRename"
          >
            重命名
          </el-button>
        </template>
        <el-tag size="small" effect="plain" type="info">Python</el-tag>
        <el-tag v-if="source.store" size="small" effect="plain" :type="storeTagType">
          {{ storeLabel }}
        </el-tag>
      </div>
      <nav class="sd-top-tabs" aria-label="实例视图">
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
        <el-button
          size="small"
          type="primary"
          :loading="savingCode"
          :disabled="!auth.isAdmin || !source.editable"
          @click="onHeaderSave"
        >
          保存
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

      <!-- 策略回测 / 详情分析 -->
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
              {{ btRunning ? "回测运行中…" : "请先运行回测，查看收益曲线与统计指标" }}
            </div>
          </div>
        </div>

        <div v-else-if="subTab === 'daily'" class="sd-panel-scroll">
          <el-table :data="btDaily" size="small" height="100%" empty-text="暂无每日结果">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="net_pnl" label="净盈亏" width="110" />
            <el-table-column prop="balance" label="结余" width="120" />
            <el-table-column prop="drawdown" label="回撤" width="110" />
            <el-table-column prop="turnover" label="成交额" min-width="100" />
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

        <div v-else-if="subTab === 'logs'" class="sd-panel-scroll sd-console-full">
          <pre v-if="consoleLines.length">{{ consoleLines.join("\n") }}</pre>
          <pre v-else class="sd-console__empty">暂无日志 — 保存 / 编译 / 回测后将显示输出</pre>
        </div>

        <div v-else class="sd-panel-scroll sd-console-full">
          <pre>{{ variablesText }}</pre>
        </div>
      </section>

      <!-- 代码编辑 -->
      <section v-else-if="mainTab === 'code'" class="sd-ide">
        <section class="sd-editor-pane">
          <div class="sd-editor-toolbar">
            <el-select
              v-model="selectedParent"
              size="small"
              class="sd-parent-select"
              placeholder="基类"
              :disabled="!auth.isAdmin || !source.editable"
              @change="onParentChange"
            >
              <el-option
                v-for="row in baseClasses"
                :key="row.class_name"
                :label="`${row.display_name || row.class_name}`"
                :value="row.class_name"
              />
            </el-select>
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
            <PythonCodeEditor
              v-model="source.content"
              :readonly="!auth.isAdmin || !source.editable"
              :font-size="editorFontSize"
            />
          </div>
          <div class="sd-editor-foot">
            <span>{{ source.file_path || "—" }}</span>
            <span v-if="parentClass">父类 {{ parentClass }}</span>
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

          <div
            class="sd-console-resize"
            title="拖动调整日志高度"
            @mousedown.prevent="startConsoleResize"
          />
          <div class="sd-console-pane" :style="{ height: consoleHeightPct + '%' }">
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
      </section>

      <!-- 参数配置 -->
      <section v-else class="sd-main sd-settings-pane">
        <el-form label-width="120px" class="sd-settings-form" @submit.prevent>
          <el-form-item label="策略模型">
            <el-select
              v-model="selectedModelId"
              clearable
              filterable
              placeholder="选择模型"
              style="width: 100%"
              :disabled="!auth.isAdmin"
              @change="onModelPick"
            >
              <el-option
                v-for="m in models"
                :key="m.id"
                :label="`${m.name}（${m.code}）`"
                :value="m.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="模型版本">
            <el-select
              v-model="selectedModelVersionId"
              clearable
              filterable
              placeholder="钉住的模型版本"
              style="width: 100%"
              :disabled="!auth.isAdmin || !selectedModelId"
              @change="onModelVersionPick"
            >
              <el-option
                v-for="v in modelVersions"
                :key="v.id"
                :label="`${v.label || 'v' + v.version_no} · #${v.id}`"
                :value="v.id"
              />
            </el-select>
            <p class="sd-hint">
              保存实例时会钉住所选模型版本；实盘初始化/启动与回测按钉住版本参数加载。
            </p>
          </el-form-item>
          <el-divider content-position="left">运行参数</el-divider>
          <el-form-item v-for="(val, key) in settingForm" :key="String(key)" :label="String(key)">
            <el-input v-model="settingForm[key]" size="small" />
          </el-form-item>
          <el-form-item v-if="!Object.keys(settingForm).length">
            <el-empty description="暂无可编辑参数" :image-size="72" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :disabled="!auth.isAdmin" @click="saveSettings">保存参数并建版本</el-button>
            <el-button :loading="compiling" :disabled="!auth.isAdmin" @click="compileSave">编译源码</el-button>
          </el-form-item>
        </el-form>

        <div class="sd-version-block">
          <h4>实例版本历史</h4>
          <el-table :data="instanceVersions" size="small" border empty-text="暂无实例版本">
            <el-table-column prop="version_no" label="#" width="48" />
            <el-table-column prop="model_version_id" label="模型版本" width="90" />
            <el-table-column label="运行参数" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ formatJson(row.runtime_params) }}</template>
            </el-table-column>
            <el-table-column prop="note" label="备注" min-width="100" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </div>

        <div class="sd-version-block">
          <h4>回测记录（按实例版本）</h4>
          <el-table :data="backtestRuns" size="small" border empty-text="暂无回测记录">
            <el-table-column prop="id" label="ID" width="64" />
            <el-table-column prop="instance_version_id" label="实例版本" width="90" />
            <el-table-column prop="model_version_id" label="模型版本" width="90" />
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column label="运行配置" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ formatJson(row.run_params) }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </div>
      </section>
    </div>

    <el-drawer v-model="varsVisible" title="策略变量" size="360px">
      <pre class="sd-drawer-pre">{{ variablesText }}</pre>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { http } from "@/api";
import { useAuthStore, useStrategyStore } from "@/stores";
import PythonCodeEditor from "@/components/PythonCodeEditor.vue";

type MainTab = "backtest" | "report" | "code" | "settings";
type SubTab = "overview" | "daily" | "trades" | "logs" | "vars";
type BaseClassRow = {
  class_name: string;
  display_name: string;
  enabled?: boolean;
};
type ModelRow = {
  id: number;
  code: string;
  name: string;
  class_name: string;
  latest_version_id?: number | null;
  default_params?: Record<string, unknown>;
};
type ModelVersionRow = {
  id: number;
  model_id: number;
  version_no: number;
  label: string;
  params?: Record<string, unknown>;
};

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const strategy = useStrategyStore();

const loading = ref(false);
const savingCode = ref(false);
const compiling = ref(false);
const renaming = ref(false);
const renamingBusy = ref(false);
const renameDraft = ref("");
const renameInputRef = ref<{ focus?: () => void; input?: HTMLInputElement } | null>(null);
const instance = ref<Record<string, unknown> | null>(null);
const varsVisible = ref(false);
const consoleTab = ref<"logs" | "trades" | "vars">("logs");
const editorFontSize = ref(13);
const settingForm = reactive<Record<string, string>>({});
const baseClasses = ref<BaseClassRow[]>([]);
const selectedParent = ref("EliteCtaTemplate");
const models = ref<ModelRow[]>([]);
const modelVersions = ref<ModelVersionRow[]>([]);
const selectedModelId = ref<number | null>(null);
const selectedModelVersionId = ref<number | null>(null);
const instanceVersions = ref<Record<string, unknown>[]>([]);
const backtestRuns = ref<Record<string, unknown>[]>([]);
/** Bottom console share of the right column (default ~38%). */
const consoleHeightPct = ref(38);

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

const topTabs: { key: MainTab; label: string }[] = [
  { key: "backtest", label: "策略回测" },
  { key: "report", label: "详情分析" },
  { key: "code", label: "代码编辑" },
  { key: "settings", label: "参数配置" },
];

const subnavItems: { key: SubTab; label: string; icon: string }[] = [
  { key: "overview", label: "结果概览", icon: "概" },
  { key: "daily", label: "每日明细", icon: "日" },
  { key: "trades", label: "成交记录", icon: "成" },
  { key: "logs", label: "运行日志", icon: "志" },
  { key: "vars", label: "策略变量", icon: "变" },
];

const name = computed(() => decodeURIComponent(String(route.params.name || "")));
const displayTitle = computed(() => String(instance.value?.strategy_name || name.value || "—"));
const parentClass = computed(() => source.parent_class || selectedParent.value || "EliteCtaTemplate");
const className = computed(() => String(instance.value?.class_name || btForm.class_name || ""));

const mainTab = computed<MainTab>(() => {
  const raw = String(route.query.tab || "report").toLowerCase();
  if (raw === "backtest" || raw === "bt") return "backtest";
  if (raw === "code" || raw === "edit") return "code";
  if (raw === "settings" || raw === "params") return "settings";
  if (raw === "report" || raw === "analysis" || raw === "overview") return "report";
  return "report";
});

const subTab = computed<SubTab>(() => {
  const raw = String(route.query.sub || "overview").toLowerCase();
  if (raw === "daily" || raw === "trades" || raw === "logs" || raw === "vars") return raw;
  return "overview";
});

const showSubnav = computed(() => mainTab.value === "backtest" || mainTab.value === "report");

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
    { key: "annual_return", label: "基准收益", aliases: ["年化收益"] },
    { key: "return_drawdown_ratio", label: "Alpha" },
    { key: "beta", label: "Beta" },
    { key: "sharpe_ratio", label: "Sharpe", aliases: ["夏普比率"] },
    { key: "max_ddpercent", label: "最大回撤", aliases: ["max_drawdown", "最大回撤"] },
  ]),
);

const kpiItemsWide = computed(() =>
  buildKpi([
    { key: "total_return", label: "总收益率", aliases: ["总收益率"] },
    { key: "annual_return", label: "年化收益", aliases: ["年化收益"] },
    { key: "max_ddpercent", label: "最大回撤", aliases: ["max_drawdown", "最大回撤"] },
    { key: "max_drawdown_duration", label: "回撤天数" },
    { key: "sharpe_ratio", label: "夏普比率", aliases: ["夏普比率"] },
    { key: "return_drawdown_ratio", label: "收益回撤比" },
    { key: "total_net_pnl", label: "总盈亏", aliases: ["总盈亏"] },
    { key: "total_commission", label: "总手续费" },
    { key: "total_trade_count", label: "总成交笔数", aliases: ["总成交次数"] },
    { key: "daily_net_pnl", label: "日均盈亏" },
    { key: "daily_trade_count", label: "日均成交" },
    { key: "win_rate", label: "胜率" },
  ]),
);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let resizeStartY = 0;
let resizeStartPct = 38;
let rightColEl: HTMLElement | null = null;

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
  if (item.key.includes("drawdown") || item.key.includes("ddpercent")) return n < 0 ? "is-neg" : "";
  if (n > 0) return "is-pos";
  if (n < 0) return "is-neg";
  return "";
}

function goList() {
  router.push("/strategy/cta");
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

function showApiHint() {
  ElMessage.info(`父类 ${parentClass.value}；源码存 MySQL，运行前动态编译`);
}

function zoomEditor(delta: number) {
  editorFontSize.value = Math.min(20, Math.max(11, editorFontSize.value + delta));
}

function syncSettingForm() {
  const params = (instance.value?.parameters as Record<string, unknown>) || {};
  Object.keys(settingForm).forEach((k) => delete settingForm[k]);
  for (const [k, v] of Object.entries(params)) {
    settingForm[k] = String(v ?? "");
  }
}

async function startRename() {
  if (!auth.isAdmin) return;
  renameDraft.value = displayTitle.value;
  renaming.value = true;
  await nextTick();
  renameInputRef.value?.focus?.();
  renameInputRef.value?.input?.focus?.();
}

function cancelRename() {
  renaming.value = false;
  renameDraft.value = "";
}

async function commitRename() {
  const n = name.value;
  const next = renameDraft.value.trim();
  if (!n || !next) {
    ElMessage.warning("实例名不能为空");
    return;
  }
  if (next === n) {
    cancelRename();
    return;
  }
  renamingBusy.value = true;
  try {
    const { data } = await http.post(`/api/cta/instances/${encodeURIComponent(n)}/rename`, {
      strategy_name: next,
    });
    const newName = String(data?.strategy_name || next);
    ElMessage.success("已重命名");
    renaming.value = false;
    await strategy.refresh();
    await router.replace({
      path: `/strategy/detail/${encodeURIComponent(newName)}`,
      query: route.query,
    });
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "重命名失败");
  } finally {
    renamingBusy.value = false;
  }
}

async function loadBaseClasses() {
  try {
    const { data } = await http.get("/api/cta/base-classes", { params: { enabled_only: true } });
    baseClasses.value = Array.isArray(data) ? data : [];
  } catch {
    baseClasses.value = [
      { class_name: "EliteCtaTemplate", display_name: "Elite CTA 模板" },
      { class_name: "TargetPosTemplate", display_name: "目标仓位模板" },
      { class_name: "CtaTemplate", display_name: "CTA 基础模板" },
    ];
  }
}

async function onParentChange(parent: string) {
  if (!parent || !source.editable) return;
  try {
    const { data } = await http.post("/api/cta/source/apply-parent", {
      content: source.content,
      parent_class: parent,
    });
    if (data?.content != null) source.content = String(data.content);
    source.parent_class = String(data?.parent_class || parent);
    selectedParent.value = source.parent_class;
    ElMessage.success(`已切换基类为 ${source.parent_class}`);
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "切换基类失败");
  }
}

function formatJson(value: unknown) {
  if (!value || typeof value !== "object") return "—";
  try {
    return JSON.stringify(value);
  } catch {
    return "—";
  }
}

async function loadModels() {
  try {
    const { data } = await http.get("/api/cta/models", { params: { enabled_only: true } });
    models.value = Array.isArray(data) ? data : [];
  } catch {
    models.value = [];
  }
}

async function loadModelVersions(modelId: number | null) {
  if (!modelId) {
    modelVersions.value = [];
    return;
  }
  try {
    const { data } = await http.get(`/api/cta/models/${modelId}/versions`);
    modelVersions.value = Array.isArray(data) ? data : [];
  } catch {
    modelVersions.value = [];
  }
}

async function loadVersionHistory() {
  const n = name.value;
  if (!n) return;
  try {
    const [vRes, bRes] = await Promise.all([
      http.get(`/api/cta/instances/${encodeURIComponent(n)}/versions`),
      http.get(`/api/cta/instances/${encodeURIComponent(n)}/backtests`),
    ]);
    instanceVersions.value = Array.isArray(vRes.data) ? vRes.data : [];
    backtestRuns.value = Array.isArray(bRes.data) ? bRes.data : [];
  } catch {
    instanceVersions.value = [];
    backtestRuns.value = [];
  }
}

async function onModelPick(modelId: number | null) {
  selectedModelVersionId.value = null;
  await loadModelVersions(modelId);
  if (modelId) {
    const m = models.value.find((x) => x.id === modelId);
    if (m?.latest_version_id) selectedModelVersionId.value = m.latest_version_id;
    if (m?.class_name) btForm.class_name = m.class_name;
  }
}

async function onModelVersionPick(_vid: number | null) {
  /* pin applied on saveSettings / saveSource */
}

async function loadInstance() {
  const n = name.value;
  if (!n) return;
  try {
    const { data } = await http.get(`/api/cta/instances/${encodeURIComponent(n)}`);
    instance.value = data;
    btForm.class_name = String(data?.class_name || "");
    if (data?.vt_symbol) btForm.vt_symbol = String(data.vt_symbol);
    selectedModelId.value = data?.model_id != null ? Number(data.model_id) : null;
    selectedModelVersionId.value =
      data?.model_version_id != null ? Number(data.model_version_id) : null;
    await loadModelVersions(selectedModelId.value);
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
  selectedParent.value = source.parent_class;
}

async function loadDefaultTemplate() {
  const cn = className.value || "UserStrategy";
  const { data } = await http.get("/api/cta/strategies/template", {
    params: { class_name: cn, parent_class: selectedParent.value || "" },
  });
  applySource(data);
  ElMessage.success("已载入默认模板（未保存）");
}

async function saveSource() {
  const n = name.value;
  if (!n) return;
  savingCode.value = true;
  try {
    if (selectedModelVersionId.value != null) {
      await http.post(`/api/cta/instances/${encodeURIComponent(n)}/pin-model`, {
        model_id: selectedModelId.value,
        model_version_id: selectedModelVersionId.value,
      });
    }
    const { data } = await http.put(`/api/cta/instances/${encodeURIComponent(n)}/source`, {
      content: source.content,
      reload: true,
      create_version: true,
      note: "保存源码",
      model_version_id: selectedModelVersionId.value,
    });
    source.store = String(data?.store ?? "mysql_instance");
    source.updated_at = data?.updated_at ?? source.updated_at;
    source.is_default = false;
    ElMessage.success(data?.reloaded ? "已保存到 MySQL 并热加载" : "已保存到 MySQL");
    await loadVersionHistory();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    savingCode.value = false;
  }
}

async function onHeaderSave() {
  if (mainTab.value === "settings") {
    await saveSettings();
    return;
  }
  await saveSource();
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
    if (selectedModelId.value != null || selectedModelVersionId.value != null) {
      await http.post(`/api/cta/instances/${encodeURIComponent(n)}/pin-model`, {
        model_id: selectedModelId.value,
        model_version_id: selectedModelVersionId.value,
      });
    }
    await http.patch(`/api/cta/instances/${encodeURIComponent(n)}`, {
      setting,
      model_id: selectedModelId.value,
      model_version_id: selectedModelVersionId.value,
      create_version: true,
      note: "保存运行参数",
    });
    ElMessage.success("参数已更新并创建实例版本");
    await loadInstance();
    await loadVersionHistory();
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
    const wasRunning = btRunning.value;
    btRunning.value = Boolean(statusRes.data?.running);
    btHasResult.value = Boolean(statusRes.data?.has_result);
    btStats.value = (resultRes.data?.statistics as Record<string, unknown>) || null;
    btDaily.value = Array.isArray(resultRes.data?.daily_results) ? resultRes.data.daily_results : [];
    btTrades.value = Array.isArray(tradesRes.data) ? tradesRes.data : [];
    // When a run finishes, snapshot stats onto the current instance version
    if (wasRunning && !btRunning.value && name.value) {
      try {
        await http.post("/api/backtest/persist-result", null, {
          params: { strategy_name: name.value },
        });
        await loadVersionHistory();
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
  if (mainTab.value === "report" || mainTab.value === "backtest") {
    setSubTab("logs");
  }
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

async function refreshAll() {
  loading.value = true;
  try {
    await Promise.all([strategy.refresh(), loadInstance(), loadBaseClasses(), loadModels()]);
    await loadSource();
    await loadBacktest();
    await loadVersionHistory();
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void refreshAll();
});

onUnmounted(() => {
  stopPolling();
  stopConsoleResize();
});

watch(
  () => route.params.name,
  () => {
    void refreshAll();
  },
);
</script>

<style scoped src="@/styles/strategy-detail.css"></style>
