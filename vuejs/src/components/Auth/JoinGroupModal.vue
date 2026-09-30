<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'joined'])

const toast = useToast()
const { t } = useI18n()
const code = ref('')
const busy = ref(false)

function close() {
  emit('update:open', false)
}

async function submit() {
  const c = code.value.trim()
  if (c.length !== 10) {
    toast.error(t('chat.joinGroupModal.toastInvalidLength'))
    return
  }
  busy.value = true
  try {
    const { data } = await axios.post(
      '/api/messages/groups/join',
      { code: c },
      { withCredentials: true }
    )
    toast.success(t('chat.joinGroupModal.toastJoined'))
    emit('joined', data)
    close()
  } catch (e) {
    toast.error(e?.response?.data?.detail || t('chat.joinGroupModal.toastInvalidCode'))
  } finally {
    busy.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) code.value = ''
  }
)
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/45" @click="close" />
      <div class="relative z-10 w-full max-w-sm bg-white rounded-2xl shadow-xl p-5">
        <h3 class="text-lg font-semibold text-gray-900 mb-1">{{ t('chat.joinGroupModal.title') }}</h3>
        <p class="text-sm text-gray-500 mb-4">{{ t('chat.joinGroupModal.subtitle') }}</p>
        <input
          v-model="code"
          type="text"
          maxlength="10"
          :placeholder="t('chat.joinGroupModal.codePlaceholder')"
          class="w-full px-3 py-2.5 rounded-xl bg-gray-100 font-mono tracking-wider outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
          @keyup.enter="submit"
        />
        <div class="flex justify-end gap-2 mt-4">
          <button type="button" class="px-4 py-2 rounded-full text-sm text-gray-600 hover:bg-gray-100" @click="close">
            {{ t('chat.joinGroupModal.cancel') }}
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-full text-sm font-medium text-white bg-[var(--msg-accent)] disabled:opacity-40"
            :disabled="busy"
            @click="submit"
          >
            {{ t('chat.joinGroupModal.join') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
