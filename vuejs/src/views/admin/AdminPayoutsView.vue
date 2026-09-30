<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()
const rows = ref([])
const loading = ref(false)
const noteById = ref({})
const busyId = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/admin/marketplace/payouts/pending', {
      params: { limit: 100 },
    })
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function execute(row, { forceFail = false } = {}) {
  busyId.value = row.order_id
  const note = (noteById.value[row.order_id] || '').trim() || null
  try {
    await axios.post(`/api/admin/marketplace/payouts/${row.order_id}/execute`, {
      note,
      force_fail: forceFail,
    })
    toast.success(forceFail ? t('admin.payouts.toast.executeForcedFail') : t('admin.payouts.toast.payoutExecuted'))
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busyId.value = null
  }
}

async function markPaid(row) {
  busyId.value = row.order_id
  const note = (noteById.value[row.order_id] || '').trim() || null
  try {
    await axios.post(`/api/admin/marketplace/payouts/${row.order_id}/mark-paid`, { note })
    toast.success(t('admin.payouts.toast.markedPaidManual'))
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
      <h2 class="text-lg font-semibold">{{ t('admin.payouts.heading') }}</h2>
      <button type="button" class="text-sm underline" @click="load">{{ t('admin.payouts.refresh') }}</button>
    </div>
    <p class="text-sm text-gray-600">
      {{ t('admin.payouts.intro') }}
    </p>
    <p v-if="loading" class="text-gray-500 text-sm">{{ t('admin.payouts.loading') }}</p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.payouts.table.order') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.pin') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.seller') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.amountVnd') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.destination') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.payouts.table.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.order_id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">{{ t('admin.payouts.table.orderCell', { orderId: row.order_id }) }}</td>
            <td class="px-3 py-2">
              <a :href="`/pin/${row.pin_id}`" class="underline" target="_blank" rel="noopener">
                {{ t('admin.payouts.table.pinLink', { pinId: row.pin_id }) }}
              </a>
            </td>
            <td class="px-3 py-2">{{ row.seller_user_id }}</td>
            <td class="px-3 py-2 tabular-nums">{{ row.payout_amount_vnd }}</td>
            <td class="px-3 py-2 max-w-xs break-words">
              <div>{{ t('admin.payouts.table.destinationLine', { payoutMethodType: row.payout_method_type, payoutAccountIdentifier: row.payout_account_identifier }) }}</div>
              <div class="text-xs text-gray-500">
                <span v-if="row.payout_bank_code">{{ t('admin.payouts.table.binPrefix', { payoutBankCode: row.payout_bank_code }) }}</span>
                {{ row.payout_account_holder || t('admin.payouts.table.accountHolderFallback') }}
              </div>
            </td>
            <td class="px-3 py-2">{{ row.payout_status }}</td>
            <td class="px-3 py-2 space-y-2 min-w-[220px]">
              <input
                v-model="noteById[row.order_id]"
                class="w-full border rounded-md px-2 py-1"
                :placeholder="t('admin.payouts.optionalNotePlaceholder')"
              />
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                  :disabled="busyId === row.order_id"
                  @click="execute(row)"
                >
                  {{ t('admin.payouts.execute') }}
                </button>
                <button
                  type="button"
                  class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                  :disabled="busyId === row.order_id"
                  @click="markPaid(row)"
                >
                  {{ t('admin.payouts.markPaid') }}
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!rows.length && !loading">
            <td colspan="7" class="px-3 py-6 text-center text-gray-500">{{ t('admin.payouts.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
