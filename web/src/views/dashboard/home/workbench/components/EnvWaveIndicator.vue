<template>
  <div class="env-wave" :class="[`env-wave--${tone}`, `env-wave--${size}`, { 'env-wave--live': ripple }]">
    <template v-if="ripple">
      <span class="env-wave__ripple" aria-hidden="true" />
      <span class="env-wave__ripple env-wave__ripple--delay" aria-hidden="true" />
    </template>
    <span class="env-wave__dot" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: string;
    ripple?: boolean;
    size?: "sm" | "md";
  }>(),
  { tone: "muted", ripple: false, size: "md" },
);
</script>

<style scoped lang="scss" src="../styles/env-wave-indicator.scss"></style>
