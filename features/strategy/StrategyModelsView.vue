<template>
  <div class="page-shell">
    <div class="page-list">
      <div class="cta-list-head">
        <h3 class="page-section-title">模型管理</h3>
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openCreate">
          添加模型
        </el-button>
      </div>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="模型是后端提供的策略模板（如双均线、RUMI）。修改基础参数会生成新的模型版本；策略实例保存时会钉住所选模型版本，实盘/回测按钉住版本加载，而非始终用最新版。"
        style="margin-bottom: 12px"
      />
      <el-table v-loading="loading" :data="rows" size="small" border empty-text="暂无模型">
        <el-table-column prop="name" label="模型名称" min-width="140" />
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="class_name" label="策略类" min-width="130" show-overflow-tooltip />
        <el-table-column prop="parent_template" label="父模板" width="140" show-overflow-tooltip />
        <el-table-column label="最新版本" width="100" align="center">
          <template #default="{ row }">
            {{ row.latest_version?.label || row.latest_version_id || "—" }}
          </template>
        </el-table-column>
        <el-table-column label="基础参数" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ formatParams(row.default_params) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="72" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openVersions(row)">版本</el-button>
            <el-button size="small" text type="primary" :disabled="!auth.isAdmin" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button size="small" text type="danger" :disabled="!auth.isAdmin" @click="remove(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑模型' : '添加模型'"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item label="编码">
          <el-input v-model="form.code" :disabled="Boolean(editingId)" placeholder="dual_ma" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="双均线策略" />
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
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="基础参数">
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
        <el-button type="primary" :loading="saving" @click="saveMeta">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="versionDrawer" :title="versionTitle" size="520px">
      <div class="model-version-toolbar">
        <el-button type="primary" size="small" :disabled="!auth.isAdmin" @click="openNewVersion">
          保存为新版本
        </el-button>
      </div>
      <el-table :data="versions" size="small" border empty-text="暂无版本">
        <el-table-column prop="version_no" label="#" width="48" />
        <el-table-column prop="label" label="标签" width="80" />
        <el-table-column label="参数" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ formatParams(row.params) }}</template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="100" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="160" />
      </el-table>

      <el-dialog
        v-model="versionDialog"
        title="新建模型版本"
        width="480px"
        append-to-body
        destroy-on-close
      >
        <el-form label-width="80px">
          <el-form-item label="标签">
            <el-input v-model="versionForm.label" placeholder="v2" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="versionForm.note" />
          </el-form-item>
          <el-form-item label="参数 JSON">
            <el-input v-model="versionForm.paramsJson" type="textarea" :rows="8" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="versionDialog = false">取消</el-button>
          <el-button type="primary" :loading="savingVersion" @click="saveVersion">保存版本</el-button>
        </template>
      </el-dialog>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
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
  latest_version_id: number | null;
  latest_version?: { label?: string; params?: Record<string, unknown> };
  enabled: boolean;
  sort_order: number;
};

type VersionRow = {
  id: number;
  version_no: number;
  label: string;
  note: string;
  params: Record<string, unknown>;
  created_at: string;
};

const auth = useAuthStore();
const loading = ref(false);
const saving = ref(false);
const savingVersion = ref(false);
const rows = ref<ModelRow[]>([]);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const paramsJson = ref('{"fast_window":10,"slow_window":20,"fixed_size":1}');
const form = reactive({
  code: "",
  name: "",
  description: "",
  class_name: "",
  parent_template: "EliteCtaTemplate",
  sort_order: 100,
  enabled: true,
});

const versionDrawer = ref(false);
const versionDialog = ref(false);
const activeModel = ref<ModelRow | null>(null);
const versions = ref<VersionRow[]>([]);
const versionForm = reactive({ label: "", note: "", paramsJson: "{}" });

const versionTitle = computed(() =>
  activeModel.value ? `模型版本 · ${activeModel.value.name}` : "模型版本",
);

function formatParams(params: unknown) {
  if (!params || typeof params !== "object") return "—";
  try {
    return JSON.stringify(params);
  } catch {
    return "—";
  }
}

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/cta/models");
    rows.value = Array.isArray(data) ? data : [];
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "加载模型失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, {
    code: "",
    name: "",
    description: "",
    class_name: "",
    parent_template: "EliteCtaTemplate",
    sort_order: 100,
    enabled: true,
  });
  paramsJson.value = '{"fast_window":10,"slow_window":20,"fixed_size":1}';
  dialogVisible.value = true;
}

function openEdit(row: ModelRow) {
  editingId.value = row.id;
  Object.assign(form, {
    code: row.code,
    name: row.name,
    description: row.description,
    class_name: row.class_name,
    parent_template: row.parent_template || "EliteCtaTemplate",
    sort_order: row.sort_order,
    enabled: row.enabled,
  });
  dialogVisible.value = true;
}

async function saveMeta() {
  saving.value = true;
  try {
    if (editingId.value) {
      await http.patch(`/api/cta/models/${editingId.value}`, {
        name: form.name,
        description: form.description,
        class_name: form.class_name,
        parent_template: form.parent_template,
        enabled: form.enabled,
        sort_order: form.sort_order,
      });
    } else {
      let params: Record<string, unknown> = {};
      try {
        params = JSON.parse(paramsJson.value || "{}");
      } catch {
        ElMessage.warning("基础参数 JSON 无效");
        return;
      }
      await http.post("/api/cta/models", {
        ...form,
        default_params: params,
      });
    }
    ElMessage.success("已保存");
    dialogVisible.value = false;
    await load();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function openVersions(row: ModelRow) {
  activeModel.value = row;
  versionDrawer.value = true;
  try {
    const { data } = await http.get(`/api/cta/models/${row.id}/versions`);
    versions.value = Array.isArray(data) ? data : [];
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "加载版本失败");
  }
}

function openNewVersion() {
  const base = activeModel.value?.default_params || versions.value[0]?.params || {};
  versionForm.label = `v${(versions.value[0]?.version_no || 0) + 1}`;
  versionForm.note = "";
  versionForm.paramsJson = JSON.stringify(base, null, 2);
  versionDialog.value = true;
}

async function saveVersion() {
  if (!activeModel.value) return;
  let params: Record<string, unknown> = {};
  try {
    params = JSON.parse(versionForm.paramsJson || "{}");
  } catch {
    ElMessage.warning("参数 JSON 无效");
    return;
  }
  savingVersion.value = true;
  try {
    await http.post(`/api/cta/models/${activeModel.value.id}/versions`, {
      params,
      label: versionForm.label,
      note: versionForm.note,
    });
    ElMessage.success("已创建模型版本");
    versionDialog.value = false;
    await openVersions(activeModel.value);
    await load();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "保存版本失败");
  } finally {
    savingVersion.value = false;
  }
}

async function remove(row: ModelRow) {
  await ElMessageBox.confirm(`确认删除模型「${row.name}」及其全部版本？`, "删除模型", {
    type: "warning",
  });
  try {
    await http.delete(`/api/cta/models/${row.id}`);
    ElMessage.success("已删除");
    await load();
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "删除失败");
  }
}

onMounted(() => {
  void load();
});
</script>

<style scoped>
.model-version-toolbar {
  margin-bottom: 12px;
}
</style>
