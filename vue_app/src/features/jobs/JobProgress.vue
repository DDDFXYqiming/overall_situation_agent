<template>
  <section class="job-panel">
    <h3>任务进度</h3>
    <div v-if="jobsStore.activeJob" class="job-card">
      <div class="job-row">
        <span class="dot" :class="jobsStore.activeJob.status" />
        <strong>{{ kindLabel }}</strong>
        <em>{{ statusLabel }}</em>
      </div>
      <div class="progress"><span :class="{ running: jobsStore.isBusy }" /></div>
      <p>{{ resultText }}</p>
    </div>
    <div v-else class="empty">暂无运行中的任务</div>

    <EventList />
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import EventList from "@/features/jobs/EventList.vue";
import { useJobsStore } from "@/stores/jobsStore";

const jobsStore = useJobsStore();

const kindLabel = computed(() => {
  const kind = jobsStore.activeJob?.kind;
  return kind === "import" ? "数据导入" : kind === "report" ? "报告生成" : kind === "run" ? "导入并生成" : "智能问答";
});

const statusLabel = computed(() => {
  const status = jobsStore.activeJob?.status;
  return status === "completed" ? "已完成" : status === "failed" ? "失败" : status === "running" ? "运行中" : "排队中";
});

const resultText = computed(() => {
  if (jobsStore.activeJob?.error) {
    return jobsStore.activeJob.error;
  }
  if (jobsStore.activeJob?.result) {
    return "任务已返回结果，可在对话区查看报告卡片或详情。";
  }
  return "等待后端任务事件...";
});
</script>

<style scoped>
.job-panel {
  display: grid;
  gap: 14px;
  padding: 18px;
}

h3 {
  margin: 0;
  font-size: 15px;
}

.job-card,
.empty {
  border: 1px solid var(--border);
  border-radius: 12px;
  background: white;
  padding: 14px;
  box-shadow: var(--shadow-sm);
}

.empty {
  color: var(--muted-foreground);
  font-size: 13px;
}

.job-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #94a3b8;
}

.dot.running,
.dot.completed {
  background: #10b981;
}

.dot.failed {
  background: #ef4444;
}

strong {
  flex: 1;
  font-size: 13px;
}

em {
  border-radius: 7px;
  background: rgba(0, 82, 255, 0.08);
  color: var(--accent);
  padding: 4px 7px;
  font-style: normal;
  font-weight: 700;
  font-size: 11px;
}

.progress {
  height: 6px;
  overflow: hidden;
  margin: 14px 0 10px;
  border-radius: 999px;
  background: var(--muted);
}

.progress span {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  transform: scaleX(0.78);
  border-radius: inherit;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
}

.progress span.running {
  animation: pulse-width 1.5s ease-in-out infinite;
}

p {
  margin: 0;
  color: var(--muted-foreground);
  font-size: 12px;
  line-height: 1.5;
}

@keyframes pulse-width {
  0%,
  100% {
    transform: scaleX(0.38);
  }
  50% {
    transform: scaleX(0.92);
  }
}
</style>
