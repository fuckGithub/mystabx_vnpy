<!-- 顶部栏：H-work 风格白底顶栏（品牌 + 主导航 + 工具区） -->
<template>
  <div
    class="fa-header-bar w-full bg-[var(--default-box-color,#fff)]"
    :class="[
      tabStyle === 'tab-card' || tabStyle === 'tab-google' || tabStyle === 'tab-default' ? 'max-sm:mb-3' : '',
    ]">
    <div
      class="fa-header-bar__row relative box-border flex h-14 w-full min-w-0 flex-nowrap items-center justify-between leading-14 select-none border-b border-[var(--fa-card-border,#eef0f3)] px-3 max-sm:px-2">
      <div class="fa-header-bar__left flex min-w-0 flex-1 flex-nowrap items-center overflow-hidden">
        <!-- 品牌：顶栏 / 混合布局始终展示；侧栏布局仅展示菜单按钮旁的控件 -->
        <div
          v-if="showAppLogo && (isTopMenu || isTopLeftMenu)"
          class="fa-header-bar__brand mr-4 flex shrink-0 cursor-pointer items-center gap-2"
          @click="toHome">
          <FaLogo variant="mark" :size="28" />
          <span class="fa-header-bar__brand-name max-md:!hidden text-[15px] font-semibold tracking-wide text-g-800">
            {{ brandName }}
          </span>
        </div>

        <FaLogo
          v-else-if="showAppLogo && !isLeftMenu"
          class="!hidden pl-1.5 overflow-hidden align-[-0.15em] fill-current"
          variant="mark"
          :size="28"
          @click="toHome" />

        <!-- 菜单按钮（左侧菜单布局） -->
        <FaIconButton
          v-if="isLeftMenu && shouldShowMenuButton"
          icon="ri:menu-2-fill"
          class="ml-0.5 max-sm:ml-0"
          @click="visibleMenu" />

        <!-- 快速入口 -->
        <FaFastEnter v-if="shouldShowFastEnter && width >= headerBarFastEnterMinWidth">
          <FaIconButton icon="ri:apps-2-line" class="ml-1" />
        </FaFastEnter>

        <!-- 面包屑（侧栏 / 双列） -->
        <FaBreadcrumb v-if="(shouldShowBreadcrumb && isLeftMenu) || (shouldShowBreadcrumb && isDualMenu)" />

        <!-- 顶部菜单 -->
        <FaHorizontalMenu v-if="isTopMenu" class="fa-header-bar__nav" :list="menuList" />

        <!-- 混合菜单-顶部 -->
        <FaMixedMenu v-if="isTopLeftMenu" :list="menuList" />
      </div>

      <div id="app-header-toolbar" class="fa-header-bar__right flex shrink-0 flex-nowrap items-center gap-0.5">
        <!-- 搜索：图标按钮，贴近参考密度 -->
        <FaIconButton
          v-if="shouldShowGlobalSearch"
          icon="ri:search-line"
          class="search-btn max-md:!hidden"
          :title="$t('topBar.search.title')"
          @click="openSearchDialog" />

        <!-- 刷新 -->
        <FaIconButton
          v-if="shouldShowRefreshButton"
          icon="ri:refresh-line"
          class="refresh-btn max-sm:!hidden"
          @click="reload" />

        <!-- 全屏 -->
        <FaIconButton
          v-if="shouldShowFullscreen"
          :icon="isFullscreen ? 'ri:fullscreen-exit-line' : 'ri:fullscreen-fill'"
          :class="[!isFullscreen ? 'full-screen-btn' : 'exit-full-screen-btn']"
          class="max-md:!hidden"
          @click="toggleFullScreen" />

        <!-- 组件尺寸 -->
        <div v-if="shouldShowSizeSelect" class="flex-cc max-md:!hidden">
          <FaSizeSelect />
        </div>

        <!-- 国际化 -->
        <ElDropdown @command="changeLanguage" popper-class="langDropDownStyle" v-if="shouldShowLanguage">
          <FaIconButton icon="ri:translate-2" class="language-btn text-[19px]" />
          <template #dropdown>
            <ElDropdownMenu>
              <div v-for="item in languageOptions" :key="item.value" class="lang-btn-item">
                <ElDropdownItem :command="item.value" :class="{ 'is-selected': locale === item.value }">
                  <span class="menu-txt">{{ item.label }}</span>
                  <FaSvgIcon icon="ri:check-fill" v-if="locale === item.value" />
                </ElDropdownItem>
              </div>
            </ElDropdownMenu>
          </template>
        </ElDropdown>

        <!-- 通知 -->
        <FaIconButton
          v-if="shouldShowNotification"
          icon="ri:notification-2-line"
          class="notice-button relative"
          @click="visibleNotice">
          <div class="absolute top-2 right-2 size-1.5 !bg-danger rounded-full"></div>
        </FaIconButton>

        <!-- 聊天 -->
        <FaIconButton v-if="shouldShowChat" icon="ri:message-3-line" class="chat-button relative" @click="openChat">
          <div class="breathing-dot absolute top-2 right-2 size-1.5 !bg-success rounded-full"></div>
        </FaIconButton>

        <!-- 设置 -->
        <div v-if="shouldShowSettings">
          <ElPopover :visible="showSettingGuide" placement="bottom-start" :width="190" :offset="0">
            <template #reference>
              <div class="flex-cc">
                <FaIconButton icon="ri:settings-line" class="setting-btn" @click="openSetting" />
              </div>
            </template>
            <template #default>
              <p>
                {{ $t('topBar.guide.title') }}
                <span :style="{ color: systemThemeColor }">{{ $t('topBar.guide.theme') }}</span>
                、
                <span :style="{ color: systemThemeColor }">{{ $t('topBar.guide.menu') }}</span>
                {{ $t('topBar.guide.description') }}
              </p>
            </template>
          </ElPopover>
        </div>

        <!-- 主题切换 -->
        <FaIconButton
          v-if="shouldShowThemeToggle"
          @click="themeAnimation"
          :icon="isDark ? 'ri:sun-fill' : 'ri:moon-line'" />

        <!-- 用户头像、菜单 -->
        <FaUserMenu show-name />
      </div>
    </div>

    <!-- 标签页 -->
    <FaWorkTab />

    <!-- 通知 -->
    <FaNotification v-model:value="showNotice" ref="notice" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useFullscreen, useWindowSize } from '@vueuse/core'
