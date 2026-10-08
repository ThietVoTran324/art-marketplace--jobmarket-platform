<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const job = ref(null);
const company = ref(null);
const contact = ref(null);
const companyJobs = ref([]);
const companyJobsTotalHint = ref(false);
const employees = ref([]);
const related = ref([]);
const logoUrls = ref({});
const loading = ref(true);
const error = ref(null);
const sideTab = ref('contact'); // contact | jobs

const showApply = ref(false);
const applying = ref(false);
const applyError = ref(null);
const myCvs = ref([]);
const cvMode = ref('tab');
const selectedCvId = ref(null);
const coverNote = ref('');
const coverFile = ref(null);
const oneshotFile = ref(null);

const jobId = computed(() => Number(route.params.id));
const applyBlocked = computed(() => userStore.isAuthenticated && !userStore.canApplyToJobs);
const canApply = computed(
  () =>
    job.value &&
    job.value.status === 'active' &&
    (!job.value.expires_at || new Date(job.value.expires_at).getTime() > Date.now()) &&
    !job.value.my_application &&
    (!userStore.isAuthenticated || userStore.canApplyToJobs)
);

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
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
  if (!j) return '';
  if (j.company_id) {
    return j.company_display_name || t('jobDetail.meta.companyFallback', { id: j.company_id });
  }
  return j.company_display_name || '';
}

function locationSummary(j) {
  const locs = j?.locations || [];
  if (!locs.length) return '';
  return locs
    .slice(0, 2)
    .map((l) => {
      const parts = [l.label, l.address_line, l.city].filter(Boolean);
      return parts.join(', ') || l.address_line || '';
    })
    .filter(Boolean)
    .join(' · ');
}

async function ensureLogo(ownerId) {
  if (!ownerId || logoUrls.value[ownerId]) return;
  try {
    const r = await axios.get(`/api/users/upload/${ownerId}`, { responseType: 'blob' });
    logoUrls.value = { ...logoUrls.value, [ownerId]: URL.createObjectURL(r.data) };
  } catch {
    /* ignore */
  }
}

async function load() {
  loading.value = true;
  error.value = null;
  job.value = null;
  company.value = null;
  contact.value = null;
  companyJobs.value = [];
  employees.value = [];
  related.value = [];
  try {
    const { data } = await axios.get(`/api/job-market/jobs/${jobId.value}`);
    job.value = data;
    const cid = data.company_id;
    if (cid) {
      const [cRes, contactRes, jobsRes, empRes] = await Promise.allSettled([
        axios.get(`/api/job-market/companies/${cid}`),
        axios.get(`/api/job-market/companies/${cid}/contact`),
        axios.get(`/api/job-market/companies/${cid}/job-posts`, {
          params: { status: 'active', limit: 5 },
        }),
        axios.get(`/api/job-market/companies/${cid}/employees`, {
          params: { offset: 0, limit: 8 },
        }),
      ]);
      if (cRes.status === 'fulfilled') company.value = cRes.value.data;
      if (contactRes.status === 'fulfilled') contact.value = contactRes.value.data;
      if (jobsRes.status === 'fulfilled') {
        const list = jobsRes.value.data || [];
        companyJobs.value = list.slice(0, 5);
        companyJobsTotalHint.value = list.length > 5;
      }
      if (empRes.status === 'fulfilled') {
        employees.value = empRes.value.data?.employees || [];
      }
    }
    const { data: rel } = await axios.get(`/api/job-market/jobs/${jobId.value}/related`, {
      params: { limit: 10 },
    });
    related.value = rel || [];
    const owners = new Set(
      related.value.map((j) => j.company_owner_user_id).filter(Boolean)
    );
    if (data.company_owner_user_id) owners.add(data.company_owner_user_id);
    await Promise.all([...owners].map((id) => ensureLogo(id)));
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobDetail.errors.notFound');
  } finally {
    loading.value = false;
  }
}

function requireLogin(redirectTo) {
  if (userStore.isAuthenticated) return true;
  openAuthModal('login', { redirectTo: redirectTo || route.fullPath });
  return false;
}

