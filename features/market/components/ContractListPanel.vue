<template>
  <aside class="board">
    <div class="board-search">
      <el-input
        v-model="keyword"
        size="small"
        clearable
        placeholder="代码 / 名称 / 交易所"
        @change="emit('search', keyword)"
        @keyup.enter="emit('search', keyword)"
      />
    </div>
    <div class="board-toolbar">
      <el-radio-group v-model="tab" size="small" class="board-tabs" @change="emit('tab', tab)">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="main">主力</el-radio-button>
        <el-radio-button value="index">指数</el-radio-button>
        <el-radio-button value="product">品种</el-radio-button>
      </el-radio-group>
      <el-button
        v-if="allowSubscribe"
        size="small"
        type="primary"
        plain
        class="board-sub"
        @click="emit('subscribe', undefined)"
      >
        订阅合约
      </el-button>
    </div>
    <div class="board-list">
      <section v-for="group in groups" :key="group.key" class="board-group">
        <header class="board-group__title">{{ group.title }}</header>
        <div
          v-for="row in group.rows"
          :key="rowKey(row)"
          class="board-row"
          :class="{
            active: rowKey(row) === selectedKey,
            subscribed: isSubscribed(row),
            'board-row--no-sub': !allowSubscribe,
          }"
        >
          <button type="button" class="board-row__main" @click="emit('select', row)">
            <span class="board-row__id">
              <InstrumentCell :code="String(row.symbol || '')" :name="displayName(row)" />
            </span>
            <span class="board-row__px" :class="pnlClass(changeOf(row))">
              {{ fmtPriceOrDash(lastOf(row)) }}
            </span>
            <span class="board-row__chg" :class="pnlClass(changeOf(row))">
              {{ fmtPct(changeOf(row)) }}
            </span>
          </button>
          <button
            v-if="allowSubscribe"
            type="button"
            class="board-row__sub"
            :class="{ on: isSubscribed(row) }"
            @click.stop="onSubClick(row)"
          >
            {{ isSubscribed(row) ? (allowUnsubscribe ? "退订" : "已订") : "订阅" }}
          </button>
        </div>
      </section>
      <div v-if="!groups.some((g) => g.rows.length)" class="board-empty">
        {{ emptyText }}
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import InstrumentCell from "@/components/InstrumentCell.vue";
import { contractKey, groupContracts, productName, type BoardTab, type ContractRow } from "../contracts";
import { finitePrice, fmtPct, fmtPriceOrDash, pnlClass, quoteChangePct } from "../../workbench/liveMap";

const props = withDefaults(
  defineProps<{
    contracts: ContractRow[];
    ticks: Record<string, Record<string, unknown>>;
    selectedKey: string;
    subscribedKeys?: Record<string, true>;
    /** center = 行情中心（全市场）；live = 实时行情（已订阅） */
    variant?: "center" | "live";
    allowSubscribe?: boolean;
    allowUnsubscribe?: boolean;
    emptyText?: string;
  }>(),
  {
    variant: "center",
    allowSubscribe: true,
    allowUnsubscribe: false,
    emptyText: "暂无合约。请先连接行情通道，合约查询成功后将按交易所 / 品种列出。",
  },
);

const emit = defineEmits<{
  select: [row: ContractRow];
  search: [keyword: string];
  tab: [tab: BoardTab];
  subscribe: [row: ContractRow | undefined];
  unsubscribe: [row: ContractRow];
}>();

const keyword = ref("");
const tab = ref<BoardTab>("all");

const subscribedSet = computed(() => new Set(Object.keys(props.subscribedKeys || {})));
const groups = computed(() => groupContracts(props.contracts, tab.value, props.ticks, subscribedSet.value));

function rowKey(row: ContractRow) {
  return contractKey(row);
}

function isSubscribed(row: ContractRow) {
  return Boolean(props.subscribedKeys?.[rowKey(row)]);
}

function onSubClick(row: ContractRow) {
  if (isSubscribed(row) && props.allowUnsubscribe) {
    emit("unsubscribe", row);
    return;
  }
  emit("subscribe", row);
}

function displayName(row: ContractRow) {
  const raw = String(row.name || "").trim();
  if (raw && raw.toUpperCase() !== String(row.symbol || "").toUpperCase()) return raw;
  return productName(row);
}

function tickOf(row: ContractRow) {
  const want = contractKey(row);
  return Object.values(props.ticks).find(
    (tick) => `${String(tick.exchange || "").toUpperCase()}.${String(tick.symbol || "").toUpperCase()}` === want,
  );
}

function lastOf(row: ContractRow) {
  return finitePrice(tickOf(row)?.last_price);
}

function changeOf(row: ContractRow) {
  return quoteChangePct(tickOf(row));
}
</script>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: var(--dash-surface);
  border: 1px solid var(--dash-border);
  border-radius: var(--dash-card-radius, 8px);
  box-shadow: var(--dash-shadow);
}
.board-search { padding: 8px 8px 0; }
.board-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 8px;
}
.board-tabs {
  display: flex;
  flex-wrap: nowrap;
  flex: 1;
  min-width: 0;
  margin: 0;
}
.board-sub {
  flex: 0 0 auto;
  padding: 5px 8px;
  font-size: 11px;
}
.board-tabs :deep(.el-radio-button__inner) {
  padding: 5px 8px;
  font-size: 11px;
  border-color: var(--dash-border);
  background: var(--dash-pill-bg);
  color: var(--dash-text-secondary);
  box-shadow: none;
}
.board-tabs :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: var(--dash-border-accent);
  color: var(--primary);
  background: var(--dash-primary-soft);
  box-shadow: none;
}
.board-list { flex: 1; min-height: 0; overflow: auto; }
.board-group__title {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
  color: var(--dash-text-muted);
  background: var(--dash-surface-soft);
  border-top: 1px solid var(--dash-border);
  border-bottom: 1px solid var(--dash-border);
}
.board-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 36px;
  align-items: stretch;
  width: 100%;
  border-bottom: 1px solid var(--dash-border);
  background: transparent;
  color: inherit;
}
.board-row--no-sub {
  grid-template-columns: minmax(0, 1fr);
}
.board-row:hover { background: var(--dash-surface-soft); }
.board-row.active { background: var(--dash-primary-soft); }
.board-row.subscribed { box-shadow: inset 3px 0 0 var(--primary, #409eff); }
.board-row__main {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 64px 52px;
  gap: 6px;
  width: 100%;
  min-width: 0;
  padding: 5px 6px 5px 10px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.board-row__sub {
  margin: 0;
  padding: 0 8px 0 0;
  border: 0;
  background: transparent;
  align-self: center;
  font-size: 10px;
  line-height: 1.2;
  color: var(--dash-text-muted);
  text-align: right;
  white-space: nowrap;
  cursor: pointer;
}
.board-row__sub:hover { color: var(--primary, #409eff); }
.board-row__sub.on { color: var(--primary, #409eff); font-weight: 600; }
.board-row__id { min-width: 0; }
.board-row__px,
.board-row__chg {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  text-align: right;
  align-self: center;
}
.board-empty {
  padding: 24px 12px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--dash-text-muted);
  text-align: center;
}
</style>
