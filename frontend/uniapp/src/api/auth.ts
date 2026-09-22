import { http } from '@/http'
import { sm2 } from 'sm-crypto'

const AUTH_BASE_URL = '/system/auth'

// SM2 公钥缓存
let smPublicKey: string | null = null

/**
 * 从后端获取 SM2 公钥
 */
async function fetchSmPublicKey(): Promise<string | null> {
  if (smPublicKey) return smPublicKey
  try {
    const data: any = await http.Get(`${AUTH_BASE_URL}/sm-public-key`)
    smPublicKey = data?.public_key || null
    return smPublicKey
  } catch {
    return null
  }
}

const AuthAPI = {
  /**
   * 登录
   * - 若后端启用了 SM2 加密，自动获取公钥并加密密码
   * - 若获取公钥失败或未开启，回退为明文密码
   * @param body 登录表单数据
   * @returns 登录结果
   */
  async login(body: LoginFormData): Promise<LoginResult> {
    // 获取 SM2 公钥并加密密码
    const publicKey = await fetchSmPublicKey()
    if (!publicKey) {
      return Promise.reject(new Error('无法获取 SM2 公钥，加密登录不可用'))
    }
    const password = sm2.doEncrypt(body.password, publicKey)

    // 手动构建 URL-encoded 字符串（nativeHttp 不支持自动编码）
    const params = new URLSearchParams()
    params.append('username', body.username)
    params.append('password', password)
    params.append('captcha_key', body.captcha_key || '')
    params.append('captcha', body.captcha || '')
    params.append('remember', String(body.remember))
    params.append('login_type', body.login_type || 'UNIAPP')

    return new Promise((resolve, reject) => {
      uni.request({
        url: `${import.meta.env.VITE_API_BASE_URL}${import.meta.env.VITE_APP_BASE_API}${AUTH_BASE_URL}/login`,
        method: 'POST',
        header: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: params.toString(),
        success: (res: any) => {
          const data = res.data
          if (res.statusCode === 200 && data?.code === 0) {
            resolve(data.data)
          } else {
            reject(new Error(data?.msg || '登录失败'))
          }
        },
        fail: (err) => reject(new Error(err.errMsg || '网络错误')),
      })
    })
  },

  /**
   * 刷新令牌
   * @param body 刷新令牌请求体
   * @returns 新的访问令牌
   */
  refreshToken(body: RefreshToekenBody): Promise<any> {
    return http.Post(`${AUTH_BASE_URL}/token/refresh`, body)
  },

  /**
   * 获取验证码
   * @returns 验证码信息
   */
  getCaptcha(): Promise<any> {
    const ts = new Date().getTime()
    return http.Get(`${AUTH_BASE_URL}/captcha/get?timestamp=${ts}`)
  },

  /**
   * 登出
   * @param body 登出请求体
   * @returns 登出结果
   */
  logout(): Promise<any> {
    return http.Post(`${AUTH_BASE_URL}/logout`)
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
