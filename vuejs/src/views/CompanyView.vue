<script setup>
import { computed, ref, watch } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';
import CompanyCommentSection from '@/components/Auth/JobMarket/CompanyCommentSection.vue';
import CompanySideStack from '@/components/Auth/JobMarket/CompanySideStack.vue';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const companyId = computed(() => {
  const n = Number(route.params.id);
  return Number.isFinite(n) && n > 0 ? n : null;
});

const company = ref(null);
const loading = ref(true);
const error = ref(null);
const avatarUrl = ref(null);

async function load() {
  if (!companyId.value) return;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${companyId.value}`);
    company.value = data;
    const ownerId = company.value.owner_user_id;
    avatarUrl.value = getCachedCompanyAvatar(ownerId);
    if (ownerId) {
      avatarUrl.value = await fetchCompanyAvatar(ownerId);
    }
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyView.loadFailed');
  } finally {
    loading.value = false;
  }
}

function companySizeLabel(c) {
  return t('jobMarket.companyView.companySize', {
    min: c.size_min ?? '—',
    max: c.size_max ?? '—',
  });
}

watch(companyId, () => load(), { immediate: true });
</script>

<template>
  <div class="ml-24 mr-6 mt-8 mb-12">
    <button type="button" class="text-sm text-gray-600 hover:underline mb-4" @click="router.back()">
      {{ t('jobMarket.companyView.back') }}
    </button>

    <p v-if="!companyId" class="text-red-600">{{ t('jobMarket.companyView.invalidCompany') }}</p>
    <p v-else-if="loading" class="text-gray-500">{{ t('jobMarket.companyView.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>

    <template v-else-if="company">
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <!-- 3/4 -->
        <div class="lg:col-span-3 space-y-6">
          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
            <div class="flex items-start gap-4">
              <img
                v-if="avatarUrl"
                :src="avatarUrl"
                alt=""
                class="w-20 h-20 rounded-2xl object-cover bg-gray-100 shrink-0"
              />
              <div
                v-else
                class="w-20 h-20 rounded-2xl bg-gray-100 shrink-0 flex items-center justify-center text-gray-400"
              >
                <i class="pi pi-building text-3xl" />
              </div>
              <div class="min-w-0">
                <h1 class="text-3xl font-extrabold text-gray-900">{{ company.display_name }}</h1>
                <p v-if="company.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
                <p v-if="company.description" class="text-sm text-gray-700 mt-3 whitespace-pre-line">
                  {{ company.description }}
                </p>
                <p v-if="company.website" class="text-sm mt-2">
                  <a :href="company.website" target="_blank" rel="noopener" class="text-red-600 hover:underline">
                    {{ company.website }}
                  </a>
                </p>
                <p
                  v-if="company.size_min != null || company.size_max != null"
                  class="text-xs text-gray-500 mt-2"
                >
                  {{ companySizeLabel(company) }}
                </p>
              </div>
            </div>
          </section>

          <CompanyCommentSection :company-id="companyId" />
        </div>

        <!-- 1/4: Contact · Open roles · Artists -->
        <aside class="lg:col-span-1 lg:sticky lg:top-8">
          <CompanySideStack
            :company-id="companyId"
            :company-owner-user-id="company.owner_user_id"
            :company-display-name="company.display_name"
          />
        </aside>
      </div>
    </template>
  </div>
</template>
