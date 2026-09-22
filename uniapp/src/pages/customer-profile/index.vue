<script setup lang="ts">
import { useUserStore } from '@/store/userStore'
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'

definePage({
  name: 'customer-profile',
  style: {
    navigationBarTitleText: '个人中心',
  },
})

const userStore = useUserStore()

interface MenuItem {
  icon: string
  title: string
  path: string
  badge?: string
}

const menuGroups = ref<MenuItem[][]>([
  [{ icon: 'order', title: '我的订单', path: '/pages/customer-orders/index', badge: '' }],
  [
    { icon: 'location', title: '收货地址', path: '', badge: '' },
    { icon: 'star', title: '我的收藏', path: '', badge: '' },
  ],
  [
    { icon: 'setting', title: '设置', path: '', badge: '' },
    { icon: 'info', title: '关于', path: '', badge: '' },
  ],
])

const handleMenuClick = (item: MenuItem) => {
  if (item.path) {
    uni.navigateTo({ url: item.path })
  } else {
    uni.showToast({ title: `${item.title}功能待接入`, icon: 'none' })
  }
}

const handleLogout = () => {
  uni.showModal({
    title: '确认退出',
    content: '确定要退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        userStore.logout()
      }
    },
  })
}

const getAvatarUrl = () => {
  return userStore.userInfo?.avatar || '/static/logo.png'
}

const getNickName = () => {
  return userStore.userInfo?.nickname || userStore.userInfo?.username || '未登录用户'
}

onLoad(() => {
  if (!userStore.isLogin) {
    userStore.checkLogin()
  }
})
</script>

<template>
  <view class="profile-page">
    <!-- 用户信息头部 -->
    <view class="user-header">
      <view class="avatar-wrap">
        <image :src="getAvatarUrl()" mode="aspectFill" class="avatar" />
      </view>
      <view class="user-info">
        <text class="nickname">{{ getNickName() }}</text>
        <text v-if="userStore.userInfo?.phone" class="user-desc">
          {{ userStore.userInfo.phone }}
        </text>
      </view>
      <wd-icon name="arrow-right" size="16px" color="rgba(255,255,255,0.7)" />
    </view>

    <!-- 统计卡片 -->
    <view class="stats-card">
      <view class="stat-item">
        <text class="stat-num">0</text>
        <text class="stat-label">待接单</text>
      </view>
      <view class="stat-divider" />
      <view
        class="stat-item"
        @click="handleMenuClick({ icon: 'order', title: '配送中', path: '/pages/customer-orders/index' })">
        <text class="stat-num">0</text>
        <text class="stat-label">配送中</text>
      </view>
      <view class="stat-divider" />
      <view class="stat-item">
        <text class="stat-num">0</text>
        <text class="stat-label">待评价</text>
      </view>
    </view>

    <!-- 菜单列表 -->
    <view class="menu-section">
      <view v-for="(group, gIdx) in menuGroups" :key="gIdx" class="menu-group">
        <view v-for="(item, idx) in group" :key="idx" class="menu-item" @click="handleMenuClick(item)">
          <view class="menu-left">
            <wd-icon :name="item.icon" size="20px" color="#666" />
            <text class="menu-title">{{ item.title }}</text>
          </view>
          <view class="menu-right">
            <text v-if="item.badge" class="menu-badge">{{ item.badge }}</text>
            <wd-icon name="arrow-right" size="14px" color="#ccc" />
          </view>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-section">
      <button class="logout-btn" @click="handleLogout">退出登录</button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  background: #f8f8f8;
}

.user-header {
  background: linear-gradient(135deg, #ff6b35, #ff8a50);
  padding: 40rpx 30rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
}

.avatar-wrap {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  overflow: hidden;
  border: 4rpx solid rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.avatar {
  width: 100%;
  height: 100%;
  background: #f0f0f0;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.nickname {
  font-size: 34rpx;
  font-weight: 700;
  color: #fff;
}

.user-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

/* 统计卡片 */
.stats-card {
  display: flex;
  align-items: center;
  background: #fff;
  margin: -30rpx 20rpx 12rpx;
  border-radius: 16rpx;
  padding: 24rpx 0;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 1;
}

.stat-item {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.stat-num {
  font-size: 32rpx;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 22rpx;
  color: #999;
}

.stat-divider {
  width: 1px;
  height: 40rpx;
  background: #eee;
}

/* 菜单 */
.menu-section {
  margin: 0 20rpx;
}

.menu-group {
  background: #fff;
  border-radius: 16rpx;
  margin-bottom: 16rpx;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 24rpx;
  border-bottom: 1px solid #f5f5f5;

  &:last-child {
    border-bottom: none;
  }
}

.menu-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.menu-title {
  font-size: 28rpx;
  color: #333;
}

.menu-right {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.menu-badge {
  font-size: 22rpx;
  color: #ff6b35;
  background: #fff5f0;
  padding: 2rpx 12rpx;
  border-radius: 20rpx;
}

/* 退出 */
.logout-section {
  padding: 40rpx 20rpx;
}

.logout-btn {
  width: 100%;
  height: 80rpx;
  background: #fff;
  border-radius: 16rpx;
  color: #ff4d4f;
  font-size: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #f0f0f0;
}
</style>
