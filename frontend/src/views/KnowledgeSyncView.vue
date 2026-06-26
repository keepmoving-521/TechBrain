<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";

import {
  getKnowledgeSyncSchedule,
  getKnowledgeSyncTask,
  listKnowledgeSyncTasks,
  triggerKnowledgeSync,
  updateKnowledgeSyncSchedule,
  type KnowledgeSyncSchedule,
  type KnowledgeSyncTask,
} from "@/services/knowledgeSync";

const tasks = ref<KnowledgeSyncTask[]>([]);
const selectedTask = ref<KnowledgeSyncTask | null>(null);
const schedule = ref<KnowledgeSyncSchedule | null>(null);
const scheduleForm = ref({
  enabled: false,
  interval_seconds: 3600,
});
const loading = ref(false);
const triggering = ref(false);
const scheduleLoading = ref(false);
const scheduleSaving = ref(false);

const latestTask = computed(() => tasks.value[0] ?? null);

function statusType(status: string) {
  if (status === "success") {
    return "success";
  }
  if (status === "partial_success") {
    return "warning";
  }
  return "danger";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    failed: "失败",
    partial_success: "部分成功",
    success: "成功",
  };
  return labels[status] ?? status;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatOptionalTime(value: string | null) {
  return value ? formatTime(value) : "-";
}

async function refreshSchedule() {
  scheduleLoading.value = true;
  try {
    const current = await getKnowledgeSyncSchedule();
    schedule.value = current;
    scheduleForm.value = {
      enabled: current.enabled,
      interval_seconds: current.interval_seconds,
    };
  } finally {
    scheduleLoading.value = false;
  }
}

async function handleSaveSchedule() {
  scheduleSaving.value = true;
  try {
    schedule.value = await updateKnowledgeSyncSchedule(scheduleForm.value);
    scheduleForm.value = {
      enabled: schedule.value.enabled,
      interval_seconds: schedule.value.interval_seconds,
    };
    ElMessage.success("定时同步配置已保存");
  } finally {
    scheduleSaving.value = false;
  }
}

async function refreshTasks() {
  loading.value = true;
  try {
    tasks.value = await listKnowledgeSyncTasks();
    if (selectedTask.value) {
      selectedTask.value =
        tasks.value.find((task) => task.id === selectedTask.value?.id) ?? selectedTask.value;
    } else {
      selectedTask.value = latestTask.value;
    }
  } finally {
    loading.value = false;
  }
}

async function handleTriggerSync() {
  triggering.value = true;
  try {
    const task = await triggerKnowledgeSync();
    ElMessage.success(`同步完成：任务 #${task.id}`);
    tasks.value = [task, ...tasks.value.filter((item) => item.id !== task.id)];
    selectedTask.value = task;
    await refreshSchedule();
  } finally {
    triggering.value = false;
  }
}

async function handleSelectTask(task: KnowledgeSyncTask) {
  selectedTask.value = await getKnowledgeSyncTask(task.id);
}

onMounted(() => {
  void refreshSchedule();
  void refreshTasks();
});
</script>

