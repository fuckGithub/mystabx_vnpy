<template>
  <div class="page-shell">
    <div class="page-section">
      <h3 class="page-section-title">{{ pageTitle }}</h3>
      <p v-if="status?.summary" class="page-form-hint">{{ status.summary }}</p>
      <div v-if="status" class="apps-status-row">
        <el-tag :type="stateTone(status.state)" size="small">{{ stateLabel(status.state) }}</el-tag>
        <el-tag v-if="status.package" size="small" effect="plain" type="info">{{ status.package }}</el-tag>
        <el-tag v-if="status.wiring" size="small" effect="plain">{{ wiringLabel(status.wiring) }}</el-tag>
        <span v-if="status.load_error" class="page-form-hint">{{ status.load_error }}</span>
        <span v-else-if="status.import_error" class="page-form-hint">{{ status.import_error }}</span>
      </div>
    </div>

    <div v-if="section === 'overview'" class="page-list">
      <el-table v-loading="loading" :data="apps" border size="small" highlight-current-row empty-text="暂无应用">
        <el-table-column prop="title" label="应用" min-width="140" />
        <el-table-column prop="package" label="包名" min-width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="stateTone(row.state)" size="small">{{ stateLabel(row.state) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="接入" width="100" align="center">
          <template #default="{ row }">{{ wiringLabel(row.wiring) }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="100" align="center" class-name="table-action-col">
          <template #default="{ row }">
            <el-button type="primary" link @click="goApp(row.key)">打开</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p class="page-form-hint" style="margin-top: 12px">
        改动依赖或引擎加载后需<strong>重启后端</strong>；本页数据点刷新即可。安装示例：
        <code>uv pip install vnpy_ctastrategy vnpy_ctabacktester vnpy_datamanager …</code>
        或 <code>uv pip install -e ".[strategy]"</code>
      </p>
    </div>

    <template v-else-if="section === 'cta'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadCta">刷新</el-button>
      </div>
      <el-form class="page-query" :inline="true" @submit.prevent="addCta">
        <el-form-item label="类名">
          <el-select v-model="ctaForm.class_name" filterable clearable style="width: 180px" placeholder="策略类">
            <el-option v-for="name in ctaClasses" :key="name" :label="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-form-item label="实例名">
          <el-input v-model="ctaForm.strategy_name" style="width: 140px" />
        </el-form-item>
        <el-form-item label="合约">
          <el-input v-model="ctaForm.vt_symbol" placeholder="rb2501.SHFE" style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" @click="addCta">添加</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="ctaStrategies" border size="small" empty-text="暂无策略实例">
        <el-table-column prop="strategy_name" label="实例" min-width="120" />
        <el-table-column prop="class_name" label="类" min-width="120" />
        <el-table-column prop="vt_symbol" label="合约" min-width="120" />
        <el-table-column prop="inited" label="已初始化" width="90" align="center" />
        <el-table-column prop="trading" label="交易中" width="80" align="center" />
        <el-table-column prop="pos" label="仓位" width="80" align="center" />
        <el-table-column label="操作" width="220" align="center" class-name="table-action-col">
          <template #default="{ row }">
            <span class="table-row-actions">
              <el-button type="primary" link @click="ctaAction(row.strategy_name, 'init')">初始化</el-button>
              <el-button type="primary" link @click="ctaAction(row.strategy_name, 'start')">启动</el-button>
              <el-button type="warning" link @click="ctaAction(row.strategy_name, 'stop')">停止</el-button>
              <el-button type="danger" link @click="ctaRemove(row.strategy_name)">删除</el-button>
            </span>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else-if="section === 'backtester'">
      <el-form label-width="88px" class="page-dialog-form" style="max-width: 640px" @submit.prevent="runBacktest">
        <el-form-item label="策略类">
          <el-select v-model="btForm.class_name" filterable clearable class="w-full">
            <el-option v-for="name in btClasses" :key="name" :label="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-form-item label="合约">
          <el-input v-model="btForm.vt_symbol" placeholder="rb2501.SHFE" />
        </el-form-item>
        <el-form-item label="周期">
          <el-input v-model="btForm.interval" placeholder="1m" />
        </el-form-item>
        <el-form-item label="开始">
          <el-input v-model="btForm.start" placeholder="2024-01-01T00:00:00" />
        </el-form-item>
        <el-form-item label="结束">
          <el-input v-model="btForm.end" placeholder="2024-06-01T00:00:00" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" :loading="btRunning" @click="runBacktest">启动回测</el-button>
          <el-button @click="loadBacktestStatus">刷新结果</el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="btRunning" type="warning" :closable="false" title="回测线程运行中…" style="margin-bottom: 12px" />
      <pre v-if="btStats" class="apps-pre">{{ btStats }}</pre>
    </template>

    <template v-else-if="section === 'datamanager'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadDm">刷新概览</el-button>
      </div>
      <el-table :data="dmRows" border size="small" empty-text="无 Bar 概览（检查 database 配置）">
        <el-table-column prop="symbol" label="合约" />
        <el-table-column prop="exchange" label="交易所" width="100" />
        <el-table-column prop="interval" label="周期" width="80" />
        <el-table-column prop="count" label="条数" width="90" />
        <el-table-column prop="start" label="起" min-width="160" />
        <el-table-column prop="end" label="止" min-width="160" />
      </el-table>
    </template>

    <template v-else-if="section === 'recorder'">
      <el-form class="page-query" :inline="true" @submit.prevent>
        <el-form-item label="合约">
          <el-input v-model="recSymbol" placeholder="rb2501.SHFE" style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" @click="recAdd('tick')">加 Tick</el-button>
          <el-button type="primary" :disabled="!status?.loaded" @click="recAdd('bar')">加 Bar</el-button>
          <el-button @click="loadRecorder">刷新</el-button>
        </el-form-item>
      </el-form>
      <p class="page-form-hint">录制线程 active={{ recActive }}</p>
      <el-table :data="recTickRows" border size="small" style="margin-bottom: 12px" empty-text="无 Tick 录制">
        <el-table-column prop="vt_symbol" label="Tick 录制" />
        <el-table-column label="操作" width="90" class-name="table-action-col">
          <template #default="{ row }">
            <el-button type="danger" link @click="recRemove('tick', row.vt_symbol)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table :data="recBarRows" border size="small" empty-text="无 Bar 录制">
        <el-table-column prop="vt_symbol" label="Bar 录制" />
        <el-table-column label="操作" width="90" class-name="table-action-col">
          <template #default="{ row }">
            <el-button type="danger" link @click="recRemove('bar', row.vt_symbol)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else-if="section === 'risk'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadRisk">刷新规则</el-button>
      </div>
      <el-table :data="riskRows" border size="small" empty-text="无规则或引擎未加载">
        <el-table-column prop="name" label="规则" min-width="140" />
        <el-table-column prop="detail" label="数据" min-width="280" show-overflow-tooltip />
      </el-table>
    </template>

    <template v-else-if="section === 'algo'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadAlgo">刷新</el-button>
        <el-button type="danger" :disabled="!status?.loaded" @click="stopAllHint">停止需点行内按钮</el-button>
      </div>
      <p class="page-form-hint">模板：{{ algoTemplates.join(", ") || "—" }}</p>
      <el-table :data="algoRows" border size="small" empty-text="无运行中算法">
        <el-table-column prop="algo_name" label="算法" min-width="140" />
        <el-table-column prop="template" label="模板" width="120" />
        <el-table-column prop="vt_symbol" label="合约" min-width="120" />
        <el-table-column prop="active" label="活跃" width="80" />
        <el-table-column label="操作" width="90" class-name="table-action-col">
          <template #default="{ row }">
            <el-button type="danger" link @click="stopAlgo(row.algo_name)">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else-if="section === 'paper'">
      <el-form label-width="120px" style="max-width: 480px" @submit.prevent="savePaper">
        <el-form-item label="滑点(跳)">
          <el-input-number v-model="paperForm.trade_slippage" :min="0" />
        </el-form-item>
        <el-form-item label="撮合间隔(秒)">
          <el-input-number v-model="paperForm.timer_interval" :min="1" />
        </el-form-item>
        <el-form-item label="即时成交">
          <el-switch v-model="paperForm.instant_trade" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" @click="savePaper">保存</el-button>
          <el-button @click="loadPaper">刷新</el-button>
        </el-form-item>
      </el-form>
    </template>

    <template v-else-if="section === 'rpc'">
      <el-form label-width="100px" style="max-width: 520px" @submit.prevent>
        <el-form-item label="状态">
          <el-tag :type="rpcActive ? 'success' : 'info'" size="small">{{ rpcActive ? "运行中" : "未启动" }}</el-tag>
        </el-form-item>
        <el-form-item label="REP">
          <el-input v-model="rpcForm.rep_address" />
        </el-form-item>
        <el-form-item label="PUB">
          <el-input v-model="rpcForm.pub_address" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" @click="rpcStart">启动</el-button>
          <el-button :disabled="!status?.loaded" @click="rpcStop">停止</el-button>
          <el-button @click="loadRpc">刷新</el-button>
        </el-form-item>
      </el-form>
    </template>

    <template v-else-if="section === 'chart'">
      <el-alert type="info" :closable="false" title="ChartWizard 引擎可加载；产品内 K 线请使用行情中心 QuoteChart（含 MACD），避免重复实现整套图表。" />
      <div class="page-toolbar" style="margin-top: 12px">
        <el-button type="primary" @click="$router.push('/market/quotes')">打开行情中心</el-button>
      </div>
    </template>

    <template v-else-if="section === 'webtrader'">
      <el-alert
        type="success"
        :closable="false"
        title="本项目已是 Web 交易台（FastAPI + Vue + 进程内 MainEngine）。不会加载官方 vnpy_webtrader（与 RpcService 的 app_name 冲突）。"
      />
      <p class="page-form-hint" style="margin-top: 12px">健康检查：<code>/health</code> · 入口：<code>main.py</code> / <code>start.sh</code></p>
    </template>

    <template v-else-if="section === 'excelrtd'">
      <el-alert type="warning" :closable="false" title="Excel RTD 依赖 Windows + Excel COM；当前 macOS/Linux 环境通常无法安装或启用。" />
      <p class="page-form-hint" style="margin-top: 12px">若在 Windows 上需要：<code>uv pip install vnpy_excelrtd</code> 后重启后端，并由 MYSTABX_APPS 包含 excelrtd。</p>
    </template>

    <template v-else-if="section === 'spread'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="spreadStart">启动引擎</el-button>
        <el-button :disabled="!status?.loaded" @click="spreadStop">停止</el-button>
        <el-button @click="loadSpread">刷新</el-button>
      </div>
      <p class="page-form-hint">active={{ spreadActive }} · 价差合约配置仍使用 vnpy 侧设置文件，本页不虚构套利盈亏。</p>
    </template>

    <template v-else-if="section === 'option'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadOption">刷新组合名</el-button>
      </div>
      <el-table :data="optionNames.map((n) => ({ name: n }))" border size="small" empty-text="无组合或引擎未加载">
        <el-table-column prop="name" label="期权组合" />
      </el-table>
    </template>

    <template v-else-if="section === 'portfolio'">
      <div class="page-toolbar">
        <el-button type="primary" :disabled="!status?.loaded" @click="loadPortfolio">刷新</el-button>
      </div>
      <p class="page-form-hint">策略类：{{ portfolioClasses.join(", ") || "—" }}</p>
      <el-table :data="portfolioStrategies" border size="small" empty-text="暂无组合策略实例">
        <el-table-column prop="strategy_name" label="实例" />
        <el-table-column prop="class_name" label="类" />
        <el-table-column prop="inited" label="已初始化" width="90" />
        <el-table-column prop="trading" label="交易中" width="80" />
        <el-table-column label="操作" width="140" class-name="table-action-col">
          <template #default="{ row }">
            <el-button type="primary" link @click="portfolioAction(row.strategy_name, 'start')">启动</el-button>
            <el-button type="warning" link @click="portfolioAction(row.strategy_name, 'stop')">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <template v-else-if="section === 'portfolio_mgr'">
      <el-form class="page-query" :inline="true" @submit.prevent="loadPortfolioMgr">
        <el-form-item label="reference">
          <el-input v-model="pmRef" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!status?.loaded" @click="loadPortfolioMgr">查询</el-button>
        </el-form-item>
      </el-form>
      <pre class="apps-pre">{{ pmResult }}</pre>
    </template>

    <template v-else-if="section === 'script'">
      <el-alert type="info" :closable="false" :title="scriptNote" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { http } from "@/api";

type AppStatus = {
  key: string;
  title: string;
  package: string;
  wiring: string;
  summary: string;
  state: string;
  loaded: boolean;
  load_error?: string | null;
  import_error?: string | null;
};

const route = useRoute();
const router = useRouter();
const section = computed(() => String(route.params.section || "overview"));
const loading = ref(false);
const apps = ref<AppStatus[]>([]);
const status = ref<AppStatus | null>(null);

const ctaClasses = ref<string[]>([]);
const ctaStrategies = ref<Record<string, unknown>[]>([]);
const ctaForm = reactive({ class_name: "", strategy_name: "", vt_symbol: "" });

const btClasses = ref<string[]>([]);
const btForm = reactive({
  class_name: "",
  vt_symbol: "",
  interval: "1m",
  start: "2024-01-01T00:00:00",
  end: "2024-06-01T00:00:00",
});
const btRunning = ref(false);
const btStats = ref("");

const dmRows = ref<Record<string, unknown>[]>([]);
const recSymbol = ref("");
const recActive = ref(false);
const recTickRows = ref<{ vt_symbol: string }[]>([]);
const recBarRows = ref<{ vt_symbol: string }[]>([]);
const riskRows = ref<{ name: string; detail: string }[]>([]);
const algoTemplates = ref<string[]>([]);
const algoRows = ref<Record<string, unknown>[]>([]);
const paperForm = reactive({ trade_slippage: 0, timer_interval: 3, instant_trade: false });
const rpcForm = reactive({ rep_address: "tcp://*:2014", pub_address: "tcp://*:4102" });
const rpcActive = ref(false);
const spreadActive = ref(false);
const optionNames = ref<string[]>([]);
const portfolioClasses = ref<string[]>([]);
const portfolioStrategies = ref<Record<string, unknown>[]>([]);
const pmRef = ref("");
const pmResult = ref("");
const scriptNote = ref("脚本引擎状态加载中…");

const pageTitle = computed(() => {
  if (section.value === "overview") return "策略应用总览";
  return status.value?.title || section.value;
});

function stateLabel(state: string) {
  const map: Record<string, string> = {
    loaded: "已加载",
    missing: "包未安装",
    failed: "加载失败",
    disabled: "未启用",
    na: "不适用",
  };
  return map[state] || state;
}

function stateTone(state: string) {
  if (state === "loaded") return "success";
  if (state === "missing" || state === "failed") return "danger";
  if (state === "disabled") return "warning";
  return "info";
}

function wiringLabel(wiring: string) {
  const map: Record<string, string> = {
    wired: "已接线",
    status: "状态/钩子",
    link: "链接现有页",
    na: "N/A",
    optional: "可选/平台限制",
  };
  return map[wiring] || wiring;
}

function goApp(key: string) {
  router.push(`/apps/${key}`);
}

async function loadOverview() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/apps");
    apps.value = data;
  } finally {
    loading.value = false;
  }
}

