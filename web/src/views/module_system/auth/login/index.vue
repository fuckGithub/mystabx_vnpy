<!-- 登录页：vnpy AuthBrandPanel + 表单；无验证码；租户选择 + 多语言 -->
<template>
  <div class="auth-page">
    <AuthBrandPanel />

    <section class="form-panel">
      <div class="auth-toolbar">
        <ElDropdown trigger="click" @command="changeLanguage">
          <button type="button" class="auth-toolbar-btn auth-toolbar-btn--locale" :title="t('login.languageToggle')">
            {{ currentLanguageLabel }}
          </button>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem
                v-for="lang in languageOptions"
                :key="lang.value"
                :command="lang.value"
                :class="{ 'is-selected': locale === lang.value }">
                <span>{{ lang.label }}</span>
              </ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </div>

      <div class="form-wrapper">
        <div class="form-main">
          <div class="form-header">
            <p class="form-eyebrow">{{ panelEyebrow }}</p>
            <div class="form-header-brand">
              <img :src="wordmarkSrc" class="form-header-logo" alt="Stabx" />
              <p class="form-subtitle">{{ panelSubTitle }}</p>
            </div>
          </div>

          <div class="form-body">
            <template v-if="authPanel === 'login'">
              <LoginAccountForm
                ref="accountFormRef"
                :login-form="loginForm"
                :rules="rules"
                :form-key="formKey"
                :loading="loading"
                :tenants="tenants"
                :tenant-loading="tenantLoading"
                @submit="handleSubmit"
                @forget="setAuthPanel('forget')"
                @register="setAuthPanel('register')" />
            </template>

            <LoginRegisterPanel
              v-else-if="authPanel === 'register'"
              ref="registerPanelRef"
              v-model:register-agreement-read="registerAgreementRead"
              :register-form="registerForm"
              :register-rules="registerRules"
              :form-key="formKey"
              :register-loading="registerLoading"
              :user-agreement-href="userAgreementHref"
              @submit="submitRegister"
              @to-login="setAuthPanel('login')" />

            <LoginForgetPanel
              v-else
              ref="forgetPanelRef"
              :forget-form="forgetForm"
              :forget-rules="forgetRules"
              :form-key="formKey"
              :forget-loading="forgetLoading"
              @submit="submitForget"
              @to-login="setAuthPanel('login')" />
          </div>
        </div>

        <div v-if="authPanel === 'login'" class="form-extra-wrap">
          <aside class="info-notice" role="note">
            <p class="info-title">
              <span class="info-title-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <circle cx="12" cy="12" r="9" />
                  <path stroke-linecap="round" d="M12 10v6M12 7h.01" />
                </svg>
              </span>
              <span class="info-title-text">登录后您可以</span>
            </p>
            <ul class="info-list">
              <li v-for="(line, index) in infoLines" :key="index">
                {{ line.before }}<strong>{{ line.highlight }}</strong>{{ line.after }}
              </li>
            </ul>
          </aside>
        </div>

        <div class="form-bottom">
          <p class="legal">
            登录即表示您已阅读并了解
            <RouterLink to="/disclaimer" class="login-link">免责声明</RouterLink>。 本项目基于 vn.py，不构成投资建议。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import AuthAPI, { type LoginFormData, type LoginTenantOption } from '@/api/module_system/auth'
import wordmarkSrc from '@/assets/brand/logo-topbar.png'
import AuthBrandPanel from '@/components/auth/AuthBrandPanel.vue'
import { LanguageEnum } from '@/enums/appEnum'
import { languageOptions } from '@/locales'
import UserAPI, { type ForgetPasswordForm, type RegisterForm } from '@/api/module_system/user'
import { waitForDynamicRoutesReady } from '@/router/beforeEach'
import { useAppStore } from '@stores/modules/app.store'
import { useConfigStore } from '@stores/modules/config.store'
import { useSettingsStore } from '@stores/modules/setting.store'
import { useUserStore } from '@stores/modules/user.store'
import { resolveRedirectTarget } from '@utils/auth/redirect-target'
import { Auth } from '@utils/auth'
import { ElMessage, ElNotification, type FormRules } from 'element-plus'
import type { LocationQuery } from 'vue-router'
import LoginAccountForm from './components/LoginAccountForm.vue'
import LoginForgetPanel from './components/LoginForgetPanel.vue'
import LoginRegisterPanel from './components/LoginRegisterPanel.vue'

defineOptions({ name: 'Login' })

type AuthPanel = 'login' | 'register' | 'forget'

