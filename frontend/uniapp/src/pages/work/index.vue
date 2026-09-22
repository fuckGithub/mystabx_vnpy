<script setup lang="ts">
definePage({
  name: 'work',
  layout: 'tabbar',
  style: {
    navigationBarTitleText: '工作台',
  },
})

// 子包页面路径映射
const subPagePath: Record<string, string> = {
  skills: '/subPages/skills/index',
  router: '/subPages/router/index',
  request: '/subPages/request/index',
  icon: '/subPages/icon/index',
  styles: '/subPages/styles/index',
  pinia: '/subPages/pinia/index',
  'create-uni': '/subPages/create-uni/index',
  ci: '/subPages/ci/index',
  root: '/subPages/uni-ku-root/index',
}

function navigateTo(name: string) {
  const path = subPagePath[name]
  if (path) {
    uni.navigateTo({ url: path })
  }
}

function openUrl(url: string) {
  window.open(url, '_blank')
}
</script>

<template>
  <view class="box-border py-3">
    <view class="mx-3 box-border rounded-3 bg-white px-4 py-6 text-center dark:bg-[var(--wot-dark-background2)]">
      <text class="mb-3 block text-left text-5 text-gray-800 font-bold dark:text-gray-200">Wot Starter</text>
      <text class="mb-3 block text-left text-30rpx text-gray-600 leading-relaxed dark:text-gray-300">
        ⚡️ 基于 vitesse-uni-app 由 vite & uni-app 驱动的、深度整合 Wot UI 组件库的快速启动模板
      </text>
      <text class="block text-left text-3 text-gray-400 leading-relaxed dark:text-gray-400">
        背靠 Uni Helper、Wot UI 团队，告别 HBuilderX ，拥抱现代前端开发工具链
      </text>
    </view>

    <demo-block title="工具链介绍" transparent>
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell title="🧩 WotUI组件库" is-link @click="openUrl('https://wot-ui.cn/')" />
        <wd-cell title="🧠 Agent Skills" is-link @click="navigateTo('skills')" />
        <wd-cell title="🚦 Router 路由管理" is-link @click="navigateTo('router')" />
        <wd-cell title="🌐 Alova 网络请求" is-link @click="navigateTo('request')" />
        <wd-cell title="🎨 Icon 图标" is-link @click="navigateTo('icon')" />
        <wd-cell title="✨ Unocss 原子化" is-link @click="navigateTo('styles')" />
        <wd-cell title="🍍 Pinia 持久化" is-link @click="navigateTo('pinia')" />
        <wd-cell title="🌱 CreateUni 脚手架" is-link @click="navigateTo('create-uni')" />
        <wd-cell title="🔄 CI/CD 持续集成" is-link @click="navigateTo('ci')" />
        <wd-cell title="🦾  uni-ku/root" is-link @click="navigateTo('root')" />
      </wd-cell-group>
    </demo-block>
  </view>
</template>