async function loadStatus() {
  if (section.value === "overview") {
    status.value = null;
    await loadOverview();
    return;
  }
  const { data } = await http.get(`/api/apps/${section.value}`);
  status.value = data;
}

async function loadCta() {
  if (!status.value?.loaded) return;
  const [cls, list] = await Promise.all([
    http.get("/api/apps/cta/classes"),
    http.get("/api/apps/cta/strategies"),
  ]);
  ctaClasses.value = cls.data.classes || [];
  ctaStrategies.value = list.data || [];
}

async function addCta() {
  await http.post("/api/apps/cta/strategies", { ...ctaForm, setting: {} });
  ElMessage.success("已添加");
  await loadCta();
}

async function ctaAction(name: string, action: "init" | "start" | "stop") {
  await http.post(`/api/apps/cta/strategies/${encodeURIComponent(name)}/${action}`);
  ElMessage.success("已提交");
  await loadCta();
}

async function ctaRemove(name: string) {
  await http.delete(`/api/apps/cta/strategies/${encodeURIComponent(name)}`);
  ElMessage.success("已删除");
  await loadCta();
}

async function loadBacktest() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/backtester/classes");
  btClasses.value = data.classes || [];
  await loadBacktestStatus();
}

async function runBacktest() {
  const { data } = await http.post("/api/apps/backtester/run", { ...btForm, setting: {} });
  btRunning.value = Boolean(data.running);
  ElMessage.success(data.ok ? "回测已启动" : "未能启动（可能已有任务）");
}

