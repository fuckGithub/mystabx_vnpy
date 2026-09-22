<!-- AI 供应商管理（含展开行嵌套模型管理） -->
<template>
  <ProviderTab />
</template>

<script setup lang="ts">
defineOptions({
  name: 'ProviderManage',
  inheritAttrs: false,
})

import ProviderTab from './ProviderTab.vue'
</script>
