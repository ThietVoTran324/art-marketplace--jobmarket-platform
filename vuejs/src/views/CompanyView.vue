<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import CompanyProfileTab from '@/components/Auth/JobMarket/CompanyProfileTab.vue';
import HiringJobsTab from '@/components/Auth/JobMarket/HiringJobsTab.vue';
import { authUserStore } from '@/stores/authUserStore';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const { t } = useI18n();
const router = useRouter();
const userStore = authUserStore();

const companyId = computed(() => {
  const n = Number(route.params.id);
  return Number.isFinite(n) && n > 0 ? n : null;
});

const isOwner = computed(
  () =>
    companyId.value != null &&
    userStore.accountKind === 'organization' &&
    userStore.companyId === companyId.value
);
</script>

<template>
  <div class="ml-20 min-h-screen px-10 py-10 max-w-3xl">
    <button
      type="button"
      class="text-sm text-gray-600 hover:underline mb-4"
      @click="router.back()"
    >
      {{ t('jobMarket.companyView.back') }}
    </button>

    <p v-if="!companyId" class="text-red-600">{{ t('jobMarket.companyView.invalidCompany') }}</p>
    <template v-else>
      <CompanyProfileTab :company-id="companyId" :is-owner="isOwner" />
      <div class="mt-10 border-t pt-4">
        <HiringJobsTab :company-id="companyId" />
      </div>
    </template>
  </div>
</template>
