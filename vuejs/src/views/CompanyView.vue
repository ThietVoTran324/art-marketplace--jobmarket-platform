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

const ALL_SECTION_IDS = ['overview', 'jobs', 'reviews'];

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
/** Per-field modal key, e.g. company_type | size | overview_text */
const editModal = ref(null);
const saving = ref(false);
const saveError = ref(null);
const editForm = ref({});

let scrollSpyLockedUntil = 0;

const isOwner = computed(() => {
  if (!userStore.isAuthenticated || !company.value) return false;
  const myId = Number(userStore.authUserId);
  const ownerId = Number(company.value.owner_user_id);
  if (Number.isFinite(myId) && Number.isFinite(ownerId) && myId === ownerId) return true;
  // org session linked to this company
  if (
    userStore.isOrganization &&
    userStore.companyId != null &&
    Number(userStore.companyId) === Number(company.value.id)
  ) {
    return true;
  }
  return false;
});

const editMode = computed(
  () => isOwner.value && (route.query.edit === '1' || route.query.edit === 'true')
);

/** Real visitor actions only — never on Custom page, never for owner */
const showVisitorActions = computed(
  () => !!company.value && !isOwner.value && !editMode.value
);

const sectionIds = computed(() =>
  editMode.value ? ['overview', 'jobs'] : ALL_SECTION_IDS
);

const headerTabs = computed(() => {
  const tabs = [
    { id: 'overview', label: t('jobMarket.companyView.tabs.overview') },
    { id: 'jobs', label: t('jobMarket.companyView.tabs.openingJobs') },
  ];
  if (!editMode.value) {
    tabs.push({ id: 'reviews', label: t('jobMarket.companyView.tabs.reviews') });
  }
  return tabs;
});

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
    stripEditIfNotOwner();
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyView.loadFailed');
  } finally {
    loading.value = false;
  }
}

function stripEditIfNotOwner() {
  if (!route.query.edit) return;
  if (isOwner.value) return;
  // Wait until auth id is known before stripping — avoids false strip on cold load
  if (userStore.sessionKnown !== true) return;
  const q = { ...route.query };
  delete q.edit;
  router.replace({ path: route.path, query: q });
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
  if (!companyId.value || followBusy.value || isOwner.value) return;
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
    const detail = e.response?.data?.detail;
    // only treat true duplicate follow as success — not cannot_follow_own_company
    if (e.response?.status === 409 && next && detail === 'already_following') {
      isFollowing.value = true;
    } else {
      console.error(e);
    }
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
  const ids = sectionIds.value;
  let current = ids[0];
  for (const id of ids) {
    const el = document.getElementById(`company-section-${id}`);
    if (!el) continue;
    const top = el.getBoundingClientRect().top;
    if (top - offset <= 0) current = id;
  }
  activeSection.value = current;
}

function openEdit(field) {
  if (!editMode.value || !company.value) return;
  saveError.value = null;
  const c = company.value;
  const initials = {
    display_name: c.display_name || '',
    description: c.description || '',
    website: c.website || '',
    company_type: c.company_type || '',
    industry: c.industry || '',
    size_min: c.size_min ?? '',
    size_max: c.size_max ?? '',
    working_days: c.working_days || '',
    overtime_policy: c.overtime_policy || '',
    overview_text: c.overview_text || '',
    why_work_here: c.why_work_here || '',
  };
  if (field === 'size') {
    editForm.value = { size_min: initials.size_min, size_max: initials.size_max };
  } else if (field in initials) {
    editForm.value = { [field]: initials[field] };
  } else {
    return;
  }
  editModal.value = field;
}

