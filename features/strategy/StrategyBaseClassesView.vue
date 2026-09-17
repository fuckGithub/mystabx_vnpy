<template>
  <div class="page-shell">
    <div class="page-list">
      <div class="cta-list-head">
        <h3 class="page-section-title">策略基类管理</h3>
        <el-button type="primary" :icon="Plus" :disabled="!auth.isAdmin" @click="openCreate">
          添加基类
        </el-button>
      </div>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="策略源码通过继承此处登记的父类（默认 EliteCtaTemplate）编写；详情页 IDE 可切换基类并改写 import / class 声明。"
        style="margin-bottom: 12px"
      />
      <el-table v-loading="loading" :data="rows" size="small" border empty-text="暂无基类">
        <el-table-column prop="display_name" label="显示名" min-width="140" />
        <el-table-column prop="class_name" label="类名" min-width="150" />
        <el-table-column prop="module" label="模块" min-width="160" show-overflow-tooltip />
        <el-table-column prop="base_chain" label="继承链" min-width="200" show-overflow-tooltip />
        <el-table-column label="默认" width="72" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" size="small" type="success">是</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="72" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? "是" : "否" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" :disabled="!auth.isAdmin" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button
              size="small"
              text
              type="danger"
              :disabled="!auth.isAdmin || row.is_default"
              @click="remove(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑基类' : '添加基类'"
      width="560px"
      destroy-on-close
    >
      <el-form label-width="100px">
        <el-form-item label="类名">
          <el-input v-model="form.class_name" :disabled="editing" placeholder="EliteCtaTemplate" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="模块">
          <el-input v-model="form.module" placeholder="core.strategy_shim" />
        </el-form-item>
        <el-form-item label="Import">
          <el-input
            v-model="form.import_stmt"
            type="textarea"
            :rows="2"
            placeholder="from core.strategy_shim import EliteCtaTemplate, ..."
          />
        </el-form-item>
        <el-form-item label="继承链">
          <el-input v-model="form.base_chain" />
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
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import { http } from "@/api";
import { useAuthStore } from "@/stores";

type BaseClassRow = {
  class_name: string;
  display_name: string;
  module: string;
  import_stmt: string;
  description: string;
  base_chain: string;
  enabled: boolean;
  is_default: boolean;
  sort_order: number;
};

const auth = useAuthStore();
const loading = ref(false);
const saving = ref(false);
const rows = ref<BaseClassRow[]>([]);
const dialogVisible = ref(false);
const editing = ref(false);
const form = reactive({
  class_name: "",
  display_name: "",
  module: "",
  import_stmt: "",
  description: "",
  base_chain: "",
  enabled: true,
  is_default: false,
  sort_order: 100,
});

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get("/api/cta/base-classes");
    rows.value = Array.isArray(data) ? data : [];
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    ElMessage.error(err.response?.data?.detail || "加载基类失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = false;
  Object.assign(form, {
    class_name: "",
    display_name: "",
    module: "",
    import_stmt: "",
    description: "",
    base_chain: "",
    enabled: true,
    is_default: false,
    sort_order: 100,
  });
  dialogVisible.value = true;
}

function openEdit(row: BaseClassRow) {
  editing.value = true;
  Object.assign(form, {
    class_name: row.class_name,
    display_name: row.display_name,
    module: row.module,
    import_stmt: row.import_stmt,
    description: row.description,
    base_chain: row.base_chain,
    enabled: row.enabled,
    is_default: row.is_default,
    sort_order: row.sort_order,
  });
  dialogVisible.value = true;
}

async function save() {
  if (!form.class_name.trim()) {
    ElMessage.warning("类名不能为空");
    return;
  }
  saving.value = true;
  try {
    const name = form.class_name.trim();
    if (editing.value) {
      await http.put(`/api/cta/base-classes/${encodeURIComponent(name)}`, { ...form });
    } else {
      await http.post("/api/cta/base-classes", { ...form });
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

async function remove(row: BaseClassRow) {
  await ElMessageBox.confirm(`确认删除基类「${row.class_name}」？`, "删除基类", { type: "warning" });
  try {
    await http.delete(`/api/cta/base-classes/${encodeURIComponent(row.class_name)}`);
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
