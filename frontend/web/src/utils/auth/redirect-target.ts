import type { LocationQuery, RouteLocation, RouteLocationRaw, Router } from 'vue-router'

/** 无 `redirect` 参数、或无法解析时的兜底目标 */
export const DEFAULT_REDIRECT_PATH = '/'

/** 剥离嵌套的最大层数（防止畸形 URL 造成死循环） */
const MAX_REDIRECT_DEPTH = 5

/**
 * 解析登录成功后应跳转的目标。
 *
 * `redirect` 可能指向登录页自身：跳转登录页前曾把「当前 URL」（哪怕已经是登录页）再次
 * 塞进 redirect，形成 `/login?redirect=/login?redirect=xxx` 的嵌套。若把它当作目标，
 * 登录成功后会停在登录页（表现为「首次登录不跳转，需再点一次」）；只剥一层则要再点一次
 * 才能跳走。故此处循环剥离所有指向登录页的嵌套。
 *
 * @param router 用于解析路径的路由实例（显式传入以便单测注入内存路由）
 * @param query 当前路由 query，读取其中的 `redirect`
 * @returns 目标位置（含目标自身的 query）；无法解析或全是登录页嵌套时回落 {@link DEFAULT_REDIRECT_PATH}
 */
export function resolveRedirectTarget(router: Router, query: LocationQuery): RouteLocationRaw {
  let raw = (query.redirect as string) || DEFAULT_REDIRECT_PATH

  for (let depth = 0; depth < MAX_REDIRECT_DEPTH; depth++) {
    let resolved: RouteLocation
    try {
      resolved = router.resolve(raw)
    } catch {
      return { path: DEFAULT_REDIRECT_PATH }
    }

    // 非登录页即真实目标（连带目标自身的 query，如 ?tab=1）
    if (resolved.path !== '/login' && resolved.name !== 'Login') {
      return { path: resolved.path, query: resolved.query }
    }

    const nested = resolved.query.redirect
    if (typeof nested !== 'string' || !nested) break
    raw = nested
  }

  return { path: DEFAULT_REDIRECT_PATH }
}
