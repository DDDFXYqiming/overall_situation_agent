import { defineStore } from "pinia";
import { apiClient } from "@/services/apiClient";
import type { ReportPayload } from "@/services/types";
import { createChatMessage, useConversationStore } from "./conversationStore";
import { useImportStore } from "./importStore";
import { useJobsStore } from "./jobsStore";
import { useReportStore } from "./reportStore";

function commandDates(text: string): Partial<ReportPayload> {
  const dates = text.match(/\d{4}-\d{1,2}-\d{1,2}/g) || [];
  if (!dates.length) {
    return {};
  }
  return {
    start_date: dates[0],
    end_date: dates[1] || dates[0]
  };
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    sending: false,
    error: "",
    lastFailedText: ""
  }),
  getters: {
    messages() {
      return useConversationStore().activeMessages;
    },
    sessionId() {
      return useConversationStore().activeSessionId;
    }
  },
  actions: {
    appendAssistant(content: string) {
      useConversationStore().append(createChatMessage("assistant", content));
    },
    async submitJobCommand(kind: "import" | "report" | "run", sourceText?: string) {
      const importStore = useImportStore();
      const jobsStore = useJobsStore();
      const labels = { import: "数据导入", report: "报告生成", run: "导入并生成报告" };
      if ((kind === "import" || kind === "run") && !importStore.canImport) {
        this.appendAssistant("请先在右侧填写数据文件路径，或上传主数据 Excel 后再执行。");
        return;
      }
      const reportOverrides = sourceText ? commandDates(sourceText) : {};
      const payload =
        kind === "import"
          ? importStore.importPayload()
          : kind === "report"
            ? { ...importStore.reportPayload(), ...reportOverrides }
            : { ...importStore.runPayload(), ...reportOverrides };
      await jobsStore.submit(kind, payload);
      this.appendAssistant(`已提交${labels[kind]}任务。你可以在对话区任务卡和右侧 SSE 事件中查看进度。`);
    },
    async send(content: string) {
      const text = content.trim();
      if (!text || this.sending) {
        return;
      }
      const conversations = useConversationStore();
      const importStore = useImportStore();
      conversations.append(createChatMessage("user", text));
      this.sending = true;
      this.error = "";
      try {
        if (text === "/import") {
          await this.submitJobCommand("import", text);
          return;
        }
        if (text === "/run") {
          await this.submitJobCommand("run", text);
          return;
        }
        if (text === "/report" || text.startsWith("/report ")) {
          await this.submitJobCommand("report", text);
          return;
        }
        const response = await apiClient.chat({
          message: text,
          session_id: conversations.activeSessionId || null,
          schedule_input: importStore.scheduleInput || null
        });
        conversations.setSessionId(response.session_id);
        conversations.append(createChatMessage("assistant", response.answer));
        if (response.report_paths) {
          useReportStore().add(response.report_paths, "智能问答 /report");
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.error = message;
        this.lastFailedText = text;
        conversations.append(createChatMessage("assistant", `处理失败：${message}`));
      } finally {
        this.sending = false;
      }
    },
    retryLast() {
      if (this.lastFailedText) {
        const text = this.lastFailedText;
        this.lastFailedText = "";
        void this.send(text);
      }
    }
  }
});
