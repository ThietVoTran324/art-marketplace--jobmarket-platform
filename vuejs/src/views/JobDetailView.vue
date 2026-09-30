<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { authUserStore } from '@/stores/authUserStore';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const { t } = useI18n();
const router = useRouter();
const userStore = authUserStore();
const job = ref(null);
const loading = ref(true);
const error = ref(null);
const showApply = ref(false);
const applying = ref(false);
const applyError = ref(null);
const myCvs = ref([]);
const cvMode = ref('tab');
const selectedCvId = ref(null);
const coverNote = ref('');
const coverFile = ref(null);
const oneshotFile = ref(null);
const showReport = ref(false);
const reporting = ref(false);
const reportError = ref(null);
const reportReason = ref('spam');
const reportDetail = ref('');
const reportDone = ref(false);

const reportReasons = computed(() => [
  { value: 'spam', label: t('jobDetail.reportModal.reasons.spam') },
  { value: 'scam', label: t('jobDetail.reportModal.reasons.scam') },
  { value: 'inappropriate', label: t('jobDetail.reportModal.reasons.inappropriate') },
  { value: 'other', label: t('jobDetail.reportModal.reasons.other') },
]);

const jobId = computed(() => Number(route.params.id));
const applyBlocked = computed(() => !userStore.canApplyToJobs);
const applyBlockedReason = computed(() => {
  if (userStore.isAdmin) return t('jobDetail.applyBlocked.admin');
  if (userStore.isOrganization) return t('jobDetail.applyBlocked.organization');
  return '';
});
const canApply = computed(
  () =>
    job.value &&
    job.value.status === 'active' &&
    userStore.canApplyToJobs &&
    !job.value.my_application
);
const canReport = computed(() => !!job.value && userStore.authUserId != null);

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return t('jobDetail.expiry.emDash');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('jobDetail.expiry.emDash');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeftLabel(iso) {
  if (!iso) return '';
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return '';
  const days = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return t('jobDetail.expiry.expired');
  if (days === 0) return t('jobDetail.expiry.expiresToday');
  return t('jobDetail.expiry.daysLeft', days, { days });
}

function formatSalary(j) {
  if (!j) return '';
  if (j.salary_mode === 'love_it') return t('jobDetail.salary.loveIt');
  const cur = j.currency || 'VND';
  if (j.salary_min != null && j.salary_max != null) {
    return t('jobDetail.salary.range', { min: j.salary_min, max: j.salary_max, currency: cur });
  }
  if (j.salary_min != null) return t('jobDetail.salary.from', { min: j.salary_min, currency: cur });
  if (j.salary_max != null) return t('jobDetail.salary.upTo', { max: j.salary_max, currency: cur });
  return t('jobDetail.salary.currencyOnly', { currency: cur });
}

function companyLabel(j) {
  if (j.company_id) {
    return j.company_display_name || t('jobDetail.meta.companyFallback', { id: j.company_id });
  }
  return j.company_display_name || '';
}

async function load() {
  loading.value = true;
  error.value = null;
  job.value = null;
  try {
    const { data } = await axios.get(`/api/job-market/jobs/${jobId.value}`);
    job.value = data;
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobDetail.errors.notFound');
  } finally {
    loading.value = false;
  }
}

async function openApply() {
  applyError.value = null;
  showApply.value = true;
  try {
    const { data } = await axios.get('/api/job-market/me/cvs');
    myCvs.value = data || [];
    if (myCvs.value.length) {
      cvMode.value = 'tab';
      selectedCvId.value = myCvs.value[0].id;
    } else {
      cvMode.value = 'oneshot';
    }
  } catch {
    myCvs.value = [];
    cvMode.value = 'oneshot';
  }
}

async function submitApply() {
  applying.value = true;
  applyError.value = null;
  try {
    const form = new FormData();
    if (coverNote.value.trim()) form.append('cover_note', coverNote.value.trim());
    if (coverFile.value) form.append('cover_file', coverFile.value);
    if (cvMode.value === 'tab') {
      if (!selectedCvId.value) throw new Error(t('jobDetail.applyModal.errors.selectCv'));
      form.append('cv_id', String(selectedCvId.value));
    } else {
      if (!oneshotFile.value) throw new Error(t('jobDetail.applyModal.errors.uploadCv'));
      form.append('cv', oneshotFile.value);
    }
    await axios.post(`/api/job-market/jobs/${jobId.value}/apply`, form);
    showApply.value = false;
    await load();
  } catch (e) {
    applyError.value =
      e.response?.data?.detail || e.message || t('jobDetail.applyModal.errors.failed');
  } finally {
    applying.value = false;
  }
}

