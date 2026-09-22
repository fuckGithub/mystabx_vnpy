<!-- 系统 logo：优先自定义 src，缺省用 Stabx / Cumustabilis 品牌图（与 vnpy 一致） -->
<template>
  <div class="fa-logo flex-cc" :class="`fa-logo--${variant}`">
    <img
      :style="logoStyle"
      :src="resolvedSrc"
      alt="Stabx"
      class="fa-logo__img object-contain"
      @error="onImgError" />
  </div>
</template>

<script setup lang="ts">
import brandMark from '@/assets/brand/logo-mini.svg'
import brandWordmark from '@/assets/brand/logo-topbar.png'

defineOptions({ name: 'FaLogo' })

interface Props {
  /** logo 高度（wordmark 时宽度自适应） */
  size?: number | string
  /** 自定义地址（如配置接口 sys_web_logo）；不传则用品牌资源 */
  src?: string
  /** mark=方标；wordmark=横版字标（侧栏展开） */
  variant?: 'mark' | 'wordmark'
}

const props = withDefaults(defineProps<Props>(), {
  size: 36,
  src: undefined,
  variant: 'mark',
})

const fallbackTriggered = ref(false)

const brandDefault = computed(() => (props.variant === 'wordmark' ? brandWordmark : brandMark))

const resolvedSrc = computed(() => {
  if (fallbackTriggered.value) return brandDefault.value
  const custom = props.src?.trim()
  return custom || brandDefault.value
})

function onImgError() {
  if (!fallbackTriggered.value) {
    fallbackTriggered.value = true
  }
}

const logoStyle = computed(() => {
  const h = `${props.size}px`
  if (props.variant === 'wordmark') {
    return { height: h, width: 'auto', maxWidth: '220px' }
  }
  return { width: h, height: h }
})

watch(
  () => [props.src, props.variant],
  () => {
    fallbackTriggered.value = false
  }
)
</script>

<style scoped>
.fa-logo--wordmark {
  max-width: 220px;
}

.fa-logo--wordmark .fa-logo__img {
  width: auto !important;
  max-width: 100%;
}

.fa-logo__img {
  display: block;
}
</style>
