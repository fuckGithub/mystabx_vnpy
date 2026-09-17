<template>
  <div class="page-shell">
    <div v-if="section === 'backtest'" class="page-list">
      <h3 class="page-section-title">策略回测</h3>
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
            <el-option
              v-for="c in btClasses"
              :key="c.class_name"
              :label="classLabel(c)"
              :value="c.class_name"
            />
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
      <h3 class="page-section-title">停止报单</h3>
      <el-table :data="strategy.stopOrders" border size="small" empty-text="暂无停止报单">
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
      <el-form class="page-query" :inline="true" @submit.prevent>
        <el-form-item label="策略实例">
          <el-select v-model="logFilterName" clearable filterable placeholder="全部" style="width: 220px">
            <el-option label="全部" value="" />
            <el-option v-for="name in logStrategyOptions" :key="name" :label="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Refresh" @click="strategy.refresh()">刷新实例</el-button>
        </el-form-item>
      </el-form>
      <el-table
        :data="filteredLogs"
        border
        size="small"
        highlight-current-row
        style="width: 100%"
        empty-text="暂无策略日志"
      >
        <el-table-column label="时间" width="168">
          <template #default="{ row }">{{ formatLogTime(row.time) }}</template>
        </el-table-column>
        <el-table-column label="策略" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ formatLogStrategy(row) }}</template>
        </el-table-column>
        <el-table-column label="级别" width="88" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="logLevelType(row.level)">{{ logLevelLabel(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="msg" label="内容" min-width="320" show-overflow-tooltip />
      </el-table>
    </div>

    <div v-else class="page-list">
      <h3 class="page-section-title">策略实例</h3>
      <el-alert class="cta-trial-hint" type="success" :closable="false" show-icon style="margin-bottom: 12px">
        <template #title>
          <span class="cta-trial-hint__title">试用流程</span>
        </template>
        <ol class="cta-trial-hint__steps">
          <li>管理员点击「添加策略」，选择带中文名的策略类（如「双均线策略」）</li>
          <li>填写实例名、从已订阅合约中选择合约，并选择真实通道账户</li>
          <li>列表中对该实例依次「初始化」→「启动」</li>
        </ol>
        <p class="cta-trial-hint__note">首次接入或安装依赖后需<strong>重启后端</strong>，前端<strong>硬刷新</strong>（Ctrl/Cmd+Shift+R）。</p>
      </el-alert>
      <div class="page-toolbar">
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openAdd">添加策略</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('init-all')">全部初始化</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('start-all')">全部启动</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('stop-all')">全部停止</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
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
        <el-table-column label="策略类" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ strategyDisplayName(String(row.class_name || ""), String(row.display_name || "") || null) }}
          </template>
        </el-table-column>
        <el-table-column prop="vt_symbol" label="合约" width="130" show-overflow-tooltip />
        <el-table-column label="账户" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ gatewayLabel(row.gateway_name) }}</template>
        </el-table-column>
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
            <div class="cta-class-row">
              <el-select
                v-model="form.class_name"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="选择或输入策略类名（驼峰，如 DoubleMaStrategy）"
                class="cta-class-select"
                @change="onClassChange"
              >
                <el-option
                  v-for="c in classes"
                  :key="c.class_name"
                  :label="classOptionLabel(c)"
                  :value="c.class_name"
                >
                  <span>{{ classLabel(c) }}</span>
                  <span class="cta-class-option-meta">{{ c.class_name }}</span>
                </el-option>
              </el-select>
              <el-button
                :icon="Refresh"
                :loading="reloadingClasses"
                :disabled="!auth.isAdmin"
                title="重新扫描 strategies/ 并热加载"
                @click="reloadClasses"
              >
                刷新类
              </el-button>
            </div>
            <p class="page-form-hint">
              选项来自 CTA 引擎已加载的策略类（同 VeighNa：类名驼峰，文件下划线）。可筛选，也可直接输入类名。
              <template v-if="selectedClassFilePath">
                · 源码：<code>{{ selectedClassFilePath }}</code>
              </template>
            </p>
          </el-form-item>
          <el-form-item v-if="!editingName" label="实例名称">
            <el-input v-model="form.strategy_name" />
          </el-form-item>
          <el-form-item v-if="!editingName" label="合约">
            <el-select
              v-model="form.vt_symbol"
              filterable
              clearable
              :placeholder="subscribedContractOptions.length ? '选择已订阅合约' : '请先去行情中心订阅'"
              style="width: 100%"
            >
              <el-option
                v-for="opt in subscribedContractOptions"
                :key="opt.vt_symbol"
                :label="opt.label"
                :value="opt.vt_symbol"
              >
                <span>{{ opt.name }}</span>
                <span style="float: right; color: var(--el-text-color-secondary); font-size: 12px">
                  {{ opt.vt_symbol }}
                </span>
              </el-option>
            </el-select>
            <p class="page-form-hint">
              <template v-if="subscribedContractOptions.length">
                选项来自已订阅合约；提交值为 vt_symbol（如 rb2501.SHFE）。添加后需「初始化」再「启动」。
              </template>
              <template v-else>请先去「行情中心」订阅合约后再添加策略。</template>
            </p>
          </el-form-item>
          <el-form-item label="交易账户">
            <el-select
              v-model="form.setting.gateway_name"
              clearable
              filterable
              :placeholder="channelOptions.length ? '选择已配置通道' : '暂无可用通道'"
              style="width: 100%"
            >
              <el-option
                v-for="g in channelOptions"
                :key="g.gateway_name"
                :label="g.label"
                :value="g.gateway_name"
              />
            </el-select>
            <p v-if="!channelOptions.length" class="page-form-hint">
              暂无可见通道。请先在「系统管理 → 通道配置」或「资金持仓 → 账户连接」中配置并启用账户。
            </p>
            <p v-else class="page-form-hint">选项来自当前用户可见的真实通道；提交值为 gateway_name。</p>
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
import { useAuthStore, useMarketStore, useStrategyStore, useTradeStore } from "@/stores";
import { contractKey, productName, type ContractRow } from "../market/contracts";
import { strategyDisplayName } from "./strategyNames";

