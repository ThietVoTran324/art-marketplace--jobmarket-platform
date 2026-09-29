<script setup>
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const links = [
  { to: '/admin', label: 'Overview', exact: true },
  { to: '/admin/roles', label: 'Roles' },
  { to: '/admin/audit', label: 'Audit' },
  { to: '/admin/content', label: 'Content' },
  { to: '/admin/kyc', label: 'KYC' },
  { to: '/admin/credentials', label: 'Credentials' },
  { to: '/admin/job-reports', label: 'Job reports' },
  { to: '/admin/copyright', label: 'Copyright' },
  { to: '/admin/marketplace/payment-methods', label: 'Payment methods' },
  { to: '/admin/marketplace/payouts', label: 'Payouts' },
  { to: '/admin/work-experiences', label: 'Work exp' },
]

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
      {{ link.label }}
    </RouterLink>
  </nav>
</template>
