<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { systemMenuApi } from '@/api/system'
import type { MenuItem } from '@/api/system'

definePage({
  name: 'menu',
  style: { navigationBarTitleText: '菜单管理' },
})

const tree = ref<MenuItem[]>([])
const loading = ref(false)
const expanded = ref<Set<number>>(new Set([0]))

const typeMap: Record<number, string> = { 1: '目录', 2: '菜单', 3: '按钮', 4: '外链' }
const typeColorMap: Record<number, string> = { 1: '#4d7fff', 2: '#07c160', 3: '#ff9500', 4: '#8a2be2' }

function toggle(id: number) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}

interface FlatMenu extends MenuItem {
  _depth?: number
}

function renderTree(nodes: MenuItem[], depth = 0): FlatMenu[] {
  const result: FlatMenu[] = []
  for (const node of nodes) {
    result.push({ ...node, _depth: depth })
    if (node.children && node.children.length > 0 && expanded.value.has(node.id)) {
      result.push(...renderTree(node.children, depth + 1))
    }
  }
  return result
}

const flatList = ref<FlatMenu[]>([])

async function loadData() {
  loading.value = true
  try {
    tree.value = (await systemMenuApi.getTree()) as MenuItem[]
    flatList.value = renderTree(tree.value)
  } catch {
    /* handled by http */
  } finally {
    loading.value = false
  }
}

function reload() {
  expanded.value = new Set([0])
  loadData()
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
          <view v-else class="ap" />
          <view class="av" :style="{ background: typeColorMap[item.type] || '#999' }">
            <wd-icon v-if="item.icon" :name="item.icon" size="14px" color="#fff" />
            <text v-else>{{ item.type }}</text>
          </view>
          <view class="info">
            <view class="tl">{{ item.name }}</view>
            <view class="sub">{{ item.route_path || '-' }}</view>
          </view>
          <view class="right">
            <wd-tag
              :style="{ background: `${typeColorMap[item.type]}20`, color: typeColorMap[item.type], border: 'none' }"
              size="small">
              {{ typeMap[item.type] || '未知' }}
            </wd-tag>
            <wd-tag :type="item.status === '0' ? 'success' : 'danger'" size="small" plain>
              {{ item.status === '0' ? '启用' : '禁用' }}
            </wd-tag>
          </view>
        </view>
        <view v-if="item.permission" class="card-f">
          <text class="perm">权限: {{ item.permission }}</text>
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
  padding: 16rpx 20rpx;
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
.ap {
  width: 24rpx;
  flex-shrink: 0;
}
.av {
  width: 48rpx;
  height: 48rpx;
  border-radius: 10rpx;
  color: #fff;
  font-size: 18rpx;
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
.sub {
  font-size: 20rpx;
  color: #999;
  margin-top: 2rpx;
}
.right {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  align-items: flex-end;
}
.card-f {
  margin-top: 8rpx;
  padding-top: 8rpx;
  border-top: 1px solid #f5f5f5;
}
.perm {
  font-size: 20rpx;
  color: #999;
  font-family: monospace;
}
</style>
