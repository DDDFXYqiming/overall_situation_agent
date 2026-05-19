<template>
  <main class="api-workbench">
    <section class="status-panel">
      <div>
        <span class="label">API 工作流</span>
        <h2>本地 FastAPI / SSE 状态</h2>
        <p>健康检查、启动参数、任务状态和最近事件都在这里集中查看。</p>
      </div>
      <div class="status-actions">
        <BaseButton variant="secondary" @click="refresh"><RefreshCw :size="16" />刷新状态</BaseButton>
        <BaseButton variant="primary" @click="uiStore.setMode('chat')">回到对话</BaseButton>
      </div>
    </section>

    <section class="api-grid">
      <article>
        <h3>Health</h3>
        <dl>
          <dt>Status</dt>
          <dd>{{ configStore.health?.status || "unknown" }}</dd>
          <dt>ES Index</dt>
          <dd>{{ configStore.esIndex }}</dd>
          <dt>API</dt>
          <dd>{{ configStore.apiUrl }}</dd>
        </dl>
      </article>

      <article>
        <h3>Startup</h3>
        <pre>{{ startupPreview }}</pre>
      </article>

      <article class="wide">
        <h3>最近任务</h3>
        <div v-if="jobsStore.recentJobs.length" class="job-list">
          <button v-for="job in jobsStore.recentJobs" :key="job.job_id" @click="jobsStore.activeJob = job">
            <span>{{ job.kind }}</span>
            <strong>{{ job.status }}</strong>
            <time>{{ job.updated_at }}</time>
          </button>
        </div>
        <p v-else>暂无任务。可以从右侧配置区或 CLI 工作台提交任务。</p>
      </article>
    </section>

    <JobProgress />
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RefreshCw } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import JobProgress from "@/features/jobs/JobProgress.vue";
import { useConfigStore } from "@/stores/configStore";
import { useJobsStore } from "@/stores/jobsStore";
import { useUiStore } from "@/stores/uiStore";

const configStore = useConfigStore();
const jobsStore = useJobsStore();
const uiStore = useUiStore();

const startupPreview = computed(() => JSON.stringify(configStore.startup?.defaults || {}, null, 2));

async function refresh() {
  await configStore.load();
  if (jobsStore.activeJob) {
    await jobsStore.refreshActiveJob(jobsStore.activeJob.kind);
  }
}
</script>

<style scoped>
.api-workbench {
  min-height: 0;
  overflow: auto;
  padding: 28px clamp(18px, 4vw, 48px);
}

.status-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: white;
  padding: 22px;
  box-shadow: var(--shadow-sm);
}

.label {
  color: var(--accent);
  font: 700 12px/1 var(--font-mono);
  text-transform: uppercase;
}

h2,
h3,
p {
  margin: 0;
}

h2 {
  margin-top: 8px;
  font-size: 22px;
}

p {
  color: var(--muted-foreground);
  line-height: 1.6;
}

.status-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.api-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

article {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: white;
  padding: 18px;
}

.wide {
  grid-column: 1 / -1;
}

dl {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 10px;
  margin: 14px 0 0;
  font-size: 13px;
}

dt {
  color: var(--muted-foreground);
}

dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
  font-weight: 700;
}

pre {
  overflow: auto;
  border-radius: 9px;
  background: #0f172a;
  color: white;
  padding: 12px;
  font: 500 12px/1.6 var(--font-mono);
}

.job-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.job-list button {
  display: grid;
  grid-template-columns: 90px 100px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 38px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: white;
  padding: 0 10px;
  cursor: pointer;
}

.job-list strong {
  color: var(--accent);
}

.job-list time {
  min-width: 0;
  overflow: hidden;
  color: var(--muted-foreground);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .status-panel,
  .api-grid {
    grid-template-columns: 1fr;
  }

  .status-panel {
    flex-direction: column;
  }
}
</style>
