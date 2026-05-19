<template>
  <div class="app-shell" :class="{ 'right-closed': !uiStore.rightPanelOpen }">
    <Sidebar />
    <section class="workspace">
      <TopBar />
      <ChatView v-if="uiStore.mode === 'chat'" />
      <CliWorkbench v-else-if="uiStore.mode === 'cli'" />
      <ApiWorkbench v-else-if="uiStore.mode === 'api'" />
      <ReportsView v-else-if="uiStore.mode === 'reports'" />
      <ChatView v-else />
    </section>
    <ImportPanel :class="{ 'is-collapsed': !uiStore.rightPanelOpen }" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import Sidebar from "@/features/navigation/Sidebar.vue";
import TopBar from "@/app/TopBar.vue";
import ChatView from "@/features/chat/ChatView.vue";
import ImportPanel from "@/features/import/ImportPanel.vue";
import ApiWorkbench from "@/features/api/ApiWorkbench.vue";
import CliWorkbench from "@/features/cli/CliWorkbench.vue";
import ReportsView from "@/features/reports/ReportsView.vue";
import { useConfigStore } from "@/stores/configStore";
import { useImportStore } from "@/stores/importStore";
import { useJobsStore } from "@/stores/jobsStore";
import { useUiStore } from "@/stores/uiStore";

const configStore = useConfigStore();
const importStore = useImportStore();
const jobsStore = useJobsStore();
const uiStore = useUiStore();

onMounted(async () => {
  await configStore.load();
  importStore.applyDefaults(configStore.startup?.defaults);
  if (importStore.inputPath) {
    await jobsStore.submit("import", importStore.importPayload());
  }
});
</script>

<style scoped>
.app-shell {
  height: 100dvh;
  min-height: 0;
  display: grid;
  grid-template-columns: 286px minmax(520px, 1fr) 408px;
  overflow: hidden;
  background: var(--background);
  color: var(--foreground);
}

.app-shell.right-closed {
  grid-template-columns: 286px minmax(520px, 1fr);
}

.workspace {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
  border-inline: 1px solid var(--border);
  background:
    radial-gradient(circle at 70% 0%, rgba(0, 82, 255, 0.06), transparent 32%),
    linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 240px minmax(0, 1fr) minmax(330px, 380px);
  }

  .app-shell.right-closed {
    grid-template-columns: 240px minmax(0, 1fr);
  }
}

@media (max-width: 820px) {
  .app-shell {
    height: auto;
    min-height: 100dvh;
    display: grid;
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .workspace {
    min-height: 100dvh;
    border-inline: 0;
  }
}
</style>
