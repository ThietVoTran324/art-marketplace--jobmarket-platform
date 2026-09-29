<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()
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
    toast.success(forceFail ? 'Execute forced fail' : 'Payout executed')
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
    toast.success('Marked paid (manual transfer)')
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
      <h2 class="text-lg font-semibold">Seller payouts</h2>
      <button type="button" class="text-sm underline" @click="load">Refresh</button>
    </div>
    <p class="text-sm text-gray-600">
      Paid orders awaiting disbursement. Use <strong>Execute</strong> to run payout, or
      <strong>Mark paid</strong> after you already transferred outside the app.
    </p>
    <p v-if="loading" class="text-gray-500 text-sm">Loading…</p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">Order</th>
            <th class="px-3 py-2">Pin</th>
            <th class="px-3 py-2">Seller</th>
            <th class="px-3 py-2">Amount VND</th>
            <th class="px-3 py-2">Destination</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.order_id" class="border-t border-gray-100 align-top">
            <td class="px-3 py-2 tabular-nums">#{{ row.order_id }}</td>
            <td class="px-3 py-2">
              <a :href="`/pin/${row.pin_id}`" class="underline" target="_blank" rel="noopener">
                #{{ row.pin_id }}
              </a>
            </td>
            <td class="px-3 py-2">{{ row.seller_user_id }}</td>
            <td class="px-3 py-2 tabular-nums">{{ row.payout_amount_vnd }}</td>
            <td class="px-3 py-2 max-w-xs break-words">
              <div>{{ row.payout_method_type }} · {{ row.payout_account_identifier }}</div>
              <div class="text-xs text-gray-500">
                <span v-if="row.payout_bank_code">BIN {{ row.payout_bank_code }} · </span>
                {{ row.payout_account_holder || '—' }}
              </div>
            </td>
            <td class="px-3 py-2">{{ row.payout_status }}</td>
            <td class="px-3 py-2 space-y-2 min-w-[220px]">
              <input
                v-model="noteById[row.order_id]"
                class="w-full border rounded-md px-2 py-1"
                placeholder="Optional note"
              />
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                  :disabled="busyId === row.order_id"
                  @click="execute(row)"
                >
                  Execute
                </button>
                <button
                  type="button"
                  class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                  :disabled="busyId === row.order_id"
                  @click="markPaid(row)"
                >
                  Mark paid
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!rows.length && !loading">
            <td colspan="7" class="px-3 py-6 text-center text-gray-500">Queue empty</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
