import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

/**
 * 守卫依赖的边界模块全部替换为「可观测的假实现」，
 * 使 `beforeEach.ts` 的编排逻辑（初始化去重、落点、熔断、降级）被真实执行。
 */
const mocks = vi.hoisted(() => {
  const state = {
    isLogin: true,
    /** menuStore 持有的菜单：守卫据此判断是否需要重新注册动态路由 */
    menuList: [] as any[],
    /** MenuProcessor.getMenuList() 的返回值（后端菜单） */
    backendMenus: [{ path: '/system/user', name: 'User', meta: { title: '用户' } }] as any[],
    /** MenuProcessor.validateMenuList() 的返回值 */
    menuValid: true,
    /** getUserInfo 的行为（可注入延迟/异常） */
    getUserInfo: async (): Promise<void> => {},
    getUserInfoCalls: 0,
    registered: false,
    storageInvalidated: false,
  }
  return {
    state,
    logout: vi.fn(),
    resetUserState: vi.fn(),
    resetMenuState: vi.fn(),
    addRemoveRouteFns: vi.fn(),
    register: vi.fn(),
    unregister: vi.fn(),
    clearIframe: vi.fn(),
    resetStorageInvalidated: vi.fn(),
    hideLoading: vi.fn(),
  }
})

vi.mock('@/hooks/core/useCommon', () => ({ useCommon: () => ({ homePath: { value: '/home' } }) }))

vi.mock('@stores/modules/user.store', () => ({
  useUserStore: () => ({
    get isLogin() {
      return mocks.state.isLogin
    },
    async getUserInfo() {
      mocks.state.getUserInfoCalls += 1
      await mocks.state.getUserInfo()
    },
    async logout(options?: { navigate?: boolean }) {
      mocks.state.isLogin = false
      // 透传参数：守卫以 `{ navigate: false }` 调用，避免 logout 内部再触发导航
      mocks.logout(options)
    },
    resetAllState() {
      mocks.state.isLogin = false
      mocks.resetUserState()
    },
    checkAndClearWorktabs: vi.fn(),
  }),
}))

vi.mock('@stores/modules/menu.store', () => ({
  useMenuStore: () => ({
    get menuList() {
      return mocks.state.menuList
    },
    setMenuList(list: any[]) {
      mocks.state.menuList = list
    },
    removeAllDynamicRoutes() {
      mocks.state.menuList = []
    },
    resetAllState() {
      mocks.state.menuList = []
      mocks.resetMenuState()
    },
    addRemoveRouteFns: mocks.addRemoveRouteFns,
  }),
}))

vi.mock('@stores/modules/setting.store', () => ({ useSettingsStore: () => ({ showNprogress: false }) }))
vi.mock('@stores/modules/worktab.store', () => ({ useWorktabStore: () => ({ validateWorktabs: vi.fn() }) }))

vi.mock('@utils/ui', () => ({
  loadingService: { showLoading: vi.fn(), hideLoading: mocks.hideLoading },
  NProgress: { start: vi.fn(), done: vi.fn() },
}))
vi.mock('@utils/navigation', () => ({ setPageTitle: vi.fn(), setWorktab: vi.fn() }))
vi.mock('@utils/storage', () => ({
  checkStorageInvalidated: () => mocks.state.storageInvalidated,
  // 真实实现会清除失效标志（否则守卫会因标志未清而无限重定向到登录页）
  resetStorageInvalidated: () => {
    mocks.state.storageInvalidated = false
    mocks.resetStorageInvalidated()
  },
}))
vi.mock('@utils/http', () => ({
  ApiStatus: { unauthorized: 401 },
  // 真实实现为 `error is HttpError`（带 code 字段），此处保持同等判据
  isHttpError: (error: any) => !!error && typeof error?.code === 'number',
}))

