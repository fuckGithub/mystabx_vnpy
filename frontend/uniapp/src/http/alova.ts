import type { uniappRequestAdapter } from '@alova/adapter-uniapp'
import type { IResponse } from './types'
import type { IDoubleTokenRes } from '@/api/types/login'
import AdapterUniapp from '@alova/adapter-uniapp'
import { createAlova } from 'alova'
import { createServerTokenAuthentication } from 'alova/client'
import VueHook from 'alova/vue'
import { useTokenStore } from '@/store/token'
import { isDoubleTokenMode } from '@/utils'
import { toLoginPage } from '@/utils/toLoginPage'
import { ContentTypeEnum, ResultEnum, ShowMessage } from './tools/enum'

export interface ConfigMeta {
  /** 是否忽略认证 */
  ignoreAuth?: boolean
  /** 自定义域名 */
  domain?: string
  /** 是否显示 Toast 提示 */
  toast?: boolean
}

// API 路径前缀
const { VITE_SERVER_BASEURL, VITE_APP_BASE_API, VITE_SERVER_BASEURL_SECONDARY } = import.meta.env

// 配置动态Tag
export const API_DOMAINS = {
  DEFAULT: VITE_SERVER_BASEURL + VITE_APP_BASE_API,
  SECONDARY: VITE_SERVER_BASEURL_SECONDARY,
}
// 刷新 token 状态管理
let refreshing = false // 防止重复刷新 token 标识
let taskQueue: any[] = [] // 刷新 token 请求队列

/**
 * Token认证拦截器 https://alova.js.org/zh-CN/tutorial/client/strategy/token-authentication/#%E7%BB%91%E5%AE%9A-token-%E8%AE%A4%E8%AF%81%E6%8B%A6%E6%88%AA%E5%99%A8
 */
const { onAuthRequired, onResponseRefreshToken } = createServerTokenAuthentication<
  typeof VueHook,
  typeof uniappRequestAdapter
>({
  refreshTokenOnError: {
    isExpired: (error) => {
      // token 状态在http状态码401中返回
      return error.response?.status === ResultEnum.Unauthorized
    },
    handler: async (error, method) => {
      console.log('refreshTokenOnError===>xxxx', error, method)
      await onTokenExpired(error, method)
    },
  },
  refreshTokenOnSuccess: {
    isExpired: (response, method) => {
      // return false // 调试时可以注释掉，方便查看刷新 token 的效果
      // token 状态在响应中返回
      return (response as any).data?.code === ResultEnum.Unauthorized
    },
    handler: async (response, method) => {
      console.log('refreshTokenOnSuccess===>xxxx', response, method)
      await onTokenExpired(response, method)
    },
  },
})

/**
 * alova 请求实例
 */
const alovaInstance = createAlova({
  baseURL: API_DOMAINS.DEFAULT,
  ...AdapterUniapp(),
  timeout: 5000,
  statesHook: VueHook,
  cacheFor: {
    GET: null,
  },

  beforeRequest: onAuthRequired((method) => {
    // 设置默认 Content-Type
    method.config.headers = {
      ContentType: ContentTypeEnum.JSON,
      Accept: 'application/json, text/plain, */*',
      ...method.config.headers,
    }

    const { config } = method
    const ignoreAuth = config.meta?.ignoreAuth ?? false
    if (!ignoreAuth) {
      const tokenStore = useTokenStore()
      const token = tokenStore.updateNowTime().validToken
      if (!token) {
        throw new Error('[请求错误]：未登录')
      }
      method.config.headers.Authorization = `Bearer ${token}`
    }
    // console.log('ignoreAuth===>', ignoreAuth, 'method===>', method.config)

    // 处理动态域名
    if (config.meta?.domain) {
      method.baseURL = config.meta.domain
      console.log('当前域名', method.baseURL)
    }
  }),

  responded: onResponseRefreshToken((response, method) => {
    const { config } = method
    const { requestType } = config
    const { statusCode, data: rawData, errMsg } = response as UniNamespace.RequestSuccessCallbackResult

    // 处理特殊请求类型（上传/下载）
    if (requestType === 'upload' || requestType === 'download') {
      return response
    }

    // 处理 HTTP 状态码错误
    if (statusCode !== 200) {
      const errorMessage = ShowMessage(statusCode) || `HTTP请求错误[${statusCode}]`
      console.error('errorMessage===>', errorMessage)
      uni.showToast({
        title: errorMessage,
        icon: 'error',
      })
      throw new Error(`${errorMessage}：${errMsg}`)
    }

    // 处理业务逻辑错误
    const { code, msg: message, data } = rawData as IResponse
    // 0和200当做成功都很普遍，这里直接兼容两者，见 ResultEnum
    if (code !== ResultEnum.Success0 && code !== ResultEnum.Success200) {
      if (config.meta?.toast !== false) {
        uni.showToast({
          title: message,
          icon: 'none',
        })
      }
      throw new Error(`请求错误[${code}]：${message}`)
    }
    // 处理成功响应，返回业务数据
    return data
  }),
})
/**
 * 处理 token 过期情况
 * @param response token 拦截响应
 * @param method   请求方法
 * @returns
 */
async function onTokenExpired(response: any, method: any): Promise<any> {
  const tokenStore = useTokenStore()
  if (!isDoubleTokenMode) {
    // 未启用双token策略，清理用户信息，跳转到登录页
    tokenStore.logout()
    toLoginPage()
    return Promise.reject(response)
  }

  /* -------- 无感刷新 token ----------- */
  const { refreshToken } = (tokenStore.tokenInfo as IDoubleTokenRes) || {}
  // token 失效的，且有刷新 token 的，才放到请求队列里
  if (refreshToken) {
    taskQueue.push(method)
  }

  // 如果有 refreshToken 且未在刷新中，发起刷新 token 请求
  if (refreshToken && !refreshing) {
    refreshing = true
    try {
      // 发起刷新 token 请求（使用 store 的 refreshToken 方法）
      await tokenStore.refreshToken()
      // 刷新 token 成功
      refreshing = false
      nextTick(() => {
        // 关闭其他弹窗
        uni.hideToast()
        uni.showToast({
          title: 'token 刷新成功',
          icon: 'none',
        })
      })
      // 将任务队列的所有任务重新请求
      taskQueue.forEach((method) => method.send())
    } catch (refreshErr) {
      console.error('刷新 token 失败:', refreshErr)
      refreshing = false
      // 刷新 token 失败，跳转到登录页
      nextTick(() => {
        // 关闭其他弹窗
        uni.hideToast()
        uni.showToast({
          title: '登录已过期，请重新登录',
          icon: 'none',
        })
      })
      // 清除用户信息
      await tokenStore.logout()
      // 跳转到登录页
      setTimeout(() => {
        toLoginPage()
      }, 2000)
    } finally {
      // 不管刷新 token 成功与否，都清空任务队列
      taskQueue = []
    }
  }
  return Promise.reject(response)
}

export const http = alovaInstance
