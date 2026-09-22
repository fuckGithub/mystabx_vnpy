<!-- 传输任务管理：Art + useTable -->
<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="transferSearchItems"
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
            :perm-create="['module_storage:transfer:create']"
            :perm-delete="['module_storage:transfer:delete']"
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
        <template #transfer-operation="{ row }">
          <ElSpace class="flex">
            <ElButton
              v-hasPerm="['module_storage:transfer:update']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="openDialog(row.id)">
              编辑
            </ElButton>
            <ElButton
              v-hasPerm="['module_storage:transfer:delete']"
              type="danger"
              size="small"
              link
              icon="delete"
              @click="deleteTransferRow(row.id)">
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
  name: 'StorageTransfer',
  inheritAttrs: false,
})

import StorageTransferAPI, { type StorageTransferForm, type StorageTransferTable } from '@/api/module_storage/transfer'
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

const BATCH_DELETE_MSG = '确认删除选中的传输任务吗？'

type TransferSearchForm = {
  name?: string
  transfer_status?: number
}

function buildTransferReplaceParams(u: TransferSearchForm): Record<string, unknown> {
  return {
    name: u.name,
    transfer_status: u.transfer_status,
  }
}

const searchForm = ref<TransferSearchForm>({
  name: undefined,
  transfer_status: undefined,
})

const showSearchBar = ref(true)
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null)
const searchBarRules: Record<string, unknown> = {}

const transferSearchItems = computed<SearchFormItem[]>(() => [
  {
    label: '任务名称',
    key: 'name',
    type: 'input',
    placeholder: '请输入任务名称',
    clearable: true,
    span: 6,
  },
  {
    label: '传输状态',
    key: 'transfer_status',
    type: 'select',
    props: {
      placeholder: '请选择状态',
      clearable: true,
      options: [
        { label: '待执行', value: 0 },
        { label: '执行中', value: 1 },
        { label: '成功', value: 2 },
        { label: '失败', value: 3 },
      ],
    },
    span: 6,
  },
])

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null)
const selectedRows = ref<StorageTransferTable[]>([])
const selectedIds = computed(() =>
  selectedRows.value.map((r) => r.id).filter((id): id is number => typeof id === 'number')
)
const batchDeleting = ref(false)

function onTableSelectionChange(rows: StorageTransferTable[]) {
  selectedRows.value = rows
}

function statusType(s?: number) {
  const m: Record<number, 'info' | 'warning' | 'success' | 'danger'> = {
    0: 'info',
    1: 'warning',
    2: 'success',
    3: 'danger',
  }
  return s != null ? (m[s] ?? 'info') : 'info'
}

function statusText(s?: number) {
  const m: Record<number, string> = {
    0: '待执行',
    1: '执行中',
    2: '成功',
    3: '失败',
  }
  return s != null ? (m[s] ?? '-') : '-'
}

async function deleteTransferRow(id: number | undefined) {
  if (id == null) return
  try {
    await ElMessageBox.confirm('确认删除该传输任务吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await StorageTransferAPI.deleteTransfer([id])
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
    await StorageTransferAPI.deleteTransfer(ids)
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
    apiFn: StorageTransferAPI.getTransferList,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: (): ColumnOption<StorageTransferTable>[] => [
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
        label: '任务名称',
        minWidth: 160,
        showOverflowTooltip: true,
      },
      {
        prop: 'source_id',
        label: '源节点ID',
        width: 100,
        align: 'center',
      },
      {
        prop: 'target_id',
        label: '目标节点ID',
        width: 100,
        align: 'center',
      },
      {
        prop: 'transfer_status',
        label: '传输状态',
        width: 100,
        align: 'center',
        formatter: (row) => h(ElTag, { type: statusType(row.transfer_status) }, () => statusText(row.transfer_status)),
      },
      {
        prop: 'progress',
        label: '进度',
        width: 88,
        align: 'center',
        formatter: (row) => `${row.progress ?? 0}%`,
      },
      {
        prop: 'description',
        label: '描述',
        minWidth: 160,
        showOverflowTooltip: true,
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
        slotName: 'transfer-operation',
      },
    ],
  },
})

async function handleSearchBarSearch(params: TransferSearchForm) {
  await searchBarRef.value?.validate?.()
  replaceSearchParams(buildTransferReplaceParams(params))
  getData()
}

async function onResetSearch() {
  searchForm.value = {
    name: undefined,
    transfer_status: undefined,
  }
  await resetSearchParams()
}

const dialogVisible = ref(false)
const dialogTitle = ref('新增传输任务')
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<InstanceType<typeof FaForm> | null>(null)
const formRenderKey = ref(0)

function defaultForm(): StorageTransferForm {
  return {
    name: '',
    source_id: undefined,
    target_id: undefined,
    source_path: '',
    target_path: '',
    description: '',
  }
}

const formData = ref<StorageTransferForm>(defaultForm())

const rules: FormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  source_id: [{ required: true, message: '请输入源节点ID', trigger: 'blur' }],
  target_id: [{ required: true, message: '请输入目标节点ID', trigger: 'blur' }],
}

const dialogFormItems = computed<FormItem[]>(() => [
  {
    label: '任务名称',
    key: 'name',
    type: 'input',
    span: 24,
    props: { maxlength: 100, showWordLimit: true },
  },
  {
    label: '源节点ID',
    key: 'source_id',
    type: 'input',
    span: 12,
    props: { type: 'number', min: 1 },
  },
  {
    label: '目标节点ID',
    key: 'target_id',
    type: 'input',
    span: 12,
    props: { type: 'number', min: 1 },
  },
  {
    label: '源路径',
    key: 'source_path',
    type: 'input',
    span: 24,
    props: { maxlength: 500, placeholder: '源文件/目录路径' },
  },
  {
    label: '目标路径',
    key: 'target_path',
    type: 'input',
    span: 24,
    props: { maxlength: 500, placeholder: '目标文件/目录路径' },
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
  dialogTitle.value = id ? '编辑传输任务' : '新增传输任务'
  editingId.value = id ?? null
  if (id) {
    try {
      const res = await StorageTransferAPI.getTransferDetail(id)
      const d = res.data?.data as StorageTransferTable | undefined
      if (d) {
        formData.value.name = d.name || ''
        formData.value.source_id = d.source_id
        formData.value.target_id = d.target_id
        formData.value.source_path = d.source_path || ''
        formData.value.target_path = d.target_path || ''
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
      await StorageTransferAPI.updateTransfer(editingId.value, formData.value)
      ElMessage.success('更新成功')
      dialogVisible.value = false
      await refreshUpdate()
    } else {
      await StorageTransferAPI.createTransfer(formData.value)
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
