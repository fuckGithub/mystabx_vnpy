<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <h3>新建用户</h3>
      <el-form label-width="80px">
        <el-form-item label="用户名"><el-input v-model="userForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="userForm.password" type="password" /></el-form-item>
        <el-form-item label="管理员"><el-switch v-model="userForm.is_admin" /></el-form-item>
        <el-button type="primary" @click="createUser">创建</el-button>
      </el-form>
      <el-table :data="users" style="margin-top: 16px">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户" />
        <el-table-column prop="is_admin" label="管理员" />
      </el-table>
    </el-col>
    <el-col :span="14">
      <h3>分配 CTP 账户</h3>
      <el-form label-width="90px">
        <el-form-item label="用户 ID"><el-input-number v-model="accForm.user_id" :min="1" /></el-form-item>
        <el-form-item label="账户名"><el-input v-model="accForm.account_name" /></el-form-item>
        <el-form-item label="资金账号"><el-input v-model="accForm.userid" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="accForm.password" type="password" /></el-form-item>
        <el-button type="primary" @click="createAccount">保存并加密</el-button>
      </el-form>
      <el-table :data="accounts" style="margin-top: 16px">
        <el-table-column prop="gateway_name" label="网关" />
        <el-table-column prop="user_id" label="用户" width="80" />
        <el-table-column prop="account_name" label="名称" />
        <el-table-column prop="conn_status" label="状态" />
      </el-table>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { http } from "@/api";

const users = ref<Record<string, unknown>[]>([]);
const accounts = ref<Record<string, unknown>[]>([]);
const userForm = reactive({ username: "", password: "", is_admin: false });
const accForm = reactive({ user_id: 1, account_name: "SimNow", userid: "", password: "" });

async function reload() {
  users.value = (await http.get("/api/admin/users")).data;
  accounts.value = (await http.get("/api/admin/accounts")).data;
}

async function createUser() {
  await http.post("/api/admin/users", userForm);
  ElMessage.success("用户已创建");
  await reload();
}

async function createAccount() {
  await http.post("/api/admin/accounts", {
    user_id: accForm.user_id,
    account_name: accForm.account_name,
    connect_settings: {
      用户名: accForm.userid,
      密码: accForm.password,
    },
  });
  ElMessage.success("账户已加密保存");
  accForm.password = "";
  await reload();
}

onMounted(reload);
</script>

<style scoped>
h3 { margin: 0 0 12px; font-size: 14px; color: #c9d4de; }
</style>
