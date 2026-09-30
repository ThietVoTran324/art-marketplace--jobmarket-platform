<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()
const rows = ref([])
const loading = ref(false)
const statusFilter = ref('unverified')
const busyId = ref(null)

async function load() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (statusFilter.value === 'unverified' || statusFilter.value === 'verified') {
      params.verification_status = statusFilter.value
    } else {
      params.verification_status = 'all'
    }
    const { data } = await axios.get('/api/admin/marketplace/payment-methods', { params })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function setStatus(row, verification_status) {
  busyId.value = row.id
  try {
    await axios.patch(`/api/admin/marketplace/payment-methods/${row.id}`, {
      verification_status,
    })
    toast.success(verification_status === 'verified' ? t('admin.paymentMethods.toast.verified') : t('admin.paymentMethods.toast.unverified'))
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
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="text-lg font-semibold">{{ t('admin.paymentMethods.heading') }}</h2>
      <select
        v-model="statusFilter"
        class="border rounded-md px-2 py-1 text-sm"
        @change="load"
      >
        <option value="unverified">{{ t('admin.paymentMethods.filterOptions.unverified') }}</option>
        <option value="verified">{{ t('admin.paymentMethods.filterOptions.verified') }}</option>
        <option value="all">{{ t('admin.paymentMethods.filterOptions.all') }}</option>
      </select>
      <button type="button" class="text-sm underline" @click="load">{{ t('admin.paymentMethods.refresh') }}</button>
    </div>
    <p class="text-sm text-gray-600">
      {{ t('admin.paymentMethods.intro') }}
    </p>
    <p v-if="loading" class="text-gray-500 text-sm">{{ t('admin.paymentMethods.loading') }}</p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.seller') }}</th>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.type') }}</th>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.account') }}</th>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.paymentMethods.table.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-gray-500 text-center">{{ t('admin.paymentMethods.empty') }}</td>
          </tr>
          <tr
            v-for="row in rows"
            :key="row.id"
            class="border-t border-gray-100 align-top"
          >
            <td class="px-3 py-2 tabular-nums">{{ t('admin.paymentMethods.table.idCell', { id: row.id }) }}</td>
            <td class="px-3 py-2">
              <a
                :href="`/user/${row.username}`"
                class="underline"
                target="_blank"
                rel="noopener"
              >
                {{ row.username }}
              </a>
              <div class="text-xs text-gray-500">{{ t('admin.paymentMethods.table.uid', { userId: row.user_id }) }}</div>
            </td>
            <td class="px-3 py-2">
              {{ row.method_type }}
              <span v-if="row.is_primary" class="text-xs text-emerald-700">{{ t('admin.paymentMethods.table.primary') }}</span>
              <span v-if="!row.is_active" class="text-xs text-amber-700">{{ t('admin.paymentMethods.table.inactive') }}</span>
            </td>
            <td class="px-3 py-2 max-w-xs break-words">
              <div class="font-medium">{{ row.display_name }}</div>
              <div>{{ row.account_identifier }}</div>
              <div class="text-xs text-gray-500">
                <span v-if="row.bank_code">{{ t('admin.paymentMethods.table.binPrefix', { bankCode: row.bank_code }) }}</span>
                <span v-if="row.bank_name">{{ row.bank_name }} · </span>
                {{ row.account_holder || t('admin.paymentMethods.table.accountHolderFallback') }}
              </div>
            </td>
            <td class="px-3 py-2">
              <span
                :class="
                  row.verification_status === 'verified'
                    ? 'text-emerald-700'
                    : 'text-amber-700'
                "
              >
                {{ row.verification_status }}
              </span>
              <div v-if="row.verified_by" class="text-xs text-gray-500">
                {{ t('admin.paymentMethods.table.verifiedBy', { verifiedBy: row.verified_by }) }}
              </div>
            </td>
            <td class="px-3 py-2 space-x-2 whitespace-nowrap">
              <button
                v-if="row.verification_status !== 'verified'"
                type="button"
                class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                :disabled="busyId === row.id"
                @click="setStatus(row, 'verified')"
              >
                {{ t('admin.paymentMethods.verify') }}
              </button>
              <button
                v-else
                type="button"
                class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                :disabled="busyId === row.id"
                @click="setStatus(row, 'unverified')"
              >
                {{ t('admin.paymentMethods.unverify') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
