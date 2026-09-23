<!-- 图片裁剪组件 github: https://github.com/acccccccb/vue-img-cutter -->
<template>
  <div class="cutter-container" :class="{ 'cutter-container--preview': showPreview }">
    <div class="cutter-main">
      <div v-if="title" class="cutter-heading">{{ title }}</div>
      <div class="cutter-workspace">
        <ImgCutter
          ref="imgCutterModal"
          class="img-cutter"
          v-bind="cutterProps"
          @cutDown="cutDownImg"
          @onPrintImg="cutterPrintImg"
          @onImageLoadComplete="handleImageLoadComplete"
          @onImageLoadError="handleImageLoadError"
          @onClearAll="handleClearAll">
          <template #choose>
            <ElButton type="primary" plain size="small" v-ripple>选择图片</ElButton>
          </template>
          <template #cancel>
            <ElButton type="danger" plain size="small" v-ripple>清除</ElButton>
          </template>
          <template #confirm>
            <ElButton type="primary" size="small" class="cutter-confirm-btn" v-ripple>确定</ElButton>
          </template>
        </ImgCutter>
      </div>
    </div>

    <aside v-if="showPreview" class="cutter-preview">
      <div v-if="previewTitle" class="cutter-heading cutter-heading--sm">{{ previewTitle }}</div>
      <div
        class="cutter-preview__box"
        :class="{ 'cutter-preview__box--circle': previewCircle }"
        :style="previewBoxStyle">
        <img v-if="temImgPath" class="cutter-preview__img" :src="temImgPath" alt="预览图" />
        <span v-else class="cutter-preview__empty">暂无预览</span>
      </div>
      <ElButton
        v-if="showDownload"
        class="cutter-preview__download"
        size="small"
        :disabled="!temImgPath"
        v-ripple
        @click="downloadImg">
        下载图片
      </ElButton>
    </aside>
  </div>
</template>

<script setup lang="ts">
import ImgCutter from 'vue-img-cutter'
import 'vue-img-cutter/vue-img-cutter.css'

defineOptions({ name: 'FaCutterImg' })

interface CutterProps {
  /** 是否模态框 */
  isModal?: boolean
  /** 是否显示工具栏 */
  tool?: boolean
  /** 工具栏背景色 */
  toolBgc?: string
  /** 标题 */
  title?: string
  /** 预览标题 */
  previewTitle?: string
  /** 是否显示预览 */
  showPreview?: boolean
  /** 预览是否圆形（头像场景） */
  previewCircle?: boolean
  /** 是否显示下载按钮 */
  showDownload?: boolean
  /** 容器宽度 */
  boxWidth?: number
  /** 容器高度 */
  boxHeight?: number
  /** 裁剪宽度 */
  cutWidth?: number
  /** 裁剪高度 */
  cutHeight?: number
  /** 是否允许大小调整 */
  sizeChange?: boolean
  /** 裁剪宽高比，如 "1:1" */
  rate?: string | null
  /** 是否允许移动 */
  moveAble?: boolean
  /** 是否允许图片移动 */
  imgMove?: boolean
  /** 是否允许缩放 */
  scaleAble?: boolean
  /** 是否显示原始图片 */
  originalGraph?: boolean
  /** 是否允许跨域 */
  crossOrigin?: boolean
  /** 文件类型 */
  fileType?: 'png' | 'jpeg' | 'webp'
  /** 质量 */
  quality?: number
  /** 水印文本 */
  watermarkText?: string
  /** 水印字体大小 */
  watermarkFontSize?: number
  /** 水印颜色 */
  watermarkColor?: string
  /** 是否保存裁剪位置 */
  saveCutPosition?: boolean
  /** 是否预览模式 */
  previewMode?: boolean
  /** 输入图片 */
  imgUrl?: string
}

interface CutterResult {
  fileName: string
  file: File
  blob: Blob
  dataURL: string
}

