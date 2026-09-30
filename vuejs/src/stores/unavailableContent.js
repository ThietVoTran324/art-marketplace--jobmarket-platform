import { defineStore } from 'pinia'
import { i18n } from '@/i18n'

export const useUnavailableContentStore = defineStore('unavailable_content', {
  state: () => ({
    visible: false,
    message: null,
  }),
  getters: {
    displayMessage(state) {
      return state.message || i18n.global.t('unavailable.default')
    },
  },
  actions: {
    show(message) {
      this.message = message || null
      this.visible = true
    },
    hide() {
      this.visible = false
    },
  },
})