import { LanguageEnum, MenuTypeEnum } from '@/enums/appEnum'
import { useSettingsStore } from '@stores/modules/setting.store'
import { useUserStore } from '@stores/modules/user.store'
import { useMenuStore } from '@stores/modules/menu.store'
import { languageOptions } from '@/locales'
import { mittBus } from '@utils/sys'
import { themeAnimation } from '@utils/ui'
import { useCommon } from '@/hooks/core/useCommon'
import { useHeaderBar } from '@/hooks/core/useHeaderBar'
import AppEnv from '@/config'
import FaUserMenu from './widget/FaUserMenu.vue'
import FaSizeSelect from '@/components/others/fa-size-select/index.vue'

defineOptions({ name: 'FaHeaderBar' })

const router = useRouter()
const { locale } = useI18n()
const { width } = useWindowSize()

const settingStore = useSettingsStore()
const userStore = useUserStore()
const menuStore = useMenuStore()

const {
  shouldShowMenuButton,
  shouldShowRefreshButton,
  shouldShowFastEnter,
  shouldShowBreadcrumb,
  shouldShowGlobalSearch,
  shouldShowFullscreen,
  shouldShowNotification,
  shouldShowChat,
  shouldShowLanguage,
  shouldShowSettings,
  shouldShowThemeToggle,
  shouldShowSizeSelect,
  fastEnterMinWidth: headerBarFastEnterMinWidth,
} = useHeaderBar()

const { menuOpen, systemThemeColor, showSettingGuide, menuType, isDark, tabStyle, showAppLogo } =
  storeToRefs(settingStore)

const { language } = storeToRefs(userStore)
const { menuList } = storeToRefs(menuStore)

const showNotice = ref(false)
const notice = ref(null)

const brandName = computed(() => AppEnv.systemInfo.name || 'Stabx')

const isLeftMenu = computed(() => menuType.value === MenuTypeEnum.LEFT)
const isDualMenu = computed(() => menuType.value === MenuTypeEnum.DUAL_MENU)
const isTopMenu = computed(() => menuType.value === MenuTypeEnum.TOP)
const isTopLeftMenu = computed(() => menuType.value === MenuTypeEnum.TOP_LEFT)

