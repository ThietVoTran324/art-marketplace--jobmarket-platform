import { defineStore } from 'pinia';

export const useUnavailableContentStore = defineStore('unavailable_content', {
  state: () => ({
    visible: false,
    message: 'Nội dung đã bị ẩn hoặc xóa',
  }),
  actions: {
    show(message) {
      if (message) this.message = message;
      else this.message = 'Nội dung đã bị ẩn hoặc xóa';
      this.visible = true;
    },
    hide() {
      this.visible = false;
    },
  },
});
