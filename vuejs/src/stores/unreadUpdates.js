import { defineStore } from "pinia";
import axios from "axios";

export const useUnreadUpdatesStore = defineStore("unread_updates", {
  state: () => ({
    count: 0,
  }),
  actions: {
    async fetchUnreadUpdates() {
      try {
        const response = await axios.get("/api/updates/count", {
          withCredentials: true,
        });
        const n = Number(response.data);
        this.count = Number.isFinite(n) && n > 0 ? n : 0;
      } catch (error) {
        console.error("Error fetching unread updates:", error);
      }
    },
    increment() {
      this.count++;
    },
    decrement() {
      if (this.count > 0) this.count--;
    },
  },
});
