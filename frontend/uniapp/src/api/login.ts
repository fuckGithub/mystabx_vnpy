import type { IAuthLoginRes, IUserInfoRes } from './types/login'
import { http } from '@/http/http'
import { ContentTypeEnum } from '@/http/tools/enum'

// 后端 API 路径（前缀由 alova / interceptor 统一拼接）
const AUTH = '/system/auth'
const USER = '/system/user/current'

// ============================================================
// 认证 API
// ============================================================

export interface ILoginForm {
  username: string
  password: string
}

export interface ICaptchaInfo {
  enable: boolean
  key: string
  img_base: string
}

/**
 * 获取验证码
 */
export function getCode() {
  return http.get<ICaptchaInfo>(`${AUTH}/code`)
}

/**
 * 登录：后端 /system/auth/login 使用 OAuth2 Password Flow（form-urlencoded）
 */
export async function login(loginForm: ILoginForm): Promise<IAuthLoginRes> {
  const params = new URLSearchParams()
  params.append('username', loginForm.username)
  params.append('password', loginForm.password)
  params.append('captcha_key', '')
  params.append('captcha_code', '')

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${AUTH}/login`,
      method: 'POST',
      header: { 'Content-Type': ContentTypeEnum.FORM_URLENCODED },
      data: params.toString(),
      success: (res) => {
        const resp = res.data as { code: number; data: { access_token: string; refresh_token: string } }
        if (resp.code === 0) {
          resolve({
            accessToken: resp.data.access_token,
            refreshToken: resp.data.refresh_token,
            accessExpiresIn: 7200,
            refreshExpiresIn: 86400,
          })
        } else reject(new Error((res.data as any).msg || '登录失败'))
      },
      fail: reject,
    })
  })
}

export async function getUserInfo(): Promise<IUserInfoRes> {
  const res = await http.get<{
    id: number
    username: string
    name: string
    avatar?: string
    is_superuser: boolean
    status: string
  }>(`${USER}/info`)
  return {
    userId: res.id,
    username: res.username,
    nickname: res.name,
    avatar: res.avatar || '/static/images/default-avatar.png',
    is_superuser: res.is_superuser,
    status: res.status,
  }
}

export function logout() {
  return http.post(`${AUTH}/logout`)
}

// ===== 兼容 unibest store 的额外导出 =====
/** 刷新 token */
export async function refreshToken(_refreshTokenVal: string): Promise<IAuthLoginRes> {
  return {
    accessToken: '',
    refreshToken: _refreshTokenVal,
    accessExpiresIn: 0,
    refreshExpiresIn: 0,
  }
}
export async function wxLogin(_data: { code: string }): Promise<IAuthLoginRes> {
  throw new Error('微信登录未实现')
}
export function getWxCode(): Promise<any> {
  return Promise.reject(new Error('微信登录未实现'))
}
