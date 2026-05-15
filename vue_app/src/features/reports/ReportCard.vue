<template>
  <article class="report-card">
    <div class="pdf-icon"><FileText :size="24" /></div>
    <div class="report-main">
      <strong>{{ report.title }}</strong>
      <span>{{ report.source }} · {{ report.createdAt }}</span>
      <small>{{ report.html_path }}</small>
    </div>
    <div class="report-actions">
      <BaseButton v-if="report.html_url" variant="ghost" @click="reportStore.setPreview(report.html_url)">
        <Eye :size="16" />预览
      </BaseButton>
      <a v-if="report.markdown_url" :href="report.markdown_url" target="_blank" rel="noreferrer">
        <Download :size="16" />下载
      </a>
    </div>
  </article>
</template>

<script setup lang="ts">
import { Download, Eye, FileText } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import type { ReportItem } from "@/services/types";
import { useReportStore } from "@/stores/reportStore";

defineProps<{ report: ReportItem }>();

const reportStore = useReportStore();
</script>

<style scoped>
.report-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.94);
  padding: 12px 14px;
  box-shadow: var(--shadow-sm);
}

.pdf-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  color: #ef4444;
}

.report-main {
  min-width: 0;
  display: grid;
  gap: 4px;
}

strong,
span,
small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

strong {
  font-size: 13px;
}

span,
small {
  color: var(--muted-foreground);
  font-size: 12px;
}

.report-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

a {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 10px;
  padding: 0 12px;
  color: var(--accent);
  font-weight: 700;
  font-size: 13px;
  text-decoration: none;
}

a:hover {
  background: rgba(0, 82, 255, 0.08);
}

@media (max-width: 640px) {
  .report-card {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .report-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>
