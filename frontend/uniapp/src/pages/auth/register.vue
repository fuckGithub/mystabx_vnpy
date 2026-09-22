<script lang="ts" setup>
import { LOGIN_PAGE } from '@/router/config'
import { http } from '@/http/http'
import { ContentTypeEnum } from '@/http/tools/enum'

definePage({
  style: {
    navigationBarTitleText: '注册',
  },
})

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const loading = ref(false)

const rules = {
  username: [
    { required: true, message: '请输入账号' },
    { minLength: 2, maxLength: 20, message: '账号长度 2-20 个字符' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { minLength: 6, maxLength: 32, message: '密码长度 6-32 个字符' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码' },
    {
      validator: (_value: string, done: (arg: boolean) => void) => {
        done(form.password !== form.confirmPassword)
      },
      message: '两次输入的密码不一致',
    },
  ],
}

const formRef = ref<any>(null)

async function doRegister() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('username', form.username)
    params.append('password', form.password)

    await http<{ code: number; data: any; msg: string }>({
      url: '/system/auth/register',
      method: 'POST',
      header: { 'Content-Type': ContentTypeEnum.FORM_URLENCODED },
      data: params.toString(),
    })

    uni.showToast({ title: '注册成功', icon: 'success' })

    // 注册成功后跳转到登录页
    setTimeout(() => {
      uni.navigateTo({ url: LOGIN_PAGE })
    }, 1500)
  } catch (error: any) {
    const msg = error?.errMsg || error?.message || '注册失败'
    uni.showToast({ title: msg, icon: 'none' })
  } finally {
    loading.value = false
  }
}

function goLogin() {
  uni.navigateTo({ url: LOGIN_PAGE })
}
</script>

<template>
  <view class="register-page">
    <view class="register-card">
      <view class="title">管理后台</view>
      <view class="subtitle">管理平台</view>

      <wd-form ref="formRef" :model="form" :rules="rules" class="mt-6">
        <wd-input v-model="form.username" label="账号" placeholder="请输入账号" clearable prop="username" />
        <wd-input
          v-model="form.password"
          label="密码"
          type="password"
          placeholder="请输入密码"
          clearable
          prop="password"
          class="mt-4" />
        <wd-input
          v-model="form.confirmPassword"
          label="确认密码"
          type="password"
          placeholder="请再次输入密码"
          clearable
          prop="confirmPassword"
          class="mt-4" />
      </wd-form>

      <wd-button type="primary" block class="mt-6" :loading="loading" @click="doRegister">注册</wd-button>

      <view class="footer" @click="goLogin">已有账号？去登录</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.register-page {
  display: flex;
  justify-content: center;
  padding: 80rpx 30rpx;
  min-height: 100vh;
  background: linear-gradient(180deg, #ff6b35 0%, #ff8f5e 30%, #f5f5f5 30%);
}

.register-card {
  width: 100%;
  max-width: 600rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 60rpx 40rpx;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.08);
}

.title {
  font-size: 48rpx;
  font-weight: bold;
  text-align: center;
  color: #333;
}

.subtitle {
  font-size: 28rpx;
  text-align: center;
  color: #999;
  margin-top: 10rpx;
}

.footer {
  text-align: center;
  color: #ff6b35;
  font-size: 28rpx;
  margin-top: 40rpx;
}
</style>
