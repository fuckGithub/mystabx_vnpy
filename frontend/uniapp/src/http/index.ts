// 导出类型
import type { CustomRequestOptions, IResponse } from './types'
// 使用原生 http 适配器（避免 alova 在 H5 下的兼容问题）
import { http as nativeHttp } from './adapters/http'

// 导出默认请求实例
export const http = nativeHttp

// 导出所有类型
export type { CustomRequestOptions, IResponse }

// 导出请求适配器，允许手动选择使用哪种请求方式
export { nativeHttp }