vi.mock('@/router/dynamicRoutes', () => ({
  RouteRegistry: class {
    isRegistered() {
      return mocks.state.registered
    }
    register() {
      mocks.state.registered = true
      mocks.register()
    }
    unregister() {
      mocks.state.registered = false
      mocks.unregister()
    }
    getRemoveRouteFns() {
      return []
    }
  },
}))

vi.mock('@/router/MenuProcessor', () => ({
  MenuProcessor: class {
    async getMenuList() {
      return mocks.state.backendMenus
    }
    validateMenuList() {
      return mocks.state.menuValid
    }
  },
}))

vi.mock('@/router/staticRoutes', () => ({
  // `/blank` 仅作每个用例的「停车位」：静态路由不会被权限校验重定向，
  // 保证用例起点路径与目标路径不同（vue-router 对冗余导航不执行守卫）
  staticRoutes: [
    { path: '/home', name: 'Home', component: {} },
    { path: '/blank', name: 'Blank', component: {} },
  ],
  ROUTE_PATH_LOGIN_ALT: '/auth/login',
  IframeRouteManager: { getInstance: () => ({ save: vi.fn(), clear: mocks.clearIframe }) },
}))

import { getRouteInitFailed, resetDynamicRoutesSync, setupBeforeEachGuard } from '@/router/beforeEach'

const Stub = defineComponent({ render: () => null })

/** 与守卫交互的真实路由（内存 history）。注意不注册通配 404，否则 unmatched 分支不可达 */
const router: Router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'Root', component: Stub },
    { path: '/home', name: 'Home', component: Stub },
    { path: '/login', name: 'Login', component: Stub },
    { path: '/system/user', name: 'User', component: Stub },
    { path: '/404', name: '404', component: Stub },
    { path: '/500', name: '500', component: Stub },
    { path: '/blank', name: 'Blank', component: Stub },
  ],
})

beforeAll(() => {
  // 守卫模块级有「只注册一次」保护，整个文件共用一个 router
  setupBeforeEachGuard(router)
})

beforeEach(async () => {
  mocks.state.isLogin = true
  mocks.state.menuList = []
  mocks.state.backendMenus = [{ path: '/system/user', name: 'User', meta: { title: '用户' } }]
  mocks.state.menuValid = true
  mocks.state.getUserInfo = async () => {}
  mocks.state.getUserInfoCalls = 0
  mocks.state.registered = false
  mocks.state.storageInvalidated = false

  // 把当前位置挪到「停车位」：vue-router 对「推到当前路径」直接返回冗余导航失败且**不执行守卫**，
  // 会让后续用例看似未生效（历史：用例间位置泄漏导致 4 个用例假失败）。
  // 停车位选静态路由，否则会被菜单权限校验重定向到 /home，与其它用例的目标路径碰撞。
  await router.replace('/blank')

  // 归位后再清一次：上面这次导航自身可能触发初始化
  mocks.state.getUserInfoCalls = 0
  mocks.state.registered = false
  mocks.state.menuList = []

  // 清动态路由 + 菜单缓存 + 初始化熔断位（等价于登出后的状态）
  resetDynamicRoutesSync()
})

/** 让守卫推进到「初始化在途」的状态 */
const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

