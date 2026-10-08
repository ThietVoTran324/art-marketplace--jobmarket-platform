<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import { useI18n } from 'vue-i18n';
import CompanySideStack from '@/components/Auth/JobMarket/CompanySideStack.vue';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const job = ref(null);
const company = ref(null);
const related = ref([]);
const logoUrls = ref({});
const companyAvatarUrl = ref(null);
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
const isSaved = ref(false);
const saving = ref(false);

const jobId = computed(() => Number(route.params.id));

const reportReasons = computed(() => [
  { value: 'spam', label: t('jobDetail.reportModal.reasons.spam') },
  { value: 'scam', label: t('jobDetail.reportModal.reasons.scam') },
  { value: 'inappropriate', label: t('jobDetail.reportModal.reasons.inappropriate') },
  { value: 'other', label: t('jobDetail.reportModal.reasons.other') },
]);

const applyBlocked = computed(() => userStore.isAuthenticated && !userStore.canApplyToJobs);
const applyBlockedReason = computed(() => {
  if (userStore.isAdmin) return t('jobDetail.applyBlocked.admin');
  if (userStore.isOrganization) return t('jobDetail.applyBlocked.organization');
  return '';
});

const jobActive = computed(
  () =>
    !!job.value &&
    job.value.status === 'active' &&
    (!job.value.expires_at || new Date(job.value.expires_at).getTime() > Date.now()) &&
    !job.value.my_application
);
const showApplyCta = computed(
  () => jobActive.value && (!userStore.isAuthenticated || userStore.canApplyToJobs)
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

function appliedAtLabel(createdAt) {
  return t('jobMarket.appliedAt', { date: formatPosted(createdAt) });
}

function yearsExperienceLabel(years) {
  return t('jobDetail.meta.yearsExperience', { years });
}

function postedLabel(createdAt) {
  return t('jobDetail.meta.posted', { date: formatPosted(createdAt) });
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
  related.value = [];
  reportDone.value = false;
  try {
    const { data } = await axios.get(`/api/job-market/jobs/${jobId.value}`);
    job.value = data;
    isSaved.value = !!data.is_saved;
    const cid = data.company_id;
    if (cid) {
      try {
        const { data: c } = await axios.get(`/api/job-market/companies/${cid}`);
        company.value = c;
      } catch {
        company.value = null;
      }
    }
    companyAvatarUrl.value = getCachedCompanyAvatar(data.company_owner_user_id);
    if (data.company_owner_user_id) {
      companyAvatarUrl.value = await fetchCompanyAvatar(data.company_owner_user_id);
    }
    const { data: rel } = await axios.get(`/api/job-market/jobs/${jobId.value}/related`, {
      params: { limit: 10 },
    });
    related.value = rel || [];
    const owners = new Set(related.value.map((j) => j.company_owner_user_id).filter(Boolean));
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

async function toggleSave() {
  if (!requireLogin(route.fullPath)) return;
  if (!jobId.value || saving.value) return;
  saving.value = true;
  const next = !isSaved.value;
  try {
    if (next) {
      await axios.post(`/api/job-market/me/saved-jobs/${jobId.value}`);
    } else {
      await axios.delete(`/api/job-market/me/saved-jobs/${jobId.value}`);
    }
    isSaved.value = next;
    if (job.value) job.value.is_saved = next;
  } catch (e) {
    if (e.response?.status === 409 && next) {
      isSaved.value = true;
      if (job.value) job.value.is_saved = true;
    } else {
      console.error(e);
    }
  } finally {
    saving.value = false;
  }
}

function openExploreDetail() {
  window.open(`/explore?job=${jobId.value}`, '_blank', 'noopener,noreferrer');
}

async function openApply() {
  if (!requireLogin(route.fullPath)) return;
  if (userStore.isAuthenticated && !userStore.canApplyToJobs) return;
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
  if (!requireLogin(route.fullPath)) return;
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
    reportError.value =
      e.response?.data?.detail || e.message || t('jobDetail.reportModal.errors.failed');
  } finally {
    reporting.value = false;
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
      <header class="jm-hero-header rounded-2xl px-6 py-5 mb-6 shadow-sm">
        <button
          type="button"
          class="text-sm text-white/80 hover:text-white hover:underline mb-2"
          @click="router.back()"
        >
          {{ t('jobDetail.backToExplore') }}
        </button>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">{{ job.title }}</h1>
        <p class="text-sm text-white/75 mt-1">
          {{ company?.display_name || companyLabel(job) }}
        </p>
      </header>

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <!-- 3/4 left -->
        <div class="lg:col-span-3 space-y-6">
          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
            <div class="flex items-start gap-4">
              <img
                v-if="companyAvatarUrl"
                :src="companyAvatarUrl"
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

          <section
            class="border border-gray-200 rounded-2xl bg-white sticky top-8 self-start max-h-[80vh] min-h-[28rem] overflow-hidden flex flex-col"
          >
            <header class="shrink-0 bg-white z-10 p-6 pb-4 border-b border-gray-100 space-y-4">
              <div class="flex items-center gap-2 sm:gap-3">
                <button
                  v-if="showApplyCta"
                  type="button"
                  class="flex-1 min-w-0 py-3 px-4 rounded-xl text-white font-bold text-base sm:text-lg hover:brightness-95 transition"
                  style="background-color: #e60023"
                  @click="openApply"
                >
                  {{ t('jobDetail.actions.applyNow') }}
                </button>
                <button
                  v-else-if="applyBlocked"
                  type="button"
                  disabled
                  class="flex-1 min-w-0 py-3 px-4 rounded-xl bg-gray-300 text-gray-600 font-bold text-base cursor-not-allowed"
                  :title="applyBlockedReason"
                >
                  {{ t('jobDetail.actions.applyNow') }}
                </button>
                <div
                  v-else-if="job.my_application"
                  class="flex-1 min-w-0 py-3 px-4 rounded-xl bg-gray-100 text-gray-800 text-sm font-medium text-center"
                >
                  {{ appliedAtLabel(job.my_application.created_at) }}
                  <span class="text-gray-500 font-normal">· {{ job.my_application.status }}</span>
                </div>
                <div
                  v-else
                  class="flex-1 min-w-0 py-3 px-4 rounded-xl bg-gray-100 text-gray-500 text-sm font-medium text-center"
                >
                  {{ t('jobDetail.actions.applyNow') }}
                </div>

                <button
                  type="button"
                  class="shrink-0 w-11 h-11 flex items-center justify-center rounded-xl hover:bg-blue-50 transition"
                  :title="t('jobMarket.jobDetailPanel.actions.fullDetail')"
                  @click="openExploreDetail"
                >
                  <i class="pi pi-external-link text-2xl" style="color: #2563eb" />
                </button>

                <button
                  type="button"
                  class="shrink-0 w-11 h-11 flex items-center justify-center rounded-xl hover:bg-amber-50 transition"
                  :title="t('jobDetail.actions.report')"
                  @click="openReport"
                >
                  <i class="pi pi-exclamation-triangle text-2xl" style="color: #eab308" />
                </button>

                <button
                  type="button"
                  class="shrink-0 w-11 h-11 flex items-center justify-center rounded-xl hover:bg-red-50 transition disabled:opacity-50"
                  :disabled="saving"
                  :title="isSaved ? t('jobMarket.jobDetailPanel.actions.unsave') : t('jobMarket.jobDetailPanel.actions.save')"
                  @click="toggleSave"
                >
                  <i v-if="isSaved" class="pi pi-heart-fill text-2xl text-red-600" />
                  <i v-else class="pi pi-heart text-2xl save-heart-outline" />
                </button>
              </div>

              <div class="flex items-start gap-4">
                <img
                  v-if="companyAvatarUrl"
                  :src="companyAvatarUrl"
                  alt=""
                  class="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl object-cover bg-gray-100 shrink-0"
                />
                <div
                  v-else
                  class="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-gray-100 shrink-0 flex items-center justify-center text-gray-400"
                >
                  <i class="pi pi-building text-3xl" />
                </div>
                <div class="min-w-0 flex-1 pt-0.5">
                  <h1 class="text-xl sm:text-2xl font-extrabold text-gray-900 leading-tight">
                    {{ job.title }}
                  </h1>
                  <RouterLink
                    v-if="job.company_id"
                    :to="`/companies/${job.company_id}`"
                    class="text-sm text-gray-500 mt-1 inline-block hover:underline"
                    @click.prevent="goCompany"
                  >
                    {{ companyLabel(job) }}
                  </RouterLink>
                  <p v-else class="text-sm text-gray-500 mt-1">{{ companyLabel(job) }}</p>
                  <p class="text-sm font-medium mt-1" style="color: #16a34a">
                    {{ formatSalary(job) }}
                  </p>
                </div>
              </div>

              <p v-if="reportDone" class="text-sm text-gray-600">
                {{ t('jobDetail.actions.reportSubmitted') }}
              </p>
            </header>

            <div class="flex-1 min-h-0 overflow-y-auto px-6 pt-4 pb-6">
              <p class="text-sm text-gray-500">
                {{ yearsExperienceLabel(job.years_experience) }}
                <span v-if="job.status === 'closed'" class="ml-2 text-red-600">{{ t('jobDetail.meta.closed') }}</span>
              </p>
              <p class="text-sm text-gray-500 mt-1">{{ postedLabel(job.created_at) }}</p>

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
            </div>
          </section>
        </div>

        <!-- 1/4 right -->
        <aside class="lg:col-span-1 lg:sticky lg:top-8">
          <CompanySideStack
            v-if="job.company_id"
            :company-id="job.company_id"
            :company-owner-user-id="job.company_owner_user_id"
            :company-display-name="companyLabel(job)"
            :show-see-more="true"
          />
        </aside>
      </div>

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
                {{ yearsExperienceLabel(j.years_experience) }}
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
            <option v-for="r in reportReasons" :key="r.value" :value="r.value">{{ r.label }}</option>
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

<style scoped>
.save-heart-outline {
  color: #ffffff;
  -webkit-text-stroke: 1.75px #dc2626;
  paint-order: stroke fill;
}
</style>
