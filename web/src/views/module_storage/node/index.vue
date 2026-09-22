<!-- 存储节点管理：Art + useTable -->
<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="nodeSearchItems"
      :rules="searchBarRules"
      :is-expand="true"
      :show-expand="true"
      :show-reset="true"
      :show-search="true"
      :disabled-search="false"
      :default-expanded="false"
      @search="handleSearchBarSearch"
      @reset="onResetSearch" />

    <ElCard class="fa-table-card" :style="{ 'margin-top': showSearchBar ? '12px' : '0' }">
      <FaTableHeader
        v-model:columns="columnChecks"
        v-model:showSearchBar="showSearchBar"
        :loading="loading"
        @refresh="refreshData">
        <template #left>
          <FaTableHeaderLeft
            :remove-ids="selectedIds"
            :perm-create="['module_storage:node:create']"
            :perm-delete="['module_storage:node:delete']"
            :delete-loading="batchDeleting"
            @add="openDialog()"
            @delete="handleBatchDelete" />
        </template>
      </FaTableHeader>

      <FaTable
        ref="faTableRef"
        row-key="id"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @selection-change="onTableSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange">
        <template #node-operation="{ row }">
          <ElSpace class="flex">
            <ElButton
              v-hasPerm="['module_storage:node:update']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="openDialog(row.id)">
              编辑
            </ElButton>
            <ElButton
              v-hasPerm="['module_storage:node:delete']"
              type="danger"
              size="small"
              link
              icon="delete"
              @click="deleteNodeRow(row.id)">
              删除
            </ElButton>
          </ElSpace>
        </template>
      </FaTable>
    </ElCard>

    <FaDialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close @close="handleCloseDialog">
      <FaForm
        :key="formRenderKey"
        ref="formRef"
        v-model="formData"
        :items="dialogFormItems"
        :rules="rules"
        label-width="100px"
        label-position="right"
        :span="24"
        :gutter="16"
        :show-reset="false"
        :show-submit="false"
        class="crud-dialog-art-form" />
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitForm">保存</ElButton>
      </template>
    </FaDialog>
  </div>
</template>

<script lang="ts" setup>
defineOptions({
  name: 'StorageNode',
  inheritAttrs: false,
})

import StorageNodeAPI, { type StorageNodeForm, type StorageNodeTable } from '@/api/module_storage/node'
import type { FormItem } from '@/components/forms/fa-form/index.vue'
import FaForm from '@/components/forms/fa-form/index.vue'
import type { SearchFormItem } from '@/components/forms/fa-search-bar/index.vue'
import FaSearchBar from '@/components/forms/fa-search-bar/index.vue'
import FaDialog from '@/components/modal/fa-dialog/index.vue'
import FaTableHeaderLeft from '@/components/tables/fa-table-header-left/index.vue'
import FaTableHeader from '@/components/tables/fa-table-header/index.vue'
import FaTable from '@/components/tables/fa-table/index.vue'
import { useTable } from '@/hooks/core/useTable'
import type { ColumnOption } from '@/types/component'
import type { FormRules } from 'element-plus'
import { ElMessage, ElMessageBox, ElTag } from 'element-plus'
import { computed, h, ref } from 'vue'

const BATCH_DELETE_MSG = '确认删除选中的存储节点吗？'

type NodeSearchForm = {
  name?: string
  type?: string
  status?: string
}

function buildNodeReplaceParams(u: NodeSearchForm): Record<string, unknown> {
  return {
    name: u.name,
    type: u.type,
    status: u.status,
  }
}

const searchForm = ref<NodeSearchForm>({
  name: undefined,
  type: undefined,
  status: undefined,
})

const showSearchBar = ref(true)
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null)
const searchBarRules: Record<string, unknown> = {}

const nodeSearchItems = computed<SearchFormItem[]>(() => [
  {
    label: '节点名称',
    key: 'name',
    type: 'input',
    placeholder: '请输入节点名称',
    clearable: true,
    span: 6,
  },
  {
    label: '存储类型',
    key: 'type',
    type: 'select',
    props: {
      placeholder: '请选择存储类型',
      clearable: true,
      options: [
        { label: '本地存储', value: 'local' },
        { label: 'S3', value: 's3' },
        { label: 'FTP', value: 'ftp' },
        { label: 'SFTP', value: 'sftp' },
      ],
    },
    span: 6,
  },
  {
    label: '状态',
    key: 'status',
    type: 'select',
    props: {
      placeholder: '请选择状态',
      clearable: true,
      options: [
        { label: '正常', value: '0' },
        { label: '禁用', value: '1' },
      ],
    },
    span: 6,
  },
])

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null)
const selectedRows = ref<StorageNodeTable[]>([])
const selectedIds = computed(() =>
  selectedRows.value.map((r) => r.id).filter((id): id is number => typeof id === 'number')
)
const batchDeleting = ref(false)

function onTableSelectionChange(rows: StorageNodeTable[]) {
  selectedRows.value = rows
}

function typeLabel(t?: string) {
  const m: Record<string, string> = {
    local: '本地存储',
    s3: 'S3',
    ftp: 'FTP',
    sftp: 'SFTP',
  }
  return t ? m[t] || t : '-'
}