describe('路由守卫 — 登录后的跳转决策', () => {
  it('未登录：跳登录页并把原地址放进 redirect，不请求用户信息', async () => {
    mocks.state.isLogin = false

    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/system/user')
    expect(mocks.state.getUserInfoCalls).toBe(0)
    expect(mocks.resetUserState).toHaveBeenCalled()
    expect(mocks.resetMenuState).toHaveBeenCalled()
  })

  it('已登录但动态路由未注册：初始化一次并落在原目标', async () => {
    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/system/user')
    expect(mocks.state.getUserInfoCalls).toBe(1)
    expect(mocks.state.registered).toBe(true)
    expect(mocks.addRemoveRouteFns).toHaveBeenCalled()
    expect(mocks.state.menuList.length).toBeGreaterThan(0)
  })

  it('静态路由深链：初始化后停在原地址（不做菜单权限校验）', async () => {
    await router.push('/home')

    expect(router.currentRoute.value.path).toBe('/home')
    expect(mocks.state.getUserInfoCalls).toBe(1)
  })

  it('动态路由已注册且菜单非空：直通，不重复请求用户信息', async () => {
    mocks.state.registered = true
    mocks.state.menuList = [{ path: '/home' }]

    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/system/user')
    expect(mocks.state.getUserInfoCalls).toBe(0)
  })

  it('动态路由仍标记已注册但菜单被清空：卸下后重新注册（登出后 500ms 内再登录的场景）', async () => {
    mocks.state.registered = true
    mocks.state.menuList = []

    await router.push('/system/user')

    expect(mocks.state.getUserInfoCalls).toBe(1)
    expect(router.currentRoute.value.path).toBe('/system/user')
    expect(mocks.register).toHaveBeenCalled()
  })

  it('初始化在途期间的并发导航：不被静默取消，按本次目标重新导航，且只初始化一次', async () => {
    let releaseInit: () => void = () => {}
    mocks.state.getUserInfo = () =>
      new Promise<void>((resolve) => {
        releaseInit = resolve
      })

    const first = router.push('/home')
    await flush() // 让首个导航进入在途初始化
    const second = router.push('/system/user')
    await flush()

    releaseInit()
    // 被抢占的那次导航可能以取消失败结束，这里不关心；关键看第二次导航结果
    const [, secondResult] = await Promise.all([first.catch((e) => e), second.catch((e) => e)])

    expect(secondResult).toBeFalsy() // 未被 next(false) 静默取消
    expect(router.currentRoute.value.path).toBe('/system/user') // 本次目标胜出，不被首个导航覆盖
    expect(mocks.state.getUserInfoCalls).toBe(1) // 并发共享同一次初始化
  })

  it('后端菜单校验不通过：走 500 兜底并熔断，后续导航不再重复请求', async () => {
    mocks.state.menuValid = false

    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/500')
    expect(getRouteInitFailed()).toBe(true)

    const callsAfterFail = mocks.state.getUserInfoCalls
    await router.push('/home')

    expect(mocks.state.getUserInfoCalls).toBe(callsAfterFail) // 熔断：不再重试
    expect(router.currentRoute.value.path).toBe('/home')
  })

  it('初始化遇 401：取消本次导航但不熔断（重登后可再次初始化）', async () => {
    mocks.state.getUserInfo = async () => {
      throw Object.assign(new Error('unauthorized'), { code: 401 })
    }

    await router.push('/system/user').catch((e) => e)

    expect(getRouteInitFailed()).toBe(false)
    expect(mocks.state.registered).toBe(false)

    // 重登后重试成功
    mocks.state.getUserInfo = async () => {}
    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/system/user')
    expect(mocks.state.registered).toBe(true)
  })

  it('无权限访问动态路由：回落首页', async () => {
    mocks.state.backendMenus = [{ path: '/home', name: 'Home' }] // 菜单中没有 /system/user

    await router.push('/system/user')

    expect(router.currentRoute.value.path).toBe('/home')
  })

  it('存储失效：先登出再跳登录页', async () => {
    mocks.state.storageInvalidated = true

    await router.push('/system/user')

    expect(mocks.logout).toHaveBeenCalledWith({ navigate: false })
    expect(mocks.resetStorageInvalidated).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('根路径重定向到 homePath', async () => {
    mocks.state.registered = true
    mocks.state.menuList = [{ path: '/home' }]

    await router.push('/')

    expect(router.currentRoute.value.path).toBe('/home')
  })

  it('已初始化后访问未注册路径：走 404', async () => {
    mocks.state.registered = true
    mocks.state.menuList = [{ path: '/home' }]

    await router.push('/not-exist').catch((e) => e)

    expect(router.currentRoute.value.name).toBe('404')
  })
})
