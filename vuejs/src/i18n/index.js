import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import vi from './locales/vi.json'

export const LOCALE_STORAGE_KEY = 'app_locale'
export const SUPPORTED_LOCALES = ['en', 'vi']

export function readStoredLocale() {
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (SUPPORTED_LOCALES.includes(saved)) return saved
  } catch {
    /* ignore */
  }
  return 'en'
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: readStoredLocale(),
  fallbackLocale: 'en',
  messages: { en, vi },
})

export function setLocale(locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return
  i18n.global.locale.value = locale
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    /* ignore */
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

export function initDocumentLang() {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = i18n.global.locale.value
  }
}
