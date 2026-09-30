<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const rows = ref([])
const loading = ref(false)
const filters = ref({
  actor_user_id: '',
  action: '',
  target_type: '',
  target_id: '',
  date_from: '',
  date_to: '',
  limit: 50,
  offset: 0,
})

function buildParams() {
  const params = {
    limit: Number(filters.value.limit) || 50,
    offset: Number(filters.value.offset) || 0,
  }
  if (filters.value.actor_user_id) params.actor_user_id = Number(filters.value.actor_user_id)
  if (filters.value.action) params.action = filters.value.action
  if (filters.value.target_type) params.target_type = filters.value.target_type
  if (filters.value.target_id) params.target_id = Number(filters.value.target_id)
  if (filters.value.date_from) params.date_from = new Date(filters.value.date_from).toISOString()
  if (filters.value.date_to) params.date_to = new Date(filters.value.date_to).toISOString()
  return params
}

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/admin/audit', { params: buildParams() })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <form class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm" @submit.prevent="load">
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.actorUserId') }}</span>
        <input v-model="filters.actor_user_id" type="number" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.action') }}</span>
        <input v-model="filters.action" class="mt-1 w-full border rounded-md px-2 py-1.5" :placeholder="t('admin.audit.filters.actionPlaceholder')" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.targetType') }}</span>
        <input v-model="filters.target_type" class="mt-1 w-full border rounded-md px-2 py-1.5" :placeholder="t('admin.audit.filters.targetTypePlaceholder')" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.targetId') }}</span>
        <input v-model="filters.target_id" type="number" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.from') }}</span>
        <input v-model="filters.date_from" type="datetime-local" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.to') }}</span>
        <input v-model="filters.date_to" type="datetime-local" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.limit') }}</span>
        <input v-model="filters.limit" type="number" min="1" max="200" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <label>
        <span class="text-gray-600">{{ t('admin.audit.filters.offset') }}</span>
        <input v-model="filters.offset" type="number" min="0" class="mt-1 w-full border rounded-md px-2 py-1.5" />
      </label>
      <div class="col-span-2 md:col-span-4">
        <button type="submit" class="px-4 py-2 rounded-md bg-gray-900 text-white text-sm" :disabled="loading">
          {{ loading ? t('admin.audit.filters.loading') : t('admin.audit.filters.applyFilters') }}
        </button>
      </div>
    </form>

    <div class="overflow-x-auto border border-gray-200 rounded-lg">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.audit.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.audit.table.when') }}</th>
            <th class="px-3 py-2">{{ t('admin.audit.table.actor') }}</th>
            <th class="px-3 py-2">{{ t('admin.audit.table.action') }}</th>
            <th class="px-3 py-2">{{ t('admin.audit.table.target') }}</th>
            <th class="px-3 py-2">{{ t('admin.audit.table.meta') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ row.id }}</td>
            <td class="px-3 py-2 whitespace-nowrap">{{ row.created_at }}</td>
            <td class="px-3 py-2">{{ row.actor_user_id }}</td>
            <td class="px-3 py-2">{{ row.action }}</td>
            <td class="px-3 py-2">{{ t('admin.audit.table.targetCell', { targetType: row.target_type, targetId: row.target_id }) }}</td>
            <td class="px-3 py-2 font-mono text-xs max-w-xs truncate">{{ JSON.stringify(row.metadata || row.meta || {}) }}</td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-center text-gray-500">{{ t('admin.audit.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
