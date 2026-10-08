<script setup>
import { computed, ref, watch } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';
import CompanyCommentSection from '@/components/Auth/JobMarket/CompanyCommentSection.vue';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const companyId = computed(() => {
  const n = Number(route.params.id);
  return Number.isFinite(n) && n > 0 ? n : null;
});

const company = ref(null);
const contact = ref(null);
const jobs = ref([]);
const employees = ref([]);
const empTotal = ref(0);
const empPage = ref(1);
const empPageSize = 10;
const loading = ref(true);
const error = ref(null);
const avatarUrl = ref(null);
const sideTab = ref('contact'); // contact | artists
const jobLogoTick = ref(0);

const empTotalPages = computed(() => Math.max(1, Math.ceil(empTotal.value / empPageSize)));

function formatSalary(j) {
  if (!j) return '';
  if (j.salary_mode === 'love_it') return t('jobDetail.salary.loveIt');
  const cur = j.currency || 'VND';
  if (j.salary_min != null && j.salary_max != null) {
    return t('jobDetail.salary.range', { min: j.salary_min, max: j.salary_max, currency: cur });
  }
  if (j.salary_min != null) return t('jobDetail.salary.from', { min: j.salary_min, currency: cur });
  if (j.salary_max != null) return t('jobDetail.salary.upTo', { max: j.salary_max, currency: cur });
  return cur;
}

function locationSummary(j) {
  const locs = j?.locations || [];
  if (!locs.length) return '';
  return locs
    .slice(0, 2)
    .map((l) => [l.label, l.address_line, l.city].filter(Boolean).join(', '))
    .filter(Boolean)
    .join(' · ');
}

const contactRows = computed(() => {
  const c = contact.value;
  if (!c) return [];
  const rows = [];
  if (c.instagram) rows.push({ name: 'Instagram', value: c.instagram });
  if (c.tiktok) rows.push({ name: 'TikTok', value: c.tiktok });
  if (c.telegram) rows.push({ name: 'Telegram', value: c.telegram });
  if (c.pinterest) rows.push({ name: 'Pinterest', value: c.pinterest });
  for (const link of c.links || []) {
    rows.push({ name: link.name, value: link.value });
  }
  return rows;
});

