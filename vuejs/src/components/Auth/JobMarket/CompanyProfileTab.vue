<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import axios from 'axios';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';
import CompanyCommentSection from '@/components/Auth/JobMarket/CompanyCommentSection.vue';
import CompanyOpenRolesSection from '@/components/Auth/JobMarket/CompanyOpenRolesSection.vue';
import CompanySideStack from '@/components/Auth/JobMarket/CompanySideStack.vue';
import { authUserStore } from '@/stores/authUserStore';
import { profilePath } from '@/utils/profileLinks';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  companyId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
});

const SECTION_IDS = ['overview', 'jobs', 'reviews'];

const userStore = authUserStore();
const router = useRouter();
const { t, locale } = useI18n();

const company = ref(null);
const branches = ref([]);
const pending = ref([]);
const loading = ref(true);
const error = ref(null);
const saving = ref(false);
const avatarUrl = ref(null);
const activeSection = ref('overview');
const warnings = ref([]);
const form = ref({
  domain: '',
  employees_public: true,
});
const branchForm = ref({
  label: '',
  address_line: '',
  city: '',
  country: '',
  is_primary: false,
});

let scrollSpyLockedUntil = 0;
const sectionPrefix = computed(() => `cpt-${props.companyId}-`);

const canEdit = computed(
  () => props.isOwner && userStore.accountKind === 'organization'
);

const countryLabel = computed(() => {
  const code = (company.value?.registration_country || '').toUpperCase();
  if (!code) return '—';
  try {
    return new Intl.DisplayNames([locale.value === 'vi' ? 'vi' : 'en'], { type: 'region' }).of(code) || code;
  } catch {
    return code;
  }
});

const countryFlag = computed(() => {
  const code = (company.value?.registration_country || '').toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return '';
  return String.fromCodePoint(...[...code].map((c) => 127397 + c.charCodeAt(0)));
});

function sizeEmployeesLabel(c) {
  if (!c) return '—';
  if (c.size_min != null && c.size_max != null) {
    return t('jobMarket.companyView.sizeEmployees', { min: c.size_min, max: c.size_max });
  }
  if (c.size_min != null) return t('jobMarket.companyView.sizeFrom', { min: c.size_min });
  if (c.size_max != null) return t('jobMarket.companyView.sizeUpTo', { max: c.size_max });
  return '—';
}

