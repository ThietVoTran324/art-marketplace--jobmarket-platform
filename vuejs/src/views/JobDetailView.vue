<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { authUserStore } from '@/stores/authUserStore';

const route = useRoute();
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

const reportReasons = [
  { value: 'spam', label: 'Spam' },
  { value: 'scam', label: 'Scam' },
  { value: 'inappropriate', label: 'Inappropriate' },
  { value: 'other', label: 'Other' },
];

const jobId = computed(() => Number(route.params.id));
const applyBlocked = computed(() => !userStore.canApplyToJobs);
const applyBlockedReason = computed(() => {
  if (userStore.isAdmin) return 'Admin accounts cannot apply';
  if (userStore.isOrganization) return 'Organization accounts cannot apply';
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
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeftLabel(iso) {
  if (!iso) return '';
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return '';
  const days = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return 'expired';
  if (days === 0) return 'expires today';
  return `${days} day${days === 1 ? '' : 's'} left`;
}

function formatSalary(j) {
  if (!j) return '';
  if (j.salary_mode === 'love_it') return 'Love it';
  const cur = j.currency || 'VND';
  if (j.salary_min != null && j.salary_max != null) {
    return `${j.salary_min} – ${j.salary_max} ${cur}`;
  }
  if (j.salary_min != null) return `From ${j.salary_min} ${cur}`;
  if (j.salary_max != null) return `Up to ${j.salary_max} ${cur}`;
  return cur;
}

async function load() {
  loading.value = true;
  error.value = null;
  job.value = null;
  try {
    const { data } = await axios.get(`/api/job-market/jobs/${jobId.value}`);
    job.value = data;
  } catch (e) {
    error.value = e.response?.data?.detail || 'Job not found';
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
      if (!selectedCvId.value) throw new Error('Select a CV');
      form.append('cv_id', String(selectedCvId.value));
    } else {
      if (!oneshotFile.value) throw new Error('Upload a CV');
      form.append('cv', oneshotFile.value);
    }
    await axios.post(`/api/job-market/jobs/${jobId.value}/apply`, form);
    showApply.value = false;
    await load();
  } catch (e) {
    applyError.value =
      e.response?.data?.detail || e.message || 'Apply failed';
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
    reportError.value = e.response?.data?.detail || e.message || 'Report failed';
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
      ← Back to Explore
    </button>

    <p v-if="loading" class="text-gray-500">Loading…</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>
    <template v-else-if="job">
      <h1 class="text-3xl font-extrabold text-gray-900">{{ job.title }}</h1>
      <RouterLink
        v-if="job.company_id"
        :to="`/companies/${job.company_id}`"
        class="text-lg text-gray-700 mt-1 inline-block hover:underline"
      >
        {{ job.company_display_name || `Company #${job.company_id}` }}
      </RouterLink>
      <p v-else class="text-lg text-gray-700 mt-1">{{ job.company_display_name }}</p>
      <p class="text-sm text-gray-500 mt-2">
        {{ job.years_experience }} years experience · {{ formatSalary(job) }}
        <span v-if="job.status === 'closed'" class="ml-2 text-red-600">(Closed)</span>
      </p>
      <p class="text-sm text-gray-500 mt-1">
        Posted {{ formatPosted(job.created_at) }} · {{ daysLeftLabel(job.expires_at) }}
      </p>
      <p v-if="job.my_application" class="mt-2 text-sm font-medium text-gray-800">
        Đã apply vào {{ formatPosted(job.my_application.created_at) }}
        <span class="text-gray-500 font-normal">
          · {{ job.my_application.status }}
        </span>
      </p>

      <div class="mt-4">
        <p class="font-semibold text-gray-800">Locations</p>
        <ul class="list-disc ml-5 text-sm text-gray-700">
          <li v-for="loc in job.locations || []" :key="loc.id">
            <span v-if="loc.label">{{ loc.label }} — </span>{{ loc.address_line }}
            <span v-if="loc.city">, {{ loc.city }}</span>
          </li>
        </ul>
      </div>

      <section v-if="job.description" class="mt-6">
        <h2 class="font-bold text-gray-900 mb-1">Description</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.description }}</p>
      </section>
      <section v-if="job.requirements" class="mt-4">
        <h2 class="font-bold text-gray-900 mb-1">Requirements</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.requirements }}</p>
      </section>
      <section v-if="job.benefits" class="mt-4">
        <h2 class="font-bold text-gray-900 mb-1">Benefits</h2>
        <p class="whitespace-pre-line text-gray-800">{{ job.benefits }}</p>
      </section>

      <div class="mt-8 flex items-center gap-3 flex-wrap">
        <button
          v-if="canApply"
          type="button"
          class="px-6 py-3 rounded-2xl bg-red-600 text-white hover:bg-red-700"
          @click="openApply"
        >
          Apply
        </button>
        <button
          v-else-if="applyBlocked"
          type="button"
          disabled
          class="px-6 py-3 rounded-2xl bg-gray-300 text-gray-600 cursor-not-allowed"
        >
          Apply
        </button>
        <span v-if="applyBlocked" class="text-sm text-gray-500">{{ applyBlockedReason }}</span>
        <span
          v-else-if="job.my_application"
          class="px-6 py-3 rounded-2xl bg-gray-100 text-gray-800 text-sm font-medium"
        >
          Đã apply vào {{ formatPosted(job.my_application.created_at) }}
          <span class="text-gray-500 font-normal">· {{ job.my_application.status }}</span>
        </span>
        <button
          v-if="canReport"
          type="button"
          class="px-4 py-2 rounded-2xl border text-sm"
          @click="openReport"
        >
          Report
        </button>
        <span v-if="reportDone" class="text-sm text-gray-600">Report submitted</span>
      </div>
    </template>

    <div
      v-if="showReport"
      class="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
      @click.self="showReport = false"
    >
      <div class="bg-white rounded-2xl p-6 w-full max-w-md space-y-3">
        <h3 class="text-xl font-bold">Report job</h3>
        <p v-if="reportError" class="text-red-600 text-sm">{{ reportError }}</p>
        <label class="block text-sm">
          Reason
          <select v-model="reportReason" class="w-full border rounded-lg px-3 py-2 mt-1">
            <option v-for="r in reportReasons" :key="r.value" :value="r.value">
              {{ r.label }}
            </option>
          </select>
        </label>
        <label class="block text-sm">
          Details
          <span v-if="reportReason === 'other'"> (required)</span>
          <textarea v-model="reportDetail" rows="3" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <div class="flex gap-2 pt-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50"
            :disabled="reporting || (reportReason === 'other' && !reportDetail.trim())"
            @click="submitReport"
          >
            Submit report
          </button>
          <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="showReport = false">
            Cancel
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
        <h3 class="text-xl font-bold">Apply</h3>
        <p v-if="applyError" class="text-red-600 text-sm">{{ applyError }}</p>
        <label class="block text-sm">
          Cover note (optional)
          <textarea v-model="coverNote" rows="3" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="block text-sm">
          Cover file (optional)
          <input type="file" class="mt-1 block" accept=".pdf,.doc,.docx" @change="coverFile = $event.target.files[0]" />
        </label>
        <div class="flex gap-4 text-sm">
          <label><input type="radio" value="tab" v-model="cvMode" :disabled="!myCvs.length" /> Use saved CV</label>
          <label><input type="radio" value="oneshot" v-model="cvMode" /> Upload CV</label>
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
            Submit
          </button>
          <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="showApply = false">
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
