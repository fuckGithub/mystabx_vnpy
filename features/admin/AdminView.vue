<template>
  <div class="page-shell">
    <div v-if="section === 'accounts'" class="page-list">
      <el-form class="page-query" :inline="true" @submit.prevent="applyAccQuery">
        <el-form-item>
          <el-input
            v-model="accKeyword"
            placeholder="账户名 / 网关 / 资金账号"
            clearable
            style="width: 240px"
            @keyup.enter="applyAccQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="applyAccQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetAccQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="page-toolbar">
        <el-button type="primary" :icon="Plus" @click="openCreateAccount">新增</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="pagedAccounts"
        border
        size="small"
        highlight-current-row
        style="width: 100%"
        empty-text="暂无通道"
      >
        <el-table-column prop="gateway_name" label="网关" width="100" />
        <el-table-column label="用户" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ userLabel(row.user_id) }}</template>
        </el-table-column>
        <el-table-column prop="account_name" label="账户名" min-width="110" show-overflow-tooltip />
        <el-table-column label="资金账号" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ connectField(row, "用户名") }}</template>
        </el-table-column>
        <el-table-column label="经纪商" width="80" align="center">
          <template #default="{ row }">{{ connectField(row, "经纪商代码") }}</template>
        </el-table-column>
        <el-table-column label="交易前置" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ row["交易服务器"] || connectField(row, "交易服务器") }}</template>
        </el-table-column>
        <el-table-column label="环境" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.auto_front === false ? 'warning' : 'info'">
              {{ row.front_label || "自动" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <StatusTag :text="String(row.conn_status || 'DISCONNECTED')" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" class-name="table-action-col">
          <template #default="{ row }">
            <span class="table-row-actions">
              <el-button size="small" text @click="openEditAccount(row)">编辑</el-button>
              <el-button size="small" type="danger" text @click="removeAccount(row)">删除</el-button>
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="page-pagination">
        <el-pagination
          v-model:current-page="accPage"
          v-model:page-size="accPageSize"
          :total="filteredAccounts.length"
          :page-sizes="[10, 20, 50]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          size="small"
        />
      </div>

      <el-dialog
        v-model="accVisible"
        :title="accForm.id ? '编辑通道' : '分配 CTP 账户'"
        width="560px"
        class="page-dialog"
        align-center
        :close-on-click-modal="false"
        destroy-on-close
        @closed="resetAccForm"
      >
        <el-form :model="accForm" label-width="80px" label-position="right" class="page-dialog-form">
          <p class="page-form-kicker">账户</p>
          <el-form-item label="用户 ID">
            <el-select v-model="accForm.user_id" filterable class="w-full">
              <el-option
                v-for="user in users"
                :key="user.id"
                :label="`${user.id} · ${user.username}`"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="账户名">
            <el-input v-model="accForm.account_name" />
          </el-form-item>
          <el-form-item label="资金账号">
            <el-input v-model="accForm.用户名" autocomplete="off" placeholder="InvestorID" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="accForm.密码"
              type="password"
              show-password
              autocomplete="new-password"
              :placeholder="accForm.id ? '更新时留空表示不改密码' : '写后即加密保存'"
            />
          </el-form-item>

          <p class="page-form-kicker">柜台</p>
          <el-form-item label="经纪商">
            <el-input v-model="accForm.经纪商代码" />
          </el-form-item>
          <el-form-item label="产品名称">
            <el-input v-model="accForm.产品名称" />
          </el-form-item>
          <el-form-item label="授权编码">
            <el-input v-model="accForm.授权编码" />
          </el-form-item>
          <el-form-item label="柜台环境">
            <div class="page-static-value">
              <el-tag size="small" effect="plain" type="info">{{ accForm.柜台环境 || "实盘" }}</el-tag>
              <el-tooltip :content="interfaceNote" placement="top">
                <el-icon class="page-label-tip"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </el-form-item>

          <div class="page-front-bar">
            <div class="page-front-bar__title">
              <span>前置</span>
              <el-tag size="small" effect="plain" :type="accForm.manualFront ? 'warning' : 'info'">
                {{ accForm.manualFront ? "手动指定" : `自动 · ${autoHint.label || "—"}` }}
              </el-tag>
              <el-tooltip placement="top" :show-after="200">
                <template #content>
                  <div class="page-dialog-tip">
                    <p>
                      当前按上海时间自动使用 <strong>{{ autoHint.label || "—" }}</strong>
                      （{{ autoHint.交易服务器 }} / {{ autoHint.行情服务器 }}）。
                    </p>
                    <p>{{ autoHint.windows }}</p>
                    <p>交易时段与 7×24 只换前置，不会新建通道。</p>
                  </div>
                </template>
                <el-icon class="page-label-tip"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="page-front-bar__switch">
              <el-switch v-model="accForm.manualFront" :active-value="false" :inactive-value="true" />
              <span>自动切换前置</span>
            </div>
          </div>
          <template v-if="accForm.manualFront">
            <el-form-item label="交易服务器">
              <el-input v-model="accForm.交易服务器" />
            </el-form-item>
            <el-form-item label="行情服务器">
              <el-input v-model="accForm.行情服务器" />
            </el-form-item>
          </template>
        </el-form>
        <template #footer>
          <div class="page-dialog-footer">
            <el-button @click="accVisible = false">取消</el-button>
            <el-button type="primary" :loading="accSaving" @click="saveAccount">保存并加密</el-button>
          </div>
        </template>
      </el-dialog>
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
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, QuestionFilled, Refresh, Search } from "@element-plus/icons-vue";
import { http } from "@/api";
import StatusTag from "@/components/StatusTag.vue";

interface AdminUser {
  id: number;
  username: string;
  display_name?: string;
  is_admin: boolean;
}

interface AdminAccount {
  id: number;
  user_id: number;
  gateway_name: string;
  account_name?: string;
  conn_status?: string;
  auto_front?: boolean;
  front_label?: string;
  交易服务器?: string;
  connect?: Record<string, string>;
}

const FALLBACK_AUTO = {
  交易服务器: "182.254.243.31:30001",
  行情服务器: "182.254.243.31:30011",
  env: "session",
  label: "交易时段",
  windows: "交易时段 08:45–15:30（周一至周五）与夜盘 20:45–02:35；其余时间走 7×24。",
};

const route = useRoute();
const section = computed(() => String(route.params.section || "users"));
const users = ref<AdminUser[]>([]);
const accounts = ref<AdminAccount[]>([]);
const loading = ref(false);
const creating = ref(false);
const createVisible = ref(false);
const queryKeyword = ref("");
const appliedKeyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const userForm = reactive({ username: "", password: "", is_admin: false });

const accKeyword = ref("");
const accApplied = ref("");
const accPage = ref(1);
const accPageSize = ref(10);
const accVisible = ref(false);
const accSaving = ref(false);
const autoHint = reactive({ ...FALLBACK_AUTO });
const interfaceNote = ref("本机仅打包实盘 CTP API，SimNow 走生产前置。");
const accForm = reactive({
  id: null as number | null,
  user_id: 1,
  account_name: "SimNow",
  用户名: "",
  密码: "",
  经纪商代码: "9999",
  产品名称: "simnow_client_test",
  授权编码: "0000000000000000",
  柜台环境: "实盘",
  交易服务器: FALLBACK_AUTO.交易服务器,
  行情服务器: FALLBACK_AUTO.行情服务器,
  manualFront: false,
});

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

const filteredAccounts = computed(() => {
  const keyword = accApplied.value.trim().toLowerCase();
  if (!keyword) return accounts.value;
  return accounts.value.filter((row) => {
    const blob = [
      row.gateway_name,
      row.account_name,
      connectField(row, "用户名"),
      connectField(row, "经纪商代码"),
      row["交易服务器"],
    ]
      .join(" ")
      .toLowerCase();
    return blob.includes(keyword);
  });
});

const pagedAccounts = computed(() => {
  const start = (accPage.value - 1) * accPageSize.value;
  return filteredAccounts.value.slice(start, start + accPageSize.value);
});

function connectField(row: AdminAccount, key: string) {
  return row.connect?.[key] || "";
}

function userLabel(id: number) {
  const user = users.value.find((item) => item.id === id);
  return user ? `${user.id} · ${user.username}` : String(id);
}

function clampPage() {
  const maxPage = Math.max(1, Math.ceil(filteredUsers.value.length / pageSize.value) || 1);
  if (page.value > maxPage) page.value = maxPage;
}

function clampAccPage() {
  const maxPage = Math.max(1, Math.ceil(filteredAccounts.value.length / accPageSize.value) || 1);
  if (accPage.value > maxPage) accPage.value = maxPage;
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

function applyAccQuery() {
  accApplied.value = accKeyword.value;
  accPage.value = 1;
}

function resetAccQuery() {
  accKeyword.value = "";
  accApplied.value = "";
  accPage.value = 1;
}

function resetUserForm() {
  userForm.username = "";
  userForm.password = "";
  userForm.is_admin = false;
}

function resetAccForm() {
  accForm.id = null;
  accForm.user_id = users.value[0]?.id || 1;
  accForm.account_name = "SimNow";
  accForm.用户名 = "";
  accForm.密码 = "";
  accForm.经纪商代码 = "9999";
  accForm.产品名称 = "simnow_client_test";
  accForm.授权编码 = "0000000000000000";
  accForm.柜台环境 = "实盘";
  accForm.交易服务器 = autoHint.交易服务器;
  accForm.行情服务器 = autoHint.行情服务器;
  accForm.manualFront = false;
}

function openCreate() {
  resetUserForm();
  createVisible.value = true;
}

async function loadConnectDefaults() {
  try {
    const { data } = await http.get("/api/admin/connect-defaults");
    const defaults = data?.defaults || {};
    const auto = data?.auto || {};
    if (defaults.经纪商代码) accForm.经纪商代码 = defaults.经纪商代码;
    if (defaults.产品名称) accForm.产品名称 = defaults.产品名称;
    if (defaults.授权编码) accForm.授权编码 = defaults.授权编码;
    if (defaults.柜台环境) accForm.柜台环境 = defaults.柜台环境;
    autoHint.交易服务器 = auto.交易服务器 || FALLBACK_AUTO.交易服务器;
    autoHint.行情服务器 = auto.行情服务器 || FALLBACK_AUTO.行情服务器;
    autoHint.env = auto.env || FALLBACK_AUTO.env;
    autoHint.label = auto.label || FALLBACK_AUTO.label;
    autoHint.windows = auto.windows || FALLBACK_AUTO.windows;
    if (data?.interface?.note) interfaceNote.value = data.interface.note;
    if (!accForm.manualFront) {
      accForm.交易服务器 = autoHint.交易服务器;
      accForm.行情服务器 = autoHint.行情服务器;
    }
  } catch {
    Object.assign(autoHint, FALLBACK_AUTO);
  }
}

async function openCreateAccount() {
  resetAccForm();
  await loadConnectDefaults();
  accVisible.value = true;
}

async function openEditAccount(row: AdminAccount) {
  await loadConnectDefaults();
  accForm.id = row.id;
  accForm.user_id = row.user_id;
  accForm.account_name = row.account_name || "SimNow";
  accForm.用户名 = connectField(row, "用户名");
  accForm.密码 = "";
  accForm.经纪商代码 = connectField(row, "经纪商代码") || "9999";
  accForm.产品名称 = connectField(row, "产品名称") || "simnow_client_test";
  accForm.授权编码 = connectField(row, "授权编码") || "0000000000000000";
  accForm.柜台环境 = connectField(row, "柜台环境") || "实盘";
  accForm.交易服务器 = row["交易服务器"] || connectField(row, "交易服务器") || autoHint.交易服务器;
  accForm.行情服务器 = connectField(row, "行情服务器") || autoHint.行情服务器;
  accForm.manualFront = row.auto_front === false;
  accVisible.value = true;
}

async function reload() {
  loading.value = true;
  try {
    users.value = (await http.get("/api/admin/users")).data;
    accounts.value = (await http.get("/api/admin/accounts")).data;
    clampPage();
    clampAccPage();
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

async function saveAccount() {
  if (!accForm.user_id || !accForm.用户名.trim()) {
    ElMessage.warning("请填写用户和资金账号");
    return;
  }
  const existed = accounts.value.some(
    (row) =>
      row.user_id === accForm.user_id &&
      (String(row.account_name || "").trim() === accForm.account_name.trim() ||
        connectField(row, "用户名") === accForm.用户名.trim()),
  );
  if (!existed && !accForm.密码) {
    ElMessage.warning("新建通道请填写密码");
    return;
  }
  accSaving.value = true;
  try {
    const connect_settings: Record<string, string | boolean> = {
      用户名: accForm.用户名.trim(),
      经纪商代码: accForm.经纪商代码.trim(),
      产品名称: accForm.产品名称.trim(),
      授权编码: accForm.授权编码.trim(),
      柜台环境: accForm.柜台环境,
      auto_front: !accForm.manualFront,
      手动指定前置: accForm.manualFront,
    };
    if (accForm.密码) connect_settings.密码 = accForm.密码;
    if (accForm.manualFront) {
      connect_settings.交易服务器 = accForm.交易服务器.trim();
      connect_settings.行情服务器 = accForm.行情服务器.trim();
    }
    await http.post("/api/admin/accounts", {
      id: accForm.id || undefined,
      user_id: accForm.user_id,
      account_name: accForm.account_name.trim() || "SimNow",
      connect_settings,
    });
    ElMessage.success(existed ? "通道已更新" : "账户已加密保存");
    accForm.密码 = "";
    accVisible.value = false;
    await reload();
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "保存失败");
  } finally {
    accSaving.value = false;
  }
}

async function removeAccount(row: AdminAccount) {
  try {
    await ElMessageBox.confirm(`删除通道 ${row.gateway_name}（${row.account_name || "未命名"}）？`, "删除通道", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await http.delete(`/api/admin/accounts/${row.id}`);
    ElMessage.success("已删除");
    await reload();
  } catch (error: unknown) {
    const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    ElMessage.error(detail || "删除失败");
  }
}

watch([pageSize, filteredUsers], clampPage);
watch([accPageSize, filteredAccounts], clampAccPage);
watch(section, () => {
  void reload();
});

onMounted(reload);
</script>
