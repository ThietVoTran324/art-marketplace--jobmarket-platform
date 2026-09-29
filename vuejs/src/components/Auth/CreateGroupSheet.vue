<script setup>
import { onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'created'])

const toast = useToast()
const q = ref('')
const title = ref('')
const targets = ref([])
const selected = ref(new Set())
const loading = ref(false)
const submitting = ref(false)
let timer = null

async function loadTargets() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/messages/share-targets', {
      params: { q: q.value.trim() || undefined, limit: 80 },
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

function toggle(id) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function isSelected(id) {
  return selected.value.has(id)
}

async function submit() {
  if (!selected.value.size) {
    toast.error('Select at least one person')
    return
  }
  submitting.value = true
  try {
    const { data } = await axios.post(
      '/api/messages/groups',
      {
        title: title.value.trim() || null,
        member_ids: [...selected.value],
      },
      { withCredentials: true }
    )
    toast.success('Group created')
    emit('created', data)
    close()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Could not create group')
  } finally {
    submitting.value = false
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
      title.value = ''
      selected.value = new Set()
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
      <aside class="relative z-10 h-full w-full max-w-md bg-white shadow-2xl flex flex-col">
        <div class="h-14 px-4 flex items-center justify-between border-b border-gray-100">
          <h2 class="text-lg font-semibold">New group</h2>
          <button type="button" class="w-9 h-9 rounded-full hover:bg-gray-100" @click="close">
            <i class="pi pi-times text-lg text-gray-600" />
          </button>
        </div>

        <div class="p-4 space-y-3 border-b border-gray-100">
          <input
            v-model="title"
            type="text"
            placeholder="Group name (optional)"
            class="w-full px-3 py-2 text-sm rounded-xl bg-gray-100 outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
          />
          <div class="relative">
            <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
            <input
              v-model="q"
              type="search"
              placeholder="Search people"
              class="w-full pl-9 pr-3 py-2 text-sm rounded-full bg-gray-100 outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
              @input="onSearchInput"
            />
          </div>
        </div>

        <div class="flex-1 overflow-y-auto px-2 py-2">
          <div v-if="loading" class="p-4 space-y-3 animate-pulse">
            <div v-for="n in 6" :key="n" class="h-12 bg-gray-100 rounded-xl" />
          </div>
          <label
            v-for="t in targets"
            :key="t.user_id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 cursor-pointer"
          >
            <div
              class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-sm font-semibold"
            >
              {{ (t.username || '?')[0].toUpperCase() }}
            </div>
            <span class="flex-1 font-medium truncate">{{ t.username }}</span>
            <input
              type="checkbox"
              class="w-5 h-5 accent-[var(--msg-accent)]"
              :checked="isSelected(t.user_id)"
              @change="toggle(t.user_id)"
            />
          </label>
        </div>

        <div class="p-4 border-t border-gray-100 flex justify-end">
          <button
            type="button"
            class="px-5 py-2.5 rounded-full text-sm font-medium text-white bg-[var(--msg-accent)] disabled:opacity-40"
            :disabled="submitting || !selected.size"
            @click="submit"
          >
            Create
          </button>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