async function loadEmployees() {
  if (!companyId.value) return;
  const offset = (empPage.value - 1) * empPageSize;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${companyId.value}/employees`, {
      params: { offset, limit: empPageSize },
    });
    employees.value = data.employees || [];
    empTotal.value = data.total ?? employees.value.length;
  } catch {
    employees.value = [];
    empTotal.value = 0;
  }
}

async function load() {
  if (!companyId.value) return;
  loading.value = true;
  error.value = null;
  try {
    const [cRes, contactRes, jobsRes] = await Promise.allSettled([
      axios.get(`/api/job-market/companies/${companyId.value}`),
      axios.get(`/api/job-market/companies/${companyId.value}/contact`),
      axios.get(`/api/job-market/companies/${companyId.value}/job-posts`, {
        params: { status: 'active' },
      }),
    ]);
    if (cRes.status !== 'fulfilled') {
      throw cRes.reason;
    }
    company.value = cRes.value.data;
    if (contactRes.status === 'fulfilled') contact.value = contactRes.value.data;
    if (jobsRes.status === 'fulfilled') jobs.value = jobsRes.value.data || [];

    const ownerId = company.value.owner_user_id;
    avatarUrl.value = getCachedCompanyAvatar(ownerId);
    if (ownerId) {
      avatarUrl.value = await fetchCompanyAvatar(ownerId);
    }

    const ownerIds = jobs.value.map((j) => j.company_owner_user_id || ownerId).filter(Boolean);
    await Promise.all(
      [...new Set(ownerIds)].map(async (id) => {
        await fetchCompanyAvatar(id);
      })
    );
    jobLogoTick.value += 1;

    empPage.value = 1;
    await loadEmployees();
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyView.loadFailed');
  } finally {
    loading.value = false;
  }
}

function jobAvatar(j) {
  jobLogoTick.value;
  const id = j.company_owner_user_id || company.value?.owner_user_id;
  return getCachedCompanyAvatar(id);
}

function openJob(id) {
  window.open(`/jobs/${id}`, '_blank', 'noopener,noreferrer');
}

function requireLogin(path) {
  if (userStore.isAuthenticated) return true;
  openAuthModal('login', { redirectTo: path || route.fullPath });
  return false;
}

function prevEmpPage() {
  if (empPage.value <= 1) return;
  empPage.value -= 1;
  loadEmployees();
}

function nextEmpPage() {
  if (empPage.value >= empTotalPages.value) return;
  empPage.value += 1;
  loadEmployees();
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
                  {{ t('jobMarket.companyView.companySize', {
                    min: company.size_min ?? '—',
                    max: company.size_max ?? '—',
                  }) }}
                </p>
              </div>
            </div>
          </section>

          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
            <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('jobMarket.companyView.openRoles') }}</h2>
            <p v-if="!jobs.length" class="text-sm text-gray-500">{{ t('jobMarket.companyView.noJobs') }}</p>
            <ul v-else class="space-y-3">
              <li
                v-for="j in jobs"
                :key="j.id"
                class="border border-gray-100 rounded-xl px-4 py-3 hover:bg-gray-50 cursor-pointer flex gap-3"
                @click="openJob(j.id)"
              >
                <img
                  v-if="jobAvatar(j)"
                  :src="jobAvatar(j)"
                  alt=""
                  class="w-11 h-11 rounded-xl object-cover bg-gray-100 shrink-0"
                />
                <div v-else class="w-11 h-11 rounded-xl bg-gray-100 shrink-0" />
                <div class="min-w-0 flex-1">
                  <p class="font-bold text-gray-900">{{ j.title }}</p>
                  <p class="text-sm text-gray-600">
                    {{ formatSalary(j) }} · {{ t('jobDetail.meta.yearsExperience', { years: j.years_experience }) }}
                  </p>
                  <p v-if="locationSummary(j)" class="text-xs text-gray-500 mt-0.5 line-clamp-1">
                    {{ locationSummary(j) }}
                  </p>
                </div>
              </li>
            </ul>
          </section>

          <CompanyCommentSection :company-id="companyId" />
        </div>

        <!-- 1/4 -->
        <aside class="lg:col-span-1 space-y-4">
          <div class="border border-gray-200 rounded-2xl bg-white overflow-hidden">
            <div class="flex border-b border-gray-100">
              <button
                type="button"
                class="flex-1 px-3 py-2 text-sm font-medium"
                :class="sideTab === 'contact' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-50'"
                @click="sideTab = 'contact'"
              >
                {{ t('jobDetail.side.contact') }}
              </button>
              <button
                type="button"
                class="flex-1 px-3 py-2 text-sm font-medium"
                :class="sideTab === 'artists' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-50'"
                @click="sideTab = 'artists'"
              >
                {{ t('jobDetail.side.artists') }}
              </button>
            </div>
            <div class="p-4">
              <template v-if="sideTab === 'contact'">
                <p v-if="!contactRows.length" class="text-sm text-gray-500">{{ t('jobDetail.side.noContact') }}</p>
                <ul v-else class="space-y-3">
                  <li v-for="(row, idx) in contactRows" :key="idx" class="text-sm">
                    <p class="font-semibold text-gray-800">{{ row.name }}</p>
                    <a
                      v-if="/^https?:\/\//i.test(row.value)"
                      :href="row.value"
                      target="_blank"
                      rel="noopener"
                      class="text-red-600 break-all hover:underline"
                    >{{ row.value }}</a>
                    <p v-else class="text-gray-700 break-all">{{ row.value }}</p>
                  </li>
                </ul>
              </template>
              <template v-else>
                <p v-if="!employees.length" class="text-sm text-gray-500">{{ t('jobDetail.side.noArtists') }}</p>
                <ul v-else class="space-y-2 mb-3">
                  <li v-for="e in employees" :key="e.user_id" class="text-sm text-gray-800">
                    <button
                      type="button"
                      class="hover:underline text-left"
                      @click="requireLogin(`/user/${e.username}`) && router.push(`/user/${e.username}`)"
                    >
                      {{ e.username || `#${e.user_id}` }}
                    </button>
                    <span v-if="e.title" class="text-gray-500"> · {{ e.title }}</span>
                  </li>
                </ul>
                <div
                  v-if="empTotalPages > 1"
                  class="flex items-center justify-center gap-3 text-sm pt-2 border-t border-gray-100"
                >
                  <button
                    type="button"
                    class="px-2 py-1 rounded border disabled:opacity-40"
                    :disabled="empPage <= 1"
                    @click="prevEmpPage"
                  >
                    &lt;
                  </button>
                  <span class="min-w-[2rem] text-center font-medium">{{ empPage }}</span>
                  <button
                    type="button"
                    class="px-2 py-1 rounded border disabled:opacity-40"
                    :disabled="empPage >= empTotalPages"
                    @click="nextEmpPage"
                  >
                    &gt;
                  </button>
                </div>
              </template>
            </div>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>
