import request from '@utils/http'

const API_PATH = '/system/auth'

/** 第三方 OAuth 登录渠道（与后端 `/system/auth/oauth/{provider}` 一致） */
export type OAuthProvider = 'wechat' | 'qq' | 'github' | 'gitee'

const AuthAPI = {
  /**
   * 登录
   * @param body 登录参数
   * @returns 登录响应
   */
  login(body: LoginFormData) {
    return request<ApiResponse<LoginResult>>({
      url: `${API_PATH}/login`,
      method: 'post',
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      data: body,
    })
  },

  /**
   * 获取SM2公钥（用于登录密码加密）
   * @returns SM2公钥（hex，通常 130 字符含 04 前缀；前端加密须保留 04）
   */
  getSmPublicKey() {
    return request<ApiResponse<SmPublicKeyResult>>({
      url: `${API_PATH}/sm-public-key`,
      method: 'get',
    })
  },

  refreshToken(body: RefreshToekenBody) {
    return request<ApiResponse<LoginResult>>({
      url: `${API_PATH}/token/refresh`,
      method: 'post',
      data: body,
    })
  },

  getCaptcha() {
    return request<ApiResponse<CaptchaInfo>>({
      url: `${API_PATH}/captcha/get`,
      method: 'get',
    })
  },

  /** 登录页可选租户（免登录） */
  listLoginTenants() {
    return request<ApiResponse<LoginTenantOption[]>>({
      url: `${API_PATH}/tenants`,
      method: 'get',
    })
  },

  logout() {
    return request<ApiResponse>({
      url: `${API_PATH}/logout`,
      method: 'post',
    })
  },

  /** 获取免登录用户列表 */
  getAutoLoginUsers() {
    return request<ApiResponse<AutoLoginUser[]>>({
      url: `${API_PATH}/auto-login/users`,
      method: 'get',
    })
  },

  /** 获取免登录Token */
  getAutoLoginToken(userId: number) {
    return request<ApiResponse<AutoLoginToken>>({
      url: `${API_PATH}/auto-login/token`,
      method: 'post',
      params: { user_id: userId },
    })
  },

  /** 免登录 */
  autoLogin(token: string) {
    return request<ApiResponse<LoginResult>>({
      url: `${API_PATH}/auto-login`,
      method: 'post',
      params: { token },
    })
  },
}

export default AuthAPI

/** 登录表单数据 */
export interface LoginFormData {
  username: string
  password: string
  captcha_key: string
  captcha: string
  remember: boolean
  login_type: string
  /** 所选租户 ID */
  tenant_id?: number | null
}

/** 登录页租户选项 */
export interface LoginTenantOption {
  id: number
  name: string
  code: string
}

// 刷新令牌
export interface RefreshToekenBody {
  refresh_token: string
}

/** 登录响应 */
export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** 验证码信息 */
export interface CaptchaInfo {
  enable: boolean
  key: string
  img_base: string
}

/** 免登录用户信息 */
export interface AutoLoginUser {
  id: number
  username: string
  name: string
  avatar: string | null
}

/** 免登录Token响应 */
export interface AutoLoginToken {
  token: string
  user: AutoLoginUser
}

/** SM2公钥响应 */
export interface SmPublicKeyResult {
  public_key: string
}
