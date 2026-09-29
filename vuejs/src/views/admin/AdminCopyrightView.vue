<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const rows = ref([])
const loading = ref(false)
const statusFilter = ref('open')
const noteById = ref({})
const busyId = ref(null)

async function load() {
  loading.value = true
  try {
    const params = { limit: 50 }
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await axios.get('/api/admin/copyright-reports', { params })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function decide(row, status) {
  busyId.value = row.id
  const note = (noteById.value[row.id] || '').trim() || null
  try {
    await axios.patch(`/api/admin/copyright-reports/${row.id}`, {
      status,
      admin_note: note,
    })
    toast.success(status === 'resolved' ? 'Resolved — related listing unpublished if any' : 'Dismissed')
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <label class="text-sm">
        Status
        <select v-model="statusFilter" class="ml-2 border rounded-md px-2 py-1" @change="load">
          <option value="open">open</option>
          <option value="resolved">resolved</option>
          <option value="dismissed">dismissed</option>
        </select>
      </label>
      <button type="button" class="text-sm underline" @click="load">Refresh</button>
    </div>

    <p class="text-sm text-gray-600">
      Resolve unlists the pin’s marketplace listing. Dismiss does not. Paid licenses are not revoked.
    </p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">Id</th>
            <th class="px-3 py-2">Pin</th>
            <th class="px-3 py-2">Reporter</th>
            <th class="px-3 py-2">Reason</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2">
              <a :href="`/pin/${row.pin_id}`" class="underline" target="_blank" rel="noopener">
                #{{ row.pin_id }}
              </a>
            </td>
            <td class="px-3 py-2">{{ row.reporter_user_id }}</td>
            <td class="px-3 py-2 max-w-xs break-words">{{ row.reason }}</td>
            <td class="px-3 py-2">{{ row.status }}</td>
            <td class="px-3 py-2 space-y-2 min-w-[220px]">
              <template v-if="row.status === 'open'">
                <input
                  v-model="noteById[row.id]"
                  class="w-full border rounded-md px-2 py-1"
                  placeholder="Optional note"
                />
                <div class="flex flex-wrap gap-2">
                  <button
                    type="button"
                    class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="decide(row, 'resolved')"
                  >
                    Resolve
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="decide(row, 'dismissed')"
                  >
                    Dismiss
                  </button>
                </div>
              </template>
              <span v-else class="text-gray-500">{{ row.admin_note || '—' }}</span>
            </td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-center text-gray-500">No reports</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
