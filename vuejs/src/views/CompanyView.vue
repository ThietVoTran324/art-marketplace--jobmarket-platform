<script setup>
import { computed, ref, watch } from 'vue';
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
const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

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

const isOwner = computed(
  () =>
    userStore.isAuthenticated &&
    company.value?.owner_user_id != null &&
    Number(userStore.user?.id) === Number(company.value.owner_user_id)
);

const showVisitorActions = computed(() => !!company.value && !isOwner.value);

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
  } catch (e) {
    error.value = e.response?.data?.detail || t('jobMarket.companyView.loadFailed');
  } finally {
    loading.value = false;
  }
}

function companySizeLabel(c) {
  return t('jobMarket.companyView.companySize', {
    min: c.size_min ?? '—',
    max: c.size_max ?? '—',
  });
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
    if (e.response?.status === 409 && next) {
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
    if (response.status === 200) {
      await router.push(`/messages?chat_id=${chatId}`);
    } else {
      await router.push(`/messages?chat_id=${chatId}&new_chat=true`);
    }
  } catch (e) {
    console.error(e);
  } finally {
    openingChat.value = false;
  }
}

watch(companyId, () => load(), { immediate: true });
</script>

<template>
  <div class="ml-24 mr-6 mt-8 mb-12">
    <button type="button" class="text-sm text-gray-600 hover:underline mb-4" @click="router.back()">
      {{ t('jobMarket.companyView.back') }}
    </button>

    <p v-if="!companyId" class="text-red-600">{{ t('jobMarket.companyView.invalidCompany') }}</p>
    <p v-else-if="loading" class="text-gray-500">{{ t('jobMarket.companyView.loading') }}</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>

    <template v-else-if="company">
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        <!-- 3/4 -->
        <div class="lg:col-span-3 space-y-6">
          <section class="border border-gray-200 rounded-2xl p-6 bg-white">
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
                  <div class="min-w-0">
                    <h1 class="text-3xl font-extrabold text-gray-900">{{ company.display_name }}</h1>
                    <p v-if="company.industry" class="text-sm text-gray-600 mt-1">{{ company.industry }}</p>
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
                <p v-if="company.description" class="text-sm text-gray-700 mt-3 whitespace-pre-line">
                  {{ company.description }}
                </p>
                <p v-if="company.website" class="text-sm mt-2">
                  <a :href="company.website" target="_blank" rel="noopener" class="text-red-600 hover:underline">
                    {{ company.website }}
                  </a>
                </p>
                <p
                  v-if="company.size_min != null || company.size_max != null"
                  class="text-xs text-gray-500 mt-2"
                >
                  {{ companySizeLabel(company) }}
                </p>
              </div>
            </div>
          </section>

          <CompanyOpenRolesSection
            :company-id="companyId"
            :company-owner-user-id="company.owner_user_id"
            :company-display-name="company.display_name"
          />

          <CompanyCommentSection :company-id="companyId" />
        </div>

        <!-- 1/4: Contact · Artists -->
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
  </div>
</template>
