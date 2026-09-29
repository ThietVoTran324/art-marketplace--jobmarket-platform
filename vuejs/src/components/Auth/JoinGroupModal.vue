<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'joined'])

const toast = useToast()
const code = ref('')
const busy = ref(false)

function close() {
  emit('update:open', false)
}

async function submit() {
  const c = code.value.trim()
  if (c.length !== 10) {
    toast.error('Enter the 10-character group code')
    return
  }
  busy.value = true
  try {
    const { data } = await axios.post(
      '/api/messages/groups/join',
      { code: c },
      { withCredentials: true }
    )
    toast.success('Joined group')
    emit('joined', data)
    close()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Invalid code')
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
        <h3 class="text-lg font-semibold text-gray-900 mb-1">Join a group</h3>
        <p class="text-sm text-gray-500 mb-4">Enter the 10-character invite code</p>
        <input
          v-model="code"
          type="text"
          maxlength="10"
          placeholder="Ab12Cd34Ef"
          class="w-full px-3 py-2.5 rounded-xl bg-gray-100 font-mono tracking-wider outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
          @keyup.enter="submit"
        />
        <div class="flex justify-end gap-2 mt-4">
          <button type="button" class="px-4 py-2 rounded-full text-sm text-gray-600 hover:bg-gray-100" @click="close">
            Cancel
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-full text-sm font-medium text-white bg-[var(--msg-accent)] disabled:opacity-40"
            :disabled="busy"
            @click="submit"
          >
            Join
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
