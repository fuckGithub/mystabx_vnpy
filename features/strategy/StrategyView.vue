<template>
  <div class="page-shell">
    <div v-if="section === 'stoporders'" class="page-list">
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

    <div v-else class="page-list cta-list-page">
      <div class="cta-list-head">
        <h3 class="page-section-title">策略管理</h3>
        <el-input
          v-model="listSearch"
          clearable
          placeholder="搜索名称 / 策略类"
          :prefix-icon="Search"
          class="cta-list-search"
        />
      </div>

      <div class="cta-trial-hint" :class="{ 'is-collapsed': !tipsExpanded }">
        <div class="cta-trial-hint__bar">
          <div class="cta-trial-hint__bar-main">
            <el-icon class="cta-trial-hint__icon"><SuccessFilled /></el-icon>
            <span class="cta-trial-hint__title">试用流程</span>
            <span v-if="!tipsExpanded" class="cta-trial-hint__summary">
              添加策略 → 初始化 → 启动；首次接入需重启后端并硬刷新
            </span>
          </div>
          <el-button
            class="cta-trial-hint__toggle"
            text
            type="primary"
            size="small"
            @click="tipsExpanded = !tipsExpanded"
          >
            {{ tipsExpanded ? "收起" : "展开" }}
          </el-button>
        </div>
        <div v-show="tipsExpanded" class="cta-trial-hint__body">
          <ol class="cta-trial-hint__steps">
            <li>管理员点击「添加策略」，选择带中文名的策略类（如「双均线策略」）</li>
            <li>填写实例名、从已订阅合约中选择合约，并选择真实通道账户</li>
            <li>点击名称或「详情」进入实例详情（回测报告 / 策略回测 IDE）；列表中也可「初始化」→「启动」</li>
          </ol>
          <p class="cta-trial-hint__note">
            首次接入或安装依赖后需<strong>重启后端</strong>，前端<strong>硬刷新</strong>（Ctrl/Cmd+Shift+R）。
          </p>
        </div>
      </div>

      <div class="page-toolbar cta-list-toolbar">
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openAdd">添加策略</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('init-all')">全部初始化</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('start-all')">全部启动</el-button>
        <el-button :disabled="!auth.isAdmin" @click="batch('stop-all')">全部停止</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        class="cta-list-table"
        :data="pagedInstances"
        border
        size="small"
        highlight-current-row
        empty-text="暂无策略实例"
      >
        <el-table-column label="名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <router-link
              class="cta-name-link"
              :to="detailPath(row)"
              :title="String(row.strategy_name || '')"
            >
              {{ row.strategy_name }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="策略" min-width="168" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cta-strategy-cell">
              <span class="cta-strategy-cell__name">
                {{ strategyDisplayName(String(row.class_name || ""), String(row.display_name || "") || null) }}
              </span>
              <span class="cta-strategy-cell__code">{{ row.class_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="vt_symbol" label="合约" width="118" show-overflow-tooltip />
        <el-table-column label="修改时间" width="168" show-overflow-tooltip>
          <template #default="{ row }">{{ formatUpdatedAt(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="历史回测" width="88" align="center">
          <template #default="{ row }">
            <router-link
              class="cta-name-link"
              :class="{ 'cta-name-link--muted': !Number(row.backtest_count || 0) }"
              :to="`${detailPath(row)}?tab=report`"
            >
              {{ row.backtest_count ?? 0 }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="账户" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="cta-account-cell">{{ gatewayLabel(row.gateway_name) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="light"
              :type="statusMeta(row).type"
              class="cta-status-tag"
            >
              {{ statusMeta(row).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pos" label="仓位" width="64" align="center" />
        <el-table-column
          label="操作"
          width="360"
          align="center"
          fixed="right"
          header-class-name="table-action-col"
          class-name="table-action-col"
        >
          <template #default="{ row }">
            <span class="table-row-actions cta-row-actions">
              <el-button size="small" text type="primary" :icon="View" @click="$router.push(detailPath(row))">
                详情
              </el-button>
              <el-button
                size="small"
                text
                type="primary"
                :icon="RefreshRight"
                :disabled="!auth.isAdmin"
                @click="act(row, 'init')"
              >
                初始化
              </el-button>
              <el-button
                size="small"
                text
                type="success"
                :icon="VideoPlay"
                :disabled="!auth.isAdmin || !row.inited"
                @click="act(row, 'start')"
              >
                启动
              </el-button>
              <el-button
                size="small"
                text
                type="danger"
                :icon="VideoPause"
                :disabled="!auth.isAdmin"
                @click="act(row, 'stop')"
              >
                停止
              </el-button>
              <el-dropdown
                trigger="click"
                :disabled="!auth.isAdmin"
                @command="(cmd: string) => onMoreCommand(cmd, row)"
              >
                <el-button size="small" text :icon="MoreFilled" :disabled="!auth.isAdmin">
                  更多
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit" :disabled="Boolean(row.trading)">编辑</el-dropdown-item>
                    <el-dropdown-item command="remove" divided :disabled="Boolean(row.trading)">
                      <span class="cta-danger-text">移除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="page-pagination">
        <el-pagination
          v-model:current-page="listPage"
          v-model:page-size="listPageSize"
          :total="filteredInstances.length"
          :page-sizes="[10, 20, 50]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          size="small"
        />
      </div>

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
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  MoreFilled,
  Plus,
  Refresh,
  RefreshRight,
  Search,
  SuccessFilled,
  VideoPause,
  VideoPlay,
  View,
} from "@element-plus/icons-vue";
import { http } from "@/api";
import { useAuthStore, useMarketStore, useStrategyStore, useTradeStore } from "@/stores";
import { contractKey, productName, type ContractRow } from "../market/contracts";
import { strategyDisplayName } from "./strategyNames";

const TIPS_STORAGE_KEY = "mystabx.strategy.tipsExpanded";

function readTipsExpanded() {
  try {
    const raw = localStorage.getItem(TIPS_STORAGE_KEY);
    if (raw === null) return false;
    return raw === "1";
  } catch {
    return false;
  }
}

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const strategy = useStrategyStore();
const trade = useTradeStore();
const market = useMarketStore();
const section = computed(() => String(route.params.section || "cta"));

const loading = ref(false);
const saving = ref(false);
const listSearch = ref("");
const listPage = ref(1);
const listPageSize = ref(10);
const tipsExpanded = ref(readTipsExpanded());
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

const filteredInstances = computed(() => {
  const q = listSearch.value.trim().toLowerCase();
  if (!q) return strategy.instances;
  return strategy.instances.filter((row) => {
    const name = String(row.strategy_name || "").toLowerCase();
    const cls = String(row.class_name || "").toLowerCase();
    const display = strategyDisplayName(
      String(row.class_name || ""),
      String(row.display_name || "") || null,
    ).toLowerCase();
    const symbol = String(row.vt_symbol || "").toLowerCase();
    const account = gatewayLabel(row.gateway_name).toLowerCase();
    return (
      name.includes(q) ||
      cls.includes(q) ||
      display.includes(q) ||
      symbol.includes(q) ||
      account.includes(q)
    );
  });
});

const pagedInstances = computed(() => {
  const start = (listPage.value - 1) * listPageSize.value;
  return filteredInstances.value.slice(start, start + listPageSize.value);
});

function clampListPage() {
  const maxPage = Math.max(1, Math.ceil(filteredInstances.value.length / listPageSize.value) || 1);
  if (listPage.value > maxPage) listPage.value = maxPage;
}

function statusMeta(row: Record<string, unknown>) {
  if (row.trading) return { label: "交易中", type: "success" as const };
  if (row.inited) return { label: "已初始化", type: "warning" as const };
  return { label: "未初始化", type: "info" as const };
}

function onMoreCommand(cmd: string, row: Record<string, unknown>) {
  if (cmd === "edit") void openEdit(row);
  else if (cmd === "remove") void remove(row);
}

function detailPath(row: Record<string, unknown>) {
  return `/strategy/detail/${encodeURIComponent(String(row.strategy_name || ""))}`;
}

function formatUpdatedAt(value: unknown) {
  const raw = String(value || "").trim();
  if (!raw) return "—";
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;
  return raw.replace("T", " ").slice(0, 19);
}

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

/** Prefer workbench-activated channel; else first visible gateway. */
function defaultGatewayName() {
  const options = channelOptions.value;
  if (!options.length) return "";
  const preferred = String(trade.activeGatewayName || "").trim();
  if (preferred && options.some((row) => row.gateway_name === preferred)) return preferred;
  return options[0]?.gateway_name || "";
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
  const currentGw = String(form.setting.gateway_name || "").trim();
  form.setting = {
    ...params,
    gateway_name: currentGw || defaultGatewayName(),
  };
}

async function openAdd() {
  editingName.value = "";
  form.strategy_name = "";
  form.vt_symbol = "";
  form.setting = { gateway_name: defaultGatewayName() };
  paramSchema.value = {};
  dialogVisible.value = true;
  await loadClasses();
  form.class_name = classes.value[0]?.class_name || "";
  if (form.class_name) onClassChange(form.class_name);
  else form.setting.gateway_name = defaultGatewayName();
  void Promise.all([
    trade.refresh(),
    market.loadSubscriptions(),
    market.loadContracts(),
  ]).then(() => {
    if (editingName.value) return;
    const current = String(form.setting.gateway_name || "").trim();
    if (!current || !channelOptions.value.some((row) => row.gateway_name === current)) {
      form.setting.gateway_name = defaultGatewayName();
    }
  });
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

onMounted(async () => {
  if (section.value === "backtest") {
    router.replace("/strategy/cta");
    return;
  }
  loading.value = true;
  try {
    await Promise.all([
      strategy.refresh(),
      loadClasses(),
      trade.refresh(),
      market.loadSubscriptions(),
      market.loadContracts(),
    ]);
  } finally {
    loading.value = false;
  }
});

watch(section, (s) => {
  if (s === "backtest") {
    router.replace("/strategy/cta");
    return;
  }
  if (s === "cta" || !s) {
    void strategy.refresh();
    void trade.refresh();
  }
  if (s === "logs" || s === "stoporders") void strategy.refresh();
});

watch(listSearch, () => {
  listPage.value = 1;
});

watch([filteredInstances, listPageSize], clampListPage);

watch(tipsExpanded, (expanded) => {
  try {
    localStorage.setItem(TIPS_STORAGE_KEY, expanded ? "1" : "0");
  } catch {
    /* ignore quota / private mode */
  }
});
</script>

<style scoped src="@/styles/strategy.css"></style>
