<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const rows = ref([])
const loading = ref(false)
const statusFilter = ref('open')
const noteById = ref({})
const busyId = ref(null)

const STATUS_OPTIONS = ['open', 'dismissed', 'actioned']

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
    toast.success(action === 'dismiss' ? t('admin.jobReports.toast.dismissed') : t('admin.jobReports.toast.markedActioned'))
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

async function suspend(row) {
  if (!row.company_id) {
    toast.error(t('admin.jobReports.toast.noCompanyLinked'))
    return
  }
  const reason = window.prompt(t('admin.jobReports.prompt.suspendReason', { companyId: row.company_id }))
  if (!reason || !reason.trim()) return
  if (!window.confirm(t('admin.jobReports.prompt.confirmSuspend', { companyId: row.company_id }))) return
  busyId.value = row.id
  try {
    await axios.post(`/api/job-market/admin/companies/${row.company_id}/suspend`, {
      reason: reason.trim(),
    })
    toast.success(t('admin.jobReports.toast.companySuspended'))
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

async function unsuspend(row) {
  if (!row.company_id) {
    toast.error(t('admin.jobReports.toast.noCompanyLinked'))
    return
  }
  if (!window.confirm(t('admin.jobReports.prompt.confirmUnsuspend', { companyId: row.company_id }))) return
  busyId.value = row.id
  try {
    await axios.post(`/api/job-market/admin/companies/${row.company_id}/unsuspend`)
    toast.success(t('admin.jobReports.toast.companyUnsuspended'))
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
        {{ t('admin.jobReports.status') }}
        <select v-model="statusFilter" class="ml-2 border rounded-md px-2 py-1" @change="load">
          <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ t(`admin.jobReports.statusOptions.${s}`) }}</option>
        </select>
      </label>
      <button type="button" class="text-sm underline" @click="load">{{ t('admin.jobReports.refresh') }}</button>
    </div>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.job') }}</th>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.company') }}</th>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.reason') }}</th>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.jobReports.table.noteActions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2">
              {{ t('admin.jobReports.table.jobCell', { jobPostId: row.job_post_id }) }}
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
                :placeholder="t('admin.jobReports.optionalNotePlaceholder')"
              />
              <div class="flex flex-wrap gap-2">
                <template v-if="row.status === 'open'">
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="resolve(row, 'dismiss')"
                  >
                    {{ t('admin.jobReports.dismiss') }}
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="resolve(row, 'actioned')"
                  >
                    {{ t('admin.jobReports.actioned') }}
                  </button>
                </template>
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-amber-700 text-white text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="suspend(row)"
                >
                  {{ t('admin.jobReports.suspendCo') }}
                </button>
                <button
                  type="button"
                  class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="unsuspend(row)"
                >
                  {{ t('admin.jobReports.unsuspend') }}
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-center text-gray-500">{{ t('admin.jobReports.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
