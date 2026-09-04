<template>
  <ElTag :type="tone" size="small">{{ text }}</ElTag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ElTag } from "element-plus";

const props = defineProps<{ text: string }>();

type TagTone = "success" | "danger" | "warning" | "info";

const tone = computed<TagTone>(() => {
  const value = props.text;
  if (value.includes("TRADED") || value === "CONNECTED") return "success";
  if (value.includes("REJECT") || value === "DISCONNECTED") return "danger";
  if (value.includes("CANCEL") || value === "CONNECTING") return "warning";
  return "info";
});
</script>
