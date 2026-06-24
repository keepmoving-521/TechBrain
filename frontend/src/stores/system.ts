import { defineStore } from "pinia";

import { healthApi, type HealthResponse } from "@/services/health";
import { getErrorMessage } from "@/utils/errors";

interface SystemState {
  health: HealthResponse | null;
  loading: boolean;
  lastError: string;
}

export const useSystemStore = defineStore("system", {
  state: (): SystemState => ({
    health: null,
    loading: false,
    lastError: "",
  }),
  actions: {
    async refreshHealth() {
      this.loading = true;
      this.lastError = "";

      try {
        this.health = await healthApi.getLive();
      } catch (error) {
        this.health = null;
        this.lastError = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
  },
});
