<template>
  <form class="composer" @submit.prevent="submit">
    <textarea
      ref="textareaRef"
      v-model="draft"
      rows="2"
      placeholder="输入问题..."
      @keydown.enter.exact.prevent="submit"
      @keydown.enter.shift.exact.stop
    />
    <div class="composer-actions">
      <div class="left-actions">
        <BaseButton variant="ghost" icon-only title="查看帮助" @click="chatStore.send('/help')"><CircleHelp :size="18" /></BaseButton>
        <BaseButton variant="ghost" icon-only title="上下文" @click="chatStore.send('/context')"><AtSign :size="18" /></BaseButton>
        <BaseButton variant="ghost" icon-only title="生成报告" @click="chatStore.send('/report')"><FileText :size="18" /></BaseButton>
      </div>
      <div class="right-actions">
        <BaseButton v-if="chatStore.error" variant="danger" @click="chatStore.retryLast">重试</BaseButton>
        <BaseButton variant="secondary" @click="chatStore.send('/report')"><FileText :size="16" />生成报告</BaseButton>
        <BaseButton variant="primary" icon-only :disabled="chatStore.sending || !draft.trim()" type="submit" title="发送">
          <SendHorizontal :size="19" />
        </BaseButton>
      </div>
    </div>
    <p>{{ chatStore.sending ? "正在处理..." : "Shift + Enter 换行，Enter 发送" }}</p>
  </form>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { AtSign, CircleHelp, FileText, SendHorizontal } from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import { useChatStore } from "@/stores/chatStore";
import { useUiStore } from "@/stores/uiStore";

const chatStore = useChatStore();
const uiStore = useUiStore();
const draft = ref("");
const textareaRef = ref<HTMLTextAreaElement | null>(null);

watch(
  () => uiStore.composerFocusToken,
  async () => {
    await nextTick();
    textareaRef.value?.focus();
  }
);

async function submit() {
  const text = draft.value;
  draft.value = "";
  await chatStore.send(text);
}
</script>

<style scoped>
.composer {
  margin: 0 clamp(16px, 4vw, 56px) 22px;
  border: 1px solid rgba(0, 82, 255, 0.45);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  padding: 12px;
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.08);
}

textarea {
  width: 100%;
  min-height: 54px;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--foreground);
  font: 500 14px/1.6 var(--font-ui);
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.left-actions,
.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

p {
  margin: 8px 4px 0 0;
  text-align: right;
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 640px) {
  .composer-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .right-actions {
    justify-content: flex-end;
  }
}
</style>
