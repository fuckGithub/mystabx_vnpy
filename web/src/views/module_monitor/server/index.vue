<template>
  <div v-loading="loading" class="server-monitor">
    <header class="server-monitor__toolbar">
      <div class="server-monitor__titles">
        <h2 class="server-monitor__heading">服务器监控</h2>
        <p class="server-monitor__sub">实时查看主机资源与运行环境状态</p>
      </div>
      <ElButton :icon="Refresh" plain size="small" :loading="loading" @click="getList">刷新</ElButton>
    </header>

    <ElRow :gutter="12">
      <!-- CPU -->
      <ElCol :xs="24" :lg="12" class="server-monitor__col">
        <section class="sm-card">
          <div class="sm-card__head">
            <div class="sm-card__title">
              <span class="sm-card__icon sm-card__icon--cpu"><ElIcon :size="16"><Cpu /></ElIcon></span>
              <span>CPU 使用情况</span>
            </div>
            <ElTooltip content="展示 CPU 核心数及使用率">
              <ElIcon class="sm-card__hint"><QuestionFilled /></ElIcon>
            </ElTooltip>
          </div>
          <div class="sm-metric-grid">
            <article class="sm-metric">
              <div class="sm-metric__label">核心数</div>
              <div class="sm-metric__ring">
                <ElProgress
                  type="circle"
                  :width="108"
                  :stroke-width="10"
                  :percentage="100"
                  color="#1677ff"
                  :format="() => `${server.cpu?.cpu_num || 0}`" />
              </div>
              <dl class="sm-kv">
                <div class="sm-kv__row">
                  <dt>总核心数</dt>
                  <dd>{{ server.cpu?.cpu_num || 0 }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>已用核心</dt>
                  <dd>{{ Math.floor(((server.cpu?.used || 0) * (server.cpu?.cpu_num || 0)) / 100) }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>空闲核心</dt>
                  <dd>{{ Math.floor(((server.cpu?.free || 0) * (server.cpu?.cpu_num || 0)) / 100) }}</dd>
                </div>
              </dl>
            </article>
            <article class="sm-metric">
              <div class="sm-metric__label">使用率</div>
              <div class="sm-metric__ring">
                <ElProgress
                  type="circle"
                  :width="108"
                  :stroke-width="10"
                  :percentage="Number(server.cpu?.used || 0)"
                  :color="usageColor(server.cpu?.used)"
                  :format="(p) => `${Number(p).toFixed(1)}%`" />
              </div>
              <dl class="sm-kv">
                <div class="sm-kv__row">
                  <dt>用户使用率</dt>
                  <dd>{{ (server.cpu?.used || 0).toFixed(1) }}%</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>系统使用率</dt>
                  <dd>{{ (server.cpu?.sys || 0).toFixed(1) }}%</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>当前空闲率</dt>
                  <dd>{{ (server.cpu?.free || 0).toFixed(1) }}%</dd>
                </div>
              </dl>
            </article>
          </div>
        </section>
      </ElCol>

      <!-- Memory -->
      <ElCol :xs="24" :lg="12" class="server-monitor__col">
        <section class="sm-card">
          <div class="sm-card__head">
            <div class="sm-card__title">
              <span class="sm-card__icon sm-card__icon--mem"><ElIcon :size="16"><Memo /></ElIcon></span>
              <span>内存使用情况</span>
            </div>
            <ElTooltip content="展示系统内存和 Python 程序内存使用情况">
              <ElIcon class="sm-card__hint"><QuestionFilled /></ElIcon>
            </ElTooltip>
          </div>
          <div class="sm-metric-grid">
            <article class="sm-metric">
              <div class="sm-metric__label">系统内存</div>
              <div class="sm-metric__ring">
                <ElProgress
                  type="circle"
                  :width="108"
                  :stroke-width="10"
                  :percentage="Number(server.mem?.usage || 0)"
                  :color="usageColor(server.mem?.usage)"
                  :format="(p) => `${Number(p).toFixed(1)}%`" />
              </div>
              <dl class="sm-kv">
                <div class="sm-kv__row">
                  <dt>总内存</dt>
                  <dd>{{ server.mem?.total || '-' }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>已用内存</dt>
                  <dd>{{ server.mem?.used || '-' }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>空闲内存</dt>
                  <dd>{{ server.mem?.free || '-' }}</dd>
                </div>
              </dl>
            </article>
            <article class="sm-metric">
              <div class="sm-metric__label">Python 内存</div>
              <div class="sm-metric__ring">
                <ElProgress
                  type="circle"
                  :width="108"
                  :stroke-width="10"
                  :percentage="Number(server.py?.memory_usage || 0)"
                  :color="usageColor(server.py?.memory_usage)"
                  :format="(p) => `${Number(p).toFixed(1)}%`" />
              </div>
              <dl class="sm-kv">
                <div class="sm-kv__row">
                  <dt>总内存</dt>
                  <dd>{{ server.py?.memory_total || '-' }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>已用内存</dt>
                  <dd>{{ server.py?.memory_used || '-' }}</dd>
                </div>
                <div class="sm-kv__row">
                  <dt>空闲内存</dt>
                  <dd>{{ server.py?.memory_free || '-' }}</dd>
                </div>
              </dl>
            </article>
          </div>
        </section>
      </ElCol>

      <!-- Server info -->
      <ElCol :span="24" class="server-monitor__col">
        <section class="sm-card">
          <div class="sm-card__head">
            <div class="sm-card__title">
              <span class="sm-card__icon sm-card__icon--sys"><ElIcon :size="16"><Monitor /></ElIcon></span>
              <span>服务器基本信息</span>
            </div>
            <ElTooltip content="展示服务器基本配置信息">
              <ElIcon class="sm-card__hint"><QuestionFilled /></ElIcon>
            </ElTooltip>
          </div>
          <div class="sm-info-grid sm-info-grid--2">
            <div v-for="item in sysInfoItems" :key="item.label" class="sm-info-cell">
              <span class="sm-info-cell__label">{{ item.label }}</span>
              <span class="sm-info-cell__value" :title="item.value">{{ item.value }}</span>
            </div>
          </div>
        </section>
      </ElCol>

      <!-- Python env -->
      <ElCol :span="24" class="server-monitor__col">
        <section class="sm-card">
          <div class="sm-card__head">
            <div class="sm-card__title">
              <span class="sm-card__icon sm-card__icon--py"><ElIcon :size="16"><Dish /></ElIcon></span>
              <span>Python 运行环境</span>
            </div>
            <ElTooltip content="展示 Python 环境配置及运行状态">
              <ElIcon class="sm-card__hint"><QuestionFilled /></ElIcon>
            </ElTooltip>
          </div>
          <div class="sm-info-grid sm-info-grid--3">
            <div v-for="item in pyInfoItems" :key="item.label" class="sm-info-cell">
              <span class="sm-info-cell__label">{{ item.label }}</span>
              <span class="sm-info-cell__value" :title="item.value">{{ item.value }}</span>
            </div>
          </div>
        </section>
      </ElCol>

      <!-- Disks -->
      <ElCol :span="24" class="server-monitor__col">
        <section class="sm-card sm-card--table">
          <div class="sm-card__head">
            <div class="sm-card__title">
              <span class="sm-card__icon sm-card__icon--disk"><ElIcon :size="16"><Files /></ElIcon></span>
              <span>磁盘使用情况</span>
            </div>
            <ElTooltip content="展示磁盘空间使用详情">
              <ElIcon class="sm-card__hint"><QuestionFilled /></ElIcon>
            </ElTooltip>
          </div>
          <ElTable :data="server.disks" size="small" class="sm-disk-table" stripe>
            <template #empty>
              <ElEmpty :image-size="72" description="暂无磁盘数据" />
            </template>
            <ElTableColumn label="盘符路径" prop="dir_name" min-width="140" :show-overflow-tooltip="true" />
            <ElTableColumn label="文件系统" prop="sys_type_name" align="center" width="100" />
            <ElTableColumn label="盘符名称" prop="type_name" min-width="120" :show-overflow-tooltip="true" />
            <ElTableColumn prop="usage" label="使用率" align="center" min-width="180">
              <template #default="{ row }">
                <ElProgress
                  :percentage="Number(row.usage)"
                  :color="usageColor(row.usage)"
                  :stroke-width="12"
                  :text-inside="true" />
              </template>
            </ElTableColumn>
            <ElTableColumn label="总大小" prop="total" align="center" width="100" />
            <ElTableColumn label="可用大小" prop="free" align="center" width="100" />
            <ElTableColumn label="已用大小" prop="used" align="center" width="100" />
          </ElTable>
        </section>
      </ElCol>
    </ElRow>
  </div>
</template>

<script lang="ts" setup>
import { Refresh } from '@element-plus/icons-vue'
import ServerAPI, { type ServerInfo } from '@/api/module_monitor/server'

defineOptions({ name: 'MonitorServer' })

const loading = ref(false)
const server = ref<ServerInfo>({
  cpu: {
    cpu_num: 0,
    used: 0,
    sys: 0,
    free: 0,
  },
  mem: {
    total: '',
    used: '',
    free: '',
    usage: 0,
  },
  sys: {
    computer_name: '',
    os_name: '',
    computer_ip: '',
    os_arch: '',
    user_dir: '',
  },
  py: {
    name: '',
    version: '',
    start_time: '',
    run_time: '',
    home: '',
    memory_total: '',
    memory_used: '',
    memory_free: '',
    memory_usage: 0,
  },
  disks: [],
})

const sysInfoItems = computed(() => [
  { label: '服务器名称', value: server.value.sys?.computer_name || '-' },
  { label: '操作系统', value: server.value.sys?.os_name || '-' },
  { label: '服务器 IP', value: server.value.sys?.computer_ip || '-' },
  { label: '系统架构', value: server.value.sys?.os_arch || '-' },
])

const pyInfoItems = computed(() => [
  { label: 'Python 名称', value: server.value.py?.name || '-' },
  { label: 'Python 版本', value: server.value.py?.version || '-' },
  { label: '启动时间', value: server.value.py?.start_time || '-' },
  { label: '运行时长', value: server.value.py?.run_time || '-' },
  { label: '安装路径', value: server.value.py?.home || '-' },
  { label: '项目路径', value: server.value.sys?.user_dir || '-' },
])

function usageColor(value?: number) {
  const n = Number(value || 0)
  if (n > 80) return '#ff4d4f'
  if (n > 60) return '#faad14'
  return '#1677ff'
}

async function getList() {
  loading.value = true
  try {
    const response = await ServerAPI.getServer()
    server.value = response.data.data
  } catch (error) {
    console.error('获取服务器信息失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getList()
})
</script>

<style lang="scss" scoped>
.server-monitor {
  --sm-primary: #1677ff;
  --sm-surface: var(--default-box-color, #fff);
  --sm-soft: #f8fafc;
  --sm-border: #e2e8f0;
  --sm-text: #334155;
  --sm-muted: #64748b;
  --sm-heading: #0f172a;
  --sm-radius: 8px;
  --sm-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);

  box-sizing: border-box;
  min-width: 0;
  color: var(--sm-text);
}

.server-monitor__toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.server-monitor__heading {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--sm-heading);
  letter-spacing: 0.01em;
}

.server-monitor__sub {
  margin: 2px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--sm-muted);
}

.server-monitor__col {
  margin-bottom: 12px;
}

.sm-card {
  box-sizing: border-box;
  height: 100%;
  padding: 14px 16px 16px;
  background: var(--sm-surface);
  border: 1px solid var(--sm-border);
  border-radius: var(--sm-radius);
  box-shadow: var(--sm-shadow);
}

.sm-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid color-mix(in srgb, var(--sm-border) 80%, transparent);
}

.sm-card__title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--sm-heading);
}

.sm-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  color: var(--sm-primary);
  background: color-mix(in srgb, var(--sm-primary) 10%, transparent);
}

