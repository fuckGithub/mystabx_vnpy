<script setup lang="ts">
import { reactive, ref } from 'vue'

definePage({
  name: 'work-config',
  style: {
    navigationBarTitleText: '系统配置',
  },
})

const configForm = reactive({
  siteName: 'FastAPI Admin',
  siteDesc: '',
  logo: '',
  recordNo: '京ICP备00000000号',
  contactEmail: 'admin@example.com',
  contactPhone: '400-000-0000',
  orderAutoCancel: '30',
  userInitPoints: '100',
  deliveryBaseFee: '5',
  deliveryFreeThreshold: '50',
})

const saving = ref(false)

function handleSave() {
  saving.value = true
  setTimeout(() => {
    uni.showToast({ title: '配置已保存', icon: 'success' })
    saving.value = false
  }, 800)
}

function handleReset() {
  uni.showModal({
    title: '确认重置',
    content: '确定要恢复默认配置吗？',
    success: (res) => {
      if (res.confirm) {
        uni.showToast({ title: '已恢复默认', icon: 'success' })
      }
    },
  })
}
</script>

<template>
  <view class="p-3">
    <wd-cell-group title="基本设置" border>
      <wd-input v-model="configForm.siteName" label="站点名称" placeholder="请输入站点名称" />
      <wd-input v-model="configForm.siteDesc" label="站点描述" placeholder="请输入站点描述" />
      <wd-input v-model="configForm.recordNo" label="备案号" placeholder="请输入备案号" />
    </wd-cell-group>

    <view class="h-3" />

    <wd-cell-group title="联系方式" border>
      <wd-input v-model="configForm.contactEmail" label="联系邮箱" placeholder="请输入邮箱" />
      <wd-input v-model="configForm.contactPhone" label="联系电话" placeholder="请输入电话" />
    </wd-cell-group>

    <view class="h-3" />

    <wd-cell-group title="业务设置" border>
      <wd-input v-model="configForm.orderAutoCancel" label="自动取消(分钟)" type="digit" placeholder="30" />
      <wd-input v-model="configForm.userInitPoints" label="初始积分" type="digit" placeholder="100" />
      <wd-input v-model="configForm.deliveryBaseFee" label="配送基础费(元)" type="digit" placeholder="5" />
      <wd-input v-model="configForm.deliveryFreeThreshold" label="免配送门槛(元)" type="digit" placeholder="50" />
    </wd-cell-group>

    <view class="action-bar">
      <wd-button type="primary" block :loading="saving" @click="handleSave">保存配置</wd-button>
      <wd-button plain block custom-class="mt-3" @click="handleReset">恢复默认</wd-button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.h-3 {
  height: 16rpx;
}

.action-bar {
  margin-top: 32rpx;
  padding-bottom: 40rpx;
}

.mt-3 {
  margin-top: 16rpx;
}
</style>
