<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const { t } = useI18n()

const links = computed(() => [
  { to: '/admin', labelKey: 'admin.nav.overview', exact: true },
  { to: '/admin/roles', labelKey: 'admin.nav.roles' },
  { to: '/admin/audit', labelKey: 'admin.nav.audit' },
  { to: '/admin/content', labelKey: 'admin.nav.content' },
  { to: '/admin/kyc', labelKey: 'admin.nav.kyc' },
  { to: '/admin/credentials', labelKey: 'admin.nav.credentials' },
  { to: '/admin/job-reports', labelKey: 'admin.nav.jobReports' },
  { to: '/admin/copyright', labelKey: 'admin.nav.copyright' },
  { to: '/admin/marketplace/payment-methods', labelKey: 'admin.nav.paymentMethods' },
  { to: '/admin/marketplace/payouts', labelKey: 'admin.nav.payouts' },
  { to: '/admin/work-experiences', labelKey: 'admin.nav.workExp' },
])

function isActive(to, exact = false) {
  if (exact) return route.path === to
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <nav class="flex flex-wrap gap-2 mb-8 border-b border-gray-200 pb-3">
    <RouterLink
      v-for="link in links"
      :key="link.to"
      :to="link.to"
      class="px-3 py-1.5 rounded-md text-sm"
      :class="isActive(link.to, link.exact) ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'"
    >
      {{ t(link.labelKey) }}
    </RouterLink>
  </nav>
</template>