const configStore = useConfigStore()
const settingStore = useSettingsStore()
const appStore = useAppStore()
const userStore = useUserStore()
const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()

const authPanel = ref<AuthPanel>('login')

const panelEyebrow = computed(() => {
  if (authPanel.value === 'register') return t('login.reg')
  if (authPanel.value === 'forget') return t('login.resetPassword')
  return '欢迎回来！'
})

const panelSubTitle = computed(() => {
  if (authPanel.value === 'register') return t('register.subTitle')
  if (authPanel.value === 'forget') return t('forgetPassword.subTitle')
  return '登录您的账户，进入 Stabx 交易台'
})

const currentLanguageLabel = computed(
  () => languageOptions.find((item) => item.value === locale.value)?.label || '简体中文'
)

function changeLanguage(lang: LanguageEnum) {
  if (locale.value === lang) return
  locale.value = lang
  userStore.setLanguage(lang)
}

const infoLines = [
  { before: '查看', highlight: '实时行情', after: '，掌握合约盘口与关键价格' },
  { before: '处理', highlight: '下单与撤单', after: '，推动交易高效闭环' },
  { before: '管理', highlight: '资金与持仓', after: '，按账户安全访问所需信息' },
  { before: '追溯', highlight: '成交与操作记录', after: '，满足风控与合规管理要求' },
]

const userAgreementHref = computed(() => configStore.configData?.sys_web_clause?.config_value || '#')

function setAuthPanel(panel: AuthPanel) {
  authPanel.value = panel
  nextTick(() => {
    accountFormRef.value?.clearValidate?.()
    registerPanelRef.value?.clearValidate?.()
    forgetPanelRef.value?.clearValidate?.()
  })
}

async function tryConsumeOAuthCallback() {
  const q = route.query
  const oauthError = q.oauth_error as string | undefined
  const access = q.access_token as string | undefined
  const refresh = q.refresh_token as string | undefined

  if (!oauthError && !(access && refresh)) return

  const rest: Record<string, unknown> = { ...q }
  delete rest.oauth_error
  delete rest.access_token
  delete rest.refresh_token
  delete rest.token_type

  if (oauthError) {
    ElMessage.error(decodeURIComponent(oauthError))
    await router.replace({ path: route.path, query: rest as LocationQuery })
    return
  }

  if (access && refresh) {
    try {
      Auth.setTokens(access, refresh, true)
      userStore.setToken(access, refresh)
      userStore.setLoginStatus(true)
      ElNotification({
        title: t('login.oauthNoticeTitle'),
        message: t('login.oauthLoginSuccess'),
        type: 'success',
      })
      await router.replace(resolveRedirectTarget(router, rest as LocationQuery))
      if (settingStore.showGuide) {
        appStore.showGuide(true)
      }
    } catch (error) {
      console.error('[Login] OAuth callback:', error)
      ElMessage.error(t('login.oauthLoginFailed'))
      await router.replace({ path: route.path, query: rest as LocationQuery })
    }
  }
}

const formKey = ref(0)

watch(locale, () => {
  formKey.value++
})

const accountFormRef = ref<InstanceType<typeof LoginAccountForm> | null>(null)
const registerPanelRef = ref<InstanceType<typeof LoginRegisterPanel> | null>(null)
const forgetPanelRef = ref<InstanceType<typeof LoginForgetPanel> | null>(null)

const loading = ref(false)
const registerLoading = ref(false)
const forgetLoading = ref(false)
const tenantLoading = ref(false)
const tenants = ref<LoginTenantOption[]>([{ id: 1, name: '系统租户', code: 'system' }])

const registerAgreementRead = ref(false)

const registerForm = reactive<RegisterForm>({
  username: '',
  password: '',
  confirmPassword: '',
})

const forgetForm = reactive<ForgetPasswordForm>({
  username: '',
  new_password: '',
  confirmPassword: '',
})

const validateRegisterPassword = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (!value) {
    callback(new Error(t('login.message.password.required')))
    return
  }
  if (registerForm.confirmPassword) {
    registerPanelRef.value?.validateField?.('confirmPassword')
  }
  callback()
}

const validateRegisterConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (!value) {
    callback(new Error(t('login.message.password.required')))
    return
  }
  if (value !== registerForm.password) {
    callback(new Error(t('login.message.password.inconformity')))
    return
  }
  callback()
}

