<!-- 聊天页模型选择器：按供应商分组的下拉，置顶显示当前模型 -->
<template>
  <div class="model-selector">
    <ElSelect
      :model-value="modelValue"
      :loading="loading"
      filterable
      placeholder="选择模型"
      class="model-select"
      @update:model-value="handleChange"
      @visible-change="handleVisibleChange">
      <ElOptionGroup v-for="group in groups" :key="group.provider_id" :label="group.provider_name">
        <ElOption v-for="m in group.models" :key="m.id" :label="m.name" :value="m.id">
          <div class="model-option">
            <span class="model-option-name">{{ m.name }}</span>
            <ElTag v-if="m.is_default" size="small" type="success" effect="plain">默认</ElTag>
          </div>
        </ElOption>
      </ElOptionGroup>
    </ElSelect>
    <ElButton v-if="refreshable" text :icon="Refresh" class="refresh-btn" @click="loadModels(true)" />
    <div class="thinking-toggle" :title="'思考模式'">
      <ElTooltip :content="enableThinking ? '思考模式已开启' : '思考模式已关闭'" placement="top">
        <ElSwitch :model-value="enableThinking" class="thinking-switch" @update:model-value="handleThinkingChange" />
      </ElTooltip>
      <span class="thinking-label" @click="handleThinkingChange(!enableThinking)">思考模式</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import AiModelAPI, { type AiModel, type AiModelOption } from '@/api/module_ai/model'
import AiProviderAPI, { type AiProvider } from '@/api/module_ai/provider'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'

interface Props {
  modelValue?: number | null
  enableThinking?: boolean
  refreshable?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: number | null): void
  (e: 'update:enableThinking', value: boolean): void
  (e: 'change', model: AiModelOption | undefined): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  enableThinking: true,
  refreshable: false,
})

const emit = defineEmits<Emits>()

const loading = ref(false)
const providers = ref<AiProvider[]>([])
const models = ref<AiModelOption[]>([])

/** AiModel → AiModelOption（仅保留下拉需要的无密钥字段） */
function toOption(m: AiModel): AiModelOption {
  return {
    id: m.id,
    provider_id: m.provider_id,
    provider_name: m.provider_name ?? null,
    vendor: m.vendor ?? null,
    api_type: m.api_type ?? null,
    model_key: m.model_key,
    name: m.name,
    thinking: m.thinking ?? null,
    tool_calling: m.tool_calling ?? null,
    vision: m.vision ?? null,
    is_default: m.is_default ?? null,
  }
}

interface ModelGroup {
  provider_id: number
  provider_name: string
  models: AiModelOption[]
}

const groups = computed<ModelGroup[]>(() =>
  providers.value
    .filter((p) => p.id != null)
    .map((p) => ({
      provider_id: p.id as number,
      provider_name: p.name,
      models: models.value.filter((m) => m.provider_id === p.id),
    }))
    .filter((g) => g.models.length > 0)
)

async function loadModels(showTip = false) {
  if (loading.value) return
  loading.value = true
  try {
    // 并行拉取供应商列表 + 全量模型列表
    const [providerRes, modelRes] = await Promise.all([AiProviderAPI.getList({}), AiModelAPI.getList({})])
    providers.value = providerRes.data.data ?? []
    models.value = (modelRes.data.data ?? []).map(toOption)
    // 无选中时回填默认模型
    ensureDefault()
    if (showTip) {
      ElMessage.success('模型列表已刷新')
    }
  } catch (error: unknown) {
    console.error(error)
    if (showTip) {
      ElMessage.error('加载模型列表失败')
    }
  } finally {
    loading.value = false
  }
}

function handleVisibleChange(visible: boolean) {
  // 首次展开时懒加载
  if (visible && providers.value.length === 0) {
    void loadModels()
  }
}

function handleChange(value: number | null) {
  const model = models.value.find((m) => m.id === value)
  emit('update:modelValue', value ?? null)
  if (model) {
    emit('update:enableThinking', model.thinking ?? true)
  }
  emit('change', model ?? undefined)
}

function handleThinkingChange(value: boolean) {
  emit('update:enableThinking', value)
}

// 默认模型回填：无选中时优先默认模型
function ensureDefault() {
  if (props.modelValue == null && models.value.length > 0) {
    const def = models.value.find((m) => m.is_default) ?? models.value[0]
    if (def) {
      emit('update:modelValue', def.id)
      emit('update:enableThinking', def.thinking ?? true)
      emit('change', def)
    }
  }
}

defineExpose({
  load: () => loadModels(true),
})

// 组件挂载时预加载（含默认回填）
void loadModels()
</script>

<style lang="scss" scoped>
.model-selector {
  display: inline-flex;
  gap: 4px;
  align-items: center;

  .model-select {
    width: 220px;
  }

  .model-option {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }

  .refresh-btn {
    padding: 4px;
  }

  .thinking-toggle {
    display: inline-flex;
    gap: 4px;
    align-items: center;

    .thinking-switch {
      :deep(.el-switch__core) {
        width: 28px;
      }
    }

    .thinking-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;

      &:hover {
        color: var(--el-color-primary);
      }
    }
  }
}
</style>
