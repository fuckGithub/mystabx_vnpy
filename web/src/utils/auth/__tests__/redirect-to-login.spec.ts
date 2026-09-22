import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  router: {
    currentRoute: { value: { path: '/home', fullPath: '/home' } },
    push: vi.fn(),
  },
  resetUserState: vi.fn(),
  resetMenuState: vi.fn(),
  notify: vi.fn(),
  error: vi.fn(),
}))

vi.mock('@/router', () => ({ router: mocks.router }))
vi.mock('@stores/modules/user.store', () => ({ useUserStore: () => ({ resetAllState: mocks.resetUserState }) }))
vi.mock('@stores/modules/menu.store', () => ({ useMenuStore: () => ({ resetAllState: mocks.resetMenuState }) }))
vi.mock('element-plus', () => ({ ElNotification: mocks.notify, ElMessage: { error: mocks.error } }))

import { redirectToLogin } from '../index'

describe('redirectToLogin — 认证失效跳转登录页', () => {
  beforeEach(() => {
    mocks.router.push.mockClear()
    mocks.router.currentRoute.value = { path: '/home', fullPath: '/home' }
  })

  it('非登录页：跳转登录页并把当前地址编码进 redirect', async () => {
    mocks.router.currentRoute.value = { path: '/system/user', fullPath: '/system/user?tab=1' }

    await redirectToLogin('登录已失效，请重新登录')

    expect(mocks.router.push).toHaveBeenCalledTimes(1)
    expect(mocks.router.push).toHaveBeenCalledWith(`/login?redirect=${encodeURIComponent('/system/user?tab=1')}`)
  })

  it('已在登录页：不再跳转，避免 redirect 自我嵌套', async () => {
    // 否则会生成 /login?redirect=/login?redirect=xxx，登录成功后被送回登录页
    mocks.router.currentRoute.value = { path: '/login', fullPath: '/login?redirect=/system/user' }

    await redirectToLogin()

    expect(mocks.router.push).not.toHaveBeenCalled()
  })

  it('清空用户与菜单状态，避免重新登录后守卫跳过动态路由注册', async () => {
    await redirectToLogin()

    expect(mocks.resetUserState).toHaveBeenCalledTimes(1)
    expect(mocks.resetMenuState).toHaveBeenCalledTimes(1)
  })

  it('并发调用只跳转一次', async () => {
    await Promise.all([redirectToLogin(), redirectToLogin(), redirectToLogin()])

    expect(mocks.router.push).toHaveBeenCalledTimes(1)
    expect(mocks.notify).toHaveBeenCalledTimes(1)
  })

  it('前一次跳转结束后可再次触发（句柄在 finally 中释放）', async () => {
    await redirectToLogin()
    mocks.router.currentRoute.value = { path: '/platform/dict', fullPath: '/platform/dict' }
    await redirectToLogin()

    expect(mocks.router.push).toHaveBeenCalledTimes(2)
    expect(mocks.router.push).toHaveBeenLastCalledWith(`/login?redirect=${encodeURIComponent('/platform/dict')}`)
  })
})
