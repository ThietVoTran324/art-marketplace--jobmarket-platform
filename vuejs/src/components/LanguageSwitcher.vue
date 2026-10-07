<script setup>
import { useI18n } from 'vue-i18n'
import { useUserPreferencesStore } from '@/stores/userPreferences'

const { locale, t } = useI18n()
const prefs = useUserPreferencesStore()

function pick(code) {
  prefs.setLocale(code)
}
</script>

<template>
  <div
    class="fixed top-3 right-4 z-[100] flex items-center gap-0.5 rounded-full bg-white/95 dark:bg-gray-900/95 shadow-md border border-gray-200 dark:border-gray-700 p-0.5"
    role="group"
    :aria-label="t('lang.switchLabel')"
  >
    <button
      type="button"
      class="min-w-[2.25rem] px-2.5 py-1.5 rounded-full text-xs font-semibold transition"
      :class="
        locale === 'en'
          ? 'bg-stone-900 text-white'
          : 'text-stone-600 hover:bg-stone-100'
      "
      :aria-pressed="locale === 'en'"
      @click="pick('en')"
    >
      {{ t('lang.en') }}
    </button>
    <button
      type="button"
      class="min-w-[2.25rem] px-2.5 py-1.5 rounded-full text-xs font-semibold transition"
      :class="
        locale === 'vi'
          ? 'bg-stone-900 text-white'
          : 'text-stone-600 hover:bg-stone-100'
      "
      :aria-pressed="locale === 'vi'"
      @click="pick('vi')"
    >
      {{ t('lang.vi') }}
    </button>
  </div>
</template>