async function openApply() {
  if (!requireLogin(route.fullPath)) return;
  if (!userStore.canApplyToJobs) return;
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

function goCompany() {
  if (!job.value?.company_id) return;
  const path = `/companies/${job.value.company_id}`;
  if (!requireLogin(path)) return;
  router.push(path);
}

function openRelated(id) {
  window.open(`/jobs/${id}`, '_blank', 'noopener,noreferrer');
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

const relatedRows = computed(() => {
  const list = related.value.slice(0, 10);
  return [list.slice(0, 5), list.slice(5, 10)];
});

onMounted(load);
watch(jobId, load);
</script>

<template>
  <div class="ml-24 mr-6 mt-8 mb-12">
    <p v-if="loading" class="text-gray-500">{{ t('jobDetail.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>

    <template v-else-if="job">
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <!-- 3/4 left -->
        <div class="lg:col-span-3 space-y-6">
          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
            <div class="flex items-start gap-4">
              <img
                v-if="job.company_owner_user_id && logoUrls[job.company_owner_user_id]"
                :src="logoUrls[job.company_owner_user_id]"
                alt=""
                class="w-16 h-16 rounded-xl object-cover bg-gray-100"
              />
              <div
                v-else
                class="w-16 h-16 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400"
              >
                <i class="pi pi-building text-2xl" />
              </div>
              <div>
                <button
                  type="button"
                  class="text-xl font-bold text-gray-900 hover:underline text-left"
                  @click="goCompany"
                >
                  {{ company?.display_name || companyLabel(job) }}
                </button>
                <p v-if="company?.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
                <p v-if="company?.description" class="text-sm text-gray-700 mt-2 whitespace-pre-line line-clamp-4">
                  {{ company.description }}
                </p>
                <p v-if="company?.website" class="text-sm mt-2">
                  <a :href="company.website" target="_blank" rel="noopener" class="text-red-600 hover:underline">
                    {{ company.website }}
                  </a>
                </p>
              </div>
            </div>
          </section>

          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
            <h1 class="text-3xl font-extrabold text-gray-900">{{ job.title }}</h1>
            <p class="text-sm text-gray-500 mt-2">
              {{ t('jobDetail.meta.yearsExperience', { years: job.years_experience }) }} · {{ formatSalary(job) }}
            </p>
            <p class="text-sm text-gray-500 mt-1">
              {{ t('jobDetail.meta.posted', { date: formatPosted(job.created_at) }) }}
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

            <div class="mt-8 flex flex-wrap gap-3">
              <button
                v-if="canApply"
                type="button"
                class="px-6 py-3 rounded-2xl bg-red-600 text-white hover:bg-red-700"
                @click="openApply"
              >
                {{ t('jobDetail.actions.apply') }}
              </button>
              <span v-if="applyBlocked" class="text-sm text-gray-500 self-center">
                {{ t('jobDetail.applyBlocked.organization') }}
              </span>
            </div>
          </section>
        </div>

        <!-- 1/4 right -->
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
                :class="sideTab === 'jobs' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-50'"
                @click="sideTab = 'jobs'"
              >
                {{ t('jobDetail.side.openJobs') }}
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
                <ul class="space-y-2">
                  <li v-for="j in companyJobs" :key="j.id">
                    <button
                      type="button"
                      class="w-full text-left text-sm hover:bg-gray-50 rounded-lg px-2 py-2"
                      @click="openRelated(j.id)"
                    >
                      <p class="font-medium text-gray-900 line-clamp-2">{{ j.title }}</p>
                      <p class="text-xs text-gray-500">{{ formatSalary(j) }}</p>
                    </button>
                  </li>
                </ul>
                <button
                  type="button"
                  class="mt-3 w-full text-sm text-red-600 hover:underline"
                  @click="goCompany"
                >
                  {{ t('jobDetail.side.seeMoreJobs') }}
                </button>
              </template>
            </div>
          </div>

          <div class="border border-gray-200 rounded-2xl p-4 bg-white">
            <h3 class="text-sm font-bold text-gray-900 mb-3">{{ t('jobDetail.side.artists') }}</h3>
            <p v-if="!employees.length" class="text-sm text-gray-500">{{ t('jobDetail.side.noArtists') }}</p>
            <ul v-else class="space-y-2">
              <li v-for="e in employees" :key="e.user_id || e.id" class="text-sm text-gray-800">
                {{ e.username || e.display_name || `#${e.user_id}` }}
                <span v-if="e.title" class="text-gray-500"> · {{ e.title }}</span>
              </li>
            </ul>
            <button
              v-if="job.company_id"
              type="button"
              class="mt-3 text-sm text-red-600 hover:underline"
              @click="goCompany"
            >
              {{ t('jobDetail.side.seeMoreArtists') }}
            </button>
          </div>
        </aside>
      </div>

      <!-- Related feed: 2×5 -->
      <section class="mt-10">
        <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('jobDetail.related.title') }}</h2>
        <p v-if="!related.length" class="text-sm text-gray-500">{{ t('jobDetail.related.empty') }}</p>
        <div v-else class="space-y-4">
          <div
            v-for="(row, rIdx) in relatedRows"
            :key="rIdx"
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3"
          >
            <button
              v-for="j in row"
              :key="j.id"
              type="button"
              class="border border-gray-200 rounded-2xl p-3 text-left hover:border-gray-400 bg-white"
              @click="openRelated(j.id)"
            >
              <div class="flex items-center gap-2.5 mb-2">
                <img
                  v-if="j.company_owner_user_id && logoUrls[j.company_owner_user_id]"
                  :src="logoUrls[j.company_owner_user_id]"
                  alt=""
                  class="w-12 h-12 rounded-xl object-cover bg-gray-100 shrink-0"
                />
                <div v-else class="w-12 h-12 rounded-xl bg-gray-100 shrink-0" />
                <p class="text-xs font-semibold text-gray-800 line-clamp-2">{{ companyLabel(j) }}</p>
              </div>
              <p class="text-sm font-bold text-gray-900 line-clamp-2">{{ j.title }}</p>
              <p class="text-xs text-gray-600 mt-1">{{ formatSalary(j) }}</p>
              <p class="text-xs text-gray-500">
                {{ t('jobDetail.meta.yearsExperience', { years: j.years_experience }) }}
              </p>
              <p v-if="locationSummary(j)" class="text-xs text-gray-500 mt-1 line-clamp-2">
                {{ locationSummary(j) }}
              </p>
            </button>
          </div>
        </div>
      </section>
    </template>

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
        <select v-if="cvMode === 'tab'" v-model="selectedCvId" class="w-full border rounded-lg px-3 py-2">
          <option v-for="c in myCvs" :key="c.id" :value="c.id">{{ c.original_filename }}</option>
        </select>
        <input v-else type="file" accept=".pdf,.doc,.docx" @change="oneshotFile = $event.target.files[0]" />
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
