<script setup>
import { onMounted, ref } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  companyId: { type: Number, required: true },
});

const router = useRouter();
const { t } = useI18n();
const jobs = ref([]);
const loading = ref(true);
const error = ref(null);

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return t('jobMarket.shared.emDash');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('jobMarket.shared.emDash');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeftLabel(iso) {
  if (!iso) return '';
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return '';
  const days = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return t('jobMarket.shared.expiry.expired');
  if (days === 0) return t('jobMarket.shared.expiry.expiresToday');
  return t('jobMarket.shared.expiry.daysLeft', days, { days });
}

function formatSalary(job) {
  if (job.salary_mode === 'love_it') return t('jobMarket.shared.salary.loveIt');
  const cur = job.currency || 'VND';
  if (job.salary_min != null && job.salary_max != null) {
    return t('jobMarket.shared.salary.range', { min: job.salary_min, max: job.salary_max, currency: cur });
  }
  if (job.salary_min != null) return t('jobMarket.shared.salary.from', { min: job.salary_min, currency: cur });
  if (job.salary_max != null) return t('jobMarket.shared.salary.upTo', { max: job.salary_max, currency: cur });
  return t('jobMarket.shared.salary.currencyOnly', { currency: cur });
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get(
      `/api/job-market/companies/${props.companyId}/job-posts`,
      { params: { status: 'active' } }
    );
    jobs.value = data || [];
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.hiringJobsTab.errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <h2 class="text-2xl font-bold mb-4">{{ t('jobMarket.hiring') }}</h2>
    <p v-if="loading" class="text-gray-500">{{ t('jobMarket.shared.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>
    <p v-else-if="!jobs.length" class="text-gray-500">{{ t('jobMarket.hiringJobsTab.empty') }}</p>
    <ul v-else class="space-y-3">
      <li
        v-for="job in jobs"
        :key="job.id"
        class="border border-gray-200 rounded-2xl px-4 py-3 cursor-pointer hover:bg-gray-50"
        @click="router.push(`/jobs/${job.id}`)"
      >
        <p class="font-semibold">{{ job.title }}</p>
        <p class="text-sm text-gray-600">
          {{ t('jobMarket.shared.yearsShort', { years: job.years_experience }) }} · {{ formatSalary(job) }}
        </p>
        <p class="text-xs text-gray-500 mt-1">
          {{ t('jobMarket.shared.posted', { date: formatPosted(job.created_at) }) }} · {{ daysLeftLabel(job.expires_at) }}
        </p>
      </li>
    </ul>
  </div>
</template>