const route = useRoute();
const auth = useAuthStore();
const strategy = useStrategyStore();
const trade = useTradeStore();
const market = useMarketStore();
const section = computed(() => String(route.params.section || "cta"));

const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const editingName = ref("");
type StrategyClassRow = {
  class_name: string;
  display_name?: string;
  parameters: Record<string, unknown>;
  file_name?: string;
  file_path?: string;
  module?: string;
};
const classes = ref<StrategyClassRow[]>([]);
const reloadingClasses = ref(false);
const paramSchema = ref<Record<string, unknown>>({});
const form = reactive({
  class_name: "",
  strategy_name: "",
  vt_symbol: "",
  setting: {} as Record<string, unknown>,
});

const btClasses = ref<StrategyClassRow[]>([]);
const btRunning = ref(false);
const btStats = ref<Record<string, unknown> | null>(null);
const btForm = reactive({
  class_name: "",
  vt_symbol: "rb2501.SHFE",
  interval: "1m",
  start: "2024-01-01",
  end: "2024-06-01",
});

const logFilterName = ref("");

const instanceByName = computed(() => {
  const map = new Map<string, Record<string, unknown>>();
  for (const row of strategy.instances) {
    const name = String(row.strategy_name || "");
    if (name) map.set(name, row);
  }
  return map;
});

const channelOptions = computed(() => {
  const seen = new Set<string>();
  const rows: { gateway_name: string; label: string }[] = [];
  for (const g of trade.gateways) {
    const gatewayName = String(g.gateway_name || "").trim();
    if (!gatewayName || seen.has(gatewayName)) continue;
    seen.add(gatewayName);
    rows.push({ gateway_name: gatewayName, label: formatChannelLabel(g) });
  }
  return rows.sort((a, b) => a.label.localeCompare(b.label, "zh"));
});

const channelLabelByGateway = computed(() => {
  const map = new Map<string, string>();
  for (const row of channelOptions.value) map.set(row.gateway_name, row.label);
  return map;
});

