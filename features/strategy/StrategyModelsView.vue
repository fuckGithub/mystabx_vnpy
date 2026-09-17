<template>
  <div class="page-shell">
    <div class="page-list">
      <div class="cta-list-head">
        <h3 class="page-section-title">策略模型</h3>
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openCreate">
          添加模型
        </el-button>
      </div>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="每个模型对应库内一个策略类（继承 vnpy CTA 模板）。普通「保存」只更新草稿；仅「保存为新版本」升级版本号。运行时从库加载合约、参数、基础配置与源码并动态编译。"
        style="margin-bottom: 12px"
      />
      <el-table
        v-loading="loading"
        :data="rows"
        size="small"
        border
        empty-text="暂无模型"
        class="model-table"
        @row-dblclick="(row) => openDetail(row as ModelRow)"
      >
        <el-table-column label="模型名称" min-width="160">
          <template #default="{ row }">
            <a class="model-name-link" href="#" @click.prevent="openDetail(row as ModelRow)">{{ (row as ModelRow).name }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="策略类" min-width="150" show-overflow-tooltip />
        <el-table-column prop="vt_symbol" label="合约" width="130" show-overflow-tooltip />
        <el-table-column label="最新版本" width="100" align="center">
          <template #default="{ row }">
            {{ (row as ModelRow).latest_version?.label || ((row as ModelRow).latest_version_id ? `#${(row as ModelRow).latest_version_id}` : "—") }}
          </template>
        </el-table-column>
        <el-table-column label="参数" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ formatParams((row as ModelRow).default_params) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="72" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="(row as ModelRow).enabled ? 'success' : 'info'">
              {{ (row as ModelRow).enabled ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openDetail(row as ModelRow, 'code')">
              模型编辑
            </el-button>
            <el-button size="small" text type="primary" @click="openDetail(row as ModelRow, 'settings')">
              模型参数
            </el-button>
            <el-button size="small" text type="primary" @click="openDetail(row as ModelRow, 'backtest')">
              运行
            </el-button>
            <el-button size="small" text type="danger" :disabled="!auth.isAdmin" @click="remove(row as ModelRow)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      title="添加模型"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item label="编码">
          <el-input v-model="form.code" placeholder="dual_ma_test" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="双均线测试策略" />
        </el-form-item>
        <el-form-item label="策略类">
          <el-input v-model="form.class_name" placeholder="DualMaTest" />
        </el-form-item>
        <el-form-item label="父模板">
          <el-select v-model="form.parent_template" style="width: 100%">
            <el-option label="EliteCtaTemplate" value="EliteCtaTemplate" />
            <el-option label="TargetPosTemplate" value="TargetPosTemplate" />
            <el-option label="CtaTemplate" value="CtaTemplate" />
          </el-select>
        </el-form-item>
        <el-form-item label="合约">
          <el-input v-model="form.vt_symbol" placeholder="rb2501.SHFE" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="基础参数">
          <el-input
            v-model="paramsJson"
            type="textarea"
            :rows="5"
            placeholder='{"fast_window":10,"slow_window":20}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import { http } from "@/api";
import { useAuthStore } from "@/stores";

type ModelRow = {
  id: number;
  code: string;
  name: string;
  description: string;
  class_name: string;
  parent_template: string;
  default_params: Record<string, unknown>;
  vt_symbol?: string;
  latest_version_id: number | null;
  latest_version?: { label?: string; params?: Record<string, unknown> };
  enabled: boolean;
  sort_order: number;
};

const auth = useAuthStore();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const rows = ref<ModelRow[]>([]);
const dialogVisible = ref(false);
const paramsJson = ref('{"fast_window":10,"slow_window":20,"fixed_size":1}');
const form = reactive({
  code: "",
  name: "",
  description: "",
  class_name: "",
  parent_template: "CtaTemplate",
  vt_symbol: "rb2501.SHFE",
  sort_order: 100,
  enabled: true,
});

function formatParams(params: unknown) {
  if (!params || typeof params !== "object") return "—";
  try {
    return JSON.stringify(params);
  } catch {
    return "—";
  }
}

function openDetail(row: ModelRow, tab: string = "code") {
  router.push({
    path: `/strategy/models/${row.id}`,
    query: { tab },
  });
}

function openCreate() {
  form.code = "";
  form.name = "";
  form.description = "";
  form.class_name = "";
  form.parent_template = "CtaTemplate";
  form.vt_symbol = "rb2501.SHFE";
  form.sort_order = 100;
  form.enabled = true;
  paramsJson.value = '{"fast_window":10,"slow_window":20,"fixed_size":1}';
  dialogVisible.value = true;
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/cta/models");
    rows.value = Array.isArray(data) ? data : [];
  } catch {
    rows.value = [];
    ElMessage.error("加载模型失败");
  } finally {
    loading.value = false;
  }
}

async function saveCreate() {
  let params: Record<string, unknown> = {};
  try {
    params = JSON.parse(paramsJson.value || "{}");
  } catch {
    ElMessage.warning("基础参数 JSON 无效");
    return;
  }
  saving.value = true;
  try {
    await http.post("/api/cta/models", {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description,
      class_name: form.class_name.trim(),
      parent_template: form.parent_template,
      vt_symbol: form.vt_symbol.trim(),
      default_params: params,
      sort_order: form.sort_order,
      enabled: form.enabled,
    });
    ElMessage.success("已创建模型");
    dialogVisible.value = false;
    await load();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "创建失败");
  } finally {
    saving.value = false;
  }
}

async function remove(row: ModelRow) {
  try {
    await ElMessageBox.confirm(`确定删除模型「${row.name}」？`, "删除确认", { type: "warning" });
  } catch {
    return;
  }
  try {
    await http.delete(`/api/cta/models/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "删除失败");
  }
}

onMounted(load);
</script>

<style scoped>
.model-name-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-weight: 600;
}
.model-name-link:hover {
  text-decoration: underline;
}
.cta-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
</style>
