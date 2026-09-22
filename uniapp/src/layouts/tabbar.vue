<script lang="ts" setup>
const { activeTabbar, getTabbarItemValue, setTabbarItemActive, tabbarList } = useTabbar()

const tabbarPathMap: Record<string, string> = {
  home: '/pages/index/index',
  work: '/pages/work/index',
  mine: '/pages/mine/index',
}

function switchTab(name: string) {
  const url = tabbarPathMap[name]
  if (url) {
    uni.switchTab({ url })
  }
}

function handleTabbarChange({ value }: { value: string }) {
  setTabbarItemActive(value)
  switchTab(value)
}

onMounted(() => {
  // #ifdef APP
  uni.hideTabBar()
  // #endif
})
</script>

<script lang="ts">
export default {
  options: {
    addGlobalClass: true,
    virtualHost: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <slot />
  <wd-gap safe-area-bottom height="var(--wot-tabbar-height, 50px)" />
  <wd-tabbar :model-value="activeTabbar.name" bordered safe-area-inset-bottom fixed @change="handleTabbarChange">
    <wd-tabbar-item
      v-for="(item, index) in tabbarList"
      :key="index"
      :name="item.name"
      :value="getTabbarItemValue(item.name)"
      :title="item.title"
      :icon="item.icon" />
  </wd-tabbar>
</template>
