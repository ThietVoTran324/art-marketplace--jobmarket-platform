<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const props = defineProps({
  open: { type: Boolean, default: false },
  pinId: { type: [Number, String], required: true },
})

const emit = defineEmits(['update:open', 'shared'])

const toast = useToast()
const q = ref('')
const targets = ref([])
const loading = ref(false)
const sharingId = ref(null)
let timer = null

const pinUrl = computed(() => {
  if (typeof window === 'undefined') return `/pin/${props.pinId}`
  return `${window.location.origin}/pin/${props.pinId}`
})

async function loadTargets() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/messages/share-targets', {
      params: { q: q.value.trim() || undefined },
      withCredentials: true,
    })
    targets.value = data || []
  } catch (e) {
    console.error(e)
    targets.value = []
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  clearTimeout(timer)
  timer = setTimeout(loadTargets, 250)
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(pinUrl.value)
    toast.success('Link copied')
  } catch {
    toast.error('Could not copy')
  }
}

async function shareTo(target) {
  sharingId.value = target.user_id
  try {
    const body = { pin_id: Number(props.pinId) }
    if (target.chat_id) body.chat_id = target.chat_id
    else body.to_user_id = target.user_id
    await axios.post('/api/messages/share-pin', body, { withCredentials: true })
    toast.success(`Shared with ${target.username}`)
    emit('shared', target)
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Share failed')
  } finally {
    sharingId.value = null
  }
}

function close() {
  emit('update:open', false)
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      q.value = ''
      loadTargets()
    }
  }
)

onMounted(() => {
  if (props.open) loadTargets()
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[80] flex justify-end">
      <div class="absolute inset-0 bg-black/45" @click="close" />
      <aside
        class="relative z-10 h-full w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in"
        role="dialog"
        aria-label="Share pin"
      >
        <div class="h-14 px-4 flex items-center justify-between border-b border-gray-100 shrink-0">
          <h2 class="text-lg font-semibold text-gray-900">Share</h2>
          <button
            type="button"
            class="w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center"
            @click="close"
          >
            <i class="pi pi-times text-lg text-gray-600" />
          </button>
        </div>

        <!-- Link copy -->
        <div class="p-4 border-b border-gray-100 shrink-0">
          <p class="text-xs font-medium text-gray-500 mb-2">Pin link</p>
          <div class="flex items-center gap-2">
            <input
              :value="pinUrl"
              readonly
              class="flex-1 min-w-0 text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 truncate"
            />
            <button
              type="button"
              class="shrink-0 px-3 py-2 rounded-xl text-sm font-medium text-white bg-[var(--msg-accent,#e11d48)]"
              @click="copyUrl"
            >
              Copy
            </button>
          </div>
        </div>

        <div class="px-4 pt-3 pb-2 shrink-0">
          <p class="text-sm font-semibold text-gray-800 mb-2">Send in Messages</p>
          <div class="relative">
            <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
            <input
              v-model="q"
              type="search"
              placeholder="Search people"
              class="w-full pl-9 pr-3 py-2 text-sm rounded-full bg-gray-100 outline-none focus:ring-2 focus:ring-[var(--msg-accent,#e11d48)]"
              @input="onSearchInput"
            />
          </div>
          <p class="text-[11px] text-gray-400 mt-1.5">
            Chats and people you follow only
          </p>
        </div>

        <div class="flex-1 overflow-y-auto min-h-0 px-2 pb-4">
          <div v-if="loading" class="p-4 space-y-3 animate-pulse">
            <div v-for="n in 6" :key="n" class="h-12 bg-gray-100 rounded-xl" />
          </div>
          <p v-else-if="!targets.length" class="text-center text-sm text-gray-500 py-10">
            No people to share with yet
          </p>
          <button
            v-for="t in targets"
            :key="t.user_id"
            type="button"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left"
            :disabled="sharingId === t.user_id"
            @click="shareTo(t)"
          >
            <div
              class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-sm font-semibold text-gray-600"
            >
              {{ (t.username || '?')[0].toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-gray-900 truncate">{{ t.username }}</p>
              <p class="text-xs text-gray-400">{{ t.source === 'chat' ? 'Chat' : 'Following' }}</p>
            </div>
            <i
              class="pi pi-send text-[var(--msg-accent,#e11d48)]"
              :class="sharingId === t.user_id ? 'opacity-40' : ''"
            />
          </button>
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.animate-slide-in {
  animation: slideIn 0.22s ease-out;
}
@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
</style>
