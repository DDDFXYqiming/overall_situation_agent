import { defineStore } from "pinia";
import { apiClient } from "@/services/apiClient";
import type { HealthResponse, StartupConfig } from "@/services/types";

export const useConfigStore = defineStore("config", {
  state: () => ({
    startup: null as StartupConfig | null,
    health: null as HealthResponse | null,
    loading: false,
    error: ""
  }),
  getters: {
    esIndex: (state) => state.startup?.es_index || state.health?.es_index || "tagged_feedback",
    isHealthy: (state) => state.health?.status === "ok",
    apiUrl: (state) => state.startup?.defaults.api_url || "http://127.0.0.1:8000"
  },
  actions: {
    async load() {
      this.loading = true;
      this.error = "";
      try {
        this.startup = await apiClient.startup();
        this.health = await apiClient.health();
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      } finally {
        this.loading = false;
      }
    },
    async refreshHealth() {
      try {
        this.health = await apiClient.health();
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error);
      }
    }
  }
});
