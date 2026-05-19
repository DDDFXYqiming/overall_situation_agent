import { defineStore } from "pinia";
import type { AppMode } from "@/services/types";

export const useUiStore = defineStore("ui", {
  state: () => ({
    mode: "chat" as AppMode,
    rightPanelOpen: true,
    composerFocusToken: 0
  }),
  actions: {
    setMode(mode: AppMode) {
      this.mode = mode;
      if (mode === "chat") {
        this.focusComposer();
      }
    },
    focusComposer() {
      this.composerFocusToken += 1;
    },
    toggleRightPanel() {
      this.rightPanelOpen = !this.rightPanelOpen;
    }
  }
});
