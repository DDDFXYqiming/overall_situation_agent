<template>
  <main class="reports-view">
    <section class="reports-head">
      <div>
        <span>REPORTS</span>
        <h2>报告中心</h2>
        <p>报告生成后会自动进入这里，支持 HTML 预览和 Markdown 下载。</p>
      </div>
      <BaseButton variant="primary" @click="chatStore.submitJobCommand('report')"><FileText :size="16" />生成报告</BaseButton>
    </section>

    <section v-if="reportStore.reports.length" class="report-list">
      <ReportCard v-for="report in reportStore.reports" :key="report.id" :report="report" />
    </section>
    <section v-else class="empty">
      <FileText :size="28" />
      <h3>暂无报告</h3>
      <p>点击生成报告，或在对话中输入 /report。</p>
    </section>

    <section v-if="reportStore.previewUrl" class="preview">
      <div>
        <strong>HTML 预览</strong>
        <BaseButton variant="ghost" @click="reportStore.setPreview('')">关闭</BaseButton>
      </div>
      <iframe :src="reportStore.previewUrl" title="报告预览" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { FileText } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import ReportCard from "@/features/reports/ReportCard.vue";
import { useChatStore } from "@/stores/chatStore";
import { useReportStore } from "@/stores/reportStore";

const chatStore = useChatStore();
const reportStore = useReportStore();
</script>

<style scoped>
.reports-view {
  min-height: 0;
  overflow: auto;
  padding: 28px clamp(18px, 4vw, 48px);
}

.reports-head,
.empty,
.preview {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: white;
  box-shadow: var(--shadow-sm);
}

.reports-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px;
}

span {
  color: var(--accent);
  font: 700 12px/1 var(--font-mono);
}

h2,
h3,
p {
  margin: 0;
}

h2 {
  margin: 8px 0;
  font-size: 22px;
}

p {
  color: var(--muted-foreground);
}

.report-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.empty {
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 240px;
  margin-top: 16px;
  color: var(--muted-foreground);
  text-align: center;
}

.preview {
  overflow: hidden;
  margin-top: 16px;
}

.preview > div {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding: 0 14px 0 18px;
}

iframe {
  width: 100%;
  height: min(66vh, 760px);
  border: 0;
}

@media (max-width: 640px) {
  .reports-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
