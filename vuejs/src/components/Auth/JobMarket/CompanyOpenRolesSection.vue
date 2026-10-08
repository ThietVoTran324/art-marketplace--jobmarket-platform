<script setup>
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useI18n } from 'vue-i18n';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';

const props = defineProps({
  companyId: { type: Number, required: true },
  companyOwnerUserId: { type: Number, default: null },
  companyDisplayName: { type: String, default: '' },
});

const { t } = useI18n();
const jobs = ref([]);
const loading = ref(false);
const avatarTick = ref(0);

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return t('explore.expiry.emDash');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('explore.expiry.emDash');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeftLabel(iso) {
  if (!iso) return '';
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return '';
  const days = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return t('explore.expiry.expired');
  if (days === 0) return t('explore.expiry.expiresToday');
  return t('explore.expiry.daysLeft', days, { named: { days } });
}

function formatSalary(j) {
  if (!j) return '';
  if (j.salary_mode === 'love_it') return t('explore.salary.loveIt');
  const cur = j.currency || 'VND';
  if (j.salary_min != null && j.salary_max != null) {
    return t('explore.salary.range', { min: j.salary_min, max: j.salary_max, currency: cur });
  }
  if (j.salary_min != null) return t('explore.salary.from', { min: j.salary_min, currency: cur });
  if (j.salary_max != null) return t('explore.salary.upTo', { max: j.salary_max, currency: cur });
  return t('explore.salary.currencyOnly', { currency: cur });
}

function locationSummary(j) {
  const locs = j?.locations || [];
  if (!locs.length) return t('explore.expiry.emDash');
  return locs
    .map((l) => [l.city, l.label || l.address_line].filter(Boolean).join(' · '))
    .join('; ');
}

function companyLabel(j) {
  return (
    j.company_display_name ||
    props.companyDisplayName ||
    t('explore.list.companyFallback', { id: j.company_id || props.companyId })
  );
}

function yearsShortLabel(years) {
  return t('explore.list.yearsShort', { years });
}

function postedLine(j) {
  const posted = t('explore.list.posted', { date: formatPosted(j.created_at) });
  const expiry = daysLeftLabel(j.expires_at);
  const count = Number(j.application_count) || 0;
  const parts = [posted];
  if (expiry) parts.push(expiry);
  parts.push(t('explore.list.appliesCount', { count }));
  return parts.join(' · ');
}

function jobLogo(j) {
  avatarTick.value;
  const id = j.company_owner_user_id || props.companyOwnerUserId;
  return getCachedCompanyAvatar(id);
}

function openJob(id) {
  window.open(`/jobs/${id}`, '_blank', 'noopener,noreferrer');
}

async function load() {
  if (!props.companyId) return;
  loading.value = true;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${props.companyId}/job-posts`, {
      params: { status: 'active' },
    });
    jobs.value = data || [];
    const ownerIds = jobs.value
      .map((j) => j.company_owner_user_id || props.companyOwnerUserId)
      .filter(Boolean);
    await Promise.all([...new Set(ownerIds)].map((id) => fetchCompanyAvatar(id)));
    avatarTick.value += 1;
  } catch {
    jobs.value = [];
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.companyId,
  () => load(),
  { immediate: false }
);

onMounted(load);
</script>

<template>
  <section class="border border-gray-200 rounded-2xl bg-white overflow-hidden flex flex-col max-h-[70vh]">
    <header class="shrink-0 z-10 bg-white border-b border-gray-100 px-6 py-4">
      <h2 class="text-xl font-bold text-gray-900">{{ t('jobMarket.companyView.openRoles') }}</h2>
    </header>
    <div class="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6">
      <p v-if="loading" class="text-sm text-gray-500">{{ t('jobMarket.companyView.loading') }}</p>
      <p v-else-if="!jobs.length" class="text-sm text-gray-500">{{ t('jobMarket.companyView.noJobs') }}</p>
      <ul v-else class="space-y-3">
        <li
          v-for="j in jobs"
          :key="j.id"
          class="border border-gray-200 rounded-2xl px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
          @click="openJob(j.id)"
        >
          <div class="flex justify-between gap-4 items-start">
            <div class="flex items-start gap-3 min-w-0">
              <img
                v-if="jobLogo(j)"
                :src="jobLogo(j)"
                alt=""
                class="w-12 h-12 rounded-xl object-cover bg-gray-100 shrink-0"
              />
              <div
                v-else
                class="w-12 h-12 rounded-xl bg-gray-100 shrink-0 flex items-center justify-center text-gray-400"
              >
                <i class="pi pi-building text-sm" />
              </div>
              <div class="min-w-0">
                <p class="text-lg font-bold text-gray-900">{{ j.title }}</p>
                <p class="text-sm text-gray-600">{{ companyLabel(j) }}</p>
              </div>
            </div>
            <p class="text-sm font-medium whitespace-nowrap shrink-0" style="color: #16a34a">
              {{ formatSalary(j) }}
            </p>
          </div>
          <p class="text-sm text-gray-500 mt-2">
            {{ yearsShortLabel(j.years_experience) }} · {{ locationSummary(j) }}
          </p>
          <p class="text-xs text-gray-500 mt-1">{{ postedLine(j) }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
