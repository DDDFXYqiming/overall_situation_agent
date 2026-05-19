import { defineStore } from "pinia";
import type { ChatMessage, Conversation } from "@/services/types";

const STORAGE_KEY = "overall-situation-agent-conversations";

function nowText() {
  return new Date().toLocaleString();
}

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function defaultAssistantMessage(): ChatMessage {
  return {
    id: messageId(),
    role: "assistant",
    content: "已连接本地整体情况 Agent。你可以直接提问，也可以使用右侧配置导入数据、生成报告。",
    createdAt: new Date().toLocaleTimeString()
  };
}

function createConversation(title = "新的对话"): Conversation {
  const createdAt = nowText();
  return {
    id: messageId(),
    title,
    sessionId: "",
    createdAt,
    updatedAt: createdAt,
    messages: [defaultAssistantMessage()]
  };
}

function safeLoad(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const useConversationStore = defineStore("conversations", {
  state: () => {
    const conversations = safeLoad();
    const seeded = conversations.length ? conversations : [createConversation("本周服务整体情况分析")];
    return {
      conversations: seeded,
      activeId: seeded[0].id
    };
  },
  getters: {
    activeConversation(state): Conversation {
      return state.conversations.find((item) => item.id === state.activeId) || state.conversations[0];
    },
    activeMessages(): ChatMessage[] {
      return this.activeConversation?.messages || [];
    },
    activeSessionId(): string {
      return this.activeConversation?.sessionId || "";
    }
  },
  actions: {
    persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.conversations.slice(0, 20)));
    },
    create(title = "新的对话") {
      const conversation = createConversation(title);
      this.conversations.unshift(conversation);
      this.activeId = conversation.id;
      this.persist();
    },
    switchTo(id: string) {
      if (this.conversations.some((item) => item.id === id)) {
        this.activeId = id;
        this.persist();
      }
    },
    append(message: ChatMessage) {
      const conversation = this.activeConversation;
      conversation.messages.push(message);
      conversation.updatedAt = nowText();
      if (message.role === "user" && conversation.title === "新的对话") {
        conversation.title = message.content.slice(0, 22) || "新的对话";
      }
      this.persist();
    },
    setSessionId(sessionId: string) {
      this.activeConversation.sessionId = sessionId;
      this.persist();
    },
    renameActive(title: string) {
      const cleaned = title.trim();
      if (cleaned) {
        this.activeConversation.title = cleaned.slice(0, 32);
        this.activeConversation.updatedAt = nowText();
        this.persist();
      }
    }
  }
});

export function createChatMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: messageId(),
    role,
    content,
    createdAt: new Date().toLocaleTimeString()
  };
}
