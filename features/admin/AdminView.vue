<template>
  <div class="page-shell">
    <div v-if="section === 'accounts'" class="page-section">
      <h3 class="page-section-title">分配 CTP 账户</h3>
      <el-form label-width="90px">
        <el-form-item label="用户 ID"><el-input-number v-model="accForm.user_id" :min="1" /></el-form-item>
        <el-form-item label="账户名"><el-input v-model="accForm.account_name" /></el-form-item>
        <el-form-item label="资金账号"><el-input v-model="accForm.userid" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="accForm.password" type="password" show-password /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="createAccount">保存并加密</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="accounts" style="margin-top: 16px">
        <el-table-column prop="gateway_name" label="网关" />
        <el-table-column prop="user_id" label="用户" width="80" />
        <el-table-column prop="account_name" label="名称" />
        <el-table-column prop="conn_status" label="状态" />
      </el-table>
    </div>

    <div v-else class="page-list">
      <el-form class="page-query" :inline="true" @submit.prevent="applyQuery">
        <el-form-item>
          <el-input
            v-model="queryKeyword"
            placeholder="用户名 / 显示名"
            clearable
            style="width: 220px"
            @keyup.enter="applyQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="applyQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="page-toolbar">
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="pagedUsers"
        border
        size="small"
        highlight-current-row
        style="width: 100%"
        empty-text="暂无用户"
      >
        <el-table-column prop="id" label="ID" width="72" />
        <el-table-column prop="username" label="用户" min-width="140" show-overflow-tooltip />
        <el-table-column prop="display_name" label="显示名" min-width="140" show-overflow-tooltip />
        <el-table-column label="管理员" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'success' : 'info'" size="small">
              {{ row.is_admin ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="page-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="filteredUsers.length"
          :page-sizes="[10, 20, 50]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          size="small"
        />
      </div>

      <el-dialog
        v-model="createVisible"
        title="新建用户"
        width="460px"
        :close-on-click-modal="false"
        destroy-on-close
        @closed="resetUserForm"
      >
        <el-form :model="userForm" label-width="80px">
          <el-form-item label="用户名">
            <el-input v-model="userForm.username" autocomplete="off" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="userForm.password" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-form-item label="管理员">
            <el-switch v-model="userForm.is_admin" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createVisible = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="createUser">创建</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Search } from "@element-plus/icons-vue";
import { http } from "@/api";

interface AdminUser {
  id: number;
  username: string;
  display_name?: string;
  is_admin: boolean;
}

const route = useRoute();
const section = computed(() => String(route.params.section || "users"));
const users = ref<AdminUser[]>([]);
const accounts = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const creating = ref(false);
const createVisible = ref(false);
const queryKeyword = ref("");
const appliedKeyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const userForm = reactive({ username: "", password: "", is_admin: false });
const accForm = reactive({ user_id: 1, account_name: "SimNow", userid: "", password: "" });

const filteredUsers = computed(() => {
  const keyword = appliedKeyword.value.trim().toLowerCase();
  if (!keyword) return users.value;
  return users.value.filter((row) => {
    const name = String(row.username || "").toLowerCase();
    const display = String(row.display_name || "").toLowerCase();
    return name.includes(keyword) || display.includes(keyword);
  });
});

const pagedUsers = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filteredUsers.value.slice(start, start + pageSize.value);
});

function clampPage() {
  const maxPage = Math.max(1, Math.ceil(filteredUsers.value.length / pageSize.value) || 1);
  if (page.value > maxPage) page.value = maxPage;
}

function applyQuery() {
  appliedKeyword.value = queryKeyword.value;
  page.value = 1;
}

function resetQuery() {
  queryKeyword.value = "";
  appliedKeyword.value = "";
  page.value = 1;
}

function resetUserForm() {
  userForm.username = "";
  userForm.password = "";
  userForm.is_admin = false;
}

function openCreate() {
  resetUserForm();
  createVisible.value = true;
}

async function reload() {
  loading.value = true;
  try {
    users.value = (await http.get("/api/admin/users")).data;
    accounts.value = (await http.get("/api/admin/accounts")).data;
    clampPage();
  } finally {
    loading.value = false;
  }
}

async function createUser() {
  if (!userForm.username.trim() || !userForm.password) {
    ElMessage.warning("请填写用户名和密码");
    return;
  }
  creating.value = true;
  try {
    await http.post("/api/admin/users", userForm);
    ElMessage.success("用户已创建");
    createVisible.value = false;
    resetUserForm();
    await reload();
    const lastPage = Math.max(1, Math.ceil(filteredUsers.value.length / pageSize.value));
    page.value = lastPage;
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "创建失败");
  } finally {
    creating.value = false;
  }
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

watch([pageSize, filteredUsers], clampPage);
watch(section, () => {
  void reload();
});

onMounted(reload);
</script>
