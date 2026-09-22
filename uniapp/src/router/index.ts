/**
 * 路由导航模块
 * 导航拦截逻辑在 router/interceptor.ts 中由 uni.addInterceptor 实现
 */

export const router = {
  /**
   * 替换当前页面（关闭所有页面重新开始）
   */
  replaceAll(options: { name: string } | { path: string }) {
    const pathMap: Record<string, string> = {
      login: '/pages/login/index',
    }
    const path = 'path' in options ? options.path : pathMap[options.name]
    if (path) {
      uni.reLaunch({ url: path })
    }
  },
}

export default router
