import { defineStore } from 'pinia'
import { setLocale, readStoredLocale, SUPPORTED_LOCALES } from '@/i18n'

export const PREFS_STORAGE_KEY = 'app_user_preferences'

const DEFAULTS = {
  theme: 'system', // light | dark | system
  reduceMotion: false,
  feedDensity: 'comfortable', // comfortable | compact
  notifications: {
    likes: true,
    comments: true,
    follows: true,
    messages: true,
    jobApps: true,
    marketplace: true,
  },
  privacy: {
    profileDiscoverable: true,
    showSavedBoards: true,
    allowMessagesFrom: 'everyone', // everyone | followers | none
  },
}

function readStoredPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_STORAGE_KEY)
    if (!raw) return { ...DEFAULTS, notifications: { ...DEFAULTS.notifications }, privacy: { ...DEFAULTS.privacy } }
    const parsed = JSON.parse(raw)
    return {
      theme: ['light', 'dark', 'system'].includes(parsed.theme) ? parsed.theme : DEFAULTS.theme,
      reduceMotion: Boolean(parsed.reduceMotion),
      feedDensity: parsed.feedDensity === 'compact' ? 'compact' : 'comfortable',
      notifications: { ...DEFAULTS.notifications, ...(parsed.notifications || {}) },
      privacy: { ...DEFAULTS.privacy, ...(parsed.privacy || {}) },
    }
  } catch {
    return { ...DEFAULTS, notifications: { ...DEFAULTS.notifications }, privacy: { ...DEFAULTS.privacy } }
  }
}

function resolvedTheme(theme) {
  if (theme === 'light' || theme === 'dark') return theme
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export const useUserPreferencesStore = defineStore('userPreferences', {
  state: () => ({
    ...readStoredPrefs(),
    locale: readStoredLocale(),
    _mediaQuery: null,
  }),

  getters: {
    effectiveTheme(state) {
      return resolvedTheme(state.theme)
    },
  },

  actions: {
    persist() {
      try {
        localStorage.setItem(
          PREFS_STORAGE_KEY,
          JSON.stringify({
            theme: this.theme,
            reduceMotion: this.reduceMotion,
            feedDensity: this.feedDensity,
            notifications: this.notifications,
            privacy: this.privacy,
          })
        )
      } catch {
        /* ignore */
      }
      this.applyToDocument()
    },

    applyToDocument() {
      if (typeof document === 'undefined') return
      const root = document.documentElement
      const mode = resolvedTheme(this.theme)
      root.classList.toggle('dark', mode === 'dark')
      root.dataset.theme = mode
      root.dataset.feedDensity = this.feedDensity
      root.classList.toggle('reduce-motion', this.reduceMotion)
      root.style.colorScheme = mode
    },

    init() {
      this.applyToDocument()
      if (typeof window === 'undefined') return
      if (this._mediaQuery) return
      this._mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const onChange = () => {
        if (this.theme === 'system') this.applyToDocument()
      }
      if (this._mediaQuery.addEventListener) {
        this._mediaQuery.addEventListener('change', onChange)
      } else if (this._mediaQuery.addListener) {
        this._mediaQuery.addListener(onChange)
      }
    },

    setLocale(code) {
      if (!SUPPORTED_LOCALES.includes(code)) return
      this.locale = code
      setLocale(code)
    },

    setTheme(theme) {
      if (!['light', 'dark', 'system'].includes(theme)) return
      this.theme = theme
      this.persist()
    },

    setReduceMotion(value) {
      this.reduceMotion = Boolean(value)
      this.persist()
    },

    setFeedDensity(value) {
      this.feedDensity = value === 'compact' ? 'compact' : 'comfortable'
      this.persist()
    },

    setNotification(key, value) {
      if (!(key in this.notifications)) return
      this.notifications[key] = Boolean(value)
      this.persist()
    },

    setPrivacy(key, value) {
      if (!(key in this.privacy)) return
      this.privacy[key] = value
      this.persist()
    },
  },
})
