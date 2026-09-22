<script lang="ts" setup>
import { useTokenStore } from '@/store/token'

definePage({
  style: {
    navigationBarTitleText: '登录',
  },
})

const tokenStore = useTokenStore()

const form = reactive({
  username: 'admin',
  password: '123456',
})
const remember = ref(false)

async function doLogin() {
  if (tokenStore.hasLogin) {
    uni.navigateBack()
    return
  }
  try {
    await tokenStore.login({
      username: form.username,
      password: form.password,
    })
    // 登录成功后跳转首页（tabbar 首页）
    uni.switchTab({ url: '/pages/index/index' })
  } catch (error) {
    console.error('登录失败', error)
    uni.showToast({ title: '登录失败', icon: 'none' })
  }
}
</script>

<template>
  <view class="login-page min-h-[100vh] flex justify-center px-[30rpx] py-20">
    <view
      class="login-card max-w-[600rpx] w-full rounded-[24rpx] bg-white px-10 py-15 shadow-[0_4rpx_20rpx_rgba(0,0,0,0.08)]">
      <view class="text-center text-[48rpx] text-[#333] font-bold">管理后台</view>
      <view class="mt-[10rpx] text-center text-[28rpx] text-[#999]">管理平台</view>

      <wd-input v-model="form.username" label="账号" placeholder="请输入账号" clearable class="mt-6" />
      <wd-input v-model="form.password" label="密码" type="password" placeholder="请输入密码" clearable class="mt-4" />

      <view class="mt-4 flex items-center">
        <wd-checkbox v-model="remember" />
        <text class="ml-2 text-sm text-gray-500">记住我</text>
      </view>

      <wd-button type="primary" block class="mt-6" @click="doLogin">登录</wd-button>

      <view class="mt-[40rpx] text-center text-[24rpx] text-[#999]">商户端登录</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.login-page {
  background: linear-gradient(180deg, #ff6b35 0%, #ff8f5e 30%, #f5f5f5 30%);
}
</style>