async function loadBacktestStatus() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/backtester/status");
  btRunning.value = Boolean(data.running);
  btStats.value = data.statistics ? JSON.stringify(data.statistics, null, 2) : "尚无统计结果";
}

async function loadDm() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/datamanager/overview");
  dmRows.value = data;
}

async function loadRecorder() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/recorder/recordings");
  recActive.value = Boolean(data.active);
  recTickRows.value = (data.tick || []).map((vt_symbol: string) => ({ vt_symbol }));
  recBarRows.value = (data.bar || []).map((vt_symbol: string) => ({ vt_symbol }));
}

async function recAdd(kind: "tick" | "bar") {
  await http.post(`/api/apps/recorder/${kind}`, { vt_symbol: recSymbol.value });
  await loadRecorder();
}

async function recRemove(kind: "tick" | "bar", vt: string) {
  await http.delete(`/api/apps/recorder/${kind}/${encodeURIComponent(vt)}`);
  await loadRecorder();
}

async function loadRisk() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/risk/rules");
  riskRows.value = (data.names || []).map((name: string) => ({
    name,
    detail: JSON.stringify(data.rules?.[name] ?? {}),
  }));
}

async function loadAlgo() {
  if (!status.value?.loaded) return;
  const [t, a] = await Promise.all([http.get("/api/apps/algo/templates"), http.get("/api/apps/algo/algos")]);
  algoTemplates.value = t.data.templates || [];
  algoRows.value = a.data || [];
}