const registerRules = computed<FormRules<RegisterForm>>(() => ({
  username: [{ required: true, message: t('login.message.username.required'), trigger: 'blur' }],
  password: [
    { required: true, validator: validateRegisterPassword, trigger: 'blur' },
    { min: 6, message: t('login.message.password.min'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('login.message.password.required'), trigger: 'blur' },
    { min: 6, message: t('login.message.password.min'), trigger: 'blur' },
    { validator: validateRegisterConfirm, trigger: 'blur' },
  ],
}))

const validateForgetConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (!value) {
    callback(new Error(t('login.message.password.required')))
    return
  }
  if (value !== forgetForm.new_password) {
    callback(new Error(t('login.message.password.inconformity')))
    return
  }
  callback()
}

const forgetRules = computed<FormRules<ForgetPasswordForm>>(() => ({
  username: [{ required: true, message: t('login.message.username.required'), trigger: 'blur' }],
  new_password: [
    { required: true, message: t('login.message.password.required'), trigger: 'blur' },
    { min: 6, message: t('login.message.password.min'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('login.message.password.required'), trigger: 'blur' },
    { min: 6, message: t('login.message.password.min'), trigger: 'blur' },
    { validator: validateForgetConfirm, trigger: 'blur' },
  ],
}))

const loginForm = reactive<LoginFormData>({
  username: 'super',
  password: '',
  captcha: '',
  captcha_key: '',
  remember: true,
  login_type: 'PC',
  tenant_id: 1,
})

const rules = computed<FormRules>(() => ({
  tenant_id: [
    {
      required: true,
      trigger: 'change',
      message: t('login.message.tenant.required'),
    },
  ],
  username: [
    {
      required: true,
      trigger: 'blur',
      message: t('login.message.username.required'),
    },
  ],
  password: [
    {
      required: true,
      trigger: 'blur',
      message: t('login.message.password.required'),
    },
    {
      min: 6,
      message: t('login.message.password.min'),
      trigger: 'blur',
    },
  ],
}))

async function loadTenants() {
  try {
    tenantLoading.value = true
    const response = await AuthAPI.listLoginTenants()
    const list = response.data.data || []
    if (list.length) {
      tenants.value = list
      const ids = list.map((item) => item.id)
      if (!ids.includes(loginForm.tenant_id as number)) {
        loginForm.tenant_id = list[0].id
      }
    }
  } catch (error) {
    console.debug('[Login] load tenants failed, fallback to system tenant:', error)
  } finally {
    tenantLoading.value = false
  }
}

onMounted(async () => {
  await configStore.getConfig()
  await tryConsumeOAuthCallback()
  await loadTenants()
})

const handleSubmit = async () => {
  if (!accountFormRef.value) return

  try {
    await accountFormRef.value.validate?.()
  } catch {
    ElMessage.warning('请完善登录信息（用户名与密码）')
    return
  }

  loading.value = true
  try {
    await userStore.login(loginForm)

    await waitForDynamicRoutesReady()
    const target = resolveRedirectTarget(router, route.query)
    await router.replace(target)

    if (settingStore.showGuide) {
      appStore.showGuide(true)
    }
  } catch (error) {
    const msg =
      (error as any)?.data?.msg ||
      (error as any)?.message ||
      t('login.message.password.required')
    ElMessage.error(String(msg))
    console.debug('[Login] login failed:', msg)
  } finally {
    loading.value = false
  }
}

async function submitRegister() {
  if (!registerAgreementRead.value) {
    ElMessage.warning(t('login.message.agree.required'))
    return
  }
  if (!registerPanelRef.value) return
  try {
    await registerPanelRef.value.validate?.()
    registerLoading.value = true
    await UserAPI.registerUser(registerForm)
    loginForm.username = registerForm.username
    loginForm.password = registerForm.password
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerAgreementRead.value = false
    setAuthPanel('login')
  } catch (error) {
    console.error('[Login] register:', error)
  } finally {
    registerLoading.value = false
  }
}

async function submitForget() {
  if (!forgetPanelRef.value) return
  try {
    await forgetPanelRef.value.validate?.()
    forgetLoading.value = true
    await UserAPI.forgetPassword(forgetForm)
    loginForm.username = forgetForm.username
    loginForm.password = forgetForm.new_password
    forgetForm.username = ''
    forgetForm.new_password = ''
    forgetForm.confirmPassword = ''
    setAuthPanel('login')
  } catch (error) {
    console.error('[Login] forget password:', error)
  } finally {
    forgetLoading.value = false
  }
}
</script>

<style src="@/styles/auth-page.css"></style>
