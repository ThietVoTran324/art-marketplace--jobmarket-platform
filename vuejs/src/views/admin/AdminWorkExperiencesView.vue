<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const rows = ref([])
const loading = ref(false)
const statusFilter = ref('pending')
const busyId = ref(null)

const STATUS_OPTIONS = ['pending', 'approved', 'rejected']

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/job-market/admin/work-experiences', {
      params: { status: statusFilter.value, limit: 100 },
    })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function decide(row, action) {
  if (!row.company_id) {
    toast.error(t('admin.workExp.toast.noCompanyLinked'))
    return
  }
  busyId.value = row.id
  try {
    await axios.post(`/api/job-market/admin/work-experiences/${row.id}/${action}`)
    toast.success(action === 'approve' ? t('admin.workExp.toast.approved') : t('admin.workExp.toast.rejected'))
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
        {{ t('admin.workExp.status') }}
        <select v-model="statusFilter" class="ml-2 border rounded-md px-2 py-1" @change="load">
          <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ t(`admin.workExp.statusOptions.${s}`) }}</option>
        </select>
      </label>
      <button type="button" class="text-sm underline" @click="load">{{ t('admin.workExp.refresh') }}</button>
    </div>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.workExp.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.artist') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.company') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.title') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.type') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.dates') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.workExp.table.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2">
              {{ row.artist_username || t('admin.workExp.table.artistFallback') }}
              <div class="text-gray-500">{{ t('admin.workExp.table.artistUserId', { artistUserId: row.artist_user_id || row.user_id }) }}</div>
            </td>
            <td class="px-3 py-2">
              {{ row.company_name }}
              <div class="text-gray-500">
                {{ row.company_id != null ? t('admin.workExp.table.companyCoPrefix', { companyId: row.company_id }) : t('admin.workExp.table.companyCoMissing') }}
              </div>
            </td>
            <td class="px-3 py-2">{{ row.title }}</td>
            <td class="px-3 py-2">{{ row.employment_type }}</td>
            <td class="px-3 py-2 whitespace-nowrap">
              {{ t('admin.workExp.table.datesRange', { startDate: row.start_date, endDateOrPresent: row.end_date || t('admin.workExp.table.datesPresent') }) }}
            </td>
            <td class="px-3 py-2">{{ row.status }}</td>
            <td class="px-3 py-2">
              <div v-if="row.status === 'pending'" class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="decide(row, 'approve')"
                >
                  {{ t('admin.workExp.approve') }}
                </button>
                <button
                  type="button"
                  class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                  :disabled="busyId === row.id || !row.company_id"
                  @click="decide(row, 'reject')"
                >
                  {{ t('admin.workExp.reject') }}
                </button>
              </div>
              <span v-else class="text-gray-400">{{ t('admin.workExp.table.noActions') }}</span>
            </td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td colspan="8" class="px-3 py-6 text-center text-gray-500">{{ t('admin.workExp.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