<template>
  <div class="sync-page">
    <ElCard shadow="never" class="content-card">
      <template #header>
        <div class="card-header">
          <span>手动同步</span>
          <div class="sync-actions">
            <ElButton :loading="loading" @click="refreshTasks">刷新记录</ElButton>
            <ElButton type="primary" :loading="triggering" @click="handleTriggerSync">
              立即同步
            </ElButton>
          </div>
        </div>
      </template>

      <ElAlert
        title="同步会扫描当前配置的 Markdown 知识库，并处理新增、修改、移动、删除和恢复。"
        type="info"
        :closable="false"
        show-icon
      />

      <div v-if="latestTask" class="sync-summary">
        <ElStatistic title="最近任务" :value="`#${latestTask.id}`" />
        <ElStatistic title="扫描文件" :value="latestTask.scanned_count" />
        <ElStatistic title="成功处理" :value="latestTask.success_count" />
        <ElStatistic title="失败数量" :value="latestTask.failed_count" />
        <ElTag :type="statusType(latestTask.status)" effect="dark">
          {{ statusLabel(latestTask.status) }}
        </ElTag>
      </div>

      <ElEmpty v-else class="placeholder-empty" description="暂无同步任务记录" />
    </ElCard>

    <ElCard shadow="never" class="content-card">
      <template #header>
        <div class="card-header">
          <span>定时同步</span>
          <ElButton :loading="scheduleLoading" @click="refreshSchedule">刷新配置</ElButton>
        </div>
      </template>

      <ElForm v-loading="scheduleLoading" label-width="120px" class="schedule-form">
        <ElFormItem label="启用定时同步">
          <ElSwitch v-model="scheduleForm.enabled" />
        </ElFormItem>
        <ElFormItem label="同步周期">
          <ElInputNumber
            v-model="scheduleForm.interval_seconds"
            :min="60"
            :step="60"
            controls-position="right"
          />
          <span class="form-tip">秒，最小 60 秒</span>
        </ElFormItem>
        <ElFormItem>
          <ElButton type="primary" :loading="scheduleSaving" @click="handleSaveSchedule">
            保存配置
          </ElButton>
        </ElFormItem>
      </ElForm>

      <ElDescriptions v-if="schedule" :column="3" border>
        <ElDescriptionsItem label="当前状态">
          <ElTag :type="schedule.enabled ? 'success' : 'info'">
            {{ schedule.enabled ? "已启用" : "已停用" }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="是否执行中">
          <ElTag :type="schedule.running ? 'warning' : 'info'">
            {{ schedule.running ? "执行中" : "空闲" }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="最近任务">
          {{ schedule.last_task_id ? `#${schedule.last_task_id}` : "-" }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="最近开始">
          {{ formatOptionalTime(schedule.last_started_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="最近结束">
          {{ formatOptionalTime(schedule.last_finished_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="最近错误">
          {{ schedule.last_error ?? "-" }}
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>

    <ElCard shadow="never" class="content-card">
      <template #header>
        <div class="card-header">
          <span>同步任务记录</span>
        </div>
      </template>

      <ElTable
        v-loading="loading"
        :data="tasks"
        empty-text="暂无同步任务"
        @row-click="handleSelectTask"
      >
        <ElTableColumn prop="id" label="任务 ID" width="100" />
        <ElTableColumn label="状态" width="120">
          <template #default="{ row }">
            <ElTag :type="statusType(row.status)">{{ statusLabel(row.status) }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="开始时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="scanned_count" label="扫描" width="90" />
        <ElTableColumn prop="success_count" label="成功" width="90" />
        <ElTableColumn prop="failed_count" label="失败" width="90" />
        <ElTableColumn prop="created_count" label="新增" width="90" />
        <ElTableColumn prop="updated_count" label="更新" width="90" />
        <ElTableColumn prop="deleted_count" label="删除" width="90" />
      </ElTable>
    </ElCard>

    <ElCard v-if="selectedTask" shadow="never" class="content-card">
      <template #header>
        <div class="card-header">
          <span>任务 #{{ selectedTask.id }} 详情</span>
          <ElTag :type="statusType(selectedTask.status)">
            {{ statusLabel(selectedTask.status) }}
          </ElTag>
        </div>
      </template>

      <ElDescriptions :column="3" border>
        <ElDescriptionsItem label="开始时间">
          {{ formatTime(selectedTask.started_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="结束时间">
          {{ formatTime(selectedTask.finished_at) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="扫描文件">{{ selectedTask.scanned_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="新增">{{ selectedTask.created_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="更新">{{ selectedTask.updated_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="恢复">{{ selectedTask.restored_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="未变化">{{ selectedTask.unchanged_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="软删除">{{ selectedTask.deleted_count }}</ElDescriptionsItem>
        <ElDescriptionsItem label="失败">{{ selectedTask.failed_count }}</ElDescriptionsItem>
      </ElDescriptions>

      <ElDivider>失败详情</ElDivider>

      <ElTable :data="selectedTask.failures" empty-text="无失败记录">
        <ElTableColumn prop="path" label="文件" min-width="220" />
        <ElTableColumn prop="stage" label="阶段" width="100" />
        <ElTableColumn prop="code" label="错误码" min-width="180" />
        <ElTableColumn prop="field" label="字段" width="140" />
        <ElTableColumn prop="line" label="行" width="80" />
        <ElTableColumn prop="column" label="列" width="80" />
        <ElTableColumn prop="message" label="说明" min-width="240" />
      </ElTable>
    </ElCard>
  </div>
</template>

<style scoped>
.sync-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.content-card {
  border-radius: 12px;
}

.card-header,
.sync-actions {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.sync-summary {
  align-items: center;
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  margin-top: 20px;
}

.schedule-form {
  margin-bottom: 16px;
  max-width: 520px;
}

.form-tip {
  color: var(--el-text-color-secondary);
  margin-left: 12px;
}

.placeholder-empty {
  padding: 24px 0;
}
</style>
