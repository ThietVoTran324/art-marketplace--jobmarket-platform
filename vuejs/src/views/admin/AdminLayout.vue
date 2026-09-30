<script setup>
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/Admin/AdminNav.vue'

const { t } = useI18n()
</script>

<template>
  <div class="min-h-screen pl-24 pr-8 py-8 max-w-5xl">
    <header class="mb-8">
      <h1 class="text-3xl font-semibold text-gray-900">{{ t('admin.layout.title') }}</h1>
      <p class="text-sm text-gray-500 mt-1">{{ t('admin.layout.subtitle') }}</p>
    </header>
    <AdminNav />
    <RouterView />
  </div>
</template>
