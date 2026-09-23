<!-- 用户菜单：个人中心、更新日志、配置中心、文档、引导、锁屏、退出 -->
<template>
  <!-- inline-flex + items-center：与顶栏 FaIconButton 同一中线对齐 -->
  <div class="fa-user-menu inline-flex shrink-0 items-center leading-none gap-1.5 pl-1">
    <ElPopover
      ref="userMenuPopover"
      placement="bottom-end"
      :width="240"
      :hide-after="0"
      :offset="10"
      trigger="hover"
      :show-arrow="false"
      popper-class="user-menu-popover"
      popper-style="padding: 5px 16px;">
      <template #reference>
        <div class="fa-user-menu__trigger c-p flex shrink-0 items-center gap-2" :class="showName ? 'pr-1' : ''">
          <div
            class="fa-user-menu__avatar-ref flex size-8.5 max-sm:w-6.5 max-sm:h-6.5 shrink-0 items-center justify-center">
            <img
              v-if="userAvatar"
              :key="userAvatar"
              class="size-full rounded-full object-cover block"
              :src="userAvatar"
              alt="avatar" />
            <img v-else class="size-full rounded-full block" src="@imgs/user/avatar.webp" alt="avatar" />
            <span class="fa-user-menu__online-dot" aria-hidden="true" />
          </div>
          <span v-if="showName" class="fa-user-menu__name max-sm:!hidden text-[13px] text-g-700 truncate max-w-24">
            {{ displayName }}
          </span>
        </div>
      </template>
      <template #default>
        <div class="pt-3">
          <div class="flex-c pb-1 px-0">
            <img
              v-if="userAvatar"
              :key="`menu-${userAvatar}`"
              class="w-10 h-10 mr-3 ml-0 overflow-hidden rounded-full float-left object-cover"
              :src="userAvatar"
              alt="" />
            <img
              v-else
              class="w-10 h-10 mr-3 ml-0 overflow-hidden rounded-full float-left"
              src="@imgs/user/avatar.webp"
              alt="" />
            <div class="w-[calc(100%-60px)] h-full">
              <span class="block text-sm font-medium text-g-800 truncate">
                {{ displayName }}
              </span>
              <span class="block mt-0.5 text-xs text-g-500 truncate">{{ displayEmail }}</span>
            </div>
          </div>
          <ul class="py-4 mt-3 border-t border-g-300/80">
            <li class="btn-item" @click="goPage('/fastlink/profile')">
              <FaSvgIcon icon="ri:user-3-line" />
              <span>{{ $t('topBar.user.userCenter') }}</span>
            </li>
            <li class="btn-item" @click="goChangeLog">
              <FaSvgIcon icon="ri:draft-line" />
              <span>{{ $t('topBar.user.changeLog') }}</span>
            </li>
            <li class="btn-item" @click="openParamConfig">
              <FaSvgIcon icon="ri:settings-3-line" />
              <span>{{ $t('topBar.user.paramConfig') }}</span>
            </li>
            <li class="btn-item" @click="toDocs()">
              <FaSvgIcon icon="ri:book-2-line" />
              <span>{{ $t('topBar.user.docs') }}</span>
            </li>
            <li class="btn-item" @click="startTour">
              <FaSvgIcon icon="ri:compass-3-line" />
              <span>{{ $t('topBar.user.tour') }}</span>
            </li>
            <li class="btn-item" @click="lockScreen()">
              <FaSvgIcon icon="ri:lock-line" />
              <span>{{ $t('topBar.user.lockScreen') }}</span>
            </li>
            <div class="w-full h-px my-2 bg-g-300/80"></div>
            <li class="btn-item btn-item--logout" @click="handleLogout">
              {{ $t('topBar.user.logout') }}
            </li>
          </ul>
        </div>
      </template>
    </ElPopover>

    <ConfigInfoDrawer v-model="paramDrawerVisible" />
  </div>
</template>

