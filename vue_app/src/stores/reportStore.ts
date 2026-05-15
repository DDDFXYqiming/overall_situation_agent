import { defineStore } from "pinia";
import type { ReportItem, ReportPaths } from "@/services/types";

function isReportPaths(payload: unknown): payload is ReportPaths {
  return Boolean(payload && typeof payload === "object" && "html_path" in payload && "markdown_path" in payload);
}

export const useReportStore = defineStore("reports", {
  state: () => ({
    reports: [] as ReportItem[],
    previewUrl: ""
  }),
  getters: {
    latest: (state) => state.reports[0] || null
  },
  actions: {
    add(paths: ReportPaths, source: string) {
      const title = paths.html_path.split(/[\\/]/).pop() || "整体情况报告";
      const item: ReportItem = {
        id: `${Date.now()}-${title}`,
        title,
        source,
        createdAt: new Date().toLocaleString(),
        ...paths
      };
      this.reports = [item, ...this.reports.filter((report) => report.html_path !== paths.html_path)].slice(0, 8);
      if (paths.html_url) {
        this.previewUrl = paths.html_url;
      }
    },
    addFromUnknown(payload: unknown, source: string) {
      if (isReportPaths(payload)) {
        this.add(payload, source);
      }
    },
    setPreview(url: string | null | undefined) {
      this.previewUrl = url || "";
    }
  }
});
