<template>
  <div class="wrap">
    <el-card class="card">
      <h2>Stabx Web 交易台</h2>
      <p class="hint">默认管理员 admin / admin123（仅本机首次引导）</p>
      <el-form @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" native-type="submit" style="width: 100%">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores";

const auth = useAuthStore();
const router = useRouter();
const username = ref("admin");
const password = ref("");
const loading = ref(false);

async function onSubmit() {
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    await router.push("/market");
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.wrap { min-height: 100%; display: grid; place-items: center; }
.card { width: 360px; }
.hint { color: #8a97a6; font-size: 12px; }
</style>
