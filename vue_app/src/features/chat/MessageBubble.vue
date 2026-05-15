<template>
  <article class="message" :class="`message--${message.role}`">
    <div v-if="message.role !== 'user'" class="avatar"><Layers :size="18" /></div>
    <div class="bubble">
      <div v-if="message.role !== 'user'" class="meta">
        <strong>整体情况 Agent</strong>
        <time>{{ message.createdAt }}</time>
      </div>
      <p>{{ message.content }}</p>
    </div>
    <div v-if="message.role === 'user'" class="user-avatar"><UserRound :size="18" /></div>
  </article>
</template>

<script setup lang="ts">
import { Layers, UserRound } from "lucide-vue-next";
import type { ChatMessage } from "@/services/types";

defineProps<{ message: ChatMessage }>();
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
