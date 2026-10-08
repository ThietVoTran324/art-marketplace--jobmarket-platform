<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';
import CompanyCommentSection from '@/components/Auth/JobMarket/CompanyCommentSection.vue';
import CompanyOpenRolesSection from '@/components/Auth/JobMarket/CompanyOpenRolesSection.vue';
import CompanySideStack from '@/components/Auth/JobMarket/CompanySideStack.vue';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const router = useRouter();
const { t, locale } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const SECTION_IDS = ['overview', 'jobs', 'reviews'];

const companyId = computed(() => {
  const n = Number(route.params.id);
  return Number.isFinite(n) && n > 0 ? n : null;
});

const company = ref(null);
const loading = ref(true);
const error = ref(null);
const avatarUrl = ref(null);
const isFollowing = ref(false);
const followBusy = ref(false);
const openingChat = ref(false);
const activeSection = ref('overview');
const editModal = ref(null); // 'header' | 'general' | 'overview' | 'why' | null
const saving = ref(false);
const saveError = ref(null);
const editForm = ref({});

let scrollSpyLockedUntil = 0;

const isOwner = computed(
  () =>
    userStore.isAuthenticated &&
    company.value?.owner_user_id != null &&
    Number(userStore.user?.id) === Number(company.value.owner_user_id)
);

const editMode = computed(
  () => isOwner.value && (route.query.edit === '1' || route.query.edit === 'true')
);

const showVisitorActions = computed(() => !!company.value && !isOwner.value);

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

