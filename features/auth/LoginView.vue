<template>
  <div class="auth-page">
    <AuthBrandPanel />

    <section class="form-panel">
      <div class="form-wrapper">
        <div class="form-main">
          <div class="form-header">
            <p class="form-eyebrow">欢迎回来！</p>
            <div class="form-header-brand">
              <img :src="wordmarkSrc" class="form-header-logo" alt="Stabx" />
              <p class="form-subtitle">登录您的账户，进入 Stabx 交易台</p>
            </div>
          </div>

          <div class="form-body">
            <el-form
              size="large"
              class="login-content-form"
              ref="loginFormRef"
              :rules="loginRules"
              :model="form"
              @keyup.enter="onSubmit"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="form.username"
                  placeholder="请输入用户名"
                  clearable
                  autocomplete="username"
                  class="login-input login-input--auth"
                >
                  <template #prefix>
                    <span class="login-field-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 14a7 7 0 0 0-7 7h14a7 7 0 0 0-7-7Z" />
                      </svg>
                    </span>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  :type="showPassword ? 'text' : 'password'"
                  v-model="form.password"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  class="login-input login-input--auth"
                >
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
                      @click="showPassword = !showPassword"
                    >
                      <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.58 10.58A2 2 0 0 0 12 14c1.38 0 2.5-1.12 2.5-2.5 0-.42-.1-.82-.29-1.17" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9.88 5.09A10.94 10.94 0 0 1 12 5c5.52 0 10 4.5 10 7s-1.02 2.28-2.62 3.72" />
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6.61 6.61C4.39 8.09 3 10.2 2 12c1.5 2.5 5.5 7 10 7 1.05 0 2.06-.2 3-.57" />
                      </svg>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item class="login-submit-item">
                <el-button type="primary" class="login-btn login-btn--auth w-full" :loading="loading" @click="onSubmit">
                  <span>登 录</span>
                </el-button>
              </el-form-item>
            </el-form>

            <p class="disclaimer-entry">
              <RouterLink :to="{ name: 'disclaimer' }" class="disclaimer-entry-link">免责声明</RouterLink>
              <span class="disclaimer-entry-hint">交易有风险，软件不提供投资建议</span>
            </p>
          </div>
        </div>

        <div class="form-extra-wrap">
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
            <RouterLink :to="{ name: 'disclaimer' }" class="login-link">免责声明</RouterLink>。
            本项目基于 vn.py，不构成投资建议。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage } from "element-plus";
import AuthBrandPanel from "@/components/auth/AuthBrandPanel.vue";
import { useAuthStore } from "@/stores";
import wordmarkSrc from "@/assets/brand/logo-topbar.png";

const auth = useAuthStore();
const router = useRouter();
const loginFormRef = ref<FormInstance>();
const loading = ref(false);
const showPassword = ref(false);

const form = reactive({
  username: "admin",
  password: "",
});

const loginRules: FormRules = {
  username: [{ required: true, trigger: "blur", message: "请输入用户名" }],
  password: [{ required: true, trigger: "blur", message: "请输入密码" }],
};

const infoLines = [
  { before: "查看", highlight: "实时行情", after: "，掌握合约盘口与关键价格" },
  { before: "处理", highlight: "下单与撤单", after: "，推动交易高效闭环" },
  { before: "管理", highlight: "资金与持仓", after: "，按账户安全访问所需信息" },
  { before: "追溯", highlight: "成交与操作记录", after: "，满足风控与合规管理要求" },
];

async function onSubmit() {
  const valid = await loginFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await auth.login(form.username, form.password);
    ElMessage.success("欢迎回来！");
    await router.push("/workbench");
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>
