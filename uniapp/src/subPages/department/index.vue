<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { systemDeptApi } from '@/api/system'
import type { DeptItem } from '@/api/system'

definePage({
  name: 'department',
  style: { navigationBarTitleText: '部门管理' },
})

const tree = ref<DeptItem[]>([])
const loading = ref(false)
const expanded = ref<Set<number>>(new Set())

function toggle(id: number) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}

interface FlatDept extends DeptItem {
  _depth?: number
}

function renderTree(nodes: DeptItem[], depth = 0): FlatDept[] {
  const result: FlatDept[] = []
  for (const node of nodes) {
    result.push({ ...node, _depth: depth })
    if (node.children && node.children.length > 0 && expanded.value.has(node.id)) {
      result.push(...renderTree(node.children, depth + 1))
    }
  }
  return result
}

const flatList = ref<FlatDept[]>([])

async function loadData() {
  loading.value = true
  try {
    tree.value = (await systemDeptApi.getTree()) as DeptItem[]
    flatList.value = renderTree(tree.value)
  } catch {
    /* handled by http */
  } finally {
    loading.value = false
  }
}

onLoad(() => {
  loadData()
})
</script>

<template>
  <view class="p-3">
    <view v-if="loading" class="hint">加载中...</view>
    <view v-else class="list">
      <view
        v-for="item in flatList"
        :key="item.id"
        class="card"
        :style="{ marginLeft: `${(item._depth || 0) * 40}rpx` }">
        <view class="card-h" @click="toggle(item.id)">
          <view v-if="item.children?.length" class="arrow" :class="{ expanded: expanded.has(item.id) }">›</view>
          <view v-else class="arrow-placeholder" />
          <view class="av">{{ item.name.charAt(0) }}</view>
          <view class="info">
            <view class="tl">{{ item.name }}</view>
            <view class="desc">{{ item.leader ? `负责人: ${item.leader}` : item.description || '暂无描述' }}</view>
          </view>
          <wd-tag :type="item.status === '0' ? 'success' : 'danger'" size="small">
            {{ item.status === '0' ? '启用' : '禁用' }}
          </wd-tag>
        </view>
      </view>
      <view v-if="!loading && flatList.length === 0" class="hint">暂无数据</view>
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
  gap: 12rpx;
}
.arrow {
  font-size: 32rpx;
  color: #999;
  width: 24rpx;
  text-align: center;
  transition: transform 0.2s;
  flex-shrink: 0;
  &.expanded {
    transform: rotate(90deg);
  }
}
.arrow-placeholder {
  width: 24rpx;
  flex-shrink: 0;
}
.av {
  width: 60rpx;
  height: 60rpx;
  border-radius: 12rpx;
  background: linear-gradient(135deg, #ff6b35, #ff8f50);
  color: #fff;
  font-size: 24rpx;
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
  font-size: 26rpx;
  font-weight: 600;
  color: #333;
}
.desc {
  font-size: 20rpx;
  color: #999;
  margin-top: 4rpx;
}
</style>
