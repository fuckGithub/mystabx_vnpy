<!-- 存储浏览：选择节点 + 文件列表 -->
<template>
  <div class="fa-full-height">
    <ElCard class="fa-table-card">
      <div class="mb-4 flex items-center gap-4">
        <span class="text-sm font-medium">存储节点</span>
        <ElSelect
          v-model="selectedNodeId"
          placeholder="请选择存储节点"
          clearable
          style="width: 240px"
          @change="handleNodeChange">
          <ElOption v-for="node in nodeOptions" :key="node.id" :label="node.name" :value="node.id" />
        </ElSelect>
        <ElInput v-model="currentPath" placeholder="浏览路径" clearable style="width: 320px" @keyup.enter="fetchFiles">
          <template #prepend>路径</template>
        </ElInput>
        <ElButton type="primary" :loading="loading" :disabled="!selectedNodeId" @click="fetchFiles">浏览</ElButton>
      </div>

      <ElTable v-loading="loading" :data="fileList" border stripe height="calc(100vh - 280px)">
        <ElTableColumn prop="name" label="名称" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <ElIcon v-if="row.type === 'directory'" color="var(--el-color-primary)">
                <Folder />
              </ElIcon>
              <ElIcon v-else color="var(--el-color-info)">
                <Document />
              </ElIcon>
              <span
                :class="{ 'cursor-pointer text-(--el-color-primary)': row.type === 'directory' }"
                @click="row.type === 'directory' && navigateTo(row.name)">
                {{ row.name }}
              </span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <ElTag :type="row.type === 'directory' ? 'primary' : 'info'" size="small">
              {{ row.type === 'directory' ? '目录' : '文件' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="size" label="大小" width="120" align="right">
          <template #default="{ row }">
            {{ row.size != null ? formatSize(row.size) : '-' }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="modified_time" label="修改时间" width="180" />
      </ElTable>
    </ElCard>
  </div>
</template>

<script lang="ts" setup>
defineOptions({
  name: 'StorageBrowse',
  inheritAttrs: false,
})

import StorageBrowseAPI, { type BrowseItem } from '@/api/module_storage/browse'
import StorageNodeAPI, { type StorageNodeTable } from '@/api/module_storage/node'
import { Document, Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

const selectedNodeId = ref<number | null>(null)
const currentPath = ref('/')
const loading = ref(false)
const fileList = ref<BrowseItem[]>([])
const nodeOptions = ref<StorageNodeTable[]>([])

async function loadNodeOptions() {
  try {
    const res = await StorageNodeAPI.getNodeList({ page_no: 1, page_size: 999 })
    nodeOptions.value = (res.data?.data?.list ?? []) as StorageNodeTable[]
  } catch {
    // 静默处理
  }
}

async function fetchFiles() {
  if (!selectedNodeId.value) {
    ElMessage.warning('请先选择存储节点')
    return
  }
  loading.value = true
  try {
    const res = await StorageBrowseAPI.listFiles({
      node_id: selectedNodeId.value,
      path: currentPath.value || '/',
    })
    const result = res.data?.data
    if (result) {
      fileList.value = result.items ?? []
    }
  } catch {
    ElMessage.error('浏览失败')
    fileList.value = []
  } finally {
    loading.value = false
  }
}

function handleNodeChange() {
  currentPath.value = '/'
  fileList.value = []
  if (selectedNodeId.value) {
    fetchFiles()
  }
}

function navigateTo(name: string) {
  const base = currentPath.value.endsWith('/') ? currentPath.value : `${currentPath.value}/`
  currentPath.value = `${base}${name}`
  fetchFiles()
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

onMounted(() => {
  loadNodeOptions()
})
</script>
