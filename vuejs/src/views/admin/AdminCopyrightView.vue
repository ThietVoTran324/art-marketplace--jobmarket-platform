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

const STATUS_OPTIONS = ['open', 'resolved', 'dismissed']

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
    toast.success(status === 'resolved' ? t('admin.copyright.toast.resolved') : t('admin.copyright.toast.dismissed'))
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
        {{ t('admin.copyright.status') }}
        <select v-model="statusFilter" class="ml-2 border rounded-md px-2 py-1" @change="load">
          <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ t(`admin.copyright.statusOptions.${s}`) }}</option>
        </select>
      </label>
      <button type="button" class="text-sm underline" @click="load">{{ t('admin.copyright.refresh') }}</button>
    </div>

    <p class="text-sm text-gray-600">
      {{ t('admin.copyright.intro') }}
    </p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.copyright.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.copyright.table.pin') }}</th>
            <th class="px-3 py-2">{{ t('admin.copyright.table.reporter') }}</th>
            <th class="px-3 py-2">{{ t('admin.copyright.table.reason') }}</th>
            <th class="px-3 py-2">{{ t('admin.copyright.table.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.copyright.table.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2">
              <a :href="`/pin/${row.pin_id}`" class="underline" target="_blank" rel="noopener">
                {{ t('admin.copyright.table.pinLink', { pinId: row.pin_id }) }}
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
                  :placeholder="t('admin.copyright.optionalNotePlaceholder')"
                />
                <div class="flex flex-wrap gap-2">
                  <button
                    type="button"
                    class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="decide(row, 'resolved')"
                  >
                    {{ t('admin.copyright.resolve') }}
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                    :disabled="busyId === row.id"
                    @click="decide(row, 'dismissed')"
                  >
                    {{ t('admin.copyright.dismiss') }}
                  </button>
                </div>
              </template>
              <span v-else class="text-gray-500">{{ row.admin_note || t('admin.copyright.emptyAdminNote') }}</span>
            </td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-center text-gray-500">{{ t('admin.copyright.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