async function saveEdit() {
  if (!editModal.value) return;
  saving.value = true;
  saveError.value = null;
  try {
    const f = editForm.value;
    const field = editModal.value;
    let payload = {};
    if (field === 'size') {
      payload = {
        size_min: f.size_min === '' || f.size_min == null ? null : Number(f.size_min),
        size_max: f.size_max === '' || f.size_max == null ? null : Number(f.size_max),
      };
    } else if (field === 'display_name') {
      const name = (f.display_name || '').trim();
      if (!name) {
        throw new Error('display_name_required');
      }
      payload = { display_name: name };
    } else if (['size_min', 'size_max'].includes(field)) {
      payload = {
        [field]: f[field] === '' || f[field] == null ? null : Number(f[field]),
      };
    } else {
      const raw = f[field];
      payload = {
        [field]: typeof raw === 'string' ? raw.trim() || null : raw ?? null,
      };
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
    saveError.value =
      e.response?.data?.detail ||
      (e.message === 'display_name_required'
        ? t('jobMarket.companyView.fields.displayName')
        : t('jobMarket.companyView.saveFailed'));
  } finally {
    saving.value = false;
  }
}

function fieldLabel(field) {
  const map = {
    display_name: 'fields.displayName',
    description: 'fields.shortDescription',
    website: 'fields.website',
    company_type: 'fields.companyType',
    industry: 'fields.companyIndustry',
    size: 'fields.companySize',
    working_days: 'fields.workingDays',
    overtime_policy: 'fields.overtimePolicy',
    overview_text: 'companyOverview',
    why_work_here: 'whyLove',
  };
  const key = map[field];
  return key ? t(`jobMarket.companyView.${key}`) : t('jobMarket.companyView.editSection');
}

watch(companyId, () => load(), { immediate: true });

watch(
  () => [route.query.edit, userStore.authUserId, userStore.sessionKnown, company.value?.id],
  () => stripEditIfNotOwner()
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
                    <div class="min-w-0 flex-1">
                      <h1 class="text-3xl font-extrabold text-gray-900">{{ company.display_name }}</h1>
                      <p v-if="company.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
                    </div>
                    <div v-if="showVisitorActions" class="flex items-center gap-2 shrink-0">
                      <button
                        v-if="company.owner_username"
                        type="button"
                        class="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
                        @click="goOwnerProfile"
                      >
                        {{ t('jobMarket.companyView.ownerProfile') }}
                      </button>
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
                    </div>
                  </div>
                  <p
                    v-if="company.description"
                    class="text-sm text-gray-700 mt-3 whitespace-pre-line line-clamp-3"
                  >
                    {{ company.description }}
                  </p>
                  <p v-if="company.website" class="text-sm mt-2">
                    <a
                      :href="company.website"
                      target="_blank"
                      rel="noopener"
                      class="text-red-600 hover:underline"
                    >{{ company.website }}</a>
                  </p>
                </div>
              </div>
            </div>

            <nav class="flex border-t border-gray-100 px-2 overflow-x-auto">
              <button
                v-for="tab in headerTabs"
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
            <div class="border border-gray-200 rounded-2xl bg-white p-6">
              <h3 class="text-base font-bold text-gray-900 mb-3">
                {{ t('jobMarket.companyView.generalInfo') }}
              </h3>
              <div class="border-t border-dashed border-gray-200 mb-5" />
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-5">
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companyType') }}</p>
                  <div class="flex items-center gap-2 min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{{ company.company_type || '—' }}</p>
                    <button
                      v-if="editMode"
                      type="button"
                      class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                      :title="t('jobMarket.companyView.editSection')"
                      @click="openEdit('company_type')"
                    >
                      <i class="pi pi-pencil text-[10px]" />
                    </button>
                  </div>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companyIndustry') }}</p>
                  <div class="flex items-center gap-2 min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{{ company.industry || '—' }}</p>
                    <button
                      v-if="editMode"
                      type="button"
                      class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                      @click="openEdit('industry')"
                    >
                      <i class="pi pi-pencil text-[10px]" />
                    </button>
                  </div>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.companySize') }}</p>
                  <div class="flex items-center gap-2 min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{{ sizeEmployeesLabel(company) }}</p>
                    <button
                      v-if="editMode"
                      type="button"
                      class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                      @click="openEdit('size')"
                    >
                      <i class="pi pi-pencil text-[10px]" />
                    </button>
                  </div>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.country') }}</p>
                  <p class="text-sm font-bold text-gray-900">
                    <span v-if="countryFlag" class="mr-1">{{ countryFlag }}</span>{{ countryLabel }}
                  </p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.workingDays') }}</p>
                  <div class="flex items-center gap-2 min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{{ company.working_days || '—' }}</p>
                    <button
                      v-if="editMode"
                      type="button"
                      class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                      @click="openEdit('working_days')"
                    >
                      <i class="pi pi-pencil text-[10px]" />
                    </button>
                  </div>
                </div>
                <div>
                  <p class="text-xs text-gray-500 mb-1">{{ t('jobMarket.companyView.fields.overtimePolicy') }}</p>
                  <div class="flex items-center gap-2 min-w-0">
                    <p class="text-sm font-bold text-gray-900 truncate">{{ company.overtime_policy || '—' }}</p>
                    <button
                      v-if="editMode"
                      type="button"
                      class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                      @click="openEdit('overtime_policy')"
                    >
                      <i class="pi pi-pencil text-[10px]" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Company overview — Custom page only -->
            <div
              v-if="editMode || company.overview_text"
              class="border border-gray-200 rounded-2xl bg-white p-6"
            >
              <div class="flex items-center gap-2 mb-3">
                <h3 class="text-base font-bold text-gray-900">
                  {{ t('jobMarket.companyView.companyOverview') }}
                </h3>
                <button
                  v-if="editMode"
                  type="button"
                  class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                  @click="openEdit('overview_text')"
                >
                  <i class="pi pi-pencil text-[10px]" />
                </button>
              </div>
              <div class="border-t border-dashed border-gray-200 mb-4" />
              <p
                v-if="company.overview_text"
                class="text-sm text-gray-800 whitespace-pre-line"
              >{{ company.overview_text }}</p>
              <p v-else class="text-sm text-gray-400 italic">{{ t('jobMarket.companyView.emptySection') }}</p>
            </div>

            <!-- Why you'll love working here — Custom page only -->
            <div
              v-if="editMode || company.why_work_here"
              class="border border-gray-200 rounded-2xl bg-white p-6"
            >
              <div class="flex items-center gap-2 mb-3">
                <h3 class="text-base font-bold text-gray-900">
                  {{ t('jobMarket.companyView.whyLove') }}
                </h3>
                <button
                  v-if="editMode"
                  type="button"
                  class="w-5 h-5 shrink-0 flex items-center justify-center rounded text-red-600 hover:bg-red-50"
                  @click="openEdit('why_work_here')"
                >
                  <i class="pi pi-pencil text-[10px]" />
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

          <!-- Opening jobs (preview only on Custom page — no job CRUD here) -->
          <section id="company-section-jobs" class="scroll-mt-36">
            <CompanyOpenRolesSection
              :company-id="companyId"
              :company-owner-user-id="company.owner_user_id"
              :company-display-name="company.display_name"
            />
          </section>

          <!-- Reviews / comments — not on Custom page -->
          <section v-if="!editMode" id="company-section-reviews" class="scroll-mt-36">
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

    <!-- Per-field edit modal -->
    <div
      v-if="editModal"
      class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      @click.self="editModal = null"
    >
      <div class="bg-white rounded-2xl p-6 w-full max-w-lg space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-bold">{{ fieldLabel(editModal) }}</h3>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>

        <template v-if="editModal === 'size'">
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
        </template>
        <template v-else-if="editModal === 'description' || editModal === 'overview_text' || editModal === 'why_work_here'">
          <textarea
            v-model="editForm[editModal]"
            rows="8"
            class="w-full border rounded-lg px-3 py-2"
          />
        </template>
        <template v-else>
          <input
            v-model="editForm[editModal]"
            class="w-full border rounded-lg px-3 py-2"
          />
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
