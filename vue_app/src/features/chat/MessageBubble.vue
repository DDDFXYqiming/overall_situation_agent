<template>
  <article class="message" :class="`message--${message.role}`">
    <div v-if="message.role !== 'user'" class="avatar"><Layers :size="18" /></div>
    <div class="bubble">
      <div v-if="message.role !== 'user'" class="meta">
        <strong>整体情况 Agent</strong>
        <time>{{ message.createdAt }}</time>
      </div>
      <div v-if="message.role !== 'user'" class="markdown-content" v-html="renderedContent"></div>
      <p v-else>{{ message.content }}</p>
    </div>
    <div v-if="message.role === 'user'" class="user-avatar"><UserRound :size="18" /></div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Layers, UserRound } from "lucide-vue-next";
import { marked } from "marked";
import type { ChatMessage } from "@/services/types";

const props = defineProps<{ message: ChatMessage }>();

// Configure marked for better compatibility
marked.setOptions({
  breaks: true, // Convert \n to <br>
  gfm: true, // GitHub Flavored Markdown
});

const renderedContent = computed(() => {
  try {
    return marked.parse(props.message.content) as string;
  } catch (e) {
    console.error("Markdown parse error:", e);
    return props.message.content;
  }
});
</script>

<style scoped>
.message {
  display: grid;
  grid-template-columns: 42px minmax(0, 720px) 42px;
  gap: 12px;
  align-items: flex-start;
  max-width: 860px;
  margin: 0 auto 18px;
}

.message--user {
  justify-content: end;
}

.avatar,
.user-avatar {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
}

.avatar {
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: white;
  box-shadow: var(--shadow-accent);
}

.user-avatar {
  grid-column: 3;
  background: var(--muted);
  color: var(--muted-foreground);
}

.bubble {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  padding: 15px 17px;
  box-shadow: var(--shadow-sm);
}

.message--user .bubble {
  grid-column: 2;
  justify-self: end;
  max-width: 620px;
  border-color: rgba(0, 82, 255, 0.12);
  background: rgba(0, 82, 255, 0.06);
}

.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.meta strong {
  font-size: 13px;
}

.meta time {
  color: #94a3b8;
  font-size: 12px;
}

/* Markdown content styles */
.markdown-content {
  margin: 0;
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
  line-height: 1.3;
}

.markdown-content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
}

.markdown-content :deep(h2) {
  font-size: 1.3em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}

.markdown-content :deep(h3) {
  font-size: 1.15em;
}

.markdown-content :deep(p) {
  margin: 0 0 12px 0;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 4px 0;
}

.markdown-content :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "Fira Code", "Consolas", "Monaco", monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  font-size: 13px;
  line-height: 1.5;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
  font-size: inherit;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid var(--accent);
  margin: 12px 0;
  padding: 8px 16px;
  background: rgba(0, 82, 255, 0.04);
  border-radius: 0 8px 8px 0;
  color: var(--muted-foreground);
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 13px;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--border);
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: var(--muted);
  font-weight: 600;
}

.markdown-content :deep(tr:nth-child(even)) {
  background: rgba(0, 0, 0, 0.02);
}

.markdown-content :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 16px 0;
}

.markdown-content :deep(strong) {
  font-weight: 600;
}

.markdown-content :deep(em) {
  font-style: italic;
}

/* User message styles */
p {
  margin: 0;
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .message {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .user-avatar {
    display: none;
  }

  .message--user .bubble {
    grid-column: 2;
  }
}
</style>