.sm-card__icon--mem {
  color: #0ea5e9;
  background: color-mix(in srgb, #0ea5e9 12%, transparent);
}

.sm-card__icon--sys {
  color: #475569;
  background: color-mix(in srgb, #64748b 12%, transparent);
}

.sm-card__icon--py {
  color: #0891b2;
  background: color-mix(in srgb, #06b6d4 12%, transparent);
}

.sm-card__icon--disk {
  color: #2563eb;
  background: color-mix(in srgb, #2563eb 10%, transparent);
}

.sm-card__hint {
  color: var(--sm-muted);
  cursor: help;
  opacity: 0.75;
}

.sm-metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.sm-metric {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--sm-soft);
  border: 1px solid color-mix(in srgb, var(--sm-border) 88%, transparent);
  border-radius: 7px;
}

.sm-metric__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--sm-muted);
}

.sm-metric__ring {
  display: flex;
  justify-content: center;
  padding: 4px 0 2px;

  :deep(.el-progress__text) {
    font-size: 18px !important;
    font-weight: 600;
    color: var(--sm-heading);
  }
}

.sm-kv {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
}

.sm-kv__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 22px;
  padding: 0 2px;
  font-size: 12px;

  dt {
    margin: 0;
    color: var(--sm-muted);
  }

  dd {
    margin: 0;
    font-weight: 560;
    font-variant-numeric: tabular-nums;
    color: var(--sm-heading);
  }
}

