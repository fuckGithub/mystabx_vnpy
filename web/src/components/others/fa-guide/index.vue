<!-- 新手引导：目标用函数延迟解析并带回退节点，避免找不到节点时浮层居中变成「纯弹窗」 -->
<template>
  <ElTour
    v-model="open"
    :show-close="false"
    :mask="true"
    :z-index="3100"
    append-to="body"
    @change="handleChange"
    @finish="handleTourFinish"
    @close="handleTourClose">
    <ElTourStep
      :target="targetMenu"
      :title="t('common.menu')"
      :description="t('common.menuDes')"
      :placement="placementMenu"
      :prev-button-props="prevBtn"
      :next-button-props="nextBtn" />
    <ElTourStep
      :target="targetToolbar"
      :title="t('common.tool')"
      :description="t('common.toolDes')"
      placement="bottom"
      :prev-button-props="prevBtn"
      :next-button-props="nextBtn" />
    <ElTourStep
      :target="targetTags"
      :title="t('common.tagsView')"
      :description="t('common.tagsViewDes')"
      placement="bottom"
      :prev-button-props="prevBtn"
      :next-button-props="doneBtn" />
    <template #indicators>
      <ElButton class="fa-guide-skip" size="small" text @click="handleSkip">
        {{ t('common.skipLabel') }}
      </ElButton>
    </template>
  </ElTour>
</template>

<script setup lang="ts">
defineOptions({ name: 'FaGuide' })
import { computed, type PropType } from 'vue'
import { useSettingsStore } from '@stores'
import { MenuTypeEnum } from '@/enums/appEnum'

const settingStore = useSettingsStore()
const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  teleport: {
    type: [String, Object] as PropType<string | HTMLElement | null>,
    default: 'body',
  },
})

const emit = defineEmits(['update:modelValue', 'change', 'prev', 'next', 'skip'])

const open = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function hasUsefulRect(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect()
  return r.width > 4 && r.height > 4
}

function firstPresent(selectors: string[]): HTMLElement | null {
  for (const sel of selectors) {
    const el = document.querySelector(sel)
    if (el instanceof HTMLElement && hasUsefulRect(el)) {
      return el
    }
  }
  return null
}

/** 菜单高亮：按菜单类型优先，其次回退到侧栏 / 顶栏菜单 / 主内容区 */
function resolveMenuEl(): HTMLElement | null {
  const mt = settingStore.menuType as MenuTypeEnum
  let order: string[] = []
  switch (mt) {
    case MenuTypeEnum.TOP:
      order = ['#app-menu-top', '#app-menu-top-left', '#app-sidebar', '#app-main']
      break
    case MenuTypeEnum.TOP_LEFT:
      order = ['#app-menu-top-left', '#app-menu-top', '#app-sidebar', '#app-main']
      break
    case MenuTypeEnum.DUAL_MENU:
    case MenuTypeEnum.LEFT:
    default:
      order = ['#app-sidebar', '#app-menu-top', '#app-menu-top-left', '#app-main']
      break
  }
  return firstPresent(order) ?? (document.querySelector('#app-main') as HTMLElement | null)
}

function resolveToolbarEl(): HTMLElement | null {
  return (
    firstPresent(['#app-header-toolbar', '#app-header']) ?? (document.querySelector('#app-main') as HTMLElement | null)
  )
}

/** 标签栏关闭时可落到内容区，保证仍有镂空指引 */
function resolveTagsEl(): HTMLElement | null {
  return (
    firstPresent(['.worktab-tags-shell', '#app-header', '#app-content']) ??
    (document.querySelector('#app-main') as HTMLElement | null)
  )
}

/** Element Plus Tour：target 支持函数，在打开时解析 DOM，避免初始渲染阶段节点未就绪 */
function targetMenu(): HTMLElement | null {
  return resolveMenuEl()
}
function targetToolbar(): HTMLElement | null {
  return resolveToolbarEl()
}
function targetTags(): HTMLElement | null {
  return resolveTagsEl()
}

const placementMenu = computed((): 'top' | 'bottom' | 'left' | 'right' => {
  const mt = settingStore.menuType as MenuTypeEnum
  return mt === MenuTypeEnum.LEFT || mt === MenuTypeEnum.DUAL_MENU ? 'right' : 'bottom'
})

const prevBtn = computed(() => ({
  children: t('common.prevLabel'),
  onClick: handlePrevClick,
}))

const nextBtn = computed(() => ({
  children: t('common.nextLabel'),
  type: 'primary' as const,
  onClick: handleNextClick,
}))

const doneBtn = computed(() => ({
  children: t('common.doneLabel'),
  type: 'primary' as const,
  onClick: handleNextClick,
}))

function handleChange(step: number) {
  emit('change', step)
}

function handleSkip() {
  open.value = false
  emit('skip')
}

function handleTourFinish() {
  open.value = false
  emit('skip')
}

function handleTourClose() {
  emit('skip')
}

function handlePrevClick() {
  emit('prev')
}

function handleNextClick() {
  emit('next')
}
</script>

<!-- Tour 挂到 body，需全局样式（ElTour 内容根节点为 .el-tour） -->
<style lang="scss">
.el-tour {
  --el-tour-width: 300px;
  --el-tour-padding-primary: 18px 20px;
  --el-tour-border-radius: 12px;
  --el-tour-title-font-size: 16px;
  --el-tour-title-font-weight: 600;
  --el-tour-title-text-color: #1e293b;
  --el-tour-font-size: 13.5px;
  --el-tour-color: #64748b;
  --el-tour-bg-color: #ffffff;
}

.el-tour__content {
  border: 1px solid #e2e8f0;
  box-shadow:
    0 12px 28px rgba(15, 23, 42, 0.1),
    0 2px 6px rgba(15, 23, 42, 0.04);
}

.el-tour__arrow {
  border: 1px solid #e2e8f0;
  box-shadow: none;
}

.el-tour__header {
  padding-bottom: 8px;
}

.el-tour__title {
  letter-spacing: 0.01em;
}

.el-tour__body {
  line-height: 1.55;
}

.el-tour__footer {
  align-items: center;
  padding-top: 14px;
  gap: 8px;
}

.el-tour .el-tour-indicators {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-right: 0;
}

.el-tour .fa-guide-skip {
  color: #94a3b8 !important;
  font-weight: 500;
  padding: 4px 8px !important;

  &:hover {
    color: #64748b !important;
    background: #f1f5f9 !important;
  }
}

.el-tour__footer .el-button {
  border-radius: 8px;
  font-weight: 500;
  min-width: 72px;
}

.el-tour__footer .el-button--primary {
  box-shadow: 0 4px 10px color-mix(in srgb, var(--el-color-primary) 28%, transparent);
}

.dark .el-tour {
  --el-tour-title-text-color: #f1f5f9;
  --el-tour-color: #94a3b8;
  --el-tour-bg-color: #1e293b;
}

.dark .el-tour__content {
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}
</style>