const subscribedContractOptions = computed(() => {
  const byVt = new Map<string, { vt_symbol: string; name: string; label: string }>();

  const upsert = (row: ContractRow, vtHint = "") => {
    const symbol = String(row.symbol || "").trim();
    const exchange = String(row.exchange || "").trim().toUpperCase();
    if (!symbol || !exchange) return;
    const vt = String(row.vt_symbol || vtHint || `${symbol}.${exchange}`).trim();
    if (!vt) return;
    const rawName = String(row.name || "").trim();
    const name =
      rawName && rawName.toUpperCase() !== symbol.toUpperCase()
        ? rawName
        : productName(row) || symbol;
    const label = name && name !== vt ? `${name}（${vt}）` : vt;
    if (!byVt.has(vt)) byVt.set(vt, { vt_symbol: vt, name, label });
  };

  for (const row of market.contracts) {
    if (!market.subscribedKeys[contractKey(row)]) continue;
    upsert(row as ContractRow);
  }
  for (const row of market.subscriptions) {
    upsert(row as ContractRow, String(row.vt_symbol || ""));
  }

  return Array.from(byVt.values()).sort((a, b) => a.label.localeCompare(b.label, "zh"));
});

const logStrategyOptions = computed(() => {
  const names = new Set<string>();
  for (const row of strategy.instances) {
    const name = String(row.strategy_name || "");
    if (name) names.add(name);
  }
  for (const row of strategy.logs) {
    const name = String(row.strategy_name || "");
    if (name) names.add(name);
  }
  return Array.from(names).sort((a, b) => a.localeCompare(b));
});

const filteredLogs = computed(() => {
  const filter = logFilterName.value;
  if (!filter) return strategy.logs;
  return strategy.logs.filter((row) => String(row.strategy_name || "") === filter);
});

function classLabel(row: StrategyClassRow) {
  return strategyDisplayName(row.class_name, row.display_name);
}

function classOptionLabel(row: StrategyClassRow) {
  const display = classLabel(row);
  return display === row.class_name ? row.class_name : `${display}（${row.class_name}）`;
}

const selectedClassFilePath = computed(() => {
  const name = String(form.class_name || "").trim();
  if (!name) return "";
  const found = classes.value.find((c) => c.class_name === name);
  if (found?.file_path) return found.file_path;
  if (found?.file_name) return `strategies/${found.file_name}`;
  return "";
});

function formatChannelLabel(g: Record<string, unknown>) {
  const gatewayName = String(g.gateway_name || "").trim();
  const accountName = String(g.account_name || "").trim();
  const front = String(g.front_label || "").trim();
  if (accountName && accountName !== gatewayName) {
    return front ? `${accountName}（${gatewayName} · ${front}）` : `${accountName}（${gatewayName}）`;
  }
  return front ? `${gatewayName}（${front}）` : gatewayName || "—";
}

function gatewayLabel(gatewayName: unknown) {
  const name = String(gatewayName || "").trim();
  if (!name) return "—";
  return channelLabelByGateway.value.get(name) || name;
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
  // 2024-09-16T15:37:30.208+08:00 → 2024-09-16 15:37:30
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;
  return raw.length > 19 ? raw.slice(0, 19).replace("T", " ") : raw.replace("T", " ");
}

function formatLogStrategy(row: Record<string, unknown>) {
  const name = String(row.strategy_name || "").trim();
  if (!name) return "—";
  const inst = instanceByName.value.get(name);
  const className = String(row.class_name || inst?.class_name || "").trim();
  if (!className) return name;
  const display = strategyDisplayName(className, String(inst?.display_name || "") || null);
  return `${name} · ${display}`;
}

function logLevelType(level: unknown) {
  const s = String(level || "").toLowerCase();
  if (s === "error" || s === "critical") return "danger";
  if (s === "warning" || s === "warn") return "warning";
  if (s === "debug") return "info";
  return "";
}

function logLevelLabel(level: unknown) {
  const s = String(level || "").toLowerCase();
  if (s === "warning") return "warning";
  if (s === "critical") return "critical";
  return s || "info";
}

function stopStatusType(status: unknown) {
  const s = String(status || "");
  if (s === "WAITING" || s === "等待中") return "warning";
  if (s === "TRIGGERED" || s === "已触发") return "success";
  return "info";
}