async function deleteNodeRow(id: number | undefined) {
  if (id == null) return
  try {
    await ElMessageBox.confirm('确认删除该存储节点吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await StorageNodeAPI.deleteNode([id])
    ElMessage.success('删除成功')
    faTableRef.value?.elTableRef?.clearSelection()
    await refreshRemove()
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  const ids = selectedIds.value
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(BATCH_DELETE_MSG, '批量删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    batchDeleting.value = true
    await StorageNodeAPI.deleteNode(ids)
    ElMessage.success('删除成功')
    selectedRows.value = []
    await refreshRemove()
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false
  }
}

const {
  columns,
  columnChecks,
  data,
  loading,
  pagination,
  getData,
  replaceSearchParams,
  resetSearchParams,
  handleSizeChange,
  handleCurrentChange,
  refreshData,
  refreshRemove,
  refreshCreate,
  refreshUpdate,
} = useTable({
  core: {
    apiFn: StorageNodeAPI.getNodeList,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: (): ColumnOption<StorageNodeTable>[] => [
      { type: 'selection', width: 48, fixed: 'left' },
      { type: 'globalIndex', width: 56, label: '序号' },
      {
        prop: 'id',
        label: 'ID',
        width: 88,
        align: 'center',
      },
      {
        prop: 'name',
        label: '节点名称',
        minWidth: 160,
        showOverflowTooltip: true,
      },
      {
        prop: 'type',
        label: '存储类型',
        minWidth: 100,
        align: 'center',
        formatter: (row) => h(ElTag, { type: 'primary' }, () => typeLabel(row.type)),
      },
      {
        prop: 'description',
        label: '描述',
        minWidth: 160,
        showOverflowTooltip: true,
      },
      {
        prop: 'status',
        label: '状态',
        width: 88,
        align: 'center',
        formatter: (row) =>
          h(ElTag, { type: row.status === '0' ? 'success' : 'danger' }, () => (row.status === '0' ? '正常' : '禁用')),
      },
      {
        prop: 'created_time',
        label: '创建时间',
        minWidth: 170,
        showOverflowTooltip: true,
      },
      {
        prop: 'operation',
        label: '操作',
        width: 140,
        fixed: 'right',
        align: 'center',
        useSlot: true,
        slotName: 'node-operation',
      },
    ],
  },
})

async function handleSearchBarSearch(params: NodeSearchForm) {
  await searchBarRef.value?.validate?.()
  replaceSearchParams(buildNodeReplaceParams(params))
  getData()
}

async function onResetSearch() {
  searchForm.value = {
    name: undefined,
    type: undefined,
    status: undefined,
  }
  await resetSearchParams()
}

const dialogVisible = ref(false)
const dialogTitle = ref('新增存储节点')
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<InstanceType<typeof FaForm> | null>(null)
const formRenderKey = ref(0)

function defaultForm(): StorageNodeForm {
  return {
    name: '',
    type: 'local',
    config: '',
    description: '',
  }
}

const formData = ref<StorageNodeForm>(defaultForm())

const rules: FormRules = {
  name: [{ required: true, message: '请输入节点名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择存储类型', trigger: 'change' }],
}

const dialogFormItems = computed<FormItem[]>(() => [
  {
    label: '节点名称',
    key: 'name',
    type: 'input',
    span: 24,
    props: { maxlength: 100, showWordLimit: true },
  },
  {
    label: '存储类型',
    key: 'type',
    type: 'select',
    span: 24,
    props: {
      style: { width: '100%' },
      options: [
        { label: '本地存储', value: 'local' },
        { label: 'S3', value: 's3' },
        { label: 'FTP', value: 'ftp' },
        { label: 'SFTP', value: 'sftp' },
      ],
      disabled: !!editingId.value,
    },
  },
  {
    label: '连接配置',
    key: 'config',
    type: 'input',
    span: 24,
    props: {
      type: 'textarea',
      rows: 6,
      placeholder: 'JSON 格式连接配置',
    },
  },
  {
    label: '描述',
    key: 'description',
    type: 'input',
    span: 24,
    props: {
      type: 'textarea',
      rows: 3,
      maxlength: 500,
      showWordLimit: true,
    },
  },
])

function resetForm() {
  Object.assign(formData.value, defaultForm())
  editingId.value = null
  formRef.value?.ref?.resetFields()
  formRef.value?.ref?.clearValidate()
}

function handleCloseDialog() {
  resetForm()
}

async function openDialog(id?: number) {
  resetForm()
  dialogTitle.value = id ? '编辑存储节点' : '新增存储节点'
  editingId.value = id ?? null
  if (id) {
    try {
      const res = await StorageNodeAPI.getNodeDetail(id)
      const d = res.data?.data as StorageNodeTable | undefined
      if (d) {
        formData.value.name = d.name || ''
        formData.value.type = d.type || 'local'
        formData.value.config = d.config || ''
        formData.value.description = d.description || ''
      }
    } catch {
      ElMessage.error('加载详情失败')
      return
    }
  }
  formRenderKey.value += 1
  dialogVisible.value = true
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editingId.value) {
      await StorageNodeAPI.updateNode(editingId.value, formData.value)
      ElMessage.success('更新成功')
      dialogVisible.value = false
      await refreshUpdate()
    } else {
      await StorageNodeAPI.createNode(formData.value)
      ElMessage.success('创建成功')
      dialogVisible.value = false
      await refreshCreate()
    }
  } catch {
    ElMessage.error(editingId.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.crud-dialog-art-form :deep(.el-row > .el-col:last-child) {
  display: none;
}

.crud-dialog-art-form :deep(.el-form-item__content) {
  max-width: 100%;
}
</style>