async function stopAlgo(name: string) {
  await http.post(`/api/apps/algo/${encodeURIComponent(name)}/stop`);
  await loadAlgo();
}

function stopAllHint() {
  ElMessage.info("请在行内停止单个算法");
}

async function loadPaper() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/paper/settings");
  paperForm.trade_slippage = data.trade_slippage;
  paperForm.timer_interval = data.timer_interval;
  paperForm.instant_trade = data.instant_trade;
}

async function savePaper() {
  await http.post("/api/apps/paper/settings", { ...paperForm });
  ElMessage.success("已保存");
  await loadPaper();
}

async function loadRpc() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/rpc/status");
  rpcActive.value = Boolean(data.active);
  rpcForm.rep_address = data.rep_address || rpcForm.rep_address;
  rpcForm.pub_address = data.pub_address || rpcForm.pub_address;
}

async function rpcStart() {
  const { data } = await http.post("/api/apps/rpc/start", { ...rpcForm });
  rpcActive.value = Boolean(data.active);
  ElMessage.success(data.ok ? "已启动" : "启动未成功（可能已在运行）");
}

async function rpcStop() {
  const { data } = await http.post("/api/apps/rpc/stop");
  rpcActive.value = Boolean(data.active);
}

async function loadSpread() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/spread/status");
  spreadActive.value = Boolean(data.active);
}

