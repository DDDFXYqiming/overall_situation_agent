import { defineStore } from "pinia";
import { apiClient } from "@/services/apiClient";
import type { ChatMessage } from "@/services/types";
import { useImportStore } from "./importStore";
import { useReportStore } from "./reportStore";

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    sessionId: "",
    messages: [
      {
        id: messageId(),
        role: "assistant",
        content: "已连接本地整体情况 Agent。你可以直接提问，也可以使用右侧配置导入数据、生成报告。",
        createdAt: new Date().toLocaleTimeString()
      }
    ] as ChatMessage[],
    sending: false,
    error: ""
  }),
  actions: {
    async send(content: string) {
      const text = content.trim();
      if (!text || this.sending) {
        return;
      }
      const importStore = useImportStore();
      this.messages.push({
        id: messageId(),
        role: "user",
        content: text,
        createdAt: new Date().toLocaleTimeString()
      });
      this.sending = true;
      this.error = "";
      try {
        const response = await apiClient.chat({
          message: text,
          session_id: this.sessionId || null,
          schedule_input: importStore.scheduleInput || null
        });
        this.sessionId = response.session_id;
        this.messages.push({
          id: messageId(),
          role: "assistant",
          content: response.answer,
          createdAt: new Date().toLocaleTimeString()
        });
        if (response.report_paths) {
          useReportStore().add(response.report_paths, "智能问答 /report");
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.error = message;
        this.messages.push({
          id: messageId(),
          role: "assistant",
          content: `处理失败：${message}`,
          createdAt: new Date().toLocaleTimeString()
        });
      } finally {
        this.sending = false;
      }
    }
  }
});
