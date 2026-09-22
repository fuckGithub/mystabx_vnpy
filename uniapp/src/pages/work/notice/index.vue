<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

definePage({
  name: 'work-notice',
  style: {
    navigationBarTitleText: '通知公告',
  },
})

interface NoticeItem {
  id: number
  title: string
  content: string
  type: string
  typeColor: string
  createTime: string
  read: boolean
}

const notices = ref<NoticeItem[]>([])

const mockNotices: NoticeItem[] = [
  {
    id: 1,
    title: '系统升级维护通知',
    content: '平台将于本周六凌晨2:00-6:00进行系统升级维护，届时将暂停所有服务。',
    type: '系统公告',
    typeColor: '#4d7fff',
    createTime: '2024-06-15',
    read: false,
  },
  {
    id: 2,
    title: '新商户入驻流程更新',
    content: '优化了商户入驻流程，新增资质在线审核功能，减少等待时间。',
    type: '更新通知',
    typeColor: '#07c160',
    createTime: '2024-06-14',
    read: false,
  },
  {
    id: 3,
    title: '端午节放假安排',
    content: '根据国家规定，6月22日至6月24日端午节放假，请各商户提前做好安排。',
    type: '通知',
    typeColor: '#ff9500',
    createTime: '2024-06-10',
    read: true,
  },
  {
    id: 4,
    title: '订单系统功能优化',
    content: '订单管理页面新增批量导出功能，支持按时间范围筛选导出订单数据。',
    type: '更新通知',
    typeColor: '#07c160',
    createTime: '2024-06-08',
    read: true,
  },
  {
    id: 5,
    title: '2024年Q2平台数据报告',
    content: '平台Q2总交易额同比增长35%，新增商户120家，活跃用户数突破10万。',
    type: '数据报告',
    typeColor: '#8a2be2',
    createTime: '2024-07-01',
    read: true,
  },
]

onLoad(() => {
  notices.value = mockNotices
})
</script>

<template>
  <view class="p-3">
    <view class="notice-list">
      <view v-for="notice in notices" :key="notice.id" class="notice-card">
        <view class="notice-top">
          <view class="notice-type" :style="{ background: `${notice.typeColor}18`, color: notice.typeColor }">
            {{ notice.type }}
          </view>
          <text v-if="!notice.read" class="unread-dot">未读</text>
        </view>
        <view class="notice-title">{{ notice.title }}</view>
        <view class="notice-content">{{ notice.content }}</view>
        <view class="notice-time">{{ notice.createTime }}</view>
      </view>

      <view v-if="notices.length === 0" class="empty-hint">暂无通知公告</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.notice-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.notice-top {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.notice-type {
  font-size: 20rpx;
  padding: 4rpx 14rpx;
  border-radius: 6rpx;
  font-weight: 500;
}

.unread-dot {
  font-size: 20rpx;
  color: #ff4d4f;
  font-weight: 500;
}

.notice-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 10rpx;
}

.notice-content {
  font-size: 24rpx;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12rpx;
}

.notice-time {
  font-size: 22rpx;
  color: #ccc;
}

.empty-hint {
  text-align: center;
  padding: 60rpx;
  color: #999;
  font-size: 26rpx;
}
</style>