async function spreadStart() {
  await http.post("/api/apps/spread/start");
  await loadSpread();
}

async function spreadStop() {
  await http.post("/api/apps/spread/stop");
  await loadSpread();
}

async function loadOption() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/option/portfolios");
  optionNames.value = data.names || [];
}

async function loadPortfolio() {
  if (!status.value?.loaded) return;
  const [c, s] = await Promise.all([
    http.get("/api/apps/portfolio/classes"),
    http.get("/api/apps/portfolio/strategies"),
  ]);
  portfolioClasses.value = c.data.classes || [];
  portfolioStrategies.value = s.data || [];
}

async function portfolioAction(name: string, action: "start" | "stop") {
  await http.post(`/api/apps/portfolio/strategies/${encodeURIComponent(name)}/${action}`);
  await loadPortfolio();
}

async function loadPortfolioMgr() {
  if (!status.value?.loaded) return;
  const { data } = await http.get("/api/apps/portfolio_mgr/result", { params: { reference: pmRef.value } });
  pmResult.value = JSON.stringify(data, null, 2);
}

async function loadScript() {
  if (!status.value?.loaded) {
    scriptNote.value = status.value?.summary || "脚本引擎未加载";
    return;
  }
  const { data } = await http.get("/api/apps/script/status");
  scriptNote.value = data.note || status.value?.summary || "";
}

async function loadSectionData() {
  await loadStatus();
  const s = section.value;
  if (s === "cta") await loadCta();
  else if (s === "backtester") await loadBacktest();
  else if (s === "datamanager") await loadDm();
  else if (s === "recorder") await loadRecorder();
  else if (s === "risk") await loadRisk();
  else if (s === "algo") await loadAlgo();
  else if (s === "paper") await loadPaper();
  else if (s === "rpc") await loadRpc();
  else if (s === "spread") await loadSpread();
  else if (s === "option") await loadOption();
  else if (s === "portfolio") await loadPortfolio();
  else if (s === "portfolio_mgr") await loadPortfolioMgr();
  else if (s === "script") await loadScript();
}

onMounted(loadSectionData);
watch(section, loadSectionData);
</script>

<style scoped>
.apps-status-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.apps-pre {
  margin: 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.5;
  background: var(--el-fill-color-light, #f5f7fa);
  border-radius: 6px;
  overflow: auto;
  max-height: 360px;
}
.w-full {
  width: 100%;
}
</style>
