import { defineStore } from "pinia";
import { apiClient } from "@/services/apiClient";
import type { ImportPayload, ReportPayload, RunPayload, StartupDefaults } from "@/services/types";

export const useImportStore = defineStore("import", {
  state: () => ({
    inputPath: "",
    scheduleInput: "",
    recreateIndex: false,
    startDate: "",
    endDate: "",
    output: "",
    uploading: false,
    uploadMessage: "",
    error: ""
  }),
  getters: {
    canImport: (state) => state.inputPath.trim().length > 0,
    hasDateFilter: (state) => Boolean(state.startDate || state.endDate)
  },
  actions: {
    applyDefaults(defaults?: StartupDefaults) {
      if (!defaults) {
        return;
      }
      this.inputPath = defaults.import_input || this.inputPath;
      this.scheduleInput = defaults.schedule_input || this.scheduleInput;
      this.recreateIndex = Boolean(defaults.recreate_index);
      this.startDate = defaults.start_date || "";
      this.endDate = defaults.end_date || "";
      this.output = defaults.output || "";
    },
    importPayload(): ImportPayload {
      return {
        input: this.inputPath.trim(),
        recreate_index: this.recreateIndex
      };
    },
    reportPayload(): ReportPayload {
      return {
        output: this.output.trim() || null,
        start_date: this.startDate || null,
        end_date: this.endDate || null,
        schedule_input: this.scheduleInput.trim() || null
      };
    },
    runPayload(): RunPayload {
      return {
        ...this.reportPayload(),
        input: this.inputPath.trim(),
        recreate_index: this.recreateIndex
      };
    },
    async uploadInputFiles(files: File[]) {
      if (!files.length) {
        return;
      }
      this.uploading = true;
      this.error = "";
      try {
        const result = await apiClient.upload(files);
        this.inputPath = result.input_path;
        this.uploadMessage = `已上传 ${result.count} 个主数据文件`;
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      } finally {
        this.uploading = false;
      }
    },
    async uploadScheduleFile(files: File[]) {
      if (!files.length) {
        return;
      }
      this.uploading = true;
      this.error = "";
      try {
        const result = await apiClient.upload(files.slice(0, 1));
        this.scheduleInput = result.input_path;
        this.uploadMessage = "已上传赛程文件";
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      } finally {
        this.uploading = false;
      }
    }
  }
});
