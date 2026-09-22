<!-- 账号密码登录（vnpy 视觉；无滑动/算术验证码；含租户选择） -->
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
      <ElFormItem prop="tenant_id">
        <ElSelect
          v-model="loginForm.tenant_id"
          class="login-input login-input--auth login-tenant-select w-full"
          popper-class="login-tenant-popper"
          placement="bottom-start"
          :teleported="true"
          :fit-input-width="true"
          :placeholder="tenantPlaceholder"
          :loading="tenantLoading">
          <template #prefix>
            <span class="login-field-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 21V7l6-4 6 4v14" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 21v-6h6v6" />
              </svg>
            </span>
          </template>
          <ElOption
            v-for="item in tenants"
            :key="item.id"
            :label="`${item.name}（${item.code}）`"
            :value="item.id">
            <div class="login-tenant-option">
              <span class="login-tenant-option__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 21h18" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 21V7l6-4 6 4v14" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 21v-6h6v6" />
                </svg>
              </span>
              <span class="login-tenant-option__text">
                <span class="login-tenant-option__name">{{ item.name }}</span>
                <span class="login-tenant-option__code">{{ item.code }}</span>
              </span>
            </div>
          </ElOption>
        </ElSelect>
      </ElFormItem>

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
import type { LoginFormData, LoginTenantOption } from '@/api/module_system/auth'
import type { FormRules } from 'element-plus'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps<{
  loginForm: LoginFormData
  rules: FormRules
  formKey: number | string
  loading: boolean
  tenants: LoginTenantOption[]
  tenantLoading: boolean
}>()

defineEmits<{
  submit: []
  forget: []
  register: []
}>()

const { t } = useI18n()
const formRef = ref()
const isCapsLock = ref(false)
const showPassword = ref(false)

const tenantPlaceholder = computed(() => t('login.placeholder.tenant'))

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