function scrollToSection(id) {
  activeSection.value = id;
  scrollSpyLockedUntil = Date.now() + 800;
  const el = document.getElementById(`${sectionPrefix.value}${id}`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function onScrollSpy() {
  if (Date.now() < scrollSpyLockedUntil) return;
  const offset = 140;
  let current = SECTION_IDS[0];
  for (const id of SECTION_IDS) {
    const el = document.getElementById(`${sectionPrefix.value}${id}`);
    if (!el) continue;
    if (el.getBoundingClientRect().top - offset <= 0) current = id;
  }
  activeSection.value = current;
}

async function loadPending() {
  if (!canEdit.value) {
    pending.value = [];
    return;
  }
  try {
    const { data } = await axios.get(
      '/api/job-market/me/company/work-experiences/pending'
    );
    pending.value = data;
  } catch {
    pending.value = [];
  }
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const [cRes, bRes] = await Promise.all([
      axios.get(`/api/job-market/companies/${props.companyId}`),
      axios.get(`/api/job-market/companies/${props.companyId}/branches`),
    ]);
    company.value = cRes.data;
    branches.value = bRes.data || [];
    form.value = {
      domain: cRes.data.domain || '',
      employees_public: cRes.data.employees_public !== false,
    };
    const ownerId = cRes.data.owner_user_id;
    avatarUrl.value = getCachedCompanyAvatar(ownerId);
    if (ownerId) {
      avatarUrl.value = await fetchCompanyAvatar(ownerId);
    }
    await loadPending();
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyProfileTab.errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

async function saveOps() {
  if (!canEdit.value) return;
  saving.value = true;
  error.value = null;
  warnings.value = [];
  try {
    const { data } = await axios.patch('/api/job-market/me/company', {
      domain: form.value.domain.trim() || null,
      employees_public: !!form.value.employees_public,
    });
    company.value = { ...company.value, ...data };
    warnings.value = data.warnings || [];
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyProfileTab.errors.saveFailed');
  } finally {
    saving.value = false;
  }
}

async function addBranch() {
  if (!canEdit.value || !branchForm.value.address_line.trim()) return;
  try {
    const { data } = await axios.post(
      '/api/job-market/me/company/branches',
      branchForm.value
    );
    branches.value.push(data);
    branchForm.value = {
      label: '',
      address_line: '',
      city: '',
      country: '',
      is_primary: false,
    };
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyProfileTab.errors.branchCreateFailed');
  }
}

async function decide(row, action) {
  try {
    await axios.post(
      `/api/job-market/me/company/work-experiences/${row.id}/${action}`
    );
    await loadPending();
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyProfileTab.errors.actionFailed', { action });
  }
}

function goCustomize() {
  router.push(`/companies/${props.companyId}?edit=1`);
}

function goPublicPage() {
  router.push(`/companies/${props.companyId}`);
}

onMounted(async () => {
  await load();
  await nextTick();
  window.addEventListener('scroll', onScrollSpy, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScrollSpy);
});
</script>

<template>
  <div class="px-4 sm:px-8 py-6 w-full max-w-6xl mx-auto">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
      <h2 class="text-2xl font-bold">{{ t('jobMarket.companyProfileTab.title') }}</h2>
      <div v-if="canEdit" class="flex flex-wrap gap-2">
        <button
          type="button"
          class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50"
          @click="goPublicPage"
        >
          {{ t('jobMarket.companyProfileTab.viewPublicPage') }}
        </button>
        <button
          type="button"
          class="text-sm px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-black"
          @click="goCustomize"
        >
          {{ t('jobMarket.companyView.customizePage') }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="text-gray-500">{{ t('jobMarket.shared.loading') }}</p>
    <p v-else-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

    <template v-else-if="company">
      <p v-if="canEdit" class="text-sm text-gray-600 mb-4">
        {{ t('jobMarket.companyProfileTab.previewHint') }}
      </p>

      <!-- Same surface as public CompanyView -->
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <div class="lg:col-span-3 space-y-6">
          <div class="sticky top-4 z-20 border border-gray-200 rounded-2xl bg-white shadow-sm overflow-hidden">
            <div class="p-6 pb-4">
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
                <div class="min-w-0 flex-1">
                  <h1 class="text-3xl font-extrabold text-gray-900">{{ company.display_name }}</h1>
                  <p v-if="company.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
                  <p v-if="company.description" class="text-sm text-gray-700 mt-3 whitespace-pre-line line-clamp-3">
                    {{ company.description }}
                  </p>
                  <p v-if="company.website" class="text-sm mt-2">
                    <a :href="company.website" target="_blank" rel="noopener" class="text-red-600 hover:underline">
                      {{ company.website }}
                    </a>
                  </p>
                </div>
              </div>
            </div>
            <nav class="flex border-t border-gray-100 px-2 overflow-x-auto">
              <button
                v-for="tab in [
                  { id: 'overview', label: t('jobMarket.companyView.tabs.overview') },
                  { id: 'jobs', label: t('jobMarket.companyView.tabs.openingJobs') },
                  { id: 'reviews', label: t('jobMarket.companyView.tabs.reviews') },
                ]"
                :key="tab.id"
                type="button"
                class="shrink-0 px-4 py-3 text-sm font-semibold border-b-2 transition"
                :class="
                  activeSection === tab.id
                    ? 'border-red-600 text-red-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                "
                @click="scrollToSection(tab.id)"
              >
                {{ tab.label }}
              </button>
            </nav>
          </div>

          <section :id="`${sectionPrefix}overview`" class="scroll-mt-36 space-y-4">
            <h3 class="text-xl font-bold text-gray-900 px-1">{{ t('jobMarket.companyView.tabs.overview') }}</h3>

            <div class="border border-gray-200 rounded-2xl bg-white p-6">
              <h4 class="text-base font-bold text-gray-900 mb-3">
                {{ t('jobMarket.companyView.generalInfo') }}
              </h4>
              <div class="border-t border-dashed border-gray-200 mb-5" />
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-5">
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companyType') }}</p>
                  <p class="text-sm font-bold text-gray-900">{{ company.company_type || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companyIndustry') }}</p>
                  <p class="text-sm font-bold text-gray-900">{{ company.industry || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companySize') }}</p>
                  <p class="text-sm font-bold text-gray-900">{{ sizeEmployeesLabel(company) }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.country') }}</p>
                  <p class="text-sm font-bold text-gray-900">
                    <span v-if="countryFlag" class="mr-1">{{ countryFlag }}</span>{{ countryLabel }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.workingDays') }}</p>
                  <p class="text-sm font-bold text-gray-900">{{ company.working_days || '—' }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.overtimePolicy') }}</p>
                  <p class="text-sm font-bold text-gray-900">{{ company.overtime_policy || '—' }}</p>
                </div>
              </div>
            </div>

            <div
              v-if="company.overview_text"
              class="border border-gray-200 rounded-2xl bg-white p-6"
            >
              <h4 class="text-base font-bold text-gray-900 mb-3">
                {{ t('jobMarket.companyView.companyOverview') }}
              </h4>
              <div class="border-t border-dashed border-gray-200 mb-4" />
              <p class="text-sm text-gray-800 whitespace-pre-line">{{ company.overview_text }}</p>
            </div>

            <div
              v-if="company.why_work_here"
              class="border border-gray-200 rounded-2xl bg-white p-6"
            >
              <h4 class="text-base font-bold text-gray-900 mb-3">
                {{ t('jobMarket.companyView.whyLove') }}
              </h4>
              <div class="border-t border-dashed border-gray-200 mb-4" />
              <p class="text-sm text-gray-800 whitespace-pre-line">{{ company.why_work_here }}</p>
            </div>
          </section>

          <section :id="`${sectionPrefix}jobs`" class="scroll-mt-36">
            <CompanyOpenRolesSection
              :company-id="companyId"
              :company-owner-user-id="company.owner_user_id"
              :company-display-name="company.display_name"
            />
          </section>

          <section :id="`${sectionPrefix}reviews`" class="scroll-mt-36">
            <CompanyCommentSection :company-id="companyId" />
          </section>
        </div>

        <aside class="lg:col-span-1 lg:sticky lg:top-8">
          <CompanySideStack
            :company-id="companyId"
            :company-owner-user-id="company.owner_user_id"
            :company-display-name="company.display_name"
            :show-open-roles="false"
          />
        </aside>
      </div>

      <!-- Owner ops only (not public page content) -->
      <div v-if="canEdit" class="mt-10 border-t border-gray-200 pt-8 space-y-8 max-w-3xl">
        <div>
          <h3 class="text-lg font-bold mb-1">{{ t('jobMarket.companyProfileTab.opsHeading') }}</h3>
          <p class="text-sm text-gray-600 mb-4">{{ t('jobMarket.companyProfileTab.opsHint') }}</p>
          <label class="block text-sm font-medium mb-3">
            {{ t('jobMarket.companyProfileTab.fields.domain') }}
            <input v-model="form.domain" class="mt-1 w-full border rounded-xl px-3 py-2" />
          </label>
          <label class="flex items-center gap-2 text-sm font-medium mb-3">
            <input v-model="form.employees_public" type="checkbox" />
            {{ t('jobMarket.companyProfileTab.fields.employeesPublic') }}
          </label>
          <ul v-if="warnings.length" class="text-amber-700 text-sm mb-3">
            <li v-for="w in warnings" :key="w.code">{{ w.message || w.code }}</li>
          </ul>
          <button
            type="button"
            class="px-5 py-2 rounded-full bg-black text-white disabled:opacity-50"
            :disabled="saving"
            @click="saveOps"
          >
            {{ saving ? t('jobMarket.companyProfileTab.save.saving') : t('jobMarket.companyProfileTab.save.opsButton') }}
          </button>
        </div>

        <div>
          <h3 class="font-semibold mb-2">{{ t('jobMarket.companyProfileTab.pendingWorkExperience.heading') }}</h3>
          <p v-if="!pending.length" class="text-sm text-gray-500">{{ t('jobMarket.companyProfileTab.pendingWorkExperience.empty') }}</p>
          <ul v-else class="space-y-3 text-sm">
            <li v-for="row in pending" :key="row.id" class="border-b pb-2">
              <p class="font-medium">
                <RouterLink
                  v-if="row.artist_username"
                  :to="profilePath(row.artist_username, { tab: 'experience', workExpId: row.id })"
                  class="underline"
                >
                  {{ row.artist_username }}
                </RouterLink>
                <span v-else>{{ t('jobMarket.shared.userFallback', { id: row.user_id }) }}</span>
                — {{ row.title }}
              </p>
              <p class="text-gray-600">{{ row.start_date }} → {{ row.end_date || t('jobMarket.shared.present') }}</p>
              <div class="flex gap-2 mt-1">
                <button
                  type="button"
                  class="px-3 py-1 bg-black text-white rounded-full text-xs"
                  @click="decide(row, 'approve')"
                >
                  {{ t('jobMarket.shared.approve') }}
                </button>
                <button
                  type="button"
                  class="px-3 py-1 border rounded-full text-xs"
                  @click="decide(row, 'reject')"
                >
                  {{ t('jobMarket.shared.reject') }}
                </button>
              </div>
            </li>
          </ul>
        </div>

        <div>
          <h3 class="font-semibold mb-2">{{ t('jobMarket.companyProfileTab.branches.heading') }}</h3>
          <ul class="text-sm space-y-1 mb-3">
            <li v-for="b in branches" :key="b.id">
              {{ b.label ? b.label + ' — ' : '' }}{{ b.address_line }}
              <span v-if="b.city">, {{ b.city }}</span>
            </li>
          </ul>
          <div class="grid gap-2">
            <input v-model="branchForm.label" :placeholder="t('jobMarket.companyProfileTab.branches.labelPlaceholder')" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.address_line" :placeholder="t('jobMarket.companyProfileTab.branches.addressPlaceholder')" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.city" :placeholder="t('jobMarket.companyProfileTab.branches.cityPlaceholder')" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.country" :placeholder="t('jobMarket.companyProfileTab.branches.countryPlaceholder')" class="border rounded-xl px-3 py-2" />
            <button type="button" class="px-4 py-2 rounded-full border w-fit" @click="addBranch">
              {{ t('jobMarket.companyProfileTab.branches.addButton') }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
