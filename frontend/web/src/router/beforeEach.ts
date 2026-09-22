/**
 * 路由前置守卫 —— 导航生命周期中的核心编排器。
 *
 * ── 职责 ──
 * 1. 存储失效检测（storage 异常时登出）
 * 2. 登录态校验 & 未登录重定向
 * 3. 动态路由延迟注册（fetch 菜单 → addRoute → 保存）
 * 4. 根路径 `/` → 首页重定向
 * 5. 工作标签同步、页面标题设置
 * 6. 404 / 500 降级兜底
 *
 * ── 核心流程 ──
 * setupBeforeEachGuard() → 注册 `router.beforeEach`
 *   └─ handleRouteGuard()   ← 单一编排入口，按优先级顺序执行
 *        ├─ checkStorageInvalidated()
 *        ├─ handleLoginStatus()
 *        ├─ routeInitError 熔断兜底（初始化失败过 → 500，不再重试）
 *        ├─ startRouteInit()  ← 按需拉菜单 + addRoute，返回本次导航落点
 *        │    └─ initializeDynamicRoutes()  ← 只负责「决定去哪」，不调 next()
 *        │    └─ applyInitOutcome()         ← 唯一的 next() 落点
 *        ├─ handleRootPathRedirect()
 *        └─ setWorktab / setPageTitle / 404
 *
 * ── 初始化去重 ──
 * 并发导航共享同一个在途 Promise（`routeInitInFlight`）：命中在途则等待后按
 * **本次**目标重新导航，而不是 `next(false)` 静默取消。
 */
import { useCommon } from '@/hooks/core/useCommon'
import type { AppRouteRecord } from '@/types/router'
import { useMenuStore } from '@stores/modules/menu.store'
import { useSettingsStore } from '@stores/modules/setting.store'
import { useUserStore } from '@stores/modules/user.store'
import { useWorktabStore } from '@stores/modules/worktab.store'
import { ApiStatus, isHttpError } from '@utils/http'
import { setPageTitle, setWorktab } from '@utils/navigation'
import { checkStorageInvalidated, resetStorageInvalidated } from '@utils/storage'
import { loadingService, NProgress } from '@utils/ui'
import { nextTick } from 'vue'
import type { NavigationGuardNext, RouteLocationNormalized, RouteLocationRaw, Router } from 'vue-router'
import { RouteRegistry } from './dynamicRoutes'
import { MenuProcessor } from './MenuProcessor'
import { IframeRouteManager, ROUTE_PATH_LOGIN_ALT, staticRoutes } from './staticRoutes'

// --- 模块级单例与守卫状态 ---

/** 动态路由注册表（惰性创建，首次导航时生成） */
let routeRegistry: RouteRegistry | null = null

/** 菜单数据处理器（不含注册逻辑，只做列表拉取 + 树形组装） */
const menuProcessor = new MenuProcessor()

/**
 * 全局 loading 开关 —— 动态路由初始化时由 beforeEach 开启，
 * afterEach 收到标志后关闭。
 */
let pendingLoading = false

/**
 * 在途的动态路由初始化句柄。
 *
 * **单一事实来源：非 null 即表示「正在初始化」**，并发导航据此等待而不是重复拉取。
 * 以前用 `routeInitInProgress` + `routeInitDeferred` + `notifyRouteInitDone()` 三个变量
 * 表达同一件事，重置时漏掉其中一个就会重现「首次登录不跳转」这类竞态；
 * 改用 Promise 后，初始化结束即在 `finally` 里自动清空，不再需要手工通知。
 */
let routeInitInFlight: Promise<InitOutcome> | null = null

/**
 * 初始化失败原因（熔断）—— 拉取/注册抛异常后置位，后续导航直接走 500 兜底，
 * 避免反复请求造成死循环。401 属可重试场景：只清空在途句柄、**不**置位本变量
 * （重新登录后 `resetRouteInitState()` 会一并清空）。
 */
let routeInitError: unknown = null

export function getPendingLoading(): boolean {
  return pendingLoading
}

export function resetPendingLoading(): void {
  pendingLoading = false
}

export function getRouteInitFailed(): boolean {
  return routeInitError !== null
}

/** 重新登录等场景重置初始化状态（在途句柄 + 失败熔断一次性清空） */
export function resetRouteInitState(): void {
  routeInitInFlight = null
  routeInitError = null
}

