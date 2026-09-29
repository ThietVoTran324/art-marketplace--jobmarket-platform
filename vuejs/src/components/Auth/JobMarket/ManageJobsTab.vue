<script setup>
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';
import { profilePath } from '@/utils/profileLinks';

const router = useRouter();

const props = defineProps({
  companyId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
});

const jobs = ref([]);
const branches = ref([]);
const loading = ref(true);
const error = ref(null);
const saving = ref(false);
const showForm = ref(false);
const editingId = ref(null);
const applicantsJobId = ref(null);
const applicants = ref([]);
const applicantsLoading = ref(false);

const form = ref(emptyForm());

function pad(n) {
  return String(n).padStart(2, '0');
}

/** Local datetime-local value from Date. */
function toLocalInput(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultExpiresLocal() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  d.setSeconds(0, 0);
  return toLocalInput(d);
}

function isoFromLocalInput(local) {
  if (!local) return null;
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
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
  const ms = end.getTime() - Date.now();
  const days = Math.ceil(ms / (24 * 60 * 60 * 1000));
  if (days < 0) return 'expired';
  if (days === 0) return 'expires today';
  return `${days} day${days === 1 ? '' : 's'} left`;
}

function emptyForm() {
  return {
    title: '',
    years_experience: 0,
    description: '',
    requirements: '',
    benefits: '',
    salary_mode: 'range',
    salary_min: '',
    salary_max: '',
    currency: 'VND',
    branch_ids: [],
    expires_at: defaultExpiresLocal(),
  };
}

function formatSalary(job) {
  if (job.salary_mode === 'love_it') return 'Love it';
  const cur = job.currency || 'VND';
  if (job.salary_min != null && job.salary_max != null) {
    return `${job.salary_min} – ${job.salary_max} ${cur}`;
  }
  if (job.salary_min != null) return `From ${job.salary_min} ${cur}`;
  if (job.salary_max != null) return `Up to ${job.salary_max} ${cur}`;
  return cur;
}

