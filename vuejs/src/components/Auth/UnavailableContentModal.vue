<script setup>
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useUnavailableContentStore } from '@/stores/unavailableContent'

const store = useUnavailableContentStore()
const { visible, displayMessage } = storeToRefs(store)
const { t } = useI18n()
</script>

<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
    @click.self="store.hide()"
  >
    <div class="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 text-center space-y-4">
      <p class="text-lg font-semibold text-gray-900">{{ displayMessage }}</p>
      <button
        type="button"
        class="px-5 py-2 rounded-full bg-black text-white text-sm"
        @click="store.hide()"
      >
        {{ t('unavailable.close') }}
      </button>
    </div>
  </div>
</template>