const { isFullscreen, toggle: toggleFullscreen } = useFullscreen()

onMounted(() => {
  initLanguage()
  document.addEventListener('click', bodyCloseNotice)
})

onUnmounted(() => {
  document.removeEventListener('click', bodyCloseNotice)
})

const toggleFullScreen = (): void => {
  toggleFullscreen()
}

const visibleMenu = (): void => {
  settingStore.setMenuOpen(!menuOpen.value)
}

const { homePath } = useCommon()
const { refresh } = useCommon()

const toHome = (): void => {
  router.push(homePath.value)
}

const reload = (time: number = 0): void => {
  setTimeout(() => {
    refresh()
  }, time)
}

const initLanguage = (): void => {
  locale.value = language.value
}

const changeLanguage = (lang: LanguageEnum): void => {
  if (locale.value === lang) return
  locale.value = lang
  userStore.setLanguage(lang)
  reload(50)
}

const openSetting = (): void => {
  mittBus.emit('openSetting')

  if (showSettingGuide.value) {
    settingStore.hideSettingGuide()
  }
}

const openSearchDialog = (): void => {
  mittBus.emit('openSearchDialog')
}

const bodyCloseNotice = (e: any): void => {
  if (!showNotice.value) return

  const target = e.target as HTMLElement
  const isNoticeButton = target.closest('.notice-button')
  const isNoticePanel = target.closest('.fa-notification-panel')

  if (!isNoticeButton && !isNoticePanel) {
    showNotice.value = false
  }
}

const visibleNotice = (): void => {
  showNotice.value = !showNotice.value
}

const openChat = (): void => {
  mittBus.emit('openChat')
}
</script>

<style lang="scss" scoped>
.fa-header-bar {
  background: var(--default-box-color, #fff);
}

.fa-header-bar__row {
  box-sizing: border-box;
  width: 100%;
  padding-inline: 12px;
}

.fa-header-bar__left,
.fa-header-bar__right {
  flex-wrap: nowrap;
}

.fa-header-bar__right {
  margin-left: auto;
}

.fa-header-bar__brand-name {
  color: var(--fa-gray-800, #1f2329);
}

.fa-header-bar__nav {
  min-width: 0;
}

@keyframes rotate180 {
  0% {
    transform: rotate(0);
  }

  100% {
    transform: rotate(180deg);
  }
}

@keyframes shake {
  0% {
    transform: rotate(0);
  }

  25% {
    transform: rotate(-5deg);
  }

  50% {
    transform: rotate(5deg);
  }

  75% {
    transform: rotate(-5deg);
  }

  100% {
    transform: rotate(0);
  }
}

@keyframes expand {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.1);
  }

  100% {
    transform: scale(1);
  }
}

@keyframes shrink {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(0.9);
  }

  100% {
    transform: scale(1);
  }
}

@keyframes moveUp {
  0% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-3px);
  }

  100% {
    transform: translateY(0);
  }
}

@keyframes breathing {
  0% {
    opacity: 0.4;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1.1);
  }

  100% {
    opacity: 0.4;
    transform: scale(0.9);
  }
}

.refresh-btn:hover :deep(.fa-svg-icon),
.setting-btn:hover :deep(.fa-svg-icon) {
  animation: rotate180 0.5s;
}

.language-btn:hover :deep(.fa-svg-icon) {
  animation: moveUp 0.4s;
}

.full-screen-btn:hover :deep(.fa-svg-icon) {
  animation: expand 0.6s forwards;
}

:deep(.size-select-btn:hover .fa-svg-icon) {
  animation: expand 0.6s forwards;
}

.exit-full-screen-btn:hover :deep(.fa-svg-icon) {
  animation: shrink 0.6s forwards;
}

.notice-button:hover :deep(.fa-svg-icon),
.chat-button:hover :deep(.fa-svg-icon) {
  animation: shake 0.5s ease-in-out;
}

.breathing-dot {
  animation: breathing 1.5s ease-in-out infinite;
}

@media screen and (width <= 640px) {
  .fa-header-bar__row {
    padding-inline: 8px;
  }
}
</style>