const props = withDefaults(defineProps<CutterProps>(), {
  isModal: false,
  tool: true,
  toolBgc: 'transparent',
  title: '',
  previewTitle: '',
  showPreview: true,
  previewCircle: false,
  showDownload: true,
  boxWidth: 700,
  boxHeight: 458,
  cutWidth: 470,
  cutHeight: 270,
  sizeChange: true,
  rate: null,
  moveAble: true,
  imgMove: true,
  scaleAble: true,
  originalGraph: true,
  crossOrigin: true,
  fileType: 'png',
  quality: 0.9,
  watermarkText: '',
  watermarkFontSize: 20,
  watermarkColor: '#ffffff',
  saveCutPosition: true,
  previewMode: true,
})

const emit = defineEmits(['update:imgUrl', 'error', 'imageLoadComplete', 'imageLoadError'])

const temImgPath = ref('')
const imgCutterModal = ref()

const previewBoxStyle = computed(() => {
  const maxSide = 120
  const w = props.cutWidth || 120
  const h = props.cutHeight || 120
  const scale = Math.min(1, maxSide / Math.max(w, h))
  return {
    width: `${Math.round(w * scale)}px`,
    height: `${Math.round(h * scale)}px`,
  }
})

const cutterProps = computed(() => ({
  isModal: props.isModal,
  tool: props.tool,
  toolBgc: props.toolBgc,
  boxWidth: props.boxWidth,
  boxHeight: props.boxHeight,
  cutWidth: props.cutWidth,
  cutHeight: props.cutHeight,
  sizeChange: props.sizeChange,
  rate: props.rate,
  moveAble: props.moveAble,
  imgMove: props.imgMove,
  scaleAble: props.scaleAble,
  originalGraph: props.originalGraph,
  crossOrigin: props.crossOrigin,
  fileType: props.fileType,
  quality: props.quality,
  saveCutPosition: props.saveCutPosition,
  previewMode: props.previewMode,
  DoNotDisplayCopyright: true,
  WatermarkText: props.watermarkText,
  WatermarkFontSize: props.watermarkFontSize,
  WatermarkColor: props.watermarkColor,
}))

function preloadImage(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve()
    img.onerror = reject
    img.src = url
  })
}

async function initImgCutter() {
  if (props.imgUrl) {
    try {
      await preloadImage(props.imgUrl)
      imgCutterModal.value?.handleOpen({
        name: '封面图片',
        src: props.imgUrl,
      })
    } catch (error) {
      emit('error', error)
      console.error('图片加载失败:', error)
    }
  }
}

onMounted(() => {
  if (props.imgUrl) {
    temImgPath.value = props.imgUrl
    initImgCutter()
  }
})

watch(
  () => props.imgUrl,
  (newVal) => {
    if (newVal) {
      temImgPath.value = newVal
      initImgCutter()
    }
  }
)

function cutterPrintImg(result: { dataURL: string }) {
  temImgPath.value = result.dataURL
}

function cutDownImg(result: CutterResult) {
  emit('update:imgUrl', result.dataURL)
}

function handleImageLoadComplete(result: unknown) {
  emit('imageLoadComplete', result)
}

function handleImageLoadError(error: unknown) {
  emit('error', error)
  emit('imageLoadError', error)
}

function handleClearAll() {
  temImgPath.value = ''
}

function downloadImg() {
  if (!temImgPath.value) return
  const a = document.createElement('a')
  a.href = temImgPath.value
  a.download = `image.${props.fileType === 'jpeg' ? 'jpg' : props.fileType}`
  a.click()
}
</script>

<style lang="scss" scoped>
.cutter-container {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 20px;
  align-items: flex-start;
  justify-content: center;
  max-width: 100%;
}

.cutter-heading {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--el-text-color-primary);

  &--sm {
    font-size: 13px;
    color: var(--el-text-color-regular);
  }
}

.cutter-main {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 100%;
}

.cutter-workspace {
  display: flex;
  justify-content: center;
  width: 100%;
}