async function load() {
  if (!props.isOwner) return;
  loading.value = true;
  error.value = null;
  try {
    const [jRes, bRes] = await Promise.all([
      axios.get('/api/job-market/me/job-posts'),
      axios.get(`/api/job-market/companies/${props.companyId}/branches`),
    ]);
    jobs.value = jRes.data || [];
    branches.value = bRes.data || [];
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load';
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  form.value = emptyForm();
  if (branches.value.length === 1) {
    form.value.branch_ids = [branches.value[0].id];
  }
  showForm.value = true;
}

function openEdit(job) {
  editingId.value = job.id;
  form.value = {
    title: job.title,
    years_experience: job.years_experience,
    description: job.description || '',
    requirements: job.requirements || '',
    benefits: job.benefits || '',
    salary_mode: job.salary_mode,
    salary_min: job.salary_min ?? '',
    salary_max: job.salary_max ?? '',
    currency: job.currency || 'VND',
    branch_ids: (job.locations || [])
      .map((l) => l.source_branch_id)
      .filter((id) => id != null),
    expires_at: job.expires_at ? toLocalInput(new Date(job.expires_at)) : defaultExpiresLocal(),
  };
  showForm.value = true;
}

function buildPayload() {
  const expiresIso = isoFromLocalInput(form.value.expires_at);
  const payload = {
    title: form.value.title.trim(),
    years_experience: Number(form.value.years_experience),
    description: form.value.description || null,
    requirements: form.value.requirements || null,
    benefits: form.value.benefits || null,
    salary_mode: form.value.salary_mode,
    currency: form.value.currency,
    branch_ids: [...form.value.branch_ids],
    expires_at: expiresIso,
  };
  if (form.value.salary_mode === 'love_it') {
    payload.salary_min = null;
    payload.salary_max = null;
  } else {
    payload.salary_min =
      form.value.salary_min === '' ? null : Number(form.value.salary_min);
    payload.salary_max =
      form.value.salary_max === '' ? null : Number(form.value.salary_max);
  }
  return payload;
}

async function save() {
  saving.value = true;
  error.value = null;
  try {
    const payload = buildPayload();
    if (!payload.branch_ids.length) {
      error.value = 'Select at least one branch';
      return;
    }
    if (!payload.expires_at) {
      error.value = 'Expires at is required';
      return;
    }
    if (editingId.value) {
      await axios.patch(`/api/job-market/me/job-posts/${editingId.value}`, payload);
    } else {
      await axios.post('/api/job-market/me/job-posts', payload);
    }
    showForm.value = false;
    await load();
  } catch (e) {
    error.value = e.response?.data?.detail || 'Save failed';
  } finally {
    saving.value = false;
  }
}

async function closeJob(id) {
  try {
    await axios.post(`/api/job-market/me/job-posts/${id}/close`);
    await load();
  } catch (e) {
    error.value = e.response?.data?.detail || 'Close failed';
  }
}

async function reopenJob(id) {
  try {
    await axios.post(`/api/job-market/me/job-posts/${id}/reopen`);
    await load();
  } catch (e) {
    const detail = e.response?.data?.detail;
    error.value =
      detail === 'expires_at_must_be_extended'
        ? 'Extend expires_at (Edit) before reopening'
        : detail || 'Reopen failed';
  }
}

async function openApplicants(jobId) {
  applicantsJobId.value = jobId;
  applicantsLoading.value = true;
  try {
    const { data } = await axios.get(`/api/job-market/me/job-posts/${jobId}/applications`);
    applicants.value = data || [];
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load applicants';
    applicants.value = [];
  } finally {
    applicantsLoading.value = false;
  }
}

async function decide(appId, action) {
  try {
    await axios.post(
      `/api/job-market/me/job-posts/${applicantsJobId.value}/applications/${appId}/${action}`
    );
    await openApplicants(applicantsJobId.value);
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action failed';
  }
}

function toggleBranch(id) {
  const idx = form.value.branch_ids.indexOf(id);
  if (idx >= 0) form.value.branch_ids.splice(idx, 1);
  else form.value.branch_ids.push(id);
}

onMounted(load);
watch(
  () => props.companyId,
  () => load()
);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold">Manage jobs</h2>
      <button
        v-if="isOwner"
        type="button"
        class="px-4 py-2 rounded-xl bg-red-600 text-white hover:bg-red-700"
        @click="openCreate"
      >
        New job
      </button>
    </div>

    <p v-if="!isOwner" class="text-gray-500">Owner only.</p>
    <p v-else-if="loading" class="text-gray-500">Loading…</p>
    <p v-if="error" class="text-red-600 mb-3">{{ error }}</p>

    <div v-if="showForm && isOwner" class="mb-6 border border-gray-200 rounded-2xl p-4 space-y-3">
      <label class="block text-sm">
        Title
        <input v-model="form.title" class="w-full border rounded-lg px-3 py-2 mt-1" />
      </label>
      <label class="block text-sm">
        Years experience
        <input v-model.number="form.years_experience" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
      </label>
      <label class="block text-sm">
        Expires at
        <input v-model="form.expires_at" type="datetime-local" class="w-full border rounded-lg px-3 py-2 mt-1" required />
      </label>
      <label class="block text-sm">
        Description
        <textarea v-model="form.description" rows="3" class="w-full border rounded-lg px-3 py-2 mt-1" />
      </label>
      <label class="block text-sm">
        Requirements
        <textarea v-model="form.requirements" rows="2" class="w-full border rounded-lg px-3 py-2 mt-1" />
      </label>
      <label class="block text-sm">
        Benefits
        <textarea v-model="form.benefits" rows="2" class="w-full border rounded-lg px-3 py-2 mt-1" />
      </label>
      <div class="flex gap-4 flex-wrap">
        <label class="text-sm">
          Salary mode
          <select v-model="form.salary_mode" class="block border rounded-lg px-3 py-2 mt-1">
            <option value="range">Range</option>
            <option value="love_it">Love it</option>
          </select>
        </label>
        <label v-if="form.salary_mode === 'range'" class="text-sm">
          Min
          <input v-model="form.salary_min" type="number" min="0" class="block border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label v-if="form.salary_mode === 'range'" class="text-sm">
          Max
          <input v-model="form.salary_max" type="number" min="0" class="block border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="text-sm">
          Currency
          <select v-model="form.currency" class="block border rounded-lg px-3 py-2 mt-1">
            <option value="VND">VND</option>
            <option value="USD">USD</option>
          </select>
        </label>
      </div>
      <div>
        <p class="text-sm font-medium mb-2">Branches (locations)</p>
        <div v-if="!branches.length" class="text-sm text-gray-500">No branches — add some in Company tab first.</div>
        <label
          v-for="b in branches"
          :key="b.id"
          class="flex items-start gap-2 text-sm mb-1"
        >
          <input
            type="checkbox"
            :checked="form.branch_ids.includes(b.id)"
            @change="toggleBranch(b.id)"
          />
          <span>
            <span v-if="b.label">{{ b.label }} — </span>{{ b.address_line }}
            <span v-if="b.city">, {{ b.city }}</span>
          </span>
        </label>
      </div>
      <div class="flex gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-xl bg-red-600 text-white disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ editingId ? 'Update' : 'Create' }}
        </button>
        <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="showForm = false">
          Cancel
        </button>
      </div>
    </div>

    <ul v-if="isOwner && !loading" class="space-y-3">
      <li
        v-for="job in jobs"
        :key="job.id"
        class="border border-gray-200 rounded-2xl px-4 py-3"
      >
        <div class="flex justify-between gap-3 items-start">
          <div>
            <p class="font-semibold">{{ job.title }}</p>
            <p class="text-sm text-gray-600">
              {{ job.status }} · {{ job.years_experience }} yrs · {{ formatSalary(job) }}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              Posted {{ formatPosted(job.created_at) }} · {{ daysLeftLabel(job.expires_at) }}
              <span v-if="job.expires_at"> (until {{ formatPosted(job.expires_at) }})</span>
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button type="button" class="text-sm px-3 py-1 rounded-lg bg-gray-100" @click="openEdit(job)">
              Edit
            </button>
            <button
              type="button"
              class="text-sm px-3 py-1 rounded-lg bg-blue-100"
              @click="openApplicants(job.id)"
            >
              Applicants
            </button>
            <button
              v-if="job.status === 'active'"
              type="button"
              class="text-sm px-3 py-1 rounded-lg bg-black text-white"
              @click="closeJob(job.id)"
            >
              Close
            </button>
            <button
              v-else
              type="button"
              class="text-sm px-3 py-1 rounded-lg bg-red-600 text-white"
              @click="reopenJob(job.id)"
            >
              Reopen
            </button>
          </div>
        </div>
      </li>
    </ul>

    <div v-if="applicantsJobId" class="mt-6 border border-gray-200 rounded-2xl p-4">
      <div class="flex justify-between items-center mb-3">
        <h3 class="font-bold">Applicants</h3>
        <button type="button" class="text-sm underline" @click="applicantsJobId = null">Close</button>
      </div>
      <p v-if="applicantsLoading" class="text-gray-500">Loading…</p>
      <p v-else-if="!applicants.length" class="text-gray-500">No applications yet.</p>
      <ul v-else class="space-y-2">
        <li
          v-for="app in applicants"
          :key="app.id"
          class="flex flex-wrap gap-2 items-center justify-between border-b border-gray-100 py-2"
        >
          <div class="text-sm">
            <button type="button" class="font-semibold underline" @click="router.push(profilePath(app.applicant_username, { tab: 'experience' }))">
              {{ app.applicant_username || app.applicant_user_id }}
            </button>
            · <span class="uppercase">{{ app.status }}</span>
            · {{ app.cv_original_filename }}
          </div>
          <div class="flex gap-2">
            <button
              type="button"
              class="text-sm px-2 py-1 rounded bg-gray-100"
              @click="router.push(`/applications/${app.id}/cv`)"
            >
              View CV
            </button>
            <button
              v-if="!['rejected','passed'].includes(app.status)"
              type="button"
              class="text-sm px-2 py-1 rounded bg-black text-white"
              @click="decide(app.id, 'reject')"
            >
              Reject
            </button>
            <button
              v-if="!['rejected','passed'].includes(app.status)"
              type="button"
              class="text-sm px-2 py-1 rounded bg-red-600 text-white"
              @click="decide(app.id, 'pass')"
            >
              Pass
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