/**
 * 等待在途初始化结束（无在途则立即返回）。
 *
 * `startRouteInit()` 保证该 Promise **一定会 settle**（内部 try/catch/finally），
 * 因此无需超时兜底；失败结果由守卫的 500 分支统一处理。
 */
async function settleRouteInit(): Promise<void> {
  if (!routeInitInFlight) return

  try {
    await routeInitInFlight
  } catch {
    // 失败已在 startRouteInit 内转换为 routeInitError / 取消导航，此处不重复处理
  }
}

/**
 * 等待动态路由注册就绪（供登录成功后跳转前调用）。
 *
 * 「登录成功但未跳转，需再点一次」的历史成因是守卫用 `next(false)` 静默取消了与
 * 初始化并发的那次导航。现守卫已改为「等待在途初始化完成后用原目标重新导航」，
 * 本函数只需把「等初始化」提前到跳转之前，使 `router.replace` 成为直通导航。
 */
export async function waitForDynamicRoutesReady(): Promise<void> {
  await settleRouteInit()
}

/** 防止 dev/HMR 或异常重复 init 导致多个 beforeEach 叠加（导航副作用与请求会成倍增长） */
let beforeEachGuardRegistered = false

export function setupBeforeEachGuard(router: Router): void {
  if (beforeEachGuardRegistered) {
    if (import.meta.env.DEV) {
      console.warn('[Router] setupBeforeEachGuard 已注册，跳过重复调用')
    }
    return
  }
  beforeEachGuardRegistered = true

  routeRegistry = new RouteRegistry(router)

  router.beforeEach(async (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    try {
      await handleRouteGuard(to, from, next, router)
    } catch (error) {
      console.error('[RouteGuard] 路由守卫处理失败:', error)
      closeLoading()
      next({ name: '500' })
    }
  })
}

function closeLoading(): void {
  if (pendingLoading) {
    nextTick(() => {
      loadingService.hideLoading()
      pendingLoading = false
    })
  }
}

/**
 * 若路由带有 query/params 传入的 title，写入 meta（净化防注入与过长字符串）
 */
function applySafeTitleFromQuery(to: RouteLocationNormalized): void {
  const rawTitle = (to.params.title as string) || (to.query.title as string)
  if (rawTitle && typeof rawTitle === 'string') {
    const safe = rawTitle.replace(/[<>]/g, '').trim().slice(0, 64)
    if (safe) {
      to.meta.title = safe
    }
  }
}

async function handleRouteGuard(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext,
  router: Router
): Promise<void> {
  // 顺序：登录 → 动态路由初始化失败兜底 → 动态路由注册 → 根路径 → 已匹配页 → 404
  const settingStore = useSettingsStore()
  const userStore = useUserStore()

  if (settingStore.showNprogress) {
    NProgress.start()
  }

  // 检查存储是否已失效（storage/index.ts 检测到异常时标记）
  if (checkStorageInvalidated()) {
    console.info('[RouteGuard] 检测到存储已失效，执行登出')
    // 传 { navigate: false } 防止 logout 内部调用 router.push() 造成重复导航，
    // 导航由本守卫通过 next() 统一控制
    await userStore.logout({ navigate: false })
    resetStorageInvalidated()
    next({ name: 'Login', replace: true })
    return
  }

  if (!handleLoginStatus(to, userStore, next)) {
    return
  }

  // 初始化已熔断（拉取/注册失败过）：已有匹配页面就直接渲染，否则走 500 兜底
  if (routeInitError !== null) {
    if (to.matched.length > 0) {
      next()
    } else {
      next({ name: '500', replace: true })
    }
    return
  }

  const menuStore = useMenuStore()
  /** 未注册动态路由，或菜单已被清空（登出延迟 reset 与再登录竞态下可能出现「已注册但 menuList 为空」） */
  const shouldInitRoutes = userStore.isLogin && (!routeRegistry?.isRegistered() || menuStore.menuList.length === 0)

  if (shouldInitRoutes) {
    // 并发导航命中在途初始化：等它结束后用**本次**目标重新导航。
    // 不能静默取消（`next(false)`）—— 那会把登录后的首次导航吞掉，
    // 表现为「登录成功但未跳转，需再点一次」。
    if (routeInitInFlight) {
      await settleRouteInit()
      next(resumeLocation(to))
      return
    }

    // 发起初始化，并把结果交给唯一的落点函数处理
    applyInitOutcome(await startRouteInit(to, router), next)
    return
  }

  if (handleRootPathRedirect(to, next)) {
    return
  }

  if (to.matched.length > 0) {
    applySafeTitleFromQuery(to)
    setWorktab(to)
    setPageTitle(to)
    next()
    return
  }

  next({ name: '404' })
}

