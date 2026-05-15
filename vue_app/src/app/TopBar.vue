<template>
  <header class="topbar">
    <div class="connection">
      <span class="status-dot" :class="{ 'is-ok': configStore.isHealthy }" />
      <span>{{ configStore.isHealthy ? "已连接" : "连接中" }}</span>
      <strong>ES: {{ configStore.esIndex }}</strong>
    </div>

    <div class="mode-tabs" aria-label="运行模式">
      <button class="is-active">Web</button>
      <button>CLI</button>
      <button>API</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useConfigStore } from "@/stores/configStore";

const configStore = useConfigStore();
</script>

<style scoped>
.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
}

.connection {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--muted-foreground);
  font-size: 13px;
}

.connection strong {
  color: var(--accent);
  font-weight: 650;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #94a3b8;
}

.status-dot.is-ok {
  background: #10b981;
  box-shadow: 0 0 0 5px rgba(16, 185, 129, 0.12);
}

.mode-tabs {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: white;
  box-shadow: var(--shadow-sm);
}

.mode-tabs button {
  min-width: 62px;
  height: 34px;
  border: 0;
  border-right: 1px solid var(--border);
  background: transparent;
  color: var(--muted-foreground);
  font: 600 13px/1 var(--font-ui);
}

.mode-tabs button:last-child {
  border-right: 0;
}

.mode-tabs .is-active {
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: white;
}

@media (max-width: 640px) {
  .topbar {
    align-items: flex-start;
    height: auto;
    flex-direction: column;
    padding: 16px;
  }
}
</style>
