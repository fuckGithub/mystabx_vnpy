/**
 * legacy 入口模块
 *
 * 从旧 frontend/app 迁移的关键数据封装入口。
 * app-unibest 中需要使用这些旧数据的模块，从这里导入。
 *
 * 包含：
 * - enums/       API 响应码和请求头枚举
 * - constants/   存储键名常量
 * - utils/       存储工具类
 * - theme.json   主题配置
 *
 * 使用示例：
 *   import { ApiCode, ApiHeader } from '@/legacy'
 *   import { Storage } from '@/legacy'
 *   import themeConfig from '@/legacy/theme.json'
 */

// Constants
export {
  APP_ACCESS_TOKEN_KEY,
  APP_MANUAL_THEME_KEY,
  APP_REFRESH_TOKEN_KEY,
  APP_THEME_KEY,
  APP_USER_INFO,
} from './constants/storage.constant'
// Enums
export { ApiCode } from './enums/api-code.enum'

export { ApiHeader } from './enums/api-header.enum'

// Utils
export { Storage } from './utils/storage'
