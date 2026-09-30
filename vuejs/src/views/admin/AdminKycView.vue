<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

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
      toast.success(t('admin.kyc.toast.approved'))
    } else if (action === 'need_more') {
      if (!note.value.trim()) {
        toast.error(t('admin.kyc.toast.noteRequired'))
        return
      }
      await axios.post(
        `/api/job-market/admin/hiring-rights-requests/${id}/need-more-info`,
        { note: note.value.trim() }
      )
      toast.success(t('admin.kyc.toast.markedNeedsMoreInfo'))
    } else if (action === 'reject') {
      if (!rejectReason.value.trim()) {
        toast.error(t('admin.kyc.toast.rejectionReasonRequired'))
        return
      }
      await axios.post(`/api/job-market/admin/hiring-rights-requests/${id}/reject`, {
        reason: rejectReason.value.trim(),
      })
      toast.success(t('admin.kyc.toast.rejected'))
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
      <p class="text-sm text-gray-600">{{ t('admin.kyc.queueDescription') }}</p>
      <label class="text-sm flex items-center gap-2">
        <input v-model="showAll" type="checkbox" />
        {{ t('admin.kyc.showAllStatuses') }}
      </label>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="border border-gray-200 rounded-lg overflow-hidden">
        <table class="min-w-full text-sm">
          <thead class="bg-gray-50 text-left">
            <tr>
              <th class="px-3 py-2">{{ t('admin.kyc.table.id') }}</th>
              <th class="px-3 py-2">{{ t('admin.kyc.table.company') }}</th>
              <th class="px-3 py-2">{{ t('admin.kyc.table.status') }}</th>
              <th class="px-3 py-2">{{ t('admin.kyc.table.requester') }}</th>
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
              <td class="px-3 py-2">{{ t('admin.kyc.table.companyCell', { companyId: row.company_id }) }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">{{ row.requester_user_id }}</td>
            </tr>
            <tr v-if="!loading && !rows.length">
              <td colspan="4" class="px-3 py-6 text-center text-gray-500">{{ t('admin.kyc.empty') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="selected" class="border border-gray-200 rounded-lg p-4 space-y-3 text-sm">
        <h2 class="text-lg font-medium">{{ t('admin.kyc.detail.title', { id: selected.id }) }}</h2>
        <dl class="grid grid-cols-2 gap-2">
          <div><dt class="text-gray-500">{{ t('admin.kyc.detail.status') }}</dt><dd>{{ selected.status }}</dd></div>
          <div><dt class="text-gray-500">{{ t('admin.kyc.detail.email') }}</dt><dd class="break-all">{{ selected.company_email }}</dd></div>
          <div><dt class="text-gray-500">{{ t('admin.kyc.detail.kycEmailLinkConfirmed') }}</dt><dd>{{ selected.company_email_confirmed_at ? t('admin.kyc.detail.yes') : t('admin.kyc.detail.no') }}</dd></div>
            <p v-if="!selected.company_email_confirmed_at" class="col-span-2 text-amber-700 text-xs">
              {{ t('admin.kyc.detail.emailLinkWarning') }}
            </p>
          <div><dt class="text-gray-500">{{ t('admin.kyc.detail.language') }}</dt><dd>{{ selected.primary_document_language }}</dd></div>
          <div class="col-span-2"><dt class="text-gray-500">{{ t('admin.kyc.detail.signer') }}</dt><dd>{{ selected.signer_full_name }}</dd></div>
        </dl>

        <div>
          <h3 class="font-medium mb-2">{{ t('admin.kyc.documents.heading') }}</h3>
          <p v-if="docsLoading" class="text-gray-500">{{ t('admin.kyc.documents.loading') }}</p>
          <ul v-else class="space-y-1">
            <li v-for="doc in docs" :key="doc.id" class="flex justify-between gap-2">
              <span>{{ t('admin.kyc.documents.item', { docType: doc.doc_type, originalFilename: doc.original_filename }) }}</span>
              <button type="button" class="text-blue-700 underline" @click="openDoc(doc)">{{ t('admin.kyc.documents.open') }}</button>
            </li>
            <li v-if="!docs.length" class="text-gray-500">{{ t('admin.kyc.documents.empty') }}</li>
          </ul>
        </div>

        <label class="block">
          <span class="text-gray-600">{{ t('admin.kyc.adminNote') }}</span>
          <textarea v-model="note" rows="2" class="mt-1 w-full border rounded-md px-2 py-1.5" />
        </label>
        <label class="block">
          <span class="text-gray-600">{{ t('admin.kyc.rejectReason') }}</span>
          <textarea v-model="rejectReason" rows="2" class="mt-1 w-full border rounded-md px-2 py-1.5" />
        </label>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-md bg-gray-900 text-white disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('approve')"
          >
            {{ t('admin.kyc.approve') }}
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md border border-gray-300 disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('need_more')"
          >
            {{ t('admin.kyc.needMoreInfo') }}
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-md bg-red-700 text-white disabled:opacity-50"
            :disabled="busy || !OPEN.has(selected.status)"
            @click="decide('reject')"
          >
            {{ t('admin.kyc.reject') }}
          </button>
        </div>
      </div>
      <div v-else class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500 text-sm">
        {{ t('admin.kyc.selectRequest') }}
      </div>
    </div>
  </div>
</template>
