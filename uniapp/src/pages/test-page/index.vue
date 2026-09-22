<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
definePage({ name: 'test-page', style: { navigationBarTitleText: '测试页' } })

const msg = ref('初始值')
onLoad(() => {
  msg.value = 'onLoad已执行'
})
</script>
<template>
  <view style="padding: 40rpx">
    <text style="font-size: 32rpx; color: #333">{{ msg }}</text>
  </view>
</template>
