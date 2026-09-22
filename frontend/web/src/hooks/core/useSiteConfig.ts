/**
 * useSiteConfig - 站点配置初始化（标题 + favicon）。
 *
 * 从 configStore 拉取系统配置，同步到浏览器标题和 favicon。
 * 通过 watch 响应配置变更（如管理员在后台修改后重新拉取时自动更新）。
 *
 * 应在 App.vue 的 onMounted 中调用。
 */

import { watch } from 'vue'
import { useConfigStore } from '@stores/modules/config.store'

/** 与 Swagger 文档页签一致的本地闪电 favicon（public/favicon.png） */
const LOCAL_FAVICON = `${import.meta.env.BASE_URL}favicon.png`

const updateFavicon = (url: string) => {
  const links = document.querySelectorAll<HTMLLinkElement>(
    'link[rel="icon"], link[rel="shortcut icon"]'
  )
  links.forEach((link) => {
    link.href = url
  })
}

const syncFromConfig = () => {
  const { sys_web_title } = useConfigStore().configData
  if (sys_web_title?.config_value) document.title = sys_web_title.config_value
  // 页签图标固定为与 Swagger 相同的 FastAPI 闪电图，避免被远程 FA logo 覆盖
  updateFavicon(LOCAL_FAVICON)
}

export function useSiteConfig() {
  const configStore = useConfigStore()

  /** 初始化：拉取配置并同步标题/favicon */
  const initSiteConfig = async () => {
    try {
      await configStore.getConfig()
      syncFromConfig()
    } catch (error) {
      console.error('[SiteConfig] 获取配置失败:', error)
    }
  }

  /** 配置更新后自动同步（管理员后台修改配置后重新拉取时） */
  watch(
    () => configStore.configData,
    () => syncFromConfig(),
    { deep: false }
  )

  return { initSiteConfig }
}
