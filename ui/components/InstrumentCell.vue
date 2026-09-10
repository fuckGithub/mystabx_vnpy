<template>
  <span class="inst">
    <strong v-if="lines.distinct">{{ lines.name }}</strong>
    <small>{{ lines.code }}</small>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { instrumentLines } from "../../features/workbench/liveMap";

const props = defineProps<{
  code: string;
  name?: unknown;
}>();

const lines = computed(() => instrumentLines(props.code, props.name));
</script>

<style scoped>
.inst {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  line-height: 1.25;
}
.inst strong {
  font-size: 12px;
  font-weight: 600;
  color: var(--dash-heading, var(--el-text-color-primary));
}
.inst small {
  font-size: 10px;
  color: var(--dash-text-muted, var(--el-text-color-secondary));
}
</style>
