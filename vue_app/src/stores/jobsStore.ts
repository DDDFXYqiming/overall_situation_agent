import { defineStore } from "pinia";
import { apiClient } from "@/services/apiClient";
import { subscribeJobEvents } from "@/services/sseClient";
import type { ChatPayload, ImportPayload, JobEvent, JobKind, JobRecord, ReportPayload, RunPayload } from "@/services/types";
import { useReportStore } from "./reportStore";

export const useJobsStore = defineStore("jobs", {
  state: () => ({
    activeJob: null as JobRecord | null,
    events: [] as JobEvent[],
    streaming: false,
    error: "",
    unsubscribe: null as null | (() => void)
  }),
  getters: {
    isBusy: (state) => state.activeJob?.status === "queued" || state.activeJob?.status === "running"
  },
  actions: {
    async submit(kind: JobKind, payload: ImportPayload | ReportPayload | RunPayload | ChatPayload) {
      this.error = "";
      this.events = [];
      this.unsubscribe?.();
      try {
        this.activeJob = await apiClient.createJob(kind, payload);
        this.streaming = true;
        this.unsubscribe = subscribeJobEvents(
          this.activeJob.job_id,
          (event) => this.events.unshift(event),
          () => {
            this.streaming = false;
            void this.refreshActiveJob(kind);
          },
          (message) => {
            this.streaming = false;
            this.error = message;
            void this.refreshActiveJob(kind);
          }
        );
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      }
    },
    async refreshActiveJob(kind?: JobKind) {
      if (!this.activeJob) {
        return;
      }
      try {
        this.activeJob = await apiClient.getJob(this.activeJob.job_id);
        if (this.activeJob.status === "completed" && this.activeJob.result && (kind === "report" || kind === "run")) {
          useReportStore().addFromUnknown(this.activeJob.result, kind === "run" ? "导入并生成" : "生成报告");
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      }
    }
  }
});
