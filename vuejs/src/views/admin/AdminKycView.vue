<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const allRows = ref([])
const loading = ref(false)
const showAll = ref(false)
const selectedId = ref(null)
const docs = ref([])
const docsLoading = ref(false)
const note = ref('')
const rejectReason = ref('')
const busy = ref(false)

const OPEN = new Set(['pending', 'need_more_info'])

const rows = computed(() => {
  if (showAll.value) return allRows.value
  return allRows.value.filter((r) => OPEN.has(r.status))
})

const selected = computed(() =>
  allRows.value.find((r) => r.id === selectedId.value) || null
)

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/job-market/admin/hiring-rights-requests')
    allRows.value = data
    if (selectedId.value && !allRows.value.some((r) => r.id === selectedId.value)) {
      selectedId.value = null
      docs.value = []
    }
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function selectRow(row) {
  selectedId.value = row.id
  note.value = row.admin_note || ''
  rejectReason.value = ''
  docsLoading.value = true
  docs.value = []
  try {
    const { data } = await axios.get(
      `/api/job-market/admin/hiring-rights-requests/${row.id}/documents`
    )
    docs.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    docsLoading.value = false
  }
}

async function openDoc(doc) {
  try {
    const { data } = await axios.get(
      `/api/job-market/admin/hiring-rights-requests/${selectedId.value}/documents/${doc.id}/file`,
      { responseType: 'blob' }
    )
    const url = URL.createObjectURL(data)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  }
}

async function decide(action) {
  if (!selected.value) return
  const id = selected.value.id
  busy.value = true
  try {
    if (action === 'approve') {
      await axios.post(`/api/job-market/admin/hiring-rights-requests/${id}/approve`)
      toast.success('Approved')
    } else if (action === 'need_more') {
      if (!note.value.trim()) {
        toast.error('A note is required when requesting more information')
        return
      }
      await axios.post(
        `/api/job-market/admin/hiring-rights-requests/${id}/need-more-info`,
        { note: note.value.trim() }
      )
      toast.success('Marked as needs more information')
    } else if (action === 'reject') {
      if (!rejectReason.value.trim()) {
        toast.error('Rejection reason is required')
        return
      }
      await axios.post(`/api/job-market/admin/hiring-rights-requests/${id}/reject`, {
        reason: rejectReason.value.trim(),
      })
      toast.success('Rejected')
    }
    await load()
    const refreshed = allRows.value.find((r) => r.id === id)
    if (refreshed) await selectRow(refreshed)
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3">
      <p class="text-sm text-gray-600">Hiring rights verification queue</p>
      <label class="text-sm flex items-center gap-2">
        <input v-model="showAll" type="checkbox" />
        Show all statuses
      </label>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="border border-gray-200 rounded-lg overflow-hidden">
        <table class="min-w-full text-sm">
          <thead class="bg-gray-50 text-left">
            <tr>
              <th class="px-3 py-2">Id</th>
              <th class="px-3 py-2">Company</th>
              <th class="px-3 py-2">Status</th>
              <th class="px-3 py-2">Requester</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              class="border-t border-gray-100 cursor-pointer"
              :class="selectedId === row.id ? 'bg-gray-100' : 'hover:bg-gray-50'"
              @click="selectRow(row)"
            >
              <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
              <td class="px-3 py-2">#{{ row.company_id }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">{{ row.requester_user_id }}</td>
            </tr>
            <tr v-if="!loading && !rows.length">
              <td colspan="4" class="px-3 py-6 text-center text-gray-500">No requests</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="selected" class="border border-gray-200 rounded-lg p-4 space-y-3 text-sm">
        <h2 class="text-lg font-medium">Request #{{ selected.id }}</h2>
        <dl class="grid grid-cols-2 gap-2">
          <div><dt class="text-gray-500">Status</dt><dd>{{ selected.status }}</dd></div>
          <div><dt class="text-gray-500">Email</dt><dd class="break-all">{{ selected.company_email }}</dd></div>
          <div><dt class="text-gray-500">KYC email link confirmed</dt><dd>{{ selected.company_email_confirmed_at ? 'yes' : 'no' }}</dd></div>
            <p v-if="!selected.company_email_confirmed_at" class="col-span-2 text-amber-700 text-xs">
              Account email may already be verified — requester still must open the “Confirm company email” mail link (Settings → Resend).
            </p>
          <div><dt class="text-gray-500">Language</dt><dd>{{ selected.primary_document_language }}</dd></div>
          <div class="col-span-2"><dt class="text-gray-500">Signer</dt><dd>{{ selected.signer_full_name }}</dd></div>
        </dl>

        <div>
          <h3 class="font-medium mb-2">Documents</h3>
          <p v-if="docsLoading" class="text-gray-500">Loading…</p>
          <ul v-else class="space-y-1">
            <li v-for="doc in docs" :key="doc.id" class="flex justify-between gap-2">
              <span>{{ doc.doc_type }} — {{ doc.original_filename }}</span>
              <button type="button" class="text-blue-700 underline" @click="openDoc(doc)">Open</button>
            </li>
            <li v-if="!docs.length" class="text-gray-500">No documents</li>
          </ul>
        </div>

        <label class="block">
          <span class="text-gray-600">Admin note (required when requesting more info)</span>
          <textarea v-model="note" rows="2" class="mt-1 w-full border rounded-md px-2 py-1.5" />
        </label>
        <label class="block">
          <span class="text-gray-600">Reject reason</span>
          <textarea v-model="rejectReason" rows="2" class="mt-1 w-full border rounded-md px-2 py-1.5" />
        </label>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-md bg-gray-900 text-white disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('approve')"
          >
            Approve
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md border border-gray-300 disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('need_more')"
          >
            Need more info
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md bg-red-700 text-white disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('reject')"
          >
            Reject
          </button>
        </div>
      </div>
      <div v-else class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500 text-sm">
        Select a request
      </div>
    </div>
  </div>
</template>
