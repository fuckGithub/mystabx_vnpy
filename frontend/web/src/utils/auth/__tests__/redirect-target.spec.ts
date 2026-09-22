import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { DEFAULT_REDIRECT_PATH, resolveRedirectTarget } from '../redirect-target'

/** 路由只用于解析，不需要真实渲染 */
const Stub = defineComponent({ render: () => null })

function createTestRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Root', component: Stub },
      { path: '/home', name: 'Home', component: Stub },
      { path: '/login', name: 'Login', component: Stub },
      { path: '/auth/login', name: 'LoginAlt', component: Stub },
      { path: '/system/user', name: 'User', component: Stub },
      { path: '/platform/dict', name: 'Dict', component: Stub },
    ],
  })
}

describe('resolveRedirectTarget — 登录后跳转目标', () => {
  const router = createTestRouter()

  it('无 redirect 参数时回落默认路径', () => {
    expect(resolveRedirectTarget(router, {})).toEqual({ path: DEFAULT_REDIRECT_PATH, query: {} })
  })

  it('redirect 为空字符串时回落默认路径', () => {
    expect(resolveRedirectTarget(router, { redirect: '' })).toEqual({ path: DEFAULT_REDIRECT_PATH, query: {} })
  })

  it('扁平 redirect：直接返回目标路径', () => {
    expect(resolveRedirectTarget(router, { redirect: '/system/user' })).toEqual({ path: '/system/user', query: {} })
  })

  it('保留目标自身的 query', () => {
    expect(resolveRedirectTarget(router, { redirect: '/system/user?tab=1&q=abc' })).toEqual({
      path: '/system/user',
      query: { tab: '1', q: 'abc' },
    })
  })

  it('剥离一层指向登录页的嵌套（首次登录不跳转的根因）', () => {
    // 旧行为：把 /login?redirect=/system/user 当作目标 → 登录成功后被送回登录页
    const target = resolveRedirectTarget(router, { redirect: '/login?redirect=/system/user' })
    expect(target).toEqual({ path: '/system/user', query: {} })
  })

  it('剥离多层嵌套', () => {
    const target = resolveRedirectTarget(router, {
      redirect: '/login?redirect=/login?redirect=/platform/dict',
    })
    expect(target).toEqual({ path: '/platform/dict', query: {} })
  })

  it('嵌套目标自身的 query 不被外层覆盖', () => {
    const target = resolveRedirectTarget(router, {
      redirect: '/login?redirect=/system/user?tab=2',
    })
    expect(target).toEqual({ path: '/system/user', query: { tab: '2' } })
  })

  it('全是登录页嵌套（超过上限）时回落默认路径，避免死循环', () => {
    let nested = '/home'
    for (let i = 0; i < 10; i++) {
      nested = `/login?redirect=${encodeURIComponent(nested)}`
    }
    // 10 层嵌套超过 MAX_REDIRECT_DEPTH，无法剥到真实目标 → 兜底而不是停在登录页
    expect(resolveRedirectTarget(router, { redirect: nested })).toEqual({ path: DEFAULT_REDIRECT_PATH })
  })

  it('登录页自身（无嵌套）时回落默认路径', () => {
    expect(resolveRedirectTarget(router, { redirect: '/login' })).toEqual({ path: DEFAULT_REDIRECT_PATH })
  })

  it('redirect 不是字符串时回落默认路径', () => {
    expect(resolveRedirectTarget(router, { redirect: ['/system/user'] })).toEqual({
      path: DEFAULT_REDIRECT_PATH,
      query: {},
    })
  })

  it('router.resolve 抛异常时回落默认路径（畸形 URL 防御）', () => {
    const throwingRouter = {
      resolve() {
        throw new Error('boom')
      },
    } as unknown as Router
    expect(resolveRedirectTarget(throwingRouter, { redirect: '/system/user' })).toEqual({
      path: DEFAULT_REDIRECT_PATH,
    })
  })
})
