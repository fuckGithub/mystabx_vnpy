<!-- 存储工作流管理：Art + useTable -->
<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="workflowSearchItems"
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
            :perm-create="['module_storage:workflow:create']"
            :perm-delete="['module_storage:workflow:delete']"
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
        <template #workflow-operation="{ row }">
          <ElSpace class="flex">
            <ElButton
              v-hasPerm="['module_storage:workflow:update']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="openDialog(row.id)">
              编辑
            </ElButton>
            <ElButton
              v-hasPerm="['module_storage:workflow:delete']"
              type="danger"
              size="small"
              link
              icon="delete"
              @click="deleteWorkflowRow(row.id)">
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
  name: 'StorageWorkflow',
  inheritAttrs: false,
})

import StorageWorkflowAPI, { type StorageWorkflowForm, type StorageWorkflowTable } from '@/api/module_storage/workflow'
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

const BATCH_DELETE_MSG = '确认删除选中的存储工作流吗？'

type WorkflowSearchForm = {
  name?: string
  code?: string
  status?: string
}

function buildWorkflowReplaceParams(u: WorkflowSearchForm): Record<string, unknown> {
  return {
    name: u.name,
    code: u.code,
    status: u.status,
  }
}

const searchForm = ref<WorkflowSearchForm>({
  name: undefined,
  code: undefined,
  status: undefined,
})

const showSearchBar = ref(true)
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null)
const searchBarRules: Record<string, unknown> = {}

const workflowSearchItems = computed<SearchFormItem[]>(() => [
  {
    label: '工作流名称',
    key: 'name',
    type: 'input',
    placeholder: '请输入工作流名称',
    clearable: true,
    span: 6,
  },
  {
    label: '工作流编码',
    key: 'code',
    type: 'input',
    placeholder: '请输入工作流编码',
    clearable: true,
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
const selectedRows = ref<StorageWorkflowTable[]>([])
const selectedIds = computed(() =>
  selectedRows.value.map((r) => r.id).filter((id): id is number => typeof id === 'number')
)
const batchDeleting = ref(false)

function onTableSelectionChange(rows: StorageWorkflowTable[]) {
  selectedRows.value = rows
}

async function deleteWorkflowRow(id: number | undefined) {
  if (id == null) return
  try {
    await ElMessageBox.confirm('确认删除该存储工作流吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await StorageWorkflowAPI.deleteWorkflow([id])
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
    await StorageWorkflowAPI.deleteWorkflow(ids)
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
    apiFn: StorageWorkflowAPI.getWorkflowList,
    apiParams: {
      page_no: 1,
      page_size: 10,
    },
    columnsFactory: (): ColumnOption<StorageWorkflowTable>[] => [
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
        label: '名称',
        minWidth: 160,
        showOverflowTooltip: true,
      },
      {
        prop: 'code',
        label: '编码',
        minWidth: 120,
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
        slotName: 'workflow-operation',
      },
    ],
  },
})

async function handleSearchBarSearch(params: WorkflowSearchForm) {
  await searchBarRef.value?.validate?.()
  replaceSearchParams(buildWorkflowReplaceParams(params))
  getData()
}

async function onResetSearch() {
  searchForm.value = {
    name: undefined,
    code: undefined,
    status: undefined,
  }
  await resetSearchParams()
}

const dialogVisible = ref(false)
const dialogTitle = ref('新增存储工作流')
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<InstanceType<typeof FaForm> | null>(null)
const formRenderKey = ref(0)

function defaultForm(): StorageWorkflowForm {
  return {
    name: '',
    code: '',
    description: '',
    nodes_json: '',
    edges_json: '',
  }
}

const formData = ref<StorageWorkflowForm>(defaultForm())

const rules: FormRules = {
  name: [{ required: true, message: '请输入工作流名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入工作流编码', trigger: 'blur' }],
}

const dialogFormItems = computed<FormItem[]>(() => [
  {
    label: '名称',
    key: 'name',
    type: 'input',
    span: 24,
    props: { maxlength: 100, showWordLimit: true },
  },
  {
    label: '编码',
    key: 'code',
    type: 'input',
    span: 24,
    props: { maxlength: 50, showWordLimit: true, disabled: !!editingId.value },
  },
  {
    label: '节点配置',
    key: 'nodes_json',
    type: 'input',
    span: 24,
    props: {
      type: 'textarea',
      rows: 6,
      placeholder: 'JSON 格式节点配置',
    },
  },
  {
    label: '连线配置',
    key: 'edges_json',
    type: 'input',
    span: 24,
    props: {
      type: 'textarea',
      rows: 6,
      placeholder: 'JSON 格式连线配置',
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
  dialogTitle.value = id ? '编辑存储工作流' : '新增存储工作流'
  editingId.value = id ?? null
  if (id) {
    try {
      const res = await StorageWorkflowAPI.getWorkflowDetail(id)
      const d = res.data?.data as StorageWorkflowTable | undefined
      if (d) {
        formData.value.name = d.name || ''
        formData.value.code = d.code || ''
        formData.value.description = d.description || ''
        formData.value.nodes_json = d.nodes_json || ''
        formData.value.edges_json = d.edges_json || ''
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
      await StorageWorkflowAPI.updateWorkflow(editingId.value, formData.value)
      ElMessage.success('更新成功')
      dialogVisible.value = false
      await refreshUpdate()
    } else {
      await StorageWorkflowAPI.createWorkflow(formData.value)
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
