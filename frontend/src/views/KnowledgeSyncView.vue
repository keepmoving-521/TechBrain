<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";

import {
  getKnowledgeSyncTask,
  listKnowledgeSyncTasks,
  triggerKnowledgeSync,
  type KnowledgeSyncTask,
} from "@/services/knowledgeSync";

const tasks = ref<KnowledgeSyncTask[]>([]);
const selectedTask = ref<KnowledgeSyncTask | null>(null);
const loading = ref(false);
const triggering = ref(false);

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
  } finally {
    triggering.value = false;
  }
}

async function handleSelectTask(task: KnowledgeSyncTask) {
  selectedTask.value = await getKnowledgeSyncTask(task.id);
}

onMounted(() => {
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
