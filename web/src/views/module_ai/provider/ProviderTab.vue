<!-- 供应商管理 + 嵌套模型管理：展开行显示模型列表 -->
<template>
  <div class="fa-full-height provider-tab-page flex flex-col min-h-0">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="providerSearchItems"
      :rules="searchBarRules"
      :is-expand="false"
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
            :perm-create="['module_ai:model:create']"
            :perm-delete="['module_ai:model:delete']"
            :delete-loading="batchDeleting"
            @add="handleOpenProviderDialog('create')"
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
        @expand-change="handleExpandChange"
        @selection-change="onTableSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange">
        <template #expand="{ row }">
          <div class="model-expand-row">
            <div class="model-expand-header">
              <ElButton
                v-if="hasAuth('module_ai:model:create')"
                type="primary"
                size="small"
                :icon="Plus"
                @click="openModelDialog('create', row.id)">
                新增模型
              </ElButton>
              <span class="model-expand-title">{{ row.name }} · 模型列表</span>
            </div>
            <ElTable
              :data="providerModels[row.id] ?? []"
              :loading="modelLoading[row.id] ?? false"
              size="small"
              border
              stripe>
              <ElTableColumn prop="name" label="模型名称" min-width="140" show-overflow-tooltip />
              <ElTableColumn prop="model_key" label="模型Key" width="150">
                <template #default="{ row: m }">
                  <ElTag effect="plain">{{ m.model_key }}</ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="能力" width="150">
                <template #default="{ row: m }">
                  <span class="capability-tags">
                    <ElTag v-if="m.tool_calling" size="small" type="info" effect="plain">工具</ElTag>
                    <ElTag v-if="m.vision" size="small" type="info" effect="plain">视觉</ElTag>
                    <ElTag v-if="m.thinking" size="small" type="info" effect="plain">思考</ElTag>
                    <span v-if="!m.tool_calling && !m.vision && !m.thinking" class="text-gray-400">—</span>
                  </span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="默认" width="70" align="center">
                <template #default="{ row: m }">{{ m.is_default ? '✔' : '—' }}</template>
              </ElTableColumn>
              <ElTableColumn label="状态" width="80">
                <template #default="{ row: m }">
                  <ElTag :type="m.status === '0' ? 'success' : 'danger'" size="small">
                    {{ m.status === '0' ? '启用' : '停用' }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="200" align="right" fixed="right">
                <template #default="{ row: m }">
                  <ElButton
                    v-if="hasAuth('module_ai:model:detail')"
                    type="primary"
                    link
                    size="small"
                    @click="openModelDialog('detail', row.id, m.id)">
                    详情
                  </ElButton>
                  <ElButton
                    v-if="hasAuth('module_ai:model:update')"
                    type="primary"
                    link
                    size="small"
                    @click="openModelDialog('update', row.id, m.id)">
                    编辑
                  </ElButton>
                  <ElButton
                    v-if="hasAuth('module_ai:model:update') && !m.is_default"
                    type="warning"
                    link
                    size="small"
                    @click="handleSetDefaultModel(row.id, m.id)">
                    设为默认
                  </ElButton>
                  <ElButton
                    v-if="hasAuth('module_ai:model:delete')"
                    type="danger"
                    link
                    size="small"
                    @click="deleteModelRow(row.id, m.id)">
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </div>
        </template>
      </FaTable>
    </ElCard>

    <!-- 供应商 Drawer -->
    <FaDrawer
      v-model="providerDialogVisible.visible"
      :title="providerDialogVisible.title"
      append-to-body
      :size="drawerSize"
      @close="handleCloseProviderDialog">
      <template v-if="providerDialogVisible.type === 'detail'">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="编号">{{ providerDetail.id }}</ElDescriptionsItem>
          <ElDescriptionsItem label="供应商名称">{{ providerDetail.name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="厂商类型">
            <ElTag>{{ providerDetail.vendor }}</ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="API协议">
            <ElTag type="primary">{{ providerDetail.api_type }}</ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="API地址" :span="2">{{ providerDetail.base_url || '—' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="API密钥" :span="2">
            <template v-if="providerDetail.api_key">
              <ElTag type="warning">已配置</ElTag>
            </template>
            <template v-else>—</template>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="默认供应商">
            <ElTag :type="providerDetail.is_default ? 'success' : 'info'">
              {{ providerDetail.is_default ? '是' : '否' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="排序">{{ providerDetail.sort_order ?? 0 }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="providerDetail.status === '0' ? 'success' : 'danger'">
              {{ providerDetail.status === '0' ? '启用' : '停用' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">{{ providerDetail.created_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="更新时间">{{ providerDetail.updated_time }}</ElDescriptionsItem>
          <ElDescriptionsItem v-if="providerDetail.models?.length" label="模型列表" :span="4">
            <div class="detail-model-grid">
              <ElTag v-for="m in providerDetail.models" :key="m.model_key" type="info" effect="plain">
                {{ m.name }}
              </ElTag>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="描述" :span="4">{{ providerDetail.description || '—' }}</ElDescriptionsItem>
        </ElDescriptions>
      </template>
      <template v-else>
        <ElForm
          ref="providerFormRef"
          :model="providerForm"
          :rules="providerRules"
          label-suffix=":"
          label-width="auto"
          label-position="right">
          <ElFormItem label="供应商名称" prop="name">
            <ElInput v-model="providerForm.name" placeholder="如 mimo-tp / DeepSeek" maxlength="64" />
          </ElFormItem>
          <ElFormItem label="厂商类型" prop="vendor">
            <ElSelect v-model="providerForm.vendor" placeholder="请选择厂商类型" allow-create filterable>
              <ElOption label="openai" value="openai" />
              <ElOption label="anthropic" value="anthropic" />
              <ElOption label="google" value="google" />
              <ElOption label="ollama" value="ollama" />
              <ElOption label="deepseek" value="deepseek" />
              <ElOption label="customendpoint" value="customendpoint" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="API协议" prop="api_type">
            <ElSelect v-model="providerForm.api_type" placeholder="请选择 API 协议" allow-create filterable>
              <ElOption label="chat-completions" value="chat-completions" />
              <ElOption label="messages" value="messages" />
              <ElOption label="gemini" value="gemini" />
              <ElOption label="ollama" value="ollama" />
              <ElOption label="azure" value="azure" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="API地址" prop="base_url">
            <ElInput v-model="providerForm.base_url" placeholder="供应商默认 API 地址（模型可覆盖）" maxlength="255" />
          </ElFormItem>
          <ElFormItem label="API密钥" prop="api_key">
            <ElInput
              v-model="providerForm.api_key"
              placeholder="供应商 API 密钥（模型级可覆盖）"
              type="password"
              show-password
              maxlength="255" />
          </ElFormItem>
          <ElFormItem label="默认供应商" prop="is_default">
            <ElSwitch v-model="providerForm.is_default" />
          </ElFormItem>
          <ElFormItem label="测试模型">
            <ElSelect
              v-model="testModelKey"
              placeholder="选择一个模型进行连通性测试"
              filterable
              :disabled="!providerForm.id"
              style="width: 100%">
              <ElOption
                v-for="m in testModelOptions"
                :key="m.model_key"
                :label="`${m.name}（${m.model_key}）`"
                :value="m.model_key" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="连通性">
            <ElButton
              type="primary"
              plain
              :loading="testLoading"
              :disabled="!testModelKey"
              :icon="Connection"
              @click="handleTestConnectivity">
              测试连通性
            </ElButton>
            <span v-if="testResult" class="ml-3" :class="testResult.success ? 'text-green-500' : 'text-red-500'">
              <template v-if="testResult.success">✔ 连通（{{ testResult.latency_ms }}ms）</template>
              <template v-else>✘ 失败：{{ testResult.error }}</template>
            </span>
          </ElFormItem>
          <ElFormItem label="排序" prop="sort_order">
            <ElInputNumber v-model="providerForm.sort_order" :min="0" :max="9999" />
          </ElFormItem>
          <ElFormItem label="状态" prop="status">
            <ElRadioGroup v-model="providerForm.status">
              <ElRadio value="0">启用</ElRadio>
              <ElRadio value="1">停用</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem label="描述" prop="description">
            <ElInput
              v-model="providerForm.description"
              :rows="3"
              :maxlength="100"
              show-word-limit
              type="textarea"
              placeholder="请输入描述" />
          </ElFormItem>
        </ElForm>
      </template>

      <template #footer>
        <div class="dialog-footer">
          <ElButton @click="handleCloseProviderDialog">取消</ElButton>
          <ElButton
            v-if="providerDialogVisible.type === 'create' || providerDialogVisible.type === 'update'"
            type="primary"
            :loading="providerSubmitLoading"
            @click="handleProviderSubmit">
            确定
          </ElButton>
          <ElButton v-else type="primary" @click="handleCloseProviderDialog">确定</ElButton>
        </div>
      </template>
    </FaDrawer>

    <!-- 模型 Drawer -->
    <FaDrawer
      v-model="modelDialogVisible.visible"
      :title="modelDialogVisible.title"
      append-to-body
      :size="drawerSize"
      @close="handleCloseModelDialog">
      <template v-if="modelDialogVisible.type === 'detail'">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="编号">{{ modelDetail.id }}</ElDescriptionsItem>
          <ElDescriptionsItem label="模型显示名">{{ modelDetail.name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="模型Key">
            <ElTag>{{ modelDetail.model_key }}</ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="供应商">
            {{ modelDetail.provider_name || `#${modelDetail.provider_id}` }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="端点地址" :span="2">{{ modelDetail.url || '—' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="工具调用">
            <ElTag :type="modelDetail.tool_calling ? 'success' : 'info'">
              {{ modelDetail.tool_calling ? '支持' : '不支持' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="视觉输入">
            <ElTag :type="modelDetail.vision ? 'success' : 'info'">
              {{ modelDetail.vision ? '支持' : '不支持' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="思考模式">
            <ElTag :type="modelDetail.thinking ? 'warning' : 'info'">
              {{ modelDetail.thinking ? '启用' : '关闭' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="默认模型">
            <ElTag :type="modelDetail.is_default ? 'success' : 'info'">
              {{ modelDetail.is_default ? '是' : '否' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="最大输入">{{ modelDetail.max_input_tokens ?? '—' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="最大输出">{{ modelDetail.max_output_tokens ?? '—' }}</ElDescriptionsItem>
          <ElDescriptionsItem label="温度">{{ modelDetail.temperature ?? 0.7 }}</ElDescriptionsItem>
          <ElDescriptionsItem label="排序">{{ modelDetail.sort_order ?? 0 }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="modelDetail.status === '0' ? 'success' : 'danger'">
              {{ modelDetail.status === '0' ? '启用' : '停用' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">{{ modelDetail.created_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="更新时间">{{ modelDetail.updated_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="描述" :span="4">{{ modelDetail.description || '—' }}</ElDescriptionsItem>
        </ElDescriptions>
      </template>
      <template v-else>
        <ElForm
          ref="modelFormRef"
          :model="modelForm"
          :rules="modelRules"
          label-suffix=":"
          label-width="auto"
          label-position="right">
          <ElFormItem label="供应商" prop="provider_id">
            <ElSelect v-model="modelForm.provider_id" placeholder="请选择供应商" filterable disabled>
              <ElOption :label="currentProviderName" :value="modelForm.provider_id!" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="模型Key" prop="model_key">
            <ElInput v-model="modelForm.model_key" placeholder="如 mimo-v2.5 / deepseek-chat" maxlength="128" />
          </ElFormItem>
          <ElFormItem label="模型显示名" prop="name">
            <ElInput v-model="modelForm.name" placeholder="如 mimo-v2.5-tp" maxlength="128" />
          </ElFormItem>
          <ElFormItem label="端点地址" prop="url">
            <ElInput v-model="modelForm.url" placeholder="模型端点（覆盖供应商 base_url，可空）" maxlength="255" />
          </ElFormItem>
          <ElFormItem label="能力" prop="capabilities">
            <div class="capability-checkboxes">
              <ElCheckbox v-model="modelForm.tool_calling">工具调用</ElCheckbox>
              <ElCheckbox v-model="modelForm.vision">视觉输入</ElCheckbox>
              <ElCheckbox v-model="modelForm.thinking">思考模式</ElCheckbox>
              <ElCheckbox v-model="modelForm.is_default">默认模型</ElCheckbox>
            </div>
          </ElFormItem>
          <ElFormItem label="最大输入" prop="max_input_tokens">
            <ElInputNumber v-model="modelForm.max_input_tokens" :min="1" :max="10000000" :step="1000" />
          </ElFormItem>
          <ElFormItem label="最大输出" prop="max_output_tokens">
            <ElInputNumber v-model="modelForm.max_output_tokens" :min="1" :max="1000000" :step="500" />
          </ElFormItem>
          <ElFormItem label="温度" prop="temperature">
            <ElInputNumber v-model="modelForm.temperature" :min="0" :max="2" :step="0.1" />
          </ElFormItem>
          <ElFormItem label="排序" prop="sort_order">
            <ElInputNumber v-model="modelForm.sort_order" :min="0" :max="9999" />
          </ElFormItem>
          <ElFormItem label="状态" prop="status">
            <ElRadioGroup v-model="modelForm.status">
              <ElRadio value="0">启用</ElRadio>
              <ElRadio value="1">停用</ElRadio>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem label="描述" prop="description">
            <ElInput
              v-model="modelForm.description"
              :rows="3"
              :maxlength="100"
              show-word-limit
              type="textarea"
              placeholder="请输入描述" />
          </ElFormItem>
        </ElForm>
      </template>

      <template #footer>
        <div class="dialog-footer">
          <ElButton @click="handleCloseModelDialog">取消</ElButton>
          <ElButton
            v-if="modelDialogVisible.type === 'create' || modelDialogVisible.type === 'update'"
            type="primary"
            :loading="modelSubmitLoading"
            @click="handleModelSubmit">
            确定
          </ElButton>
          <ElButton v-else type="primary" @click="handleCloseModelDialog">确定</ElButton>
        </div>
      </template>
    </FaDrawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'ProviderTab',
  inheritAttrs: false,
})

import AiModelAPI, { type AiModel, type AiModelPayload } from '@/api/module_ai/model'
import AiProviderAPI, {
  type AiModelItem,
  type AiProvider,
  type AiProviderPayload,
  type AiProviderQuery,
} from '@/api/module_ai/provider'
import type { SearchFormItem } from '@/components/forms/fa-search-bar/index.vue'
import FaSearchBar from '@/components/forms/fa-search-bar/index.vue'
import FaDrawer from '@/components/modal/fa-drawer/index.vue'
import FaTableHeaderLeft from '@/components/tables/fa-table-header-left/index.vue'
import FaTableHeader from '@/components/tables/fa-table-header/index.vue'
import FaTable from '@/components/tables/fa-table/index.vue'
import { DeviceEnum } from '@/enums/settings/device.enum'
import { useAuth } from '@/hooks/core/useAuth'
import { useTable } from '@/hooks/core/useTable'
import type { ColumnOption } from '@/types/component'
import { Connection, Plus } from '@element-plus/icons-vue'
import { useAppStore } from '@stores/modules/app.store'
import { renderTableOperationCell, type TableOperationAction } from '@utils/table'
import { ElMessageBox, ElTag } from 'element-plus'
import { computed, nextTick, reactive, ref } from 'vue'

const { hasAuth } = useAuth()

// ============================================================ #
//  供应商 useTable
// ============================================================ #
function fetchProviderTableList(params: Record<string, unknown>) {
  const query = { page_no: 1, page_size: 20, ...params } as AiProviderQuery
  return AiProviderAPI.getPage(query)
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
  refreshCreate,
  refreshUpdate,
  refreshRemove,
} = useTable({
  core: {
    apiFn: fetchProviderTableList,
    apiParams: { page_no: 1, page_size: 20 },
    columnsFactory: (): ColumnOption<AiProvider>[] => [
      { type: 'selection', width: 48, fixed: 'left' },
      { type: 'expand', width: 48 },
      { prop: 'name', label: '供应商名称', minWidth: 140, showOverflowTooltip: true },
      {
        prop: 'vendor',
        label: '厂商类型',
        width: 130,
        formatter: (row: AiProvider) => h(ElTag, { effect: 'plain' }, () => row.vendor),
      },
      {
        prop: 'api_type',
        label: 'API协议',
        width: 150,
        formatter: (row: AiProvider) => h(ElTag, { type: 'primary', effect: 'plain' }, () => row.api_type),
      },
      {
        prop: 'is_default',
        label: '默认',
        width: 80,
        align: 'center',
        formatter: (row: AiProvider) => (row.is_default ? '✔' : '—'),
      },
      {
        prop: 'status',
        label: '状态',
        width: 88,
        formatter: (row: AiProvider) =>
          h(ElTag, { type: row.status === '0' ? 'success' : 'danger' }, () => (row.status === '0' ? '启用' : '停用')),
      },
      { prop: 'created_time', label: '创建时间', width: 168, showOverflowTooltip: true },
      {
        prop: 'operation',
        label: '操作',
        width: 200,
        fixed: 'right',
        align: 'right',
        formatter: (row: AiProvider) =>
          renderTableOperationCell(buildProviderRowActions(row), {
            wrapperClass: 'inline-flex flex-wrap items-center justify-end gap-1',
          }),
      },
    ],
  },
})

function buildProviderRowActions(row: AiProvider): TableOperationAction[] {
  return [
    {
      key: 'detail',
      label: '详情',
      artType: 'view' as const,
      perm: 'module_ai:model:detail',
      run: () => handleOpenProviderDialog('detail', row.id!),
    },
    {
      key: 'edit',
      label: '编辑',
      artType: 'edit' as const,
      perm: 'module_ai:model:update',
      run: () => handleOpenProviderDialog('update', row.id!),
    },
    {
      key: 'default',
      label: '设为默认',
      artType: 'edit' as const,
      perm: 'module_ai:model:update',
      disabled: row.is_default === true,
      run: () => handleSetDefaultProvider(row.id!),
    },
    {
      key: 'delete',
      label: '删除',
      artType: 'delete' as const,
      perm: 'module_ai:model:delete',
      run: () => deleteProviderRow(row.id!),
    },
  ].filter((a) => a.perm == null || hasAuth(a.perm))
}

// ============================================================ #
//  展开行：模型列表
// ============================================================ #
const providerModels = ref<Record<number, AiModel[]>>({})
const modelLoading = ref<Record<number, boolean>>({})

async function handleExpandChange(row: AiProvider, expanded: AiProvider[]) {
  // ElTable expand-change: (row, expandedRows[])
  // row is the toggled row, expandedRows is current expanded list
  if (expanded.length && row.id && !providerModels.value[row.id]) {
    await loadProviderModels(row.id)
  }
}

async function loadProviderModels(providerId: number) {
  modelLoading.value[providerId] = true
  try {
    const res = await AiModelAPI.getList({ provider_id: providerId })
    providerModels.value[providerId] = res.data.data ?? []
  } catch (error: unknown) {
    console.error(error)
    providerModels.value[providerId] = []
  } finally {
    modelLoading.value[providerId] = false
  }
}

function refreshProviderModels(providerId: number) {
  loadProviderModels(providerId)
}

// ============================================================ #
//  供应商搜索
// ============================================================ #
type ProviderSearchForm = {
  name?: string
  vendor?: string
  api_type?: string
  status?: string
}

const searchForm = ref<ProviderSearchForm>({
  name: undefined,
  vendor: undefined,
  api_type: undefined,
  status: undefined,
})

const showSearchBar = ref(true)
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null)
const searchBarRules: Record<string, unknown> = {}

const statusOptions = ref([
  { label: '启用', value: '0' },
  { label: '停用', value: '1' },
])

const vendorOptions = ref([
  { label: 'openai', value: 'openai' },
  { label: 'anthropic', value: 'anthropic' },
  { label: 'google', value: 'google' },
  { label: 'ollama', value: 'ollama' },
  { label: 'deepseek', value: 'deepseek' },
  { label: 'customendpoint', value: 'customendpoint' },
])

const apiTypeOptions = ref([
  { label: 'chat-completions', value: 'chat-completions' },
  { label: 'messages', value: 'messages' },
  { label: 'gemini', value: 'gemini' },
  { label: 'ollama', value: 'ollama' },
  { label: 'azure', value: 'azure' },
])

const providerSearchItems = computed<SearchFormItem[]>(() => [
  {
    label: '供应商名称',
    key: 'name',
    type: 'input',
    placeholder: '请输入供应商名称',
    clearable: true,
    span: 6,
  },
  {
    label: '厂商类型',
    key: 'vendor',
    type: 'select',
    props: { placeholder: '请选择厂商类型', options: vendorOptions.value, clearable: true },
    span: 6,
  },
  {
    label: 'API协议',
    key: 'api_type',
    type: 'select',
    props: { placeholder: '请选择API协议', options: apiTypeOptions.value, clearable: true },
    span: 6,
  },
  {
    label: '状态',
    key: 'status',
    type: 'select',
    props: { placeholder: '请选择状态', options: statusOptions.value, clearable: true },
    span: 6,
  },
])

async function handleSearchBarSearch(params: ProviderSearchForm) {
  await searchBarRef.value?.validate?.()
  replaceSearchParams({
    name: params.name,
    vendor: params.vendor,
    api_type: params.api_type,
    status: params.status,
  })
  await getData()
}

function onResetSearch() {
  searchForm.value = { name: undefined, vendor: undefined, api_type: undefined, status: undefined }
  void resetSearchParams()
}

// ============================================================ #
//  供应商选择 & 批量操作
// ============================================================ #
const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null)
const selectedRows = ref<AiProvider[]>([])
const selectedIds = computed(() =>
  selectedRows.value.map((r) => r.id).filter((id): id is number => id != null && !Number.isNaN(id))
)
const batchDeleting = ref(false)

function onTableSelectionChange(rows: AiProvider[]) {
  selectedRows.value = rows
}

async function handleBatchDelete() {
  const ids = selectedIds.value
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 条供应商吗？其下模型将级联删除。`, '批量删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    batchDeleting.value = true
    await AiProviderAPI.delete(ids)
    selectedRows.value = []
    await refreshRemove()
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false
  }
}

// ============================================================ #
//  供应商 Drawer
// ============================================================ #
const appStore = useAppStore()
const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? '480px' : '90%'))

type ProviderForm = AiProviderPayload & Partial<Pick<AiProvider, 'id' | 'status' | 'created_time' | 'updated_time'>>

const providerFormRef = ref()
const providerSubmitLoading = ref(false)
const testLoading = ref(false)
const testResult = ref<{ success: boolean; latency_ms: number | null; error: string | null } | null>(null)
const testModelKey = ref<string>('')
const testModelOptions = ref<Array<{ model_key: string; name: string }>>([])

async function loadTestModelOptions(providerId: number) {
  testModelKey.value = ''
  testModelOptions.value = []
  try {
    const res = await AiModelAPI.getList({ provider_id: providerId })
    const models = res.data.data ?? []
    testModelOptions.value = models.map((m) => ({ model_key: m.model_key, name: m.name }))
    if (testModelOptions.value.length) {
      const defaultModel = models.find((m) => m.is_default)
      testModelKey.value = defaultModel?.model_key ?? testModelOptions.value[0].model_key
    }
  } catch {
    // ignore
  }
}

const providerForm = ref<ProviderForm>({
  id: undefined,
  name: undefined,
  vendor: undefined,
  api_type: 'chat-completions',
  api_key: undefined,
  base_url: undefined,
  is_default: false,
  sort_order: 0,
  status: '0',
  description: undefined,
})

const initialProviderForm: ProviderForm = {
  id: undefined,
  name: undefined,
  vendor: undefined,
  api_type: 'chat-completions',
  api_key: undefined,
  base_url: undefined,
  is_default: false,
  sort_order: 0,
  status: '0',
  description: undefined,
}

const providerDetail = ref<Partial<AiProvider> & { models?: AiModelItem[] | null }>({})

const providerDialogVisible = reactive({
  title: '',
  visible: false,
  type: 'create' as 'create' | 'update' | 'detail',
})

const providerRules = reactive({
  name: [{ required: true, message: '请输入供应商名称', trigger: 'blur' }],
  vendor: [{ required: true, message: '请选择厂商类型', trigger: 'blur' }],
  api_type: [{ required: true, message: '请选择API协议', trigger: 'blur' }],
})

function resetProviderForm() {
  providerFormRef.value?.resetFields()
  providerFormRef.value?.clearValidate()
  Object.assign(providerForm.value, initialProviderForm)
}

function handleCloseProviderDialog() {
  providerDialogVisible.visible = false
  testResult.value = null
  resetProviderForm()
}

async function handleOpenProviderDialog(type: 'create' | 'update' | 'detail', id?: number) {
  providerDialogVisible.type = type
  testModelKey.value = ''
  testModelOptions.value = []
  if (id) {
    const response = await AiProviderAPI.getDetail(id)
    if (type === 'detail') {
      providerDialogVisible.title = '供应商详情'
      Object.assign(providerDetail.value, response.data.data ?? {})
    } else if (type === 'update') {
      providerDialogVisible.title = '修改供应商'
      Object.assign(providerForm.value, response.data.data)
      await loadTestModelOptions(id)
    }
  } else {
    providerDialogVisible.title = '新增供应商'
    providerForm.value.id = undefined
  }
  providerDialogVisible.visible = true
  await nextTick()
  providerFormRef.value?.clearValidate()
}

async function handleProviderSubmit() {
  providerFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    providerSubmitLoading.value = true
    const id = providerForm.value.id
    try {
      if (id) {
        await AiProviderAPI.update(id, providerForm.value as AiProviderPayload)
        await refreshUpdate()
      } else {
        await AiProviderAPI.create(providerForm.value as AiProviderPayload)
        await refreshCreate()
      }
      providerDialogVisible.visible = false
      resetProviderForm()
    } catch (error: unknown) {
      console.error(error)
    } finally {
      providerSubmitLoading.value = false
    }
  })
}

async function handleTestConnectivity() {
  testLoading.value = true
  testResult.value = null
  try {
    const res = await AiProviderAPI.testConnectivity({
      ...(providerForm.value as AiProviderPayload),
      model_key: testModelKey.value,
    })
    testResult.value = res.data.data
    if (testResult.value?.success) {
      // 连通成功提示由 HTTP 拦截器统一处理
    }
  } catch (error: unknown) {
    testResult.value = { success: false, latency_ms: null, error: (error as Error).message || '请求失败' }
  } finally {
    testLoading.value = false
  }
}

async function handleSetDefaultProvider(id: number) {
  try {
    await AiProviderAPI.setDefault(id)
    await refreshData()
  } catch (error: unknown) {
    console.error(error)
  }
}

async function deleteProviderRow(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该供应商？其下模型将级联删除。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await AiProviderAPI.delete([id])
    faTableRef.value?.elTableRef?.clearSelection()
    delete providerModels.value[id]
    await refreshRemove()
  } catch {
    // 用户取消
  }
}

// ============================================================ #
//  模型 Drawer
// ============================================================ //
type ModelForm = AiModelPayload & Partial<Pick<AiModel, 'id' | 'status' | 'created_time' | 'updated_time'>>

const modelFormRef = ref()
const modelSubmitLoading = ref(false)
const currentProviderName = ref('')
const currentProviderId = ref<number>(0)

const modelForm = ref<ModelForm>({
  id: undefined,
  provider_id: undefined,
  model_key: undefined,
  name: undefined,
  url: undefined,
  tool_calling: false,
  vision: false,
  thinking: true,
  max_input_tokens: 131072,
  max_output_tokens: 4096,
  temperature: 0.7,
  is_default: false,
  sort_order: 0,
  status: '0',
  description: undefined,
})

const initialModelForm: ModelForm = {
  id: undefined,
  provider_id: undefined,
  model_key: undefined,
  name: undefined,
  url: undefined,
  tool_calling: false,
  vision: false,
  thinking: true,
  max_input_tokens: 131072,
  max_output_tokens: 4096,
  temperature: 0.7,
  is_default: false,
  sort_order: 0,
  status: '0',
  description: undefined,
}

const modelDetail = ref<Partial<AiModel>>({})

const modelDialogVisible = reactive({
  title: '',
  visible: false,
  type: 'create' as 'create' | 'update' | 'detail',
})

const modelRules = reactive({
  model_key: [{ required: true, message: '请输入模型Key', trigger: 'blur' }],
  name: [{ required: true, message: '请输入模型显示名', trigger: 'blur' }],
})

function resetModelForm() {
  modelFormRef.value?.resetFields()
  modelFormRef.value?.clearValidate()
  Object.assign(modelForm.value, initialModelForm)
}

function handleCloseModelDialog() {
  modelDialogVisible.visible = false
  resetModelForm()
}

async function openModelDialog(type: 'create' | 'update' | 'detail', providerId: number, modelId?: number) {
  modelDialogVisible.type = type
  currentProviderId.value = providerId
  modelForm.value.provider_id = providerId

  // 查找供应商名称
  const provider = data.value.find((p: AiProvider) => p.id === providerId)
  currentProviderName.value = provider?.name ?? `供应商#${providerId}`

  if (modelId) {
    const response = await AiModelAPI.getDetail(modelId)
    if (type === 'detail') {
      modelDialogVisible.title = '模型详情'
      Object.assign(modelDetail.value, response.data.data ?? {})
    } else if (type === 'update') {
      modelDialogVisible.title = '修改模型'
      Object.assign(modelForm.value, response.data.data)
    }
  } else {
    modelDialogVisible.title = '新增模型'
    modelForm.value.id = undefined
    modelForm.value.provider_id = providerId
  }
  modelDialogVisible.visible = true
  await nextTick()
  modelFormRef.value?.clearValidate()
}

async function handleModelSubmit() {
  modelFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    modelSubmitLoading.value = true
    const id = modelForm.value.id
    try {
      if (id) {
        await AiModelAPI.update(id, modelForm.value as AiModelPayload)
      } else {
        await AiModelAPI.create(modelForm.value as AiModelPayload)
      }
      modelDialogVisible.visible = false
      resetModelForm()
      refreshProviderModels(currentProviderId.value)
    } catch (error: unknown) {
      console.error(error)
    } finally {
      modelSubmitLoading.value = false
    }
  })
}

async function handleSetDefaultModel(providerId: number, modelId: number) {
  try {
    await AiModelAPI.setDefault(modelId)
    refreshProviderModels(providerId)
  } catch (error: unknown) {
    console.error(error)
  }
}

async function deleteModelRow(providerId: number, modelId: number) {
  try {
    await ElMessageBox.confirm('确认删除该模型？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await AiModelAPI.delete([modelId])
    refreshProviderModels(providerId)
  } catch {
    // 用户取消
  }
}
</script>

<style lang="scss" scoped>
.provider-tab-page {
  .detail-model-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .model-expand-row {
    padding: 12px 16px;
    background: var(--el-fill-color-lighter);

    .model-expand-header {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;

      .model-expand-title {
        font-size: 13px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .capability-tags {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .capability-checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