async function loadClasses() {
  try {
    const { data } = await http.get("/api/cta/strategies");
    classes.value = Array.isArray(data) ? data : [];
  } catch {
    classes.value = [];
  }
}

async function reloadClasses() {
  if (!auth.isAdmin) return;
  reloadingClasses.value = true;
  try {
    const { data } = await http.post("/api/cta/strategies/reload");
    classes.value = Array.isArray(data) ? data : [];
    ElMessage.success(`已重新加载 ${classes.value.length} 个策略类`);
    if (form.class_name) onClassChange(form.class_name);
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "重新加载失败");
    await loadClasses();
  } finally {
    reloadingClasses.value = false;
  }
}

async function refreshAll() {
  await Promise.all([strategy.refresh(), trade.refresh(), loadClasses()]);
}

function onClassChange(name: string | null | undefined) {
  const className = String(name || "").trim();
  form.class_name = className;
  const found = classes.value.find((c) => c.class_name === className);
  const params = { ...(found?.parameters || {}) };
  delete params.gateway_name;
  paramSchema.value = params;
  form.setting = { ...params, gateway_name: form.setting.gateway_name || "" };
}

async function openAdd() {
  editingName.value = "";
  form.strategy_name = "";
  form.vt_symbol = "";
  form.setting = {};
  paramSchema.value = {};
  dialogVisible.value = true;
  await loadClasses();
  form.class_name = classes.value[0]?.class_name || "";
  if (form.class_name) onClassChange(form.class_name);
  void Promise.all([
    trade.refresh(),
    market.loadSubscriptions(),
    market.loadContracts(),
  ]);
}

async function openEdit(row: Record<string, unknown>) {
  editingName.value = String(row.strategy_name || "");
  form.class_name = String(row.class_name || "");
  const params = { ...((row.parameters as Record<string, unknown>) || {}) };
  paramSchema.value = Object.fromEntries(Object.entries(params).filter(([k]) => k !== "gateway_name"));
  form.setting = { ...params };
  dialogVisible.value = true;
  void trade.refresh();
}

async function saveInstance() {
  saving.value = true;
  try {
    if (editingName.value) {
      await http.patch(`/api/cta/instances/${encodeURIComponent(editingName.value)}`, { setting: form.setting });
      ElMessage.success("已更新参数");
    } else {
      if (!form.class_name || !form.strategy_name || !form.vt_symbol) {
        ElMessage.warning(
          !form.vt_symbol && !subscribedContractOptions.value.length
            ? "请先去行情中心订阅合约"
            : "请填写策略类 / 实例名 / 合约",
        );
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
    await Promise.all([
      strategy.refresh(),
      loadClasses(),
      trade.refresh(),
      loadBacktestClasses(),
      market.loadSubscriptions(),
      market.loadContracts(),
    ]);
  } finally {
    loading.value = false;
  }
});

watch(section, (s) => {
  if (s === "backtest") void loadBacktestResult();
  if (s === "cta" || !s) {
    void strategy.refresh();
    void trade.refresh();
  }
  if (s === "logs" || s === "stoporders") void strategy.refresh();
});
</script>

<style scoped>
.cta-trial-hint :deep(.el-alert__content) {
  width: 100%;
}
.cta-trial-hint__title {
  font-weight: 600;
}
.cta-trial-hint__steps {
  margin: 6px 0 0;
  padding-left: 1.25em;
  line-height: 1.65;
  color: var(--el-text-color-regular);
}
.cta-trial-hint__steps code {
  padding: 0 4px;
  border-radius: 3px;
  background: var(--el-fill-color);
  font-size: 12px;
}
.cta-trial-hint__note {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}
.cta-class-row {
  display: flex;
  gap: 8px;
  width: 100%;
  align-items: center;
}
.cta-class-select {
  flex: 1;
  min-width: 0;
}
.cta-class-option-meta {
  float: right;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 12px;
}
.page-form-hint code {
  padding: 0 4px;
  border-radius: 3px;
  background: var(--el-fill-color);
  font-size: 12px;
}
</style>
