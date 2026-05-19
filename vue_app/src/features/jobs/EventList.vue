<template>
  <div class="events">
    <div class="events__header">
      <h3>任务事件（SSE）</h3>
      <button @click="jobsStore.clearEvents()">清空</button>
    </div>
    <div class="event-list">
      <div v-for="event in jobsStore.events" :key="`${event.receivedAt}-${event.event}-${JSON.stringify(event.data)}`" class="event-row">
        <span />
        <time>{{ event.receivedAt }}</time>
        <p>{{ eventText(event) }}</p>
        <em>{{ event.event }}</em>
      </div>
      <div v-if="!jobsStore.events.length" class="no-events">等待任务事件</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { JobEvent } from "@/services/types";
import { useJobsStore } from "@/stores/jobsStore";

const jobsStore = useJobsStore();

function eventText(event: JobEvent) {
  const message = event.data.message || event.data.error || event.data.job_id || "";
  return String(message || "收到任务事件");
}
</script>

<style scoped>
.events {
  display: grid;
  gap: 10px;
}

.events__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h3 {
  margin: 0;
  font-size: 14px;
}

button {
  border: 0;
  background: transparent;
  color: var(--accent);
  font-weight: 700;
  cursor: pointer;
}

.event-list {
  max-height: 220px;
  overflow: auto;
  display: grid;
  gap: 6px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: white;
  padding: 8px;
}

.event-row {
  display: grid;
  grid-template-columns: 9px 58px minmax(0, 1fr) auto;
  align-items: center;
  gap: 7px;
  min-height: 28px;
}

.event-row span {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #10b981;
}

time {
  color: #94a3b8;
  font-size: 11px;
}

p {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  color: var(--muted-foreground);
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

em {
  border-radius: 6px;
  background: rgba(0, 82, 255, 0.08);
  color: var(--accent);
  padding: 3px 6px;
  font-style: normal;
  font-weight: 800;
  font-size: 10px;
  text-transform: uppercase;
}

.no-events {
  padding: 18px;
  color: var(--muted-foreground);
  text-align: center;
  font-size: 12px;
}
</style>