/** @returns 是否继续守卫；false 表示已 `next` 跳转 */
function handleLoginStatus(
  to: RouteLocationNormalized,
  userStore: ReturnType<typeof useUserStore>,
  next: NavigationGuardNext
): boolean {
  // 勿把「整条 staticRoutes」当匿名：否则 `/` 重定向到的业务页会被误放行（未登录先进首页）。
  if (userStore.isLogin || isLoginRoute(to) || isAnonymousPublicPath(to.path)) {
    return true
  }

  userStore.resetAllState()

  // 清除菜单缓存：守卫通过 menuList.length 判断是否需要重新注册动态路由。
  // 若不清除，重新登录后守卫误认为路由已就绪而跳过注册，导致首次登录不跳转。
  useMenuStore().resetAllState()

  next({
    name: 'Login',
    query: { redirect: to.fullPath },
  })
  return false
}

/** 登录页（项目里同时存在 `/login` 与 `/auth/login` 等多套入口） */
function isLoginRoute(to: RouteLocationNormalized): boolean {
  return to.path === '/login' || to.path === ROUTE_PATH_LOGIN_ALT || to.name === 'Login'
}

/**
 * 无需登录即可访问的路径（登录页由 isLoginRoute 处理，此处为错误页、重定向等）。
 * 勿将挂载 Layout 的业务路由（如 `/home`、`/dashboard/*`、`/profile`）列入此处。
 */
function isAnonymousPublicPath(path: string): boolean {
  if (path.startsWith('/redirect')) return true
  const allow = new Set(['/401', '/404', '/500', '/403', '/disclaimer'])
  return allow.has(path)
}

/** 将父级绝对路径与相对子 path 拼成完整路径（用于识别如 `/` + `home` → `/home`） */
function resolveStaticChildFullPath(parentFullPath: string, segment: string): string {
  const seg = segment.replace(/^\/+/, '')
  if (!parentFullPath || parentFullPath === '/') {
    return `/${seg}`
  }
  return `${parentFullPath.replace(/\/$/, '')}/${seg}`
}

/**
 * 检查路由是否为静态路由
 */
function isStaticRoute(path: string): boolean {
  const checkRoute = (routes: any[], targetPath: string, parentFullPath = ''): boolean => {
    return routes.some((route) => {
      // 通配 404（pathMatch）不应视为免登录静态页；静态表里可能与 `/404` 同名，按 path 区分。
      if (route.path === '/:pathMatch(.*)*') {
        return false
      }

      const routePath = route.path ?? ''
      const fullPath = routePath.startsWith('/') ? routePath : resolveStaticChildFullPath(parentFullPath, routePath)

      const pattern = fullPath.replace(/:[^/]+/g, '[^/]+').replace(/\*/g, '.*')
      const regex = new RegExp(`^${pattern}$`)

      if (regex.test(targetPath)) {
        return true
      }
      if (route.children && route.children.length > 0) {
        return checkRoute(route.children, targetPath, fullPath)
      }
      return false
    })
  }

  return checkRoute(staticRoutes, path)
}

/**
 * 动态路由仍标记为已注册但侧边菜单已被清空时，先卸下动态路由再拉菜单。
 * 典型场景：`logout` 中 `resetRouterState(500)` 延迟执行，用户在 500ms 内再次登录，
 * 守卫若仅判断 `isRegistered()` 会跳过拉菜单，侧栏空白。
 */
function repairDynamicRoutesIfMenuEmpty(): void {
  if (!routeRegistry?.isRegistered()) return
  const ms = useMenuStore()
  if (ms.menuList.length > 0) return
  routeRegistry.unregister()
  IframeRouteManager.getInstance().clear()
  ms.removeAllDynamicRoutes()
  resetRouteInitState()
}

/** 初始化结果：本模块不再自己导航，由 {@link applyInitOutcome} 统一落点 */
type InitOutcome = { action: 'navigate'; location: RouteLocationRaw } | { action: 'cancel' }

/** 以原目标构造导航位置（保留 query/hash，replace 避免污染历史） */
function resumeLocation(to: RouteLocationNormalized): RouteLocationRaw {
  return { path: to.path, query: to.query, hash: to.hash, replace: true }
}

/** 唯一的 `next()` 落点：避免多处各自「重新导航」互相打断 */
function applyInitOutcome(outcome: InitOutcome, next: NavigationGuardNext): void {
  if (outcome.action === 'cancel') {
    next(false)
    return
  }
  next(outcome.location)
}

