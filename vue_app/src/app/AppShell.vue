<template>
  <div class="app-shell">
    <Sidebar />
    <section class="workspace">
      <TopBar />
      <ChatView />
    </section>
    <ImportPanel />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import Sidebar from "@/features/navigation/Sidebar.vue";
import TopBar from "@/app/TopBar.vue";
import ChatView from "@/features/chat/ChatView.vue";
import ImportPanel from "@/features/import/ImportPanel.vue";
import { useConfigStore } from "@/stores/configStore";
import { useImportStore } from "@/stores/importStore";
import { useJobsStore } from "@/stores/jobsStore";

const configStore = useConfigStore();
const importStore = useImportStore();
const jobsStore = useJobsStore();

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
  min-height: 100vh;
  display: grid;
  grid-template-columns: 286px minmax(520px, 1fr) 408px;
  background: var(--background);
  color: var(--foreground);
}

.workspace {
  min-width: 0;
  display: grid;
  grid-template-rows: auto 1fr;
  border-inline: 1px solid var(--border);
  background:
    radial-gradient(circle at 70% 0%, rgba(0, 82, 255, 0.06), transparent 32%),
    linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 240px minmax(0, 1fr);
  }
}

@media (max-width: 820px) {
  .app-shell {
    display: block;
  }

  .workspace {
    min-height: 100vh;
    border-inline: 0;
  }
}
</style>
