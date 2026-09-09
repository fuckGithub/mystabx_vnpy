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
  if (value.includes("TRADED") || value === "CONNECTED" || value.includes("已登录") || value.includes("已连接")) {
    return "success";
  }
  if (value.includes("REJECT") || value === "DISCONNECTED" || value.includes("未登录") || value.includes("未连接")) {
    return "danger";
  }
  if (value.includes("CANCEL") || value === "CONNECTING" || value.includes("登录中") || value.includes("连接中")) {
    return "warning";
  }
  return "info";
});
</script>
