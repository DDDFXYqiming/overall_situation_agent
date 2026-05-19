<template>
  <article class="job-inline">
    <div class="job-inline__icon"><Activity :size="18" /></div>
    <div class="job-inline__body">
      <div class="job-inline__head">
        <strong>{{ title }}</strong>
        <span :class="jobsStore.activeJob?.status">{{ statusText }}</span>
      </div>
      <div class="job-inline__bar"><i :class="{ running: jobsStore.isBusy }" /></div>
      <p>{{ description }}</p>
      <div class="job-inline__actions">
        <BaseButton variant="ghost" @click="uiStore.setMode('api')">查看 API 工作流</BaseButton>
        <BaseButton v-if="jobsStore.activeJob?.status === 'failed'" variant="danger" @click="jobsStore.retryLast">重试任务</BaseButton>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Activity } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import { useJobsStore } from "@/stores/jobsStore";
import { useUiStore } from "@/stores/uiStore";

const jobsStore = useJobsStore();
const uiStore = useUiStore();

const title = computed(() => {
  const kind = jobsStore.activeJob?.kind;
  return kind === "import" ? "数据导入任务" : kind === "report" ? "报告生成任务" : kind === "run" ? "导入并生成任务" : "智能问答任务";
});

const statusText = computed(() => {
  const status = jobsStore.activeJob?.status;
  return status === "completed" ? "已完成" : status === "failed" ? "失败" : status === "running" ? "运行中" : "排队中";
});

const description = computed(() => {
  if (jobsStore.activeJob?.error) {
    return jobsStore.activeJob.error;
  }
  if (jobsStore.activeJob?.status === "completed") {
    return "任务已完成。报告类结果会自动出现在下方报告卡片。";
  }
  return "任务已提交，正在通过 SSE 接收后端事件。";
});
</script>

<style scoped>
.job-inline {
  max-width: 760px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  margin: 0 auto 18px;
}

.job-inline__icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(0, 82, 255, 0.08);
  color: var(--accent);
}

.job-inline__body {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: white;
  padding: 14px;
  box-shadow: var(--shadow-sm);
}

.job-inline__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

strong {
  font-size: 14px;
}

span {
  border-radius: 999px;
  background: rgba(0, 82, 255, 0.08);
  color: var(--accent);
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 800;
}

span.failed {
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}

span.completed {
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
}

.job-inline__bar {
  height: 6px;
  overflow: hidden;
  margin: 12px 0 10px;
  border-radius: 999px;
  background: var(--muted);
}

.job-inline__bar i {
  display: block;
  width: 100%;
  height: 100%;
  transform: scaleX(0.85);
  transform-origin: left;
  border-radius: inherit;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
}

.job-inline__bar i.running {
  animation: working 1.2s ease-in-out infinite;
}

p {
  margin: 0;
  color: var(--muted-foreground);
  font-size: 13px;
  line-height: 1.6;
}

.job-inline__actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

@keyframes working {
  0%,
  100% {
    transform: scaleX(0.3);
  }
  50% {
    transform: scaleX(0.9);
  }
}
</style>
