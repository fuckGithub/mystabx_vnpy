<script lang="ts" setup>
import { storeToRefs } from 'pinia'
import { LOGIN_PAGE } from '@/router/config'
import { useUserStore } from '@/store'
import { useTokenStore } from '@/store/token'

definePage({
  style: { navigationBarTitleText: '我的' },
})

const userStore = useUserStore()
const tokenStore = useTokenStore()
const { userInfo } = storeToRefs(userStore)

const isLoggedIn = computed(() => tokenStore.hasLogin)

const getNickName = () => userInfo.value?.nickname || userInfo.value?.username || '未登录用户'
const getAvatarUrl = () => userInfo.value?.avatar || '/static/logo.png'

function handleLogin() {
  uni.navigateTo({ url: LOGIN_PAGE })
}

function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确定要退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        useTokenStore().logout()
        uni.showToast({ title: '退出成功', icon: 'success' })
      }
    },
  })
}

const menuGroups = [
  [
    { icon: '⚙️', title: '设置', path: '' },
    { icon: '💬', title: '关于', path: '' },
  ],
]

function handleMenuClick(path: string, title: string) {
  if (path) {
    uni.navigateTo({ url: path })
  } else {
    uni.showToast({ title: `${title}功能待接入`, icon: 'none' })
  }
}
</script>

<template>
  <view class="profile-page p-safe">
    <!-- ===== 用户头部（登录/未登录仅此处不同） ===== -->
    <view class="user-header">
      <view class="header-bg" />
      <!-- 未登录：登录引导 -->
      <view v-if="!isLoggedIn" class="header-content">
        <view class="avatar-wrap login-avatar">
          <text class="avatar-emoji">👤</text>
        </view>
        <view class="user-text">
          <text class="user-name">登录</text>
          <text class="user-sub">登录后查看更多信息</text>
        </view>
        <button class="btn-login-mini" @click="handleLogin">登录</button>
      </view>
      <!-- 已登录：用户信息 -->
      <view v-else class="header-content">
        <view class="avatar-wrap">
          <image :src="getAvatarUrl()" mode="aspectFill" class="avatar" />
        </view>
        <view class="user-text">
          <text class="user-name">{{ getNickName() }}</text>
          <text v-if="userInfo?.username" class="user-sub">{{ userInfo.username }}</text>
        </view>
        <wd-icon name="arrow-right" size="16px" color="rgba(255,255,255,0.6)" />
      </view>
    </view>

    <!-- ===== 菜单列表 ===== -->
    <view class="menu-section">
      <view v-for="(group, gi) in menuGroups" :key="gi" class="menu-group">
        <view
          v-for="(item, idx) in group"
          :key="idx"
          class="menu-item"
          hover-class="menu-hover"
          @click="handleMenuClick(item.path, item.title)">
          <view class="menu-left">
            <text class="menu-emoji">{{ item.icon }}</text>
            <text class="menu-title">{{ item.title }}</text>
          </view>
          <view class="menu-right">
            <text v-if="item.title === '我的订单'" class="menu-badge">查看全部</text>
            <wd-icon name="arrow-right" size="14px" color="#ccc" />
          </view>
        </view>
      </view>
    </view>

    <!-- ===== 退出（仅已登录） ===== -->
    <view v-if="isLoggedIn" class="logout-wrap">
      <button class="btn-logout" @click="handleLogout">退出登录</button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.profile-page {
  background: var(--page-bg);
}

/* ===== 用户头部 ===== */
.user-header {
  position: relative;
  padding: 0 32rpx;
}

.header-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 260rpx;
  background: var(--brand-gradient);
  border-radius: 0 0 40rpx 40rpx;
}

.header-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 48rpx 0 60rpx;
}

.login-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  font-size: 48rpx;
}

.btn-login-mini {
  height: 56rpx;
  padding: 0 24rpx;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 28rpx;
  color: #fff;
  font-size: 24rpx;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.4);
  flex-shrink: 0;

  &:active {
    background: rgba(255, 255, 255, 0.4);
  }
}

.avatar-wrap {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
  overflow: hidden;
  border: 4rpx solid rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
  background: #f0f0f0;
}

/* ===== 菜单列表 ===== */
.menu-section {
  margin: 0 32rpx;
}

.avatar {
  width: 100%;
  height: 100%;
}

.user-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.user-name {
  font-size: 36rpx;
  font-weight: 700;
  color: #fff;
}

.user-sub {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}

/* ===== 菜单 ===== */
.menu-section {
  margin: 0 32rpx;
}

.menu-group {
  background: var(--card-bg);
  border-radius: 20rpx;
  margin-bottom: 20rpx;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
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

.menu-hover {
  background: #fafafa !important;
}

.menu-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.menu-emoji {
  font-size: 32rpx;
  width: 40rpx;
  text-align: center;
}

.menu-title {
  font-size: 28rpx;
  color: var(--text-primary);
}

.menu-right {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.menu-badge {
  font-size: 22rpx;
  color: var(--text-tertiary);
}

/* ===== 退出 ===== */
.logout-wrap {
  padding: 40rpx 32rpx 60rpx;
}

.btn-logout {
  width: 100%;
  height: 80rpx;
  background: var(--card-bg);
  border-radius: 20rpx;
  color: #ff4d4f;
  font-size: 28rpx;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);

  &:active {
    background: #fef0ef;
    border-color: #ffccc7;
  }
}
</style>