/**
 * 启动动态路由初始化（并发导航共享同一在途句柄）。
 *
 * 两个关键顺序：
 * 1. `repairDynamicRoutesIfMenuEmpty()` 必须在建句柄**之前同步**执行 —— 它内部会调
 *    `resetRouteInitState()`，若晚于建句柄就会把刚建的在途句柄清掉，使并发导航重复初始化；
 * 2. `.finally` 在 settle 后清句柄（且只在仍指向自己时清），保证「无在途」与「已结束」一致。
 *
 * `initializeDynamicRoutes()` 内部吞掉所有异常并转为 `InitOutcome`，
 * 因此返回的 Promise **一定会 settle**（等待方无需超时兜底）。
 */
function startRouteInit(to: RouteLocationNormalized, router: Router): Promise<InitOutcome> {
  repairDynamicRoutesIfMenuEmpty()

  const pending = initializeDynamicRoutes(to, router).finally(() => {
    if (routeInitInFlight === pending) {
      routeInitInFlight = null
    }
  })
  routeInitInFlight = pending
  return pending
}

/**
 * 动态路由初始化：拉取用户信息与菜单 → addRoute → 解析本次导航的落点。
 *
 * 顺序即依赖：`fetchUserInfo()` 必须早于 `getMenuList()` —— 后端菜单随用户信息下发，
 * `MenuProcessor.processBackendMenu()` 读的正是它填充的 `userStore.routeList`。
 */
async function initializeDynamicRoutes(to: RouteLocationNormalized, router: Router): Promise<InitOutcome> {
  // 显示 loading（由 afterEach 通过 getPendingLoading/resetPendingLoading 关闭）
  pendingLoading = true
  loadingService.showLoading()

  try {
    // 1. 获取用户信息与菜单 —— 每次都取服务端最新数据。
    // 不能「info 非空就跳过」：info/routeList 会随 store 持久化到 localStorage，
    // 直接复用旧快照会在后端删改/迁移菜单后按陈旧数据注册路由
    // （例：工作流从 module_task 迁到 module_storage 后仍去加载已删除的组件）。
    await fetchUserInfo()

    // 2. 获取菜单数据
    const menuList = await menuProcessor.getMenuList()

    // 3. 验证菜单数据
    if (!menuProcessor.validateMenuList(menuList)) {
      throw new Error('获取菜单列表失败，请重新登录')
    }

    // 4. 注册动态路由
    routeRegistry?.register(menuList)

    // 5. 保存菜单数据到 store（侧栏、工作标签、权限指令的数据源）
    const menuStore = useMenuStore()
    menuStore.setMenuList(menuList)
    menuStore.addRemoveRouteFns(routeRegistry?.getRemoveRouteFns() || [])

    // 6. 保存 iframe 路由 + 验证工作标签页
    IframeRouteManager.getInstance().save()
    useWorktabStore().validateWorktabs(router)

    // 7. 静态路由不依赖菜单权限，初始化后直接恢复目标地址
    if (isStaticRoute(to.path)) {
      return { action: 'navigate', location: resumeLocation(to) }
    }

    // 8. 验证目标路径权限：无权限则回落首页
    const { homePath } = useCommon()
    const { path: validatedPath, hasPermission } = RoutePermissionValidator.validatePath(
      to.path,
      menuList,
      homePath.value || '/'
    )

    if (!hasPermission) {
      closeLoading()
      console.warn(`[RouteGuard] 用户无权限访问路径: ${to.path}，已跳转到首页`)
      return { action: 'navigate', location: { path: validatedPath, replace: true } }
    }

    return { action: 'navigate', location: resumeLocation(to) }
  } catch (error) {
    closeLoading()

    // 401：axios 拦截器已触发退出登录；取消本次导航。
    // 不置熔断位：句柄清空后可由重新登录再次初始化。
    if (isUnauthorizedError(error)) {
      console.error('[RouteGuard] 初始化遇到 401，已取消本次导航（由拦截器登出）')
      return { action: 'cancel' }
    }

    // 其它错误：置熔断位，后续导航直接走 500，避免反复请求造成死循环
    routeInitError = error
    console.error('[RouteGuard] 动态路由注册失败:', error)
    if (isHttpError(error)) {
      console.error(`[RouteGuard] 错误码: ${error.code}, 消息: ${error.message}`)
    }
    return { action: 'navigate', location: { name: '500', replace: true } }
  }
}

