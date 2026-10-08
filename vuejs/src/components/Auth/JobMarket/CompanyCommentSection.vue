<script setup>
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import { useI18n } from 'vue-i18n';

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(timezone);

const props = defineProps({
  companyId: { type: Number, required: true },
});

const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const comments = ref([]);
const offset = ref(0);
const limit = ref(5);
const loading = ref(false);
const canLoad = ref(true);
const draft = ref('');
const posting = ref(false);
const userMeta = ref({});

function formatTime(createdAt) {
  const now = dayjs();
  const createdTime = dayjs.utc(createdAt).local();
  if (now.diff(createdTime, 'minute') < 30) return t('comments.time.justNow');
  return createdTime.fromNow();
}

async function ensureUser(uid) {
  if (!uid || userMeta.value[uid]) return;
  try {
    const { data } = await axios.get(`/api/users/user_id/${uid}`);
    let avatar = null;
    try {
      const img = await axios.get(`/api/users/upload/${uid}`, { responseType: 'blob' });
      avatar = URL.createObjectURL(img.data);
    } catch {
      /* ignore */
    }
    userMeta.value = {
      ...userMeta.value,
      [uid]: { username: data.username, avatar },
    };
  } catch {
    userMeta.value = { ...userMeta.value, [uid]: { username: `#${uid}`, avatar: null } };
  }
}

async function loadMore() {
  if (loading.value || !canLoad.value) return;
  loading.value = true;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${props.companyId}/comments`, {
      params: { offset: offset.value, limit: limit.value },
    });
    const batch = data || [];
    if (batch.length < limit.value) canLoad.value = false;
    comments.value.push(...batch);
    offset.value += batch.length;
    await Promise.all(batch.map((c) => ensureUser(c.user_id)));
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function resetAndLoad() {
  comments.value = [];
  offset.value = 0;
  canLoad.value = true;
  await loadMore();
}

async function submit() {
  if (!userStore.isAuthenticated) {
    openAuthModal('login', { redirectTo: `/companies/${props.companyId}` });
    return;
  }
  const text = draft.value.trim();
  if (!text || posting.value) return;
  posting.value = true;
  try {
    const { data } = await axios.post(`/api/job-market/companies/${props.companyId}/comments`, {
      content: text,
    });
    draft.value = '';
    comments.value.unshift(data);
    await ensureUser(data.user_id);
  } catch (e) {
    console.error(e);
  } finally {
    posting.value = false;
  }
}

watch(
  () => props.companyId,
  () => resetAndLoad(),
  { immediate: false }
);

onMounted(resetAndLoad);
</script>

<template>
  <section class="border border-gray-200 rounded-2xl bg-white p-6">
    <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('jobMarket.companyView.commentsTitle') }}</h2>

    <div class="flex gap-3 mb-6">
      <textarea
        v-model="draft"
        rows="2"
        class="flex-1 border border-gray-300 rounded-xl px-3 py-2 text-sm"
        :placeholder="t('jobMarket.companyView.commentPlaceholder')"
        @focus="!userStore.isAuthenticated && openAuthModal('login', { redirectTo: `/companies/${companyId}` })"
      />
      <button
        type="button"
        class="self-end px-4 py-2 rounded-xl bg-red-600 text-white text-sm disabled:opacity-50"
        :disabled="posting || !draft.trim()"
        @click="submit"
      >
        {{ t('jobMarket.companyView.commentSubmit') }}
      </button>
    </div>

    <ul class="space-y-4">
      <li v-for="c in comments" :key="c.id" class="flex gap-3">
        <img
          v-if="userMeta[c.user_id]?.avatar"
          :src="userMeta[c.user_id].avatar"
          alt=""
          class="w-9 h-9 rounded-full object-cover bg-gray-100 shrink-0"
        />
        <div
          v-else
          class="w-9 h-9 rounded-full bg-gray-100 shrink-0"
        />
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm font-semibold text-gray-900">
              {{ userMeta[c.user_id]?.username || `User #${c.user_id}` }}
            </span>
            <span
              v-if="c.employment_status === 'current'"
              class="inline-flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full"
              :title="t('jobMarket.companyView.badgeCurrent')"
            >
              <i class="pi pi-briefcase text-[10px]" />
              {{ t('jobMarket.companyView.badgeCurrent') }}
            </span>
            <span
              v-else-if="c.employment_status === 'former'"
              class="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full"
              :title="t('jobMarket.companyView.badgeFormer')"
            >
              <i class="pi pi-briefcase text-[10px]" />
              {{ t('jobMarket.companyView.badgeFormer') }}
            </span>
            <span class="text-xs text-gray-400">{{ formatTime(c.created_at) }}</span>
          </div>
          <p class="text-sm text-gray-800 mt-1 whitespace-pre-line">{{ c.content }}</p>
        </div>
      </li>
    </ul>

    <button
      v-if="canLoad"
      type="button"
      class="mt-4 text-sm text-red-600 hover:underline disabled:opacity-50"
      :disabled="loading"
      @click="loadMore"
    >
      {{ loading ? t('jobMarket.companyView.loading') : t('jobMarket.companyView.loadMoreComments') }}
    </button>
  </section>
</template>
