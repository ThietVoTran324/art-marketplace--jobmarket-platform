<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { RouterLink } from 'vue-router'

const loading = ref(true)
const error = ref(null)
const counts = ref({
  audit_events_24h: 0,
  open_copyright_reports: 0,
  open_job_reports: 0,
  open_kyc_requests: 0,
  open_work_exp_pending: 0,
  unverified_payment_methods: 0,
})

const cards = [
  { key: 'audit_events_24h', label: 'Audit events (24h)', to: '/admin/audit' },
  { key: 'open_kyc_requests', label: 'Open KYC requests', to: '/admin/kyc' },
  { key: 'open_job_reports', label: 'Open job reports', to: '/admin/job-reports' },
  { key: 'open_copyright_reports', label: 'Open copyright reports', to: '/admin/copyright' },
  { key: 'open_work_exp_pending', label: 'Pending work exp', to: '/admin/work-experiences' },
  {
    key: 'unverified_payment_methods',
    label: 'Unverified payment methods',
    to: '/admin/marketplace/payment-methods',
  },
]

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/admin/overview')
    counts.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <p v-if="loading" class="text-gray-500">Loading overview…</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <component
        :is="card.to ? RouterLink : 'div'"
        v-for="card in cards"
        :key="card.key"
        :to="card.to"
        class="block border border-gray-200 rounded-lg p-4"
        :class="card.to ? 'hover:border-gray-400' : 'opacity-90'"
      >
        <div class="text-sm text-gray-500 flex items-center gap-2">
          {{ card.label }}
          <span v-if="card.soon" class="text-xs uppercase tracking-wide text-amber-700">Soon</span>
        </div>
        <div class="text-3xl font-semibold mt-2 tabular-nums">{{ counts[card.key] }}</div>
      </component>
    </div>
  </div>
</template>
