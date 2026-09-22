<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { systemDictApi } from '@/api/system'
import type { DictTypeItem } from '@/api/system'

definePage({
  name: 'dictionary',
  style: { navigationBarTitleText: '字典管理' },
})

const list = ref<DictTypeItem[]>([])
const loading = ref(false)
const total = ref(0)
const keyword = ref('')

const dataMap = ref<Record<number, { label: string; value: string }[]>>({})

async function loadData(page = 1) {
  loading.value = true
  try {
    const res = await systemDictApi.getTypePage({
      page_no: page,
      page_size: 20,
      ...(keyword.value && { dict_name: keyword.value }),
    })
    list.value = (res.items || []) as DictTypeItem[]
    total.value = res.total || 0
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
    <wd-input v-model="keyword" placeholder="搜索字典名称" clearable @confirm="handleSearch">
      <template #suffix>
        <wd-button size="small" type="primary" @click="handleSearch">搜索</wd-button>
      </template>
    </wd-input>
    <view class="h-3" />
    <view v-if="loading" class="hint">加载中...</view>
    <view v-else class="list">
      <view v-for="item in list" :key="item.id" class="card">
        <view class="card-h">
          <view class="av">{{ item.dict_name.charAt(0) }}</view>
          <view class="info">
            <view class="tl">{{ item.dict_name }}</view>
            <view class="sub">{{ item.dict_code }}</view>
          </view>
          <wd-tag :type="item.status === '0' ? 'success' : 'danger'" size="small">
            {{ item.status === '0' ? '正常' : '停用' }}
          </wd-tag>
        </view>
        <view v-if="item.description" class="card-f">{{ item.description }}</view>
      </view>
      <view v-if="!loading && list.length === 0" class="hint">暂无数据</view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.h-3 {
  height: 16rpx;
}
.hint {
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
}
.card-h {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.av {
  width: 72rpx;
  height: 72rpx;
  border-radius: 12rpx;
  background: linear-gradient(135deg, #5ac8fa, #8ad8ff);
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
.tl {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
}
.sub {
  font-size: 20rpx;
  color: #999;
  margin-top: 4rpx;
  font-family: monospace;
}
.card-f {
  margin-top: 12rpx;
  padding-top: 12rpx;
  border-top: 1px solid #f5f5f5;
  font-size: 22rpx;
  color: #999;
}
</style>
