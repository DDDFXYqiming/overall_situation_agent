<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark"><Layers :size="21" /></div>
      <div>
        <h1>整体情况 Agent</h1>
        <p>web · cli · api</p>
      </div>
    </div>

    <BaseButton class="new-chat" variant="primary" @click="chatStore.send('/help')">
      <Plus :size="18" />
      新建对话
      <kbd>⌘ K</kbd>
    </BaseButton>

    <nav class="nav-list" aria-label="主功能">
      <button class="is-active"><MessageCircle :size="18" />智能问答</button>
      <button @click="chatStore.send('你能做什么')"><TerminalSquare :size="18" />CLI 代理</button>
      <button @click="configStore.refreshHealth()"><Workflow :size="18" />API 工作流</button>
    </nav>

    <section class="history">
      <div class="section-title">
        <span>历史对话</span>
        <Search :size="16" />
      </div>
      <button v-for="item in historyItems" :key="item.title">
        <MessageCircle :size="15" />
        <span>{{ item.title }}</span>
        <time>{{ item.time }}</time>
      </button>
    </section>

    <section class="quick">
      <div class="section-title">快捷操作</div>
      <button @click="chatStore.send('/context')"><Info :size="16" />查看上下文</button>
      <button @click="chatStore.send('/report')"><FileText :size="16" />生成报告</button>
      <button @click="configStore.refreshHealth()"><RefreshCw :size="16" />检查 API</button>
    </section>

    <div class="account">
      <span>SA</span>
      <strong>super_admin</strong>
      <ChevronDown :size="16" />
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  ChevronDown,
  FileText,
  Info,
  Layers,
  MessageCircle,
  Plus,
  RefreshCw,
  Search,
  TerminalSquare,
  Workflow
} from "lucide-vue-next";
import BaseButton from "@/components/ui/BaseButton.vue";
import { useChatStore } from "@/stores/chatStore";
import { useConfigStore } from "@/stores/configStore";

const chatStore = useChatStore();
const configStore = useConfigStore();

const historyItems = [
  { title: "本周服务整体情况分析", time: "10:24" },
  { title: "投诉趋势与高频问题", time: "昨天" },
  { title: "接口错误率排查", time: "昨天" },
  { title: "服务满意度汇总", time: "5/19" },
  { title: "月度报告生成", time: "5/16" },
  { title: "数据导入结果检查", time: "5/15" }
];
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 22px 18px;
  background: rgba(250, 250, 250, 0.95);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: white;
  box-shadow: var(--shadow-accent);
}

h1 {
  margin: 0;
  font: 700 19px/1.1 var(--font-ui);
  letter-spacing: 0;
}

.brand p {
  margin: 4px 0 0;
  color: var(--muted-foreground);
  font: 500 12px/1 var(--font-mono);
}

.new-chat {
  width: 100%;
  justify-content: flex-start;
}

kbd {
  margin-left: auto;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.18);
  padding: 4px 7px;
  font: 600 11px/1 var(--font-ui);
}

.nav-list,
.history,
.quick {
  display: grid;
  gap: 6px;
}

.nav-list {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.nav-list button,
.history button,
.quick button {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--foreground);
  padding: 0 10px;
  text-align: left;
  font: 600 13px/1 var(--font-ui);
  cursor: pointer;
}

.nav-list button:hover,
.history button:hover,
.quick button:hover,
.nav-list .is-active,
.history button:first-of-type {
  background: rgba(0, 82, 255, 0.08);
  color: var(--accent);
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 4px 6px;
  color: var(--muted-foreground);
  font: 700 12px/1 var(--font-ui);
}

.history button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history time {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
}

.quick {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.account {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.account span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #94a3b8;
  color: white;
  font-weight: 700;
}

.account strong {
  min-width: 0;
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 820px) {
  .sidebar {
    min-height: auto;
    gap: 12px;
    padding: 18px;
  }

  .nav-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding-bottom: 10px;
  }

  .nav-list button {
    justify-content: center;
    min-width: 0;
    padding: 0 8px;
    font-size: 12px;
  }

  .history,
  .quick,
  .account {
    display: none;
  }
}
</style>