/**
 * 获取用户信息与菜单（服务端最新数据）。
 *
 * 必须走 store 的 `getUserInfo()`：它会把响应里的 `menus` 提取出来交给 `setRoute()`，
 * 而 `routeList`／`prems`（注册动态路由与权限指令的数据源）正是在 `setRoute()` 里填充的。
 * 只调 `setUserInfo()` 会遗漏菜单，使 `processBackendMenu()` 拿不到后端菜单。
 */
async function fetchUserInfo(): Promise<void> {
  const userStore = useUserStore()
  await userStore.getUserInfo()
  // 检查并清理工作台标签页（仅当登录用户发生变化时才清空）
  userStore.checkAndClearWorktabs()
}

/**
 * 立即卸下动态路由与菜单缓存（与 {@link resetRouterState} 回调一致，供刷新路由等同步场景）。
 */
export function resetDynamicRoutesSync(): void {
  routeRegistry?.unregister()
  IframeRouteManager.getInstance().clear()

  const menuStore = useMenuStore()
  menuStore.removeAllDynamicRoutes()
  menuStore.setMenuList([])

  resetRouteInitState()
}

/**
 * 延迟重置路由相关状态（登出等场景避免与导航竞态）
 */
export function resetRouterState(delay: number): void {
  setTimeout(() => {
    resetDynamicRoutesSync()
  }, delay)
}

/**
 * 处理根路径重定向到首页
 * @returns true 表示已处理跳转，false 表示无需跳转
 */
function handleRootPathRedirect(to: RouteLocationNormalized, next: NavigationGuardNext): boolean {
  if (to.path !== '/') {
    return false
  }

  const { homePath } = useCommon()
  if (homePath.value && homePath.value !== '/') {
    next({ path: homePath.value, replace: true })
    return true
  }

  return false
}

/**
 * 判断是否为未授权错误（401）
 */
function isUnauthorizedError(error: unknown): boolean {
  return isHttpError(error) && error.code === ApiStatus.unauthorized
}

/** 守卫内菜单路径权限校验（扁平菜单路径集合） */
export class RoutePermissionValidator {
  static hasPermission(targetPath: string, menuList: AppRouteRecord[]): boolean {
    if (targetPath === '/') {
      return true
    }
    return this.matchRoute(targetPath, menuList)
  }

  static buildMenuPathSet(menuList: AppRouteRecord[], pathSet: Set<string> = new Set()): Set<string> {
    if (!Array.isArray(menuList) || menuList.length === 0) {
      return pathSet
    }

    for (const menuItem of menuList) {
      if (!menuItem.path) {
        continue
      }

      const menuPath = menuItem.path.startsWith('/') ? menuItem.path : `/${menuItem.path}`
      pathSet.add(menuPath)

      if (menuItem.children?.length) {
        this.buildMenuPathSet(menuItem.children, pathSet)
      }
    }

    return pathSet
  }

  static checkPathPrefix(targetPath: string, pathSet: Set<string>): boolean {
    for (const menuPath of pathSet) {
      if (targetPath.startsWith(`${menuPath}/`)) {
        return true
      }
    }
    return false
  }

  static matchRoute(targetPath: string, routes: AppRouteRecord[]): boolean {
    if (!Array.isArray(routes) || routes.length === 0) {
      return false
    }

    for (const route of routes) {
      if (!route.path) {
        continue
      }

      const routePath = route.path.startsWith('/') ? route.path : `/${route.path}`

      if (
        routePath === targetPath ||
        this.isDynamicRouteMatch(targetPath, routePath) ||
        targetPath.startsWith(`${routePath}/`)
      ) {
        return true
      }

      if (route.children?.length && this.matchRoute(targetPath, route.children)) {
        return true
      }
    }

    return false
  }

  static isDynamicRouteMatch(targetPath: string, routePath: string): boolean {
    if (!routePath.includes(':')) {
      return false
    }

    const pattern = routePath
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/:([^/]+)/g, '[^/]+')
      .replace(/\\\*/g, '.*')

    return new RegExp(`^${pattern}$`).test(targetPath)
  }

  static validatePath(
    targetPath: string,
    menuList: AppRouteRecord[],
    homePath: string = '/'
  ): { path: string; hasPermission: boolean } {
    const hasPermission = this.hasPermission(targetPath, menuList)

    if (hasPermission) {
      return { path: targetPath, hasPermission: true }
    }

    return { path: homePath, hasPermission: false }
  }
}
