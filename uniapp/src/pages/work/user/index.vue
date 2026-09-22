<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { reactive, ref } from 'vue'
import { systemUserApi } from '@/api/system'
import type { UserInfo } from '@/api/user'

definePage({
  name: 'work-user',
  style: { navigationBarTitleText: '用户管理' },
})

const users = ref<UserInfo[]>([])
const loading = ref(false)
const total = ref(0)
const queryForm = reactive({ username: '', name: '', status: '' })
const currentPage = ref(1)

async function loadData(page = 1) {
  loading.value = true
  try {
    const res = await systemUserApi.getPage({
      page_no: page,
      page_size: 20,
      ...(queryForm.username && { username: queryForm.username }),
      ...(queryForm.name && { name: queryForm.name }),
      ...(queryForm.status && { status: queryForm.status }),
    })
    users.value = (res.items || []) as UserInfo[]
    total.value = res.total || 0
    currentPage.value = page
  } catch {
    /* handled by http */
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  loadData(1)
}

onLoad(() => {
  loadData()
})
</script>

<template>
  <view class="p-3">
    <wd-cell-group border>
      <wd-input v-model="queryForm.name" placeholder="搜索昵称" clearable @confirm="handleSearch">
        <template #suffix>
          <wd-button size="small" type="primary" @click="handleSearch">搜索</wd-button>
        </template>
      </wd-input>
    </wd-cell-group>

    <view class="h-3" />

    <view v-if="loading" class="loading-hint">加载中...</view>
    <view v-else class="list">
      <view v-for="user in users" :key="user.id" class="card">
        <view class="card-header">
          <view class="avatar">{{ (user.name || '?').charAt(0) }}</view>
          <view class="info">
            <view class="name">
              {{ user.name }}
              <text class="uname">@{{ user.username }}</text>
            </view>
            <view class="meta">{{ user.mobile || '未绑定手机' }} | {{ user.email || '未绑定邮箱' }}</view>
          </view>
          <wd-tag :type="user.status ? 'success' : 'danger'" size="small">{{ user.status ? '启用' : '停用' }}</wd-tag>
        </view>
        <view class="card-footer">
          <text>{{ user.dept_name || '未分配部门' }} · {{ user.roleNames?.join(', ') || '无角色' }}</text>
        </view>
      </view>
      <view v-if="!loading && users.length === 0" class="empty-hint">暂无数据</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.h-3 {
  height: 16rpx;
}
.loading-hint,
.empty-hint {
  text-align: center;
  padding: 60rpx;
  color: #999;
  font-size: 26rpx;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
  .card-header {
    display: flex;
    align-items: center;
    gap: 16rpx;
  }
  .avatar {
    width: 72rpx;
    height: 72rpx;
    border-radius: 50%;
    background: linear-gradient(135deg, #4d7fff, #6c9fff);
    color: #fff;
    font-size: 28rpx;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .info {
    flex: 1;
    min-width: 0;
  }
  .name {
    font-size: 28rpx;
    font-weight: 600;
    color: #333;
    display: flex;
    align-items: center;
    gap: 8rpx;
  }
  .uname {
    font-size: 20rpx;
    color: #999;
    font-weight: 400;
  }
  .meta {
    font-size: 22rpx;
    color: #999;
    margin-top: 4rpx;
  }
  .card-footer {
    margin-top: 12rpx;
    padding-top: 12rpx;
    border-top: 1px solid #f5f5f5;
    font-size: 22rpx;
    color: #999;
  }
}
</style>
