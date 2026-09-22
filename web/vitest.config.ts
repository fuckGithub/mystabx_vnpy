import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

/**
 * 测试专用配置（独立于 vite.config.ts）。
 *
 * 不复用应用构建配置的原因：
 * - 那里是函数式配置 + `loadEnv` 读取 env 目录，测试不需要；
 * - 那里挂了 Element Plus / UnoCSS / Tailwind / 预构建等重型插件，测试用不到（用例不挂载组件）；
 * - 独立配置使测试启动更快，也不受构建开关影响。
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@views': fileURLToPath(new URL('./src/views', import.meta.url)),
      '@utils': fileURLToPath(new URL('./src/utils', import.meta.url)),
      '@stores': fileURLToPath(new URL('./src/store', import.meta.url)),
      '@styles': fileURLToPath(new URL('./src/styles', import.meta.url)),
      '@icons': fileURLToPath(new URL('./src/assets/images/svg', import.meta.url)),
      '@imgs': fileURLToPath(new URL('./src/assets/images', import.meta.url)),
      '@plugins': fileURLToPath(new URL('./src/plugins', import.meta.url)),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify('test'),
    __APP_INFO__: JSON.stringify({ pkg: {}, buildTimestamp: 0 }),
  },
  test: {
    environment: 'node',
    include: ['src/**/*.spec.ts'],
    clearMocks: true,
  },
})
