<script setup lang="ts">
import { onReady, onShow } from '@dcloudio/uni-app'
import { reactive, ref } from 'vue'

definePage({
  name: 'home',
  layout: 'tabbar',
  style: {
    navigationBarTitleText: '首页',
  },
})

const current = ref<number>(0)

/**
 * 访问统计数据
 */
interface VisitStatsVO {
  todayUvCount: number
  uvGrowthRate: number
  totalUvCount: number
  todayPvCount: number
  pvGrowthRate: number
  totalPvCount: number
}

/**
 * 导航项
 */
interface NavItem {
  icon: string
  color: string
  bgColor: string
  title: string
  url: string
}

/**
 * 快捷导航列表
 */
const NAV_LIST: NavItem[] = [
  {
    icon: 'user',
    color: '#4d7fff',
    bgColor: '#eef2ff',
    title: '用户管理',
    url: '/pages/work/user/index',
  },
  {
    icon: 'security',
    color: '#8a2be2',
    bgColor: '#f3e8ff',
    title: '角色管理',
    url: '/pages/work/role/index',
  },
  {
    icon: 'notification',
    color: '#ff9500',
    bgColor: '#fff7e8',
    title: '通知公告',
    url: '/pages/work/notice/index',
  },
  {
    icon: 'settings',
    color: '#5ac8fa',
    bgColor: '#e8f8ff',
    title: '系统配置',
    url: '/pages/work/config/index',
  },
]

/**
 * 默认访问统计数据
 */
const DEFAULT_VISIT_STATS: VisitStatsVO = {
  todayUvCount: 1234,
  uvGrowthRate: 15.6,
  totalUvCount: 45678,
  todayPvCount: 5678,
  pvGrowthRate: 23.4,
  totalPvCount: 123456,
}

// 通知公告文本
const NOTICE_TEXT = '通知公告: fastapp 是一个基于 Vue3 + UniApp 的前端模板项目，提供了一套完整的前端解决方案'

// 默认日期范围（天数)
const DEFAULT_DAYS_RANGE = 7

// 访问统计数据
const visitStatsData = ref<VisitStatsVO>(DEFAULT_VISIT_STATS)

// 图表数据
const chartData = ref({})

// 日期范围
const recentDaysRange = ref(DEFAULT_DAYS_RANGE)

// 轮播图列表
const swiperList = ref(['/static/images/banner01.jpg', '/static/images/banner02.jpg'])

// 快捷导航列表
const navList = reactive(NAV_LIST)

// 导航到指定页面
function navigateTo(url: string) {
  // 避免空 URL 导航
  if (!url) return

  const tabbarPages = ['/pages/index/index', '/pages/work/index', '/pages/mine/index']
  if (tabbarPages.includes(url)) {
    uni.switchTab({ url })
  } else {
    uni.navigateTo({ url })
  }
}

// 生成静态的访问趋势数据
function generateStaticTrendData(days: number) {
  const ipList = []
  const pvList = []

  const today = new Date()

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(today.getDate() - i)

    // 生成模拟数据
    ipList.push(Math.floor(Math.random() * 500) + 200)
    pvList.push(Math.floor(Math.random() * 1000) + 500)
  }

  return {
    ipList,
    pvList,
  }
}

// 加载访问统计数据（使用静态数据）
async function loadVisitStatsData() {
  // 模拟异步加载
  setTimeout(() => {
    visitStatsData.value = { ...DEFAULT_VISIT_STATS }
  }, 100)
}

// 加载访问趋势数据（使用静态数据）
function loadVisitTrendData() {
  // 模拟异步加载
  setTimeout(() => {
    const data = generateStaticTrendData(recentDaysRange.value)

    const res = {
      series: [
        {
          name: 'UV',
          data: data.ipList,
        },
        {
          name: 'PV',
          data: data.pvList,
        },
      ],
    }
    chartData.value = JSON.parse(JSON.stringify(res))
  }, 100)
}

onReady(() => {
  loadVisitStatsData()
  loadVisitTrendData()
})

onShow(() => {
  // 确保 tabbar 状态正确
  const pages = getCurrentPages()
  if (pages.length > 0) {
    const currentPage = pages[pages.length - 1]
    if (currentPage.route === 'pages/index/index') {
      // 通过事件通知 tabbar 布局更新状态
      uni.$emit('updateTabbar', 'index')
    }
  }
})
</script>

<template>
  <view class="app-container">
    <!-- 轮播图 -->
    <view class="swiper-container">
      <wd-swiper v-model:current="current" :list="swiperList" autoplay indicator image-mode="scaleToFill" />
    </view>

    <!-- 快捷导航 -->
    <view class="nav-grid">
      <view class="nav-grid-inner">
        <view v-for="(item, index) in navList" :key="index" class="nav-card" @click="navigateTo(item.url)">
          <view class="nav-icon" :style="{ background: item.bgColor }">
            <wd-icon :name="item.icon" :color="item.color" size="22px" />
          </view>
          <text class="nav-title">{{ item.title }}</text>
        </view>
      </view>
    </view>

    <!-- 通知公告 -->
    <view class="notice-text">
      <wd-notice-bar type="warning" prefix="warn-bold" :text="NOTICE_TEXT" />
    </view>

    <!-- 数据统计 -->
    <view class="stats-grid">
      <view class="stats-item">
        <image class="stats-icon" src="/static/icons/visitor.png" lazy-load />
        <view class="stats-info">
          <wd-text text="访客数" />
          <view class="stats-value">
            <wd-text type="warning" :text="visitStatsData.todayUvCount" bold />
          </view>
        </view>
      </view>
      <view class="stats-item">
        <image class="stats-icon" src="/static/icons/browser.png" lazy-load />
        <view class="stats-info">
          <wd-text text="浏览量" />
          <view class="stats-value">
            <wd-text type="success" :text="visitStatsData.todayPvCount" bold />
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.app-container {
  padding: 20rpx;

  .swiper-container {
    margin-bottom: 20rpx;
    border-radius: 16rpx;
    overflow: hidden;
  }

  .nav-grid {
    margin-bottom: 20rpx;

    .nav-grid-inner {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16rpx;
    }

    .nav-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24rpx 12rpx;
      background: #fff;
      border-radius: 16rpx;
      gap: 12rpx;
      box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
    }

    .nav-icon {
      width: 80rpx;
      height: 80rpx;
      border-radius: 16rpx;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .nav-title {
      font-size: 24rpx;
      color: #333;
      font-weight: 500;
    }
  }

  .notice-text {
    margin-bottom: 20rpx;
    border-radius: 16rpx;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10rpx;
    margin-bottom: 20rpx;
  }

  .stats-item {
    display: flex;
    align-items: center;
    padding: 20rpx;
    background-color: var(--bg-color-2);
    border-radius: 16rpx;
  }

  .stats-icon {
    width: 80rpx;
    height: 80rpx;
    border-radius: 8rpx;
    margin-right: 20rpx;
  }
}
</style>
