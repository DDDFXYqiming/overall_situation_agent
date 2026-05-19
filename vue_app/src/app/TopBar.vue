<template>
  <header class="topbar">
    <div class="connection">
      <span class="status-dot" :class="{ 'is-ok': configStore.isHealthy }" />
      <span>{{ configStore.isHealthy ? "已连接" : "连接中" }}</span>
      <strong>ES: {{ configStore.esIndex }}</strong>
    </div>

    <div class="mode-tabs" aria-label="运行模式">
      <button :class="{ 'is-active': uiStore.mode === 'chat' }" @click="uiStore.setMode('chat')">Web</button>
      <button :class="{ 'is-active': uiStore.mode === 'cli' }" @click="uiStore.setMode('cli')">CLI</button>
      <button :class="{ 'is-active': uiStore.mode === 'api' }" @click="uiStore.setMode('api')">API</button>
    </div>

    <button
      class="panel-toggle"
      type="button"
      :title="uiStore.rightPanelOpen ? '收起配置面板' : '打开配置面板'"
      @click="uiStore.toggleRightPanel()"
    >
      <PanelRight :size="18" />
    </button>
  </header>
</template>

<script setup lang="ts">
import { PanelRight } from "lucide-vue-next";
import { useConfigStore } from "@/stores/configStore";
import { useUiStore } from "@/stores/uiStore";

const configStore = useConfigStore();
const uiStore = useUiStore();
</script>

<style scoped>
.topbar {
  position: relative;
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

.panel-toggle {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: white;
  color: var(--muted-foreground);
  cursor: pointer;
}

.panel-toggle:hover {
  color: var(--accent);
  box-shadow: var(--shadow-sm);
}

@media (max-width: 640px) {
  .topbar {
    align-items: flex-start;
    height: auto;
    flex-direction: column;
    padding: 16px;
  }

  .panel-toggle {
    position: absolute;
    top: 14px;
    right: 16px;
  }
}
</style>
