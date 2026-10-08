<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';
import {
  fetchCompanyAvatar,
  getCachedCompanyAvatar,
} from '@/composables/useCompanyAvatarCache';

const props = defineProps({
  companyId: { type: Number, required: true },
  companyOwnerUserId: { type: Number, default: null },
  companyDisplayName: { type: String, default: '' },
  /** Max open roles to show (null = all returned). */
  jobsLimit: { type: Number, default: 50 },
  /** Show "see more" links to company page. */
  showSeeMore: { type: Boolean, default: false },
});

const { t } = useI18n();
const router = useRouter();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

const contact = ref(null);
const jobs = ref([]);
const employees = ref([]);
const empTotal = ref(0);
const empPage = ref(1);
const empPageSize = 10;
const avatarTick = ref(0);
const empAvatars = ref({});

const empTotalPages = computed(() => Math.max(1, Math.ceil(empTotal.value / empPageSize)));

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

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return t('explore.expiry.emDash');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('explore.expiry.emDash');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeftLabel(iso) {
  if (!iso) return '';
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return '';
  const days = Math.ceil((end.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  if (days < 0) return t('explore.expiry.expired');
  if (days === 0) return t('explore.expiry.expiresToday');
  return t('explore.expiry.daysLeft', days, { named: { days } });
}

function formatSalary(j) {
  if (!j) return '';
  if (j.salary_mode === 'love_it') return t('explore.salary.loveIt');
  const cur = j.currency || 'VND';
  if (j.salary_min != null && j.salary_max != null) {
    return t('explore.salary.range', { min: j.salary_min, max: j.salary_max, currency: cur });
  }
  if (j.salary_min != null) return t('explore.salary.from', { min: j.salary_min, currency: cur });
  if (j.salary_max != null) return t('explore.salary.upTo', { max: j.salary_max, currency: cur });
  return t('explore.salary.currencyOnly', { currency: cur });
}

function locationSummary(j) {
  const locs = j?.locations || [];
  if (!locs.length) return t('explore.expiry.emDash');
  return locs
    .map((l) => [l.city, l.label || l.address_line].filter(Boolean).join(' · '))
    .join('; ');
}

function companyLabel(j) {
  return (
    j.company_display_name ||
    props.companyDisplayName ||
    t('explore.list.companyFallback', { id: j.company_id || props.companyId })
  );
}

function postedLine(j) {
  const posted = t('explore.list.posted', { date: formatPosted(j.created_at) });
  const expiry = daysLeftLabel(j.expires_at);
  const count = Number(j.application_count) || 0;
  const parts = [posted];
  if (expiry) parts.push(expiry);
  parts.push(t('explore.list.appliesCount', { count }));
  return parts.join(' · ');
}

function yearsShortLabel(years) {
  return t('explore.list.yearsShort', { years });
}

function artistName(e) {
  return e.username || `#${e.user_id}`;
}

function jobLogo(j) {
  avatarTick.value;
  const id = j.company_owner_user_id || props.companyOwnerUserId;
  return getCachedCompanyAvatar(id);
}

function empAvatar(userId) {
  return empAvatars.value[userId] || null;
}

async function ensureEmpAvatar(userId) {
  if (!userId || empAvatars.value[userId]) return;
  try {
    const r = await axios.get(`/api/users/upload/${userId}`, { responseType: 'blob' });
    empAvatars.value = {
      ...empAvatars.value,
      [userId]: URL.createObjectURL(r.data),
    };
  } catch {
    /* ignore */
  }
}

async function loadContactAndJobs() {
  if (!props.companyId) return;
  try {
    const [contactRes, jobsRes] = await Promise.allSettled([
      axios.get(`/api/job-market/companies/${props.companyId}/contact`),
      axios.get(`/api/job-market/companies/${props.companyId}/job-posts`, {
        params: { status: 'active' },
      }),
    ]);
    if (contactRes.status === 'fulfilled') contact.value = contactRes.value.data;
    if (jobsRes.status === 'fulfilled') {
      let list = jobsRes.value.data || [];
      if (props.jobsLimit != null) list = list.slice(0, props.jobsLimit);
      jobs.value = list;
      const ownerIds = list
        .map((j) => j.company_owner_user_id || props.companyOwnerUserId)
        .filter(Boolean);
      await Promise.all([...new Set(ownerIds)].map((id) => fetchCompanyAvatar(id)));
      avatarTick.value += 1;
    }
  } catch {
    /* ignore partial */
  }
}

async function loadEmployees() {
  if (!props.companyId) return;
  const offset = (empPage.value - 1) * empPageSize;
  try {
    const { data } = await axios.get(`/api/job-market/companies/${props.companyId}/employees`, {
      params: { offset, limit: empPageSize },
    });
    employees.value = data.employees || [];
    empTotal.value = data.total ?? employees.value.length;
    await Promise.all(employees.value.map((e) => ensureEmpAvatar(e.user_id)));
  } catch {
    employees.value = [];
    empTotal.value = 0;
  }
}

function openJob(id) {
  window.open(`/jobs/${id}`, '_blank', 'noopener,noreferrer');
}

function goArtist(e) {
  if (!e?.username) return;
  const path = `/user/${e.username}`;
  if (!userStore.isAuthenticated) {
    openAuthModal('login', { redirectTo: path });
    return;
  }
  router.push(path);
}

function goCompany() {
  const path = `/companies/${props.companyId}`;
  if (!userStore.isAuthenticated) {
    openAuthModal('login', { redirectTo: path });
    return;
  }
  router.push(path);
}

function prevEmpPage() {
  if (empPage.value <= 1) return;
  empPage.value -= 1;
  loadEmployees();
}

function nextEmpPage() {
  if (empPage.value >= empTotalPages.value) return;
  empPage.value += 1;
  loadEmployees();
}

async function reload() {
  empPage.value = 1;
  await Promise.all([loadContactAndJobs(), loadEmployees()]);
}

watch(
  () => props.companyId,
  () => reload(),
  { immediate: false }
);

onMounted(reload);
</script>

<template>
  <div class="space-y-4">
    <!-- Contact -->
    <section class="border border-gray-200 rounded-2xl bg-white overflow-hidden flex flex-col max-h-[36vh]">
      <header class="shrink-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <h3 class="text-sm font-bold text-gray-900">{{ t('jobDetail.side.contact') }}</h3>
      </header>
      <div class="flex-1 min-h-0 overflow-y-auto p-4">
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
      </div>
    </section>

    <!-- Open roles -->
    <section class="border border-gray-200 rounded-2xl bg-white overflow-hidden flex flex-col max-h-[42vh]">
      <header class="shrink-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <h3 class="text-sm font-bold text-gray-900">{{ t('jobDetail.side.openJobs') }}</h3>
      </header>
      <div class="flex-1 min-h-0 overflow-y-auto p-3">
        <p v-if="!jobs.length" class="text-sm text-gray-500 px-1">{{ t('jobMarket.companyView.noJobs') }}</p>
        <ul v-else class="space-y-3">
          <li
            v-for="j in jobs"
            :key="j.id"
            class="border border-gray-200 rounded-xl px-3 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
            @click="openJob(j.id)"
          >
            <div class="flex items-start gap-3">
              <img
                v-if="jobLogo(j)"
                :src="jobLogo(j)"
                alt=""
                class="w-11 h-11 rounded-xl object-cover bg-gray-100 shrink-0"
              />
              <div
                v-else
                class="w-11 h-11 rounded-xl bg-gray-100 shrink-0 flex items-center justify-center text-gray-400"
              >
                <i class="pi pi-building text-sm" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm font-bold text-gray-900 leading-snug">{{ j.title }}</p>
                <p class="text-xs text-gray-500 mt-0.5">{{ companyLabel(j) }}</p>
                <p class="text-xs font-medium mt-1" style="color: #16a34a">{{ formatSalary(j) }}</p>
                <p class="text-xs text-gray-500 mt-1">
                  {{ yearsShortLabel(j.years_experience) }} · {{ locationSummary(j) }}
                </p>
                <p class="text-[11px] text-gray-400 mt-0.5">{{ postedLine(j) }}</p>
              </div>
            </div>
          </li>
        </ul>
        <button
          v-if="showSeeMore && jobs.length"
          type="button"
          class="mt-3 w-full text-sm text-red-600 hover:underline"
          @click="goCompany"
        >
          {{ t('jobDetail.side.seeMoreJobs') }}
        </button>
      </div>
    </section>

    <!-- Artists on roster -->
    <section class="border border-gray-200 rounded-2xl bg-white overflow-hidden flex flex-col max-h-[42vh]">
      <header class="shrink-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <h3 class="text-sm font-bold text-gray-900">{{ t('jobDetail.side.artists') }}</h3>
      </header>
      <div class="flex-1 min-h-0 overflow-y-auto p-3">
        <p v-if="!employees.length" class="text-sm text-gray-500 px-1">{{ t('jobDetail.side.noArtists') }}</p>
        <ul v-else class="space-y-3">
          <li
            v-for="e in employees"
            :key="e.user_id"
            class="flex items-stretch border border-gray-200 rounded-xl overflow-hidden cursor-pointer hover:bg-gray-50"
            @click="goArtist(e)"
          >
            <div class="shrink-0 self-stretch aspect-square min-h-[4.5rem] bg-gray-100 relative">
              <img
                v-if="empAvatar(e.user_id)"
                :src="empAvatar(e.user_id)"
                alt=""
                class="absolute inset-0 w-full h-full object-cover"
              />
              <div
                v-else
                class="absolute inset-0 flex items-center justify-center text-gray-400"
              >
                <i class="pi pi-user text-xl" />
              </div>
            </div>
            <div class="min-w-0 flex-1 flex flex-col justify-center px-3 py-2">
              <p class="text-sm font-bold text-gray-900 truncate">
                {{ artistName(e) }}
              </p>
              <p class="text-xs text-gray-500 mt-0.5 line-clamp-2">
                {{ e.title || t('jobDetail.side.roleFallback') }}
              </p>
            </div>
          </li>
        </ul>
        <div
          v-if="empTotalPages > 1"
          class="flex items-center justify-center gap-3 text-sm pt-3 mt-1 border-t border-gray-100"
        >
          <button
            type="button"
            class="px-2 py-1 rounded border disabled:opacity-40"
            :disabled="empPage <= 1"
            @click="prevEmpPage"
          >
            &lt;
          </button>
          <span class="min-w-[2rem] text-center font-medium">{{ empPage }}</span>
          <button
            type="button"
            class="px-2 py-1 rounded border disabled:opacity-40"
            :disabled="empPage >= empTotalPages"
            @click="nextEmpPage"
          >
            &gt;
          </button>
        </div>
        <button
          v-if="showSeeMore && employees.length"
          type="button"
          class="mt-3 w-full text-sm text-red-600 hover:underline"
          @click="goCompany"
        >
          {{ t('jobDetail.side.seeMoreArtists') }}
        </button>
      </div>
    </section>
  </div>
</template>
