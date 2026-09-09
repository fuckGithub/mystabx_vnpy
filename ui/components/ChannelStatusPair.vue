<template>
  <div class="channel-status-pair">
    <span class="channel-status-pair__item">
      <span class="channel-status-pair__label">账号</span>
      <StatusTag :text="loginText" />
    </span>
    <span class="channel-status-pair__item">
      <span class="channel-status-pair__label">行情</span>
      <StatusTag :text="quoteText" />
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import StatusTag from "./StatusTag.vue";
import { loginLabel, loginStatusOf, quoteLabel, quoteStatusOf } from "@/gatewayStatus";

const props = defineProps<{
  row: Record<string, unknown>;
}>();

const loginText = computed(() => loginLabel(loginStatusOf(props.row)));
const quoteText = computed(() => quoteLabel(quoteStatusOf(props.row)));
</script>

<style scoped lang="scss">
.channel-status-pair {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 10px;
}

.channel-status-pair__item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.channel-status-pair__label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
</style>
