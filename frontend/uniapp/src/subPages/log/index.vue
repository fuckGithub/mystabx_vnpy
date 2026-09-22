<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { systemLogApi } from '@/api/system'
import type { LogItem } from '@/api/system'

definePage({
  name: 'log',
  style: { navigationBarTitleText: '日志管理' },
})

const list = ref<LogItem[]>([])
const loading = ref(false)
const total = ref(0)

async function loadData(page = 1) {
  loading.value = true
  try {
    const res = await systemLogApi.getPage({ page_no: page, page_size: 20 })
    list.value = (res.items || []) as LogItem[]
    total.value = res.total || 0
  } catch {
    /* handled by http */
  } finally {
    loading.value = false
  }
}

function getMethodColor(m: string) {
  const map: Record<string, string> = { GET: '#07c160', POST: '#4d7fff', PUT: '#ff9500', DELETE: '#ff4d4f' }
  return map[m] || '#999'
}

onLoad(() => {
  loadData()
})
</script>

<template>
  <view class="p-3">
    <view v-if="loading" class="hint">加载中...</view>
    <view v-else class="list">
      <view v-for="item in list" :key="item.id" class="card">
        <view class="card-h">
          <view class="left">
            <view
              class="method"
              :style="{
                background: `${getMethodColor(item.request_method)}18`,
                color: getMethodColor(item.request_method),
              }">
              {{ item.request_method }}
            </view>
            <view class="info">
              <view class="tl">{{ item.module }} / {{ item.method }}</view>
              <view class="url">{{ item.request_url }}</view>
            </view>
          </view>
          <view class="status">
            <wd-icon
              :name="item.status === 1 ? 'checkmark-circle' : 'close-circle'"
              :color="item.status === 1 ? '#07c160' : '#ff4d4f'"
              size="16px" />
          </view>
        </view>
        <view class="card-f">
          <text>{{ item.username || '匿名' }}</text>
          <text class="sep">|</text>
          <text>{{ item.ip || '-' }}</text>
          <text class="sep">|</text>
          <text>{{ item.cost_time ? `${item.cost_time}ms` : '-' }}</text>
        </view>
      </view>
      <view v-if="!loading && list.length === 0" class="hint">暂无日志</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.hint {
  text-align: center;
  padding: 60rpx;
  color: #999;
  font-size: 26rpx;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.card {
  background: #fff;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}
.card-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}
.left {
  display: flex;
  align-items: center;
  gap: 12rpx;
  flex: 1;
  min-width: 0;
}
.method {
  font-size: 18rpx;
  font-weight: 700;
  padding: 4rpx 10rpx;
  border-radius: 6rpx;
  font-family: monospace;
  flex-shrink: 0;
}
.info {
  flex: 1;
  min-width: 0;
}
.tl {
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
}
.url {
  font-size: 20rpx;
  color: #999;
  margin-top: 2rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status {
  flex-shrink: 0;
}
.card-f {
  margin-top: 8rpx;
  padding-top: 8rpx;
  border-top: 1px solid #f5f5f5;
  font-size: 20rpx;
  color: #999;
  display: flex;
  gap: 8rpx;
  align-items: center;
}
.sep {
  color: #ddd;
}
</style>