.sm-info-grid {
  display: grid;
  gap: 10px;
}

.sm-info-grid--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sm-info-grid--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.sm-info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 10px 12px;
  background: var(--sm-soft);
  border: 1px solid color-mix(in srgb, var(--sm-border) 88%, transparent);
  border-radius: 7px;
}

.sm-info-cell__label {
  font-size: 12px;
  color: var(--sm-muted);
}

.sm-info-cell__value {
  overflow: hidden;
  font-size: 13px;
  font-weight: 560;
  line-height: 1.4;
  color: var(--sm-heading);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sm-card--table {
  padding-bottom: 10px;
}

.sm-disk-table {
  width: 100%;

  :deep(.el-table__header th) {
    font-weight: 600;
    color: var(--sm-heading);
    background: var(--sm-soft) !important;
  }

  :deep(.el-progress-bar__outer) {
    background: #e2e8f0;
  }
}

@media (width <= 900px) {
  .sm-info-grid--3 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (width <= 640px) {
  .sm-metric-grid,
  .sm-info-grid--2,
  .sm-info-grid--3 {
    grid-template-columns: 1fr;
  }

  .server-monitor__toolbar {
    flex-wrap: wrap;
  }
}

html.dark .server-monitor,
[data-theme='dark'] .server-monitor {
  --sm-surface: var(--default-box-color, #121a27);
  --sm-soft: #1a2433;
  --sm-border: rgba(148, 163, 184, 0.16);
  --sm-text: #e2e8f0;
  --sm-muted: #94a3b8;
  --sm-heading: #f8fafc;
  --sm-shadow: none;
}
</style>
