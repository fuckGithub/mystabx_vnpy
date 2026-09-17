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
          :style="barStyle(row)"
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
            :class="{
              on: isSubscribed(row) && !allowUnsubscribe,
              unsub: isSubscribed(row) && allowUnsubscribe,
            }"
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
import {
  contractBarColors,
  contractKey,
  groupContracts,
  productName,
  type BoardTab,
  type ContractRow,
} from "../contracts";
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

const barColorByKey = computed(() => {
  const keys = new Set<string>();
  for (const key of Object.keys(props.subscribedKeys || {})) keys.add(key);
  for (const group of groups.value) {
    for (const row of group.rows) {
      if (props.subscribedKeys?.[contractKey(row)]) keys.add(contractKey(row));
    }
  }
  return contractBarColors([...keys]);
});

function rowKey(row: ContractRow) {
  return contractKey(row);
}

function barStyle(row: ContractRow) {
  if (!isSubscribed(row)) return undefined;
  const color = barColorByKey.value[rowKey(row)];
  return color ? { "--contract-bar": color } : undefined;
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

<style scoped src="@/styles/contract-list-panel.css"></style>
