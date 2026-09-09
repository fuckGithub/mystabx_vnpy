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
    <el-radio-group v-model="tab" size="small" class="board-tabs" @change="emit('tab', tab)">
      <el-radio-button value="all">全部</el-radio-button>
      <el-radio-button value="main">主力</el-radio-button>
      <el-radio-button value="index">指数</el-radio-button>
      <el-radio-button value="product">品种</el-radio-button>
    </el-radio-group>
    <div class="board-list">
      <section v-for="group in groups" :key="group.key" class="board-group">
        <header class="board-group__title">{{ group.title }}</header>
        <button
          v-for="row in group.rows"
          :key="rowKey(row)"
          type="button"
          class="board-row"
          :class="{ active: rowKey(row) === selectedKey }"
          @click="emit('select', row)"
        >
          <span class="board-row__id">
            <strong>{{ String(row.symbol || "") }}</strong>
            <em>{{ productName(row) }}</em>
          </span>
          <span class="board-row__px" :class="pnlClass(changeOf(row))">
            {{ fmtPriceOrDash(lastOf(row)) }}
          </span>
          <span class="board-row__chg" :class="pnlClass(changeOf(row))">
            {{ fmtPct(changeOf(row)) }}
          </span>
        </button>
      </section>
      <div v-if="!groups.some((g) => g.rows.length)" class="board-empty">
        暂无合约。请先连接行情通道，合约查询成功后将按交易所 / 品种列出。
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { contractKey, groupContracts, productName, type BoardTab, type ContractRow } from "../contracts";
import { finitePrice, fmtPct, fmtPriceOrDash, pnlClass, quoteChangePct } from "../../workbench/liveMap";

const props = defineProps<{
  contracts: ContractRow[];
  ticks: Record<string, Record<string, unknown>>;
  selectedKey: string;
}>();

const emit = defineEmits<{
  select: [row: ContractRow];
  search: [keyword: string];
  tab: [tab: BoardTab];
}>();

const keyword = ref("");
const tab = ref<BoardTab>("all");

const groups = computed(() => groupContracts(props.contracts, tab.value, props.ticks));

function rowKey(row: ContractRow) {
  return contractKey(row);
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
.board-tabs {
  display: flex;
  flex-wrap: nowrap;
  margin: 8px;
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
  grid-template-columns: minmax(0, 1.2fr) 72px 58px;
  gap: 6px;
  width: 100%;
  padding: 5px 10px;
  border: 0;
  border-bottom: 1px solid var(--dash-border);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.board-row:hover { background: var(--dash-surface-soft); }
.board-row.active { background: var(--dash-primary-soft); }
.board-row__id { min-width: 0; }
.board-row__id strong {
  display: block;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--dash-heading);
}
.board-row__id em {
  display: block;
  font-style: normal;
  font-size: 10px;
  color: var(--dash-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
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