.cutter-preview {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  min-width: 120px;
  padding: 12px 14px;
  background: var(--fa-gray-100);
  border: 1px solid var(--fa-gray-300);
  border-radius: 8px;

  &__box {
    display: flex;
    overflow: hidden;
    background: var(--el-fill-color-blank);
    border: 1px solid var(--fa-gray-300);
    border-radius: 6px;
    box-shadow: inset 0 0 0 1px rgb(0 0 0 / 2%);

    &--circle {
      border-radius: 50%;
    }
  }

  &__img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &__empty {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    font-size: 12px;
    color: var(--el-text-color-placeholder);
  }

  &__download {
    width: 100%;
  }
}

/* —— vue-img-cutter 布局覆盖：工具条横排、操作区不压画布 —— */
.cutter-workspace {
  :deep(.vue-img-cutter),
  :deep(.dialogMain),
  :deep(.dialogBox) {
    width: 100% !important;
    max-width: 100%;
  }

  :deep(.dialogMain) {
    background: transparent !important;
  }

  :deep(.toolBox) {
    box-sizing: border-box;
    margin: 0 auto;
    overflow: visible;
    border: 1px solid var(--fa-gray-300);
    border-radius: 8px;
  }

  /* 为底部横排工具条预留空间，避免压住画布 */
  :deep(.toolMain),
  :deep(.dialogMain > div) {
    position: relative;
  }

  :deep(.dockMain) {
    position: absolute !important;
    right: 0 !important;
    bottom: -42px !important;
    left: 0 !important;
    z-index: 20 !important;
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 6px;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    width: 100%;
    padding: 0 !important;
    overflow: visible;
    background: transparent !important;
    border-radius: 0 !important;
    opacity: 1 !important;
  }

  :deep(.dockBtn) {
    display: inline-flex !important;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 28px !important;
    padding: 0 8px !important;
    margin: 0 !important;
    font-size: 12px !important;
    line-height: 1 !important;
    color: var(--el-color-primary) !important;
    white-space: nowrap;
    cursor: pointer;
    background-color: var(--el-color-primary-light-9) !important;
    border: 1px solid var(--el-color-primary-light-5) !important;
    border-radius: 4px !important;
    transition:
      background-color 0.15s,
      border-color 0.15s,
      color 0.15s;

    &:hover {
      color: #fff !important;
      background-color: var(--el-color-primary) !important;
      border-color: var(--el-color-primary) !important;
    }
  }

  /* 旋转滑条改为紧凑宽度，避免撑破横排 */
  :deep(.dockBtnScrollBar) {
    display: inline-block !important;
    flex: 0 0 auto;
    width: 88px !important;
    height: 8px !important;
    margin: 0 2px !important;
    vertical-align: middle;
    background-color: var(--el-color-primary-light-5);
  }

  :deep(.scrollBarControl) {
    width: 14px !important;
    height: 14px !important;
    border-color: var(--el-color-primary);
  }

  :deep(.selectArea) {
    top: 6px !important;
    right: 8px !important;
    width: auto !important;
    padding: 2px 6px;
    font-size: 11px !important;
    color: #fff !important;
    background: rgb(0 0 0 / 45%);
    border-radius: 3px;
  }

  :deep(.copyright) {
    display: none !important;
  }

  :deep(.i-dialog-footer) {
    display: flex !important;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    height: auto !important;
    min-height: 32px;
    margin-top: 52px !important;
    margin-bottom: 0 !important;
    text-align: left;
  }

  :deep(.i-dialog-footer > span) {
    display: inline-flex;
    gap: 8px;
    align-items: center;
  }

  :deep(.i-dialog-footer .btn-group),
  :deep(.i-dialog-footer .fr) {
    float: none !important;
    display: inline-flex;
    gap: 8px;
    align-items: center;
    margin-left: auto;
  }

  :deep(.cutter-confirm-btn) {
    margin-left: 0;
  }

  :deep(.toolBoxControl) {
    z-index: 100;
  }

  :deep(.closeIcon) {
    line-height: 15px !important;
  }
}

.dark {
  .cutter-preview {
    background: var(--fa-gray-200);
    border-color: var(--fa-gray-300);
  }

  .cutter-workspace {
    :deep(.toolBox) {
      border-color: var(--fa-gray-400);
    }

    :deep(.dialogMain) {
      background-color: transparent !important;
    }
  }
}
</style>
