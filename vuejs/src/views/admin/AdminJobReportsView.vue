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
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await axios.get('/api/job-market/admin/job-reports', { params })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function resolve(row, action) {
  busyId.value = row.id
  const note = (noteById.value[row.id] || '').trim() || null
  try {
    await axios.post(
      `/api/job-market/admin/job-reports/${row.id}/${action}`,
      note ? { note } : {}
    )
    toast.success(action === 'dismiss' ? 'Dismissed' : 'Marked actioned')
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

async function suspend(row) {
  if (!row.company_id) {
    toast.error('No company linked to this report')
    return
  }
  const reason = window.prompt(`Suspend company #${row.company_id} — reason:`)
  if (!reason || !reason.trim()) return
  if (!window.confirm(`Suspend company #${row.company_id}?`)) return
  busyId.value = row.id
  try {
    await axios.post(`/api/job-market/admin/companies/${row.company_id}/suspend`, {
      reason: reason.trim(),
    })
    toast.success('Company suspended')
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

async function unsuspend(row) {
  if (!row.company_id) {
    toast.error('No company linked to this report')
    return
  }
  if (!window.confirm(`Unsuspend company #${row.company_id}?`)) return
  busyId.value = row.id
  try {
    await axios.post(`/api/job-market/admin/companies/${row.company_id}/unsuspend`)
    toast.success('Company unsuspended')
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
          <option value="dismissed">dismissed</option>
          <option value="actioned">actioned</option>
        </select>
      </label>
      <button type="button" class="text-sm underline" @click="load">Refresh</button>
    </div>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">Id</th>
            <th class="px-3 py-2">Job</th>
            <th class="px-3 py-2">Company</th>
            <th class="px-3 py-2">Reason</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">Note / actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2">
              #{{ row.job_post_id }}
              <div class="text-gray-500">{{ row.job_title }}</div>
            </td>
            <td class="px-3 py-2">{{ row.company_id }}</td>
            <td class="px-3 py-2">
              {{ row.reason }}
              <div v-if="row.detail" class="text-gray-500">{{ row.detail }}</div>
            </td>
            <td class="px-3 py-2">{{ row.status }}</td>
            <td class="px-3 py-2 space-y-2 min-w-[220px]">
              <input
                v-if="row.status === 'open'"
                v-model="noteById[row.id]"
                class="w-full border rounded-md px-2 py-1"
                placeholder="Optional note"
              />
              <div class="flex flex-wrap gap-2">
                <template v-if="row.status === 'open'">
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="resolve(row, 'dismiss')"
                  >
                    Dismiss
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="resolve(row, 'actioned')"
                  >
                    Actioned
                  </button>
                </template>
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-amber-700 text-white text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="suspend(row)"
                >
                  Suspend co.
                </button>
                <button
                  type="button"
                  class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="unsuspend(row)"
                >
                  Unsuspend
                </button>
              </div>
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