async function load() {
  if (!companyId.value) return;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${companyId.value}`);
    company.value = data;
    isFollowing.value = !!data.is_following;
    const ownerId = company.value.owner_user_id;
    avatarUrl.value = getCachedCompanyAvatar(ownerId);
    if (ownerId) {
      avatarUrl.value = await fetchCompanyAvatar(ownerId);
    }
    if (route.query.edit && !isOwner.value) {
      const q = { ...route.query };
      delete q.edit;
      router.replace({ path: route.path, query: q });
    }
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyView.loadFailed');
  } finally {
    loading.value = false;
  }
}

function requireLogin(redirectTo) {
  if (userStore.isAuthenticated) return true;
  openAuthModal('login', { redirectTo: redirectTo || route.fullPath });
  return false;
}

function goOwnerProfile() {
  const uname = company.value?.owner_username;
  if (!uname) return;
  const path = `/user/${uname}`;
  if (!requireLogin(path)) return;
  router.push(path);
}

function exitEditMode() {
  const q = { ...route.query };
  delete q.edit;
  router.replace({ path: route.path, query: q });
}

function enterEditMode() {
  if (!isOwner.value) return;
  router.replace({ path: route.path, query: { ...route.query, edit: '1' } });
}

async function toggleFollow() {
  if (!requireLogin(route.fullPath)) return;
  if (!companyId.value || followBusy.value) return;
  followBusy.value = true;
  const next = !isFollowing.value;
  try {
    if (next) {
      await axios.post(`/api/job-market/companies/${companyId.value}/follow`);
    } else {
      await axios.delete(`/api/job-market/companies/${companyId.value}/follow`);
    }
    isFollowing.value = next;
    if (company.value) company.value.is_following = next;
  } catch (e) {
    if (e.response?.status === 409 && next) isFollowing.value = true;
    else console.error(e);
  } finally {
    followBusy.value = false;
  }
}

async function openMessage() {
  const ownerId = company.value?.owner_user_id;
  if (!ownerId) return;
  if (!requireLogin(route.fullPath)) return;
  openingChat.value = true;
  try {
    const response = await axios.get(`/api/messages/get_chat/${ownerId}`, {
      withCredentials: true,
    });
    const chatId = response.data;
    await router.push(`/messages?chat_id=${chatId}`);
  } catch (e) {
    console.error(e);
  } finally {
    openingChat.value = false;
  }
}

function scrollToSection(id) {
  activeSection.value = id;
  scrollSpyLockedUntil = Date.now() + 800;
  const el = document.getElementById(`company-section-${id}`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function onScrollSpy() {
  if (Date.now() < scrollSpyLockedUntil) return;
  const offset = 140;
  let current = SECTION_IDS[0];
  for (const id of SECTION_IDS) {
    const el = document.getElementById(`company-section-${id}`);
    if (!el) continue;
    const top = el.getBoundingClientRect().top;
    if (top - offset <= 0) current = id;
  }
  activeSection.value = current;
}

function openEdit(section) {
  if (!editMode.value || !company.value) return;
  saveError.value = null;
  const c = company.value;
  if (section === 'header') {
    editForm.value = {
      display_name: c.display_name || '',
      industry: c.industry || '',
      description: c.description || '',
      website: c.website || '',
    };
  } else if (section === 'general') {
    editForm.value = {
      company_type: c.company_type || '',
      industry: c.industry || '',
      size_min: c.size_min ?? '',
      size_max: c.size_max ?? '',
      working_days: c.working_days || '',
      overtime_policy: c.overtime_policy || '',
    };
  } else if (section === 'overview') {
    editForm.value = { overview_text: c.overview_text || '' };
  } else if (section === 'why') {
    editForm.value = { why_work_here: c.why_work_here || '' };
  }
  editModal.value = section;
}

async function saveEdit() {
  if (!editModal.value) return;
  saving.value = true;
  saveError.value = null;
  try {
    const f = editForm.value;
    let payload = {};
    if (editModal.value === 'header') {
      payload = {
        display_name: f.display_name.trim(),
        industry: f.industry.trim() || null,
        description: f.description.trim() || null,
        website: f.website.trim() || null,
      };
    } else if (editModal.value === 'general') {
      payload = {
        company_type: f.company_type.trim() || null,
        industry: f.industry.trim() || null,
        size_min: f.size_min === '' || f.size_min == null ? null : Number(f.size_min),
        size_max: f.size_max === '' || f.size_max == null ? null : Number(f.size_max),
        working_days: f.working_days.trim() || null,
        overtime_policy: f.overtime_policy.trim() || null,
      };
    } else if (editModal.value === 'overview') {
      payload = { overview_text: f.overview_text.trim() || null };
    } else if (editModal.value === 'why') {
      payload = { why_work_here: f.why_work_here.trim() || null };
    }
    const { data } = await axios.patch('/api/job-market/me/company', payload);
    const prev = company.value || {};
    company.value = {
      ...prev,
      ...data,
      owner_username: data.owner_username ?? prev.owner_username,
      is_following: data.is_following ?? prev.is_following,
    };
    editModal.value = null;
  } catch (e) {
    saveError.value = e.response?.data?.detail || t('jobMarket.companyView.saveFailed');
  } finally {
    saving.value = false;
  }
}

watch(companyId, () => load(), { immediate: true });

watch(
  () => route.query.edit,
  () => {
    if (route.query.edit && company.value && !isOwner.value) {
      exitEditMode();
    }
  }
);

onMounted(async () => {
  await nextTick();
  window.addEventListener('scroll', onScrollSpy, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScrollSpy);
});
</script>

<template>
  <div class="ml-24 mr-6 mt-8 mb-12">
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <button type="button" class="text-sm text-gray-600 hover:underline" @click="router.back()">
        {{ t('jobMarket.companyView.back') }}
      </button>
      <template v-if="isOwner">
        <button
          v-if="!editMode"
          type="button"
          class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50"
          @click="enterEditMode"
        >
          {{ t('jobMarket.companyView.customizePage') }}
        </button>
        <button
          v-else
          type="button"
          class="text-sm px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-black"
          @click="exitEditMode"
        >
          {{ t('jobMarket.companyView.doneEditing') }}
        </button>
      </template>
      <span
        v-if="editMode"
        class="text-xs font-medium text-amber-800 bg-amber-50 border border-amber-200 px-2 py-1 rounded-lg"
      >
        {{ t('jobMarket.companyView.editModeBanner') }}
      </span>
    </div>

    <p v-if="!companyId" class="text-red-600">{{ t('jobMarket.companyView.invalidCompany') }}</p>
    <p v-else-if="loading" class="text-gray-500">{{ t('jobMarket.companyView.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>

    <template v-else-if="company">
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <div class="lg:col-span-3 space-y-6">
          <!-- Sticky header + tabs -->
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
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0 relative pr-8">
                      <h1 class="text-3xl font-extrabold text-gray-900">{{ company.display_name }}</h1>
                      <p v-if="company.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
                      <button
                        v-if="editMode"
                        type="button"
                        class="absolute top-0 right-0 w-7 h-7 flex items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                        :title="t('jobMarket.companyView.editSection')"
                        @click="openEdit('header')"
                      >
                        <i class="pi pi-pencil text-xs" />
                      </button>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <button
                        v-if="company.owner_username"
                        type="button"
                        class="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
                        @click="goOwnerProfile"
                      >
                        {{ t('jobMarket.companyView.ownerProfile') }}
                      </button>
                      <template v-if="showVisitorActions">
                        <button
                          type="button"
                          class="px-5 py-2.5 rounded-lg text-sm font-bold text-white transition disabled:opacity-50"
                          :style="{ backgroundColor: isFollowing ? '#111827' : '#e60023' }"
                          :disabled="followBusy"
                          @click="toggleFollow"
                        >
                          {{
                            isFollowing
                              ? t('jobMarket.companyView.followed')
                              : t('jobMarket.companyView.follow')
                          }}
                        </button>
                        <button
                          type="button"
                          class="relative group w-11 h-11 flex items-center justify-center rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
                          :disabled="openingChat || !company.owner_user_id"
                          :title="t('jobMarket.companyView.message')"
                          @click="openMessage"
                        >
                          <i class="pi pi-comment text-xl text-gray-800" />
                          <span
                            class="pointer-events-none absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-900 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition"
                          >
                            {{ t('jobMarket.companyView.message') }}
                          </span>
                        </button>
                      </template>
                    </div>
                  </div>
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

          <!-- Overview -->
          <section id="company-section-overview" class="scroll-mt-36 space-y-4">
            <h2 class="text-xl font-bold text-gray-900 px-1">{{ t('jobMarket.companyView.tabs.overview') }}</h2>

            <!-- General information -->
            <div class="border border-gray-200 rounded-2xl bg-white p-6 relative">
              <div class="flex items-start justify-between gap-2 mb-3">
                <h3 class="text-base font-bold text-gray-900">
                  {{ t('jobMarket.companyView.generalInfo') }}
                </h3>
                <button
                  v-if="editMode"
                  type="button"
                  class="w-7 h-7 flex items-center justify-center rounded-md text-gray-500 hover:bg-gray-100"
                  @click="openEdit('general')"
                >
                  <i class="pi pi-pencil text-xs" />
                </button>
              </div>
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

            <!-- Company overview text: visitors hide when empty; edit mode always shows -->
            <div
              v-if="editMode || company.overview_text"
              class="border border-gray-200 rounded-2xl bg-white p-6 relative"
            >
              <div class="flex items-start justify-between gap-2 mb-3">
                <h3 class="text-base font-bold text-gray-900">
                  {{ t('jobMarket.companyView.companyOverview') }}
                </h3>
                <button
                  v-if="editMode"
                  type="button"
                  class="w-7 h-7 flex items-center justify-center rounded-md text-gray-500 hover:bg-gray-100"
                  @click="openEdit('overview')"
                >
                  <i class="pi pi-pencil text-xs" />
                </button>
              </div>
              <div class="border-t border-dashed border-gray-200 mb-4" />
              <p
                v-if="company.overview_text"
                class="text-sm text-gray-800 whitespace-pre-line"
              >{{ company.overview_text }}</p>
              <p v-else class="text-sm text-gray-400 italic">{{ t('jobMarket.companyView.emptySection') }}</p>
            </div>

            <!-- Why you'll love working here: visitors hide when empty; edit mode always shows -->
            <div
              v-if="editMode || company.why_work_here"
              class="border border-gray-200 rounded-2xl bg-white p-6 relative"
            >
              <div class="flex items-start justify-between gap-2 mb-3">
                <h3 class="text-base font-bold text-gray-900">
                  {{ t('jobMarket.companyView.whyLove') }}
                </h3>
                <button
                  v-if="editMode"
                  type="button"
                  class="w-7 h-7 flex items-center justify-center rounded-md text-gray-500 hover:bg-gray-100"
                  @click="openEdit('why')"
                >
                  <i class="pi pi-pencil text-xs" />
                </button>
              </div>
              <div class="border-t border-dashed border-gray-200 mb-4" />
              <p
                v-if="company.why_work_here"
                class="text-sm text-gray-800 whitespace-pre-line"
              >{{ company.why_work_here }}</p>
              <p v-else class="text-sm text-gray-400 italic">{{ t('jobMarket.companyView.emptySection') }}</p>
            </div>
          </section>

          <!-- Opening jobs -->
          <section id="company-section-jobs" class="scroll-mt-36">
            <CompanyOpenRolesSection
              :company-id="companyId"
              :company-owner-user-id="company.owner_user_id"
              :company-display-name="company.display_name"
            />
          </section>

          <!-- Reviews / comments -->
          <section id="company-section-reviews" class="scroll-mt-36">
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
    </template>

    <!-- Edit modal -->
    <div
      v-if="editModal"
      class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      @click.self="editModal = null"
    >
      <div class="bg-white rounded-2xl p-6 w-full max-w-lg space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-bold">{{ t('jobMarket.companyView.editSection') }}</h3>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>

        <template v-if="editModal === 'header'">
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.displayName') }}
            <input v-model="editForm.display_name" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.companyIndustry') }}
            <input v-model="editForm.industry" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.shortDescription') }}
            <textarea v-model="editForm.description" rows="4" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.website') }}
            <input v-model="editForm.website" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
        </template>

        <template v-else-if="editModal === 'general'">
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.companyType') }}
            <input v-model="editForm.company_type" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.companyIndustry') }}
            <input v-model="editForm.industry" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block text-sm">
              {{ t('jobMarket.companyView.fields.sizeMin') }}
              <input v-model="editForm.size_min" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
            </label>
            <label class="block text-sm">
              {{ t('jobMarket.companyView.fields.sizeMax') }}
              <input v-model="editForm.size_max" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
            </label>
          </div>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.workingDays') }}
            <input v-model="editForm.working_days" class="w-full border rounded-lg px-3 py-2 mt-1" placeholder="Monday - Friday" />
          </label>
          <label class="block text-sm">
            {{ t('jobMarket.companyView.fields.overtimePolicy') }}
            <input v-model="editForm.overtime_policy" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
        </template>

        <template v-else-if="editModal === 'overview'">
          <label class="block text-sm">
            {{ t('jobMarket.companyView.companyOverview') }}
            <textarea v-model="editForm.overview_text" rows="8" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
        </template>

        <template v-else-if="editModal === 'why'">
          <label class="block text-sm">
            {{ t('jobMarket.companyView.whyLove') }}
            <textarea v-model="editForm.why_work_here" rows="8" class="w-full border rounded-lg px-3 py-2 mt-1" />
          </label>
        </template>

        <div class="flex gap-2 pt-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-red-600 text-white disabled:opacity-50"
            :disabled="saving"
            @click="saveEdit"
          >
            {{ t('jobMarket.companyView.save') }}
          </button>
          <button type="button" class="px-4 py-2 rounded-xl bg-gray-100" @click="editModal = null">
            {{ t('jobMarket.companyView.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
