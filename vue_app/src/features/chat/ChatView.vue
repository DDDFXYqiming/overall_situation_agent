<template>
  <main class="chat-view">
    <div class="messages" ref="messagesRef">
      <MessageBubble v-for="message in chatStore.messages" :key="message.id" :message="message" />

      <section v-if="reportStore.reports.length" class="report-strip">
        <ReportCard v-for="report in reportStore.reports.slice(0, 2)" :key="report.id" :report="report" />
      </section>

      <section v-if="reportStore.previewUrl" class="preview-panel">
        <div class="preview-panel__header">
          <span>报告预览</span>
          <BaseButton variant="ghost" @click="reportStore.setPreview('')">收起</BaseButton>
        </div>
        <iframe :src="reportStore.previewUrl" title="报告预览" />
      </section>
    </div>

    <ChatComposer />
  </main>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import MessageBubble from "@/features/chat/MessageBubble.vue";
import ChatComposer from "@/features/chat/ChatComposer.vue";
import ReportCard from "@/features/reports/ReportCard.vue";
import { useChatStore } from "@/stores/chatStore";
import { useReportStore } from "@/stores/reportStore";

const chatStore = useChatStore();
const reportStore = useReportStore();
const messagesRef = ref<HTMLElement | null>(null);

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick();
    messagesRef.value?.scrollTo({ top: messagesRef.value.scrollHeight, behavior: "smooth" });
  }
);
</script>

<style scoped>
.chat-view {
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
}

.messages {
  min-height: 0;
  overflow: auto;
  padding: 28px clamp(18px, 4vw, 56px) 24px;
}

.report-strip {
  display: grid;
  gap: 12px;
  max-width: 760px;
  margin: 18px auto 0;
}

.preview-panel {
  max-width: 900px;
  margin: 18px auto 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: white;
  box-shadow: var(--shadow-lg);
}

.preview-panel__header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding: 0 14px 0 18px;
  font-weight: 700;
}

iframe {
  width: 100%;
  height: min(62vh, 720px);
  border: 0;
  background: white;
}
</style>
