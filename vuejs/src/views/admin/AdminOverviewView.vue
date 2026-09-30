<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const loading = ref(true)
const error = ref(null)
const counts = ref({
  audit_events_24h: 0,
  open_copyright_reports: 0,
  open_job_reports: 0,
  open_kyc_requests: 0,
  open_work_exp_pending: 0,
  unverified_payment_methods: 0,
  pending_payouts: 0,
})

const cards = computed(() => [
  { key: 'audit_events_24h', labelKey: 'admin.overview.cards.auditEvents24h', to: '/admin/audit' },
  { key: 'open_kyc_requests', labelKey: 'admin.overview.cards.openKycRequests', to: '/admin/kyc' },
  { key: 'open_job_reports', labelKey: 'admin.overview.cards.openJobReports', to: '/admin/job-reports' },
  {
    key: 'open_copyright_reports',
    labelKey: 'admin.overview.cards.openCopyrightReports',
    to: '/admin/copyright',
  },
  { key: 'open_work_exp_pending', labelKey: 'admin.overview.cards.pendingWorkExp', to: '/admin/work-experiences' },
  {
    key: 'unverified_payment_methods',
    labelKey: 'admin.overview.cards.unverifiedPaymentMethods',
    to: '/admin/marketplace/payment-methods',
  },
  {
    key: 'pending_payouts',
    labelKey: 'admin.overview.cards.pendingSellerPayouts',
    to: '/admin/marketplace/payouts',
  },
])

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
    <p v-if="loading" class="text-gray-500">{{ t('admin.overview.loading') }}</p>
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
          {{ t(card.labelKey) }}
          <span v-if="card.soon" class="text-xs uppercase tracking-wide text-amber-700">{{ t('admin.overview.soon') }}</span>
        </div>
        <div class="text-3xl font-semibold mt-2 tabular-nums">{{ counts[card.key] }}</div>
      </component>
    </div>
  </div>
</template>
