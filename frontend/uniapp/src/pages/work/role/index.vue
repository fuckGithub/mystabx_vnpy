<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { reactive, ref } from 'vue'
import { systemRoleApi } from '@/api/system'
import type { RoleItem } from '@/api/system'

definePage({
  name: 'work-role',
  style: { navigationBarTitleText: '角色管理' },
})

const roles = ref<RoleItem[]>([])
const loading = ref(false)
const total = ref(0)
const queryForm = reactive({ name: '', code: '', status: '' })
const currentPage = ref(1)

async function loadData(page = 1) {
  loading.value = true
  try {
    const res = await systemRoleApi.getPage({
      page_no: page,
      page_size: 20,
      ...(queryForm.name && { name: queryForm.name }),
      ...(queryForm.code && { code: queryForm.code }),
      ...(queryForm.status && { status: queryForm.status }),
    })
    roles.value = (res.items || []) as RoleItem[]
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
      <wd-input v-model="queryForm.name" placeholder="搜索角色名称" clearable @confirm="handleSearch">
        <template #suffix>
          <wd-button size="small" type="primary" @click="handleSearch">搜索</wd-button>
        </template>
      </wd-input>
    </wd-cell-group>

    <view class="h-3" />

    <view v-if="loading" class="loading-hint">加载中...</view>
    <view v-else class="list">
      <view v-for="role in roles" :key="role.id" class="card">
        <view class="card-header">
          <view class="avatar">{{ role.name.charAt(0) }}</view>
          <view class="info">
            <view class="name">
              {{ role.name }}
              <text class="code">@{{ role.code }}</text>
            </view>
            <view class="desc">{{ role.description || '暂无描述' }}</view>
          </view>
          <wd-tag :type="role.status === '0' ? 'success' : 'danger'" size="small">
            {{ role.status === '0' ? '启用' : '禁用' }}
          </wd-tag>
        </view>
        <view class="card-footer">
          <text>
            排序: {{ role.order }} · 数据范围:
            {{ ['仅本人', '本部门', '本部门及以下', '全部', '自定义'][role.data_scope - 1] || '未知' }}
          </text>
        </view>
      </view>
      <view v-if="!loading && roles.length === 0" class="empty-hint">暂无数据</view>
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
    border-radius: 12rpx;
    background: linear-gradient(135deg, #8a2be2, #b56aff);
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
  .code {
    font-size: 20rpx;
    color: #999;
    font-weight: 400;
  }
  .desc {
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