<script setup lang="ts">
import { DeviceEnum } from '@/enums/settings/device.enum'
import { useAppStore } from '@stores/modules/app.store'
import { useSettingsStore } from '@stores/modules/setting.store'
import { useUserStore } from '@stores/modules/user.store'
import { WEB_LINKS } from '@utils/constants'
import { mittBus } from '@utils/sys'
import ConfigInfoDrawer from '@views/module_system/param/components/ConfigInfoDrawer.vue'
import { ElMessageBox } from 'element-plus'
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

defineOptions({ name: 'FaUserMenu' })

withDefaults(
  defineProps<{
    /** 是否在头像旁展示用户名（顶栏参考布局） */
    showName?: boolean
  }>(),
  { showName: false }
)

const router = useRouter()
const { t } = useI18n()
const userStore = useUserStore()
const appStore = useAppStore()
const settingStore = useSettingsStore()

const { info: userInfo } = storeToRefs(userStore)
const userMenuPopover = ref()
const paramDrawerVisible = ref(false)

const userAvatar = computed(() => {
  const a = (userInfo.value as { avatar?: string })?.avatar?.trim()
  return a || ''
})

const displayName = computed(
  () =>
    (userInfo.value as { name?: string; username?: string })?.name ||
    (userInfo.value as { username?: string })?.username ||
    '—'
)

const displayEmail = computed(() => (userInfo.value as { email?: string })?.email || '')

/** 与旧版 NavbarActions 一致：桌面浮动引导，移动端进引导页 */
const guideVisible = computed({
  get: () => appStore.guideVisible,
  set: (v: boolean) => appStore.showGuide(v),
})

function openParamConfig(): void {
  closeUserMenu()
  paramDrawerVisible.value = true
}

function goPage(path: string): void {
  router.push(path)
}

function goChangeLog(): void {
  closeUserMenu()
  router.push({ name: 'FastlinkChangeLog' }).catch(() => {})
}

function toDocs(): void {
  window.open(WEB_LINKS.DOCS)
}

function lockScreen(): void {
  mittBus.emit('openLockScreen')
}

function startTour(): void {
  closeUserMenu()
  if (appStore.device === DeviceEnum.MOBILE) {
    router.push({ name: 'Guide' })
  } else {
    guideVisible.value = true
  }
}

watch(
  () => guideVisible.value,
  (val, oldVal) => {
    if (oldVal && !val) {
      settingStore.updateSetting('showGuide', false)
    }
  }
)

function handleLogout(): void {
  closeUserMenu()
  setTimeout(async () => {
    try {
      await ElMessageBox.confirm(t('common.logoutTips'), t('common.tips'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        customClass: 'login-out-dialog',
      })
      await userStore.logout()
    } catch {
      // 用户取消
    }
  }, 200)
}

function closeUserMenu(): void {
  setTimeout(() => {
    userMenuPopover.value?.hide?.()
  }, 100)
}
</script>

<style scoped>
@reference '@styles/core/tailwind.css';

@layer components {
  .btn-item {
    @apply flex items-center p-2 mb-3 select-none rounded-md cursor-pointer last:mb-0;

    span {
      @apply text-sm;
    }

    .fa-svg-icon {
      @apply mr-2 text-base;
    }

    &:hover {
      background-color: var(--fa-gray-200);
    }
  }

  /** 退出：沿用菜单项 hover 底纹，并加重边框/文字，避免仅 shadow 几乎无反馈 */
  .btn-item.btn-item--logout {
    @apply justify-center mt-5 mb-0 py-1.5 text-xs border border-g-400;

    &:hover {
      color: var(--el-color-danger);
      background-color: var(--fa-gray-200);
      border-color: var(--el-color-danger-light-3);
    }
  }
}

.fa-user-menu .el-tooltip__trigger {
  display: inline-flex !important;
  align-items: center;
  line-height: 1;
}

.fa-user-menu__avatar-ref {
  position: relative;
  box-sizing: border-box;
}

.fa-user-menu__online-dot {
  position: absolute;
  right: 0;
  bottom: 0;
  z-index: 1;
  width: 8px;
  height: 8px;
  pointer-events: none;
  background-color: var(--el-color-success);
  border-radius: 50%;
  box-shadow: 0 0 2px rgb(0 0 0 / 20%);
}

.fa-user-menu__name {
  font-weight: 500;
}
</style>