function openReport() {
  reportError.value = null;
  reportReason.value = 'spam';
  reportDetail.value = '';
  showReport.value = true;
}

async function submitReport() {
  reporting.value = true;
  reportError.value = null;
  try {
    const payload = { reason: reportReason.value };
    if (reportReason.value === 'other' || reportDetail.value.trim()) {
      payload.detail = reportDetail.value.trim();
    }
    await axios.post(`/api/job-market/jobs/${jobId.value}/report`, payload);
    showReport.value = false;
    reportDone.value = true;
  } catch (e) {
    reportError.value = e.response?.data?.detail || e.message || t('jobDetail.reportModal.errors.failed');
  } finally {
    reporting.value = false;
  }
}

onMounted(load);
watch(jobId, () => {
  reportDone.value = false;
  load();
});
</script>

<template>
  <div class="ml-24 mr-8 mt-8 max-w-3xl">
    <button type="button" class="text-sm text-gray-600 hover:underline mb-4" @click="router.push('/explore')">
      {{ t('jobDetail.backToExplore') }}
    </button>

    <p v-if="loading" class="text-gray-500">{{ t('jobDetail.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>
    <template v-else-if="job">
      <h1 class="text-3xl font-extrabold text-gray-900">{{ job.title }}</h1>
      <RouterLink
        v-if="job.company_id"
        :to="`/companies/${job.company_id}`"
        class="text-lg text-gray-700 mt-1 inline-block hover:underline"
      >
        {{ companyLabel(job) }}
      </RouterLink>
      <p v-else class="text-lg text-gray-700 mt-1">{{ companyLabel(job) }}</p>
      <p class="text-sm text-gray-500 mt-2">
        {{ t('jobDetail.meta.yearsExperience', { years: job.years_experience }) }} · {{ formatSalary(job) }}
        <span v-if="job.status === 'closed'" class="ml-2 text-red-600">{{ t('jobDetail.meta.closed') }}</span>
      </p>
      <p class="text-sm text-gray-500 mt-1">
        {{ t('jobDetail.meta.posted', { date: formatPosted(job.created_at) }) }} · {{ daysLeftLabel(job.expires_at) }}
      </p>
      <p v-if="job.my_application" class="mt-2 text-sm font-medium text-gray-800">
        {{ t('jobMarket.appliedAt', { date: formatPosted(job.my_application.created_at) }) }}
        <span class="text-gray-500 font-normal">
          · {{ job.my_application.status }}
        </span>
      </p>

      <div class="mt-4">
        <p class="font-semibold text-gray-800">{{ t('jobDetail.sections.locations') }}</p>
        <ul class="list-disc ml-5 text-sm text-gray-700">
          <li v-for="loc in job.locations || []" :key="loc.id">
            <span v-if="loc.label">{{ loc.label }} — </span>{{ loc.address_line }}
            <span v-if="loc.city">, {{ loc.city }}</span>
          </li>
        </ul>
      </div>

      <section v-if="job.description" class="mt-6">
        <h2 class="font-bold text-gray-900 mb-1">{{ t('jobDetail.sections.description') }}</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.description }}</p>
      </section>
      <section v-if="job.requirements" class="mt-4">
        <h2 class="font-bold text-gray-900 mb-1">{{ t('jobDetail.sections.requirements') }}</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.requirements }}</p>
      </section>
      <section v-if="job.benefits" class="mt-4">
        <h2 class="font-bold text-gray-900 mb-1">{{ t('jobDetail.sections.benefits') }}</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.benefits }}</p>
      </section>

      <div class="mt-8 flex items-center gap-3 flex-wrap">
        <button
          v-if="canApply"
          type="button"
          class="px-6 py-3 rounded-2xl bg-red-600 text-white hover:bg-red-700"
          @click="openApply"
        >
          {{ t('jobDetail.actions.apply') }}
        </button>
        <button
          v-else-if="applyBlocked"
          type="button"
          disabled
          class="px-6 py-3 rounded-2xl bg-gray-300 text-gray-600 cursor-not-allowed"
        >
          {{ t('jobDetail.actions.apply') }}
        </button>
        <span v-if="applyBlocked" class="text-sm text-gray-500">{{ applyBlockedReason }}</span>
        <span
          v-else-if="job.my_application"
          class="px-6 py-3 rounded-2xl bg-gray-100 text-gray-800 text-sm font-medium"
        >
          {{ t('jobMarket.appliedAt', { date: formatPosted(job.my_application.created_at) }) }}
          <span class="text-gray-500 font-normal">· {{ job.my_application.status }}</span>
        </span>
        <button
          v-if="canReport"
          type="button"
          class="px-4 py-2 rounded-2xl border text-sm"
          @click="openReport"
        >
          {{ t('jobDetail.actions.report') }}
        </button>
        <span v-if="reportDone" class="text-sm text-gray-600">{{ t('jobDetail.actions.reportSubmitted') }}</span>
      </div>
    </template>

    <div
      v-if="showReport"
      class="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
      @click.self="showReport = false"
    >
      <div class="bg-white rounded-2xl p-6 w-full max-w-md space-y-3">
        <h3 class="text-xl font-bold">{{ t('jobDetail.reportModal.title') }}</h3>
        <p v-if="reportError" class="text-red-600 text-sm">{{ reportError }}</p>
        <label class="block text-sm">
          {{ t('jobDetail.reportModal.reason') }}
          <select v-model="reportReason" class="w-full border rounded-lg px-3 py-2 mt-1">
            <option v-for="r in reportReasons" :key="r.value" :value="r.value">
              {{ r.label }}
            </option>
          </select>
        </label>
        <label class="block text-sm">
          {{ t('jobDetail.reportModal.details') }}
          <span v-if="reportReason === 'other'">{{ t('jobDetail.reportModal.detailsRequired') }}</span>
          <textarea v-model="reportDetail" rows="3" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <div class="flex gap-2 pt-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50"
            :disabled="reporting || (reportReason === 'other' && !reportDetail.trim())"
            @click="submitReport"
          >
            {{ t('jobDetail.reportModal.submit') }}
          </button>
          <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="showReport = false">
            {{ t('jobDetail.reportModal.cancel') }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showApply"
      class="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
      @click.self="showApply = false"
    >
      <div class="bg-white rounded-2xl p-6 w-full max-w-lg space-y-3">
        <h3 class="text-xl font-bold">{{ t('jobDetail.applyModal.title') }}</h3>
        <p v-if="applyError" class="text-red-600 text-sm">{{ applyError }}</p>
        <label class="block text-sm">
          {{ t('jobDetail.applyModal.coverNote') }}
          <textarea v-model="coverNote" rows="3" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="block text-sm">
          {{ t('jobDetail.applyModal.coverFile') }}
          <input type="file" class="mt-1 block" accept=".pdf,.doc,.docx" @change="coverFile = $event.target.files[0]" />
        </label>
        <div class="flex gap-4 text-sm">
          <label><input type="radio" value="tab" v-model="cvMode" :disabled="!myCvs.length" /> {{ t('jobDetail.applyModal.cvUseSaved') }}</label>
          <label><input type="radio" value="oneshot" v-model="cvMode" /> {{ t('jobDetail.applyModal.cvUpload') }}</label>
        </div>
        <select
          v-if="cvMode === 'tab'"
          v-model="selectedCvId"
          class="w-full border rounded-lg px-3 py-2"
        >
          <option v-for="c in myCvs" :key="c.id" :value="c.id">{{ c.original_filename }}</option>
        </select>
        <input
          v-else
          type="file"
          accept=".pdf,.doc,.docx"
          @change="oneshotFile = $event.target.files[0]"
        />
        <div class="flex gap-2 pt-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-red-600 text-white disabled:opacity-50"
            :disabled="applying"
            @click="submitApply"
          >
            {{ t('jobDetail.applyModal.submit') }}
          </button>
          <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="showApply = false">
            {{ t('jobDetail.applyModal.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
