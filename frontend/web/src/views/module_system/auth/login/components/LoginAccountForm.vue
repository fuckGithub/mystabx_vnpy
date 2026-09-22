<!-- 账号密码登录（vnpy 视觉；保留算术验证码，无滑动校验） -->
<template>
  <div>
    <ElForm
      ref="formRef"
      :model="loginForm"
      :rules="rules"
      :key="formKey"
      size="large"
      class="login-content-form"
      :validate-on-rule-change="false"
      @keyup.enter="$emit('submit')">
      <ElFormItem prop="username">
        <ElInput
          v-model.trim="loginForm.username"
          class="login-input login-input--auth"
          clearable
          autocomplete="username"
          :placeholder="$t('login.placeholder.username')">
          <template #prefix>
            <span class="login-field-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 14a7 7 0 0 0-7 7h14a7 7 0 0 0-7-7Z" />
              </svg>
            </span>
          </template>
        </ElInput>
      </ElFormItem>

      <ElTooltip :visible="isCapsLock" :content="$t('login.capsLock')" placement="right">
        <ElFormItem prop="password">
          <ElInput
            v-model.trim="loginForm.password"
            class="login-input login-input--auth"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            clearable
            @keyup="checkCapsLock"
            @keyup.enter="$emit('submit')">
            <template #prefix>
              <span class="login-field-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17 11V8a5 5 0 0 0-10 0v3" />
                  <rect x="5" y="11" width="14" height="10" rx="2" />
                  <circle cx="12" cy="16" r="1.25" fill="currentColor" stroke="none" />
                </svg>
              </span>
            </template>
            <template #suffix>
              <button
                type="button"
                class="login-toggle-pwd"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword">
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18" />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M10.58 10.58A2 2 0 0 0 12 14c1.38 0 2.5-1.12 2.5-2.5 0-.42-.1-.82-.29-1.17" />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9.88 5.09A10.94 10.94 0 0 1 12 5c5.52 0 10 4.5 10 7s-1.02 2.28-2.62 3.72" />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M6.61 6.61C4.39 8.09 3 10.2 2 12c1.5 2.5 5.5 7 10 7 1.05 0 2.06-.2 3-.57" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </template>
          </ElInput>
        </ElFormItem>
      </ElTooltip>

      <ElFormItem v-if="captchaState.enable" prop="captcha" class="login-captcha-row">
        <div class="flex w-full items-center gap-3">
          <ElInput
            v-model.trim="loginForm.captcha"
            class="login-input login-input--auth login-input--captcha flex-1"
            clearable
            :placeholder="$t('login.captchaCode')"
            @keyup.enter="$emit('submit')">
            <template #prefix>
              <span class="login-field-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 3l7 4v5c0 5-3 8-7 9-4-1-7-4-7-9V7l7-4Z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.5 12l1.8 1.8L15 10" />
                </svg>
              </span>
            </template>
          </ElInput>
          <div
            class="login-captcha-img flex h-12 w-[120px] shrink-0 cursor-pointer items-center justify-center overflow-hidden"
            role="button"
            :title="$t('login.captchaClickHint')"
            @click="$emit('getCaptcha')">
            <ElIcon v-if="codeLoading" class="is-loading" :size="20">
              <Loading />
            </ElIcon>
            <ElImage
              v-else-if="captchaState.img_base"
              class="h-full w-full object-cover"
              fit="cover"
              :src="captchaState.img_base" />
            <ElText v-else type="info" size="small">
              {{ $t('login.captchaClickHint') }}
            </ElText>
          </div>
        </div>
      </ElFormItem>

      <div class="login-options-row flex-cb mb-1 text-sm">
        <ElCheckbox v-model="loginForm.remember" class="login-remember">
          {{ $t('login.rememberPwd') }}
        </ElCheckbox>
        <ElLink type="primary" underline="never" class="inline-flex items-center text-sm" @click="$emit('forget')">
          {{ $t('login.forgetPwd') }}
        </ElLink>
      </div>

      <ElFormItem class="login-submit-item">
        <ElButton
          class="login-btn login-btn--auth w-full"
          type="primary"
          :loading="loading"
          @click="$emit('submit')">
          <span>{{ $t('login.btnText') }}</span>
        </ElButton>
      </ElFormItem>
    </ElForm>

    <p class="disclaimer-entry">
      <RouterLink to="/disclaimer" class="disclaimer-entry-link">免责声明</RouterLink>
      <span class="disclaimer-entry-hint">交易有风险，软件不提供投资建议</span>
    </p>

    <p class="login-alt-links">
      <a class="login-alt-links__item" href="javascript:;" @click.prevent="$emit('register')">
        {{ $t('login.register') }}
      </a>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { CaptchaInfo, LoginFormData } from '@/api/module_system/auth'
import { Loading } from '@element-plus/icons-vue'
import type { FormRules } from 'element-plus'

defineProps<{
  loginForm: LoginFormData
  rules: FormRules
  captchaState: CaptchaInfo
  codeLoading: boolean
  formKey: number | string
  loading: boolean
}>()

defineEmits<{
  submit: []
  getCaptcha: []
  forget: []
  register: []
}>()

const formRef = ref()
const isCapsLock = ref(false)
const showPassword = ref(false)

function checkCapsLock(event: KeyboardEvent) {
  if (event instanceof KeyboardEvent) {
    isCapsLock.value = event.getModifierState('CapsLock')
  }
}

defineExpose({
  validate: () => formRef.value?.validate?.(),
  clearValidate: () => formRef.value?.clearValidate?.(),
})
</script>
