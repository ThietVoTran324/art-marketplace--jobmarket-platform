<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()
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
    toast.success(verification_status === 'verified' ? 'Verified' : 'Unverified')
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
      <h2 class="text-lg font-semibold">Seller payment methods</h2>
      <select
        v-model="statusFilter"
        class="border rounded-md px-2 py-1 text-sm"
        @change="load"
      >
        <option value="unverified">Unverified (queue)</option>
        <option value="verified">Verified</option>
        <option value="all">All</option>
      </select>
      <button type="button" class="text-sm underline" @click="load">Refresh</button>
    </div>
    <p class="text-sm text-gray-600">
      Sellers add methods as <strong>unverified</strong>. Only
      <strong>active + verified</strong> counts toward selling eligibility (P).
    </p>
    <p v-if="loading" class="text-gray-500 text-sm">Loading…</p>

    <div class="border border-gray-200 rounded-lg overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">ID</th>
            <th class="px-3 py-2">Seller</th>
            <th class="px-3 py-2">Type</th>
            <th class="px-3 py-2">Account</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loading && !rows.length">
            <td colspan="6" class="px-3 py-6 text-gray-500 text-center">No methods</td>
          </tr>
          <tr
            v-for="row in rows"
            :key="row.id"
            class="border-t border-gray-100 align-top"
          >
            <td class="px-3 py-2 tabular-nums">#{{ row.id }}</td>
            <td class="px-3 py-2">
              <a
                :href="`/user/${row.username}`"
                class="underline"
                target="_blank"
                rel="noopener"
              >
                {{ row.username }}
              </a>
              <div class="text-xs text-gray-500">uid {{ row.user_id }}</div>
            </td>
            <td class="px-3 py-2">
              {{ row.method_type }}
              <span v-if="row.is_primary" class="text-xs text-emerald-700">· primary</span>
              <span v-if="!row.is_active" class="text-xs text-amber-700">· inactive</span>
            </td>
            <td class="px-3 py-2 max-w-xs break-words">
              <div class="font-medium">{{ row.display_name }}</div>
              <div>{{ row.account_identifier }}</div>
              <div class="text-xs text-gray-500">
                <span v-if="row.bank_code">BIN {{ row.bank_code }} · </span>
                <span v-if="row.bank_name">{{ row.bank_name }} · </span>
                {{ row.account_holder || '—' }}
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
                by {{ row.verified_by }}
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
                Verify
              </button>
              <button
                v-else
                type="button"
                class="px-2 py-1 rounded border text-xs disabled:opacity-50"
                :disabled="busyId === row.id"
                @click="setStatus(row, 'unverified')"
              >
                Unverify
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
