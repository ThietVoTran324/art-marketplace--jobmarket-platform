<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import JobDetailPanel from '@/components/Auth/JobMarket/JobDetailPanel.vue';
import { prefetchJobDetail } from '@/composables/useJobDetailCache';
import { probeContentPath } from '@/composables/probeContentAvailability';
import { useUnavailableContentStore } from '@/stores/unavailableContent';
import { useI18n } from 'vue-i18n';

const PAGE_SIZE = 20;
const DAY_MS = 24 * 60 * 60 * 1000;

const router = useRouter();
const route = useRoute();
const unavailableStore = useUnavailableContentStore();
const { t } = useI18n();

/** Raw list from API (suggest or last search). Filters apply on top of this. */
const baseJobs = ref([]);
/** Visible list after Apply filters. */
const jobs = ref([]);
const loading = ref(true);
const loadingMore = ref(false);
const error = ref(null);
const showFilters = ref(false);
const selectedJobId = ref(null);
const hasMore = ref(true);
const offset = ref(0);
/** Last search query that produced baseJobs (empty = suggest). */
const activeQuery = ref('');

const q = ref('');
const yearsMin = ref('');
const yearsMax = ref('');
const salaryMin = ref('');
const salaryMax = ref('');
const currency = ref('');
const location = ref('');
const filterRecent = ref(false);
const filterExpiring = ref(false);
const filterHot = ref(false);

const listEl = ref(null);
let scrollRoot = null;

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatPosted(iso) {
  if (!iso) return t('explore.expiry.emDash');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('explore.expiry.emDash');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function daysLeft(iso) {
  if (!iso) return null;
  const end = new Date(iso);
  if (Number.isNaN(end.getTime())) return null;
  return Math.ceil((end.getTime() - Date.now()) / DAY_MS);
}

function daysLeftLabel(iso) {
  const d = daysLeft(iso);
  if (d == null) return '';
  if (d < 0) return t('explore.expiry.expired');
  if (d === 0) return t('explore.expiry.expiresToday');
  return t('explore.expiry.daysLeft', d, { days: d });
}

function formatSalary(job) {
  if (job.salary_mode === 'love_it') return t('explore.salary.loveIt');
  const cur = job.currency || 'VND';
  if (job.salary_min != null && job.salary_max != null) {
    return t('explore.salary.range', { min: job.salary_min, max: job.salary_max, currency: cur });
  }
  if (job.salary_min != null) return t('explore.salary.from', { min: job.salary_min, currency: cur });
  if (job.salary_max != null) return t('explore.salary.upTo', { max: job.salary_max, currency: cur });
  return t('explore.salary.currencyOnly', { currency: cur });
}

function locationSummary(job) {
  const locs = job.locations || [];
  if (!locs.length) return t('explore.expiry.emDash');
  return locs
    .map((l) => [l.city, l.label || l.address_line].filter(Boolean).join(' · '))
    .join('; ');
}

function jobMatchesLocation(job, needle) {
  const n = needle.trim().toLowerCase();
  if (!n) return true;
  return (job.locations || []).some((l) => {
    const hay = [l.city, l.label, l.address_line, l.country]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(n);
  });
}

function salaryOverlaps(job) {
  const fMin = salaryMin.value === '' ? null : Number(salaryMin.value);
  const fMax = salaryMax.value === '' ? null : Number(salaryMax.value);
  if (fMin == null && fMax == null) return true;
  if (job.salary_mode === 'love_it') return false;
  const jMin = job.salary_min;
  const jMax = job.salary_max;
  if (fMax != null && jMin != null && jMin > fMax) return false;
  if (fMin != null && jMax != null && jMax < fMin) return false;
  if (currency.value && job.currency !== currency.value) return false;
  return true;
}

function hotThreshold(list) {
  const counts = list.map((j) => Number(j.application_count) || 0);
  const max = counts.length ? Math.max(...counts) : 0;
  if (max <= 0) return Infinity;
  return Math.max(1, Math.ceil(max * 0.5));
}

function applyFilters() {
  const now = Date.now();
  const recentCutoff = now - 3 * DAY_MS;
  const expiringCutoff = now + 3 * DAY_MS;
  const yMin = yearsMin.value === '' ? null : Number(yearsMin.value);
  const yMax = yearsMax.value === '' ? null : Number(yearsMax.value);
  const hotMin = filterHot.value ? hotThreshold(baseJobs.value) : null;

  let list = baseJobs.value.filter((job) => {
    if (yMin != null && job.years_experience < yMin) return false;
    if (yMax != null && job.years_experience > yMax) return false;
    if (!salaryOverlaps(job)) return false;
    if (currency.value && !salaryMin.value && !salaryMax.value && job.currency !== currency.value) {
      return false;
    }
    if (location.value.trim() && !jobMatchesLocation(job, location.value)) return false;

    if (filterRecent.value) {
      const created = new Date(job.created_at).getTime();
      if (Number.isNaN(created) || created < recentCutoff) return false;
    }
    if (filterExpiring.value) {
      const exp = new Date(job.expires_at).getTime();
      if (Number.isNaN(exp) || exp < now || exp > expiringCutoff) return false;
    }
    if (filterHot.value) {
      if ((Number(job.application_count) || 0) < hotMin) return false;
    }
    return true;
  });

  if (filterRecent.value) {
    list = [...list].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at) || b.id - a.id
    );
  } else if (filterExpiring.value) {
    list = [...list].sort(
      (a, b) => new Date(a.expires_at) - new Date(b.expires_at) || a.id - b.id
    );
  } else if (filterHot.value) {
    list = [...list].sort(
      (a, b) =>
        (Number(b.application_count) || 0) - (Number(a.application_count) || 0) ||
        new Date(b.created_at) - new Date(a.created_at)
    );
  }

  jobs.value = list;
  pickDefaultSelection();
}

function selectJob(id, { syncUrl = true } = {}) {
  if (id != null) prefetchJobDetail(id);
  selectedJobId.value = id;
  if (!syncUrl) return;
  const nextQuery = { ...route.query };
  if (id != null) {
    nextQuery.job = String(id);
  } else {
    delete nextQuery.job;
  }
  router.replace({ path: '/explore', query: nextQuery });
}

function pickDefaultSelection() {
  const fromQuery = Number(route.query.job);
  if (Number.isFinite(fromQuery) && jobs.value.some((j) => j.id === fromQuery)) {
    selectJob(fromQuery, { syncUrl: false });
    return;
  }
  if (Number.isFinite(fromQuery) && fromQuery > 0) {
    probeContentPath(`/explore?job=${fromQuery}`).then((ok) => {
      if (!ok) {
        unavailableStore.show();
        const nextQuery = { ...route.query };
        delete nextQuery.job;
        router.replace({ path: '/explore', query: nextQuery });
        if (jobs.value.length) {
          selectJob(jobs.value[0].id);
        } else {
          selectJob(null);
        }
        return;
      }
      selectJob(fromQuery, { syncUrl: false });
    });
    return;
  }
  if (jobs.value.length) {
    if (!jobs.value.some((j) => j.id === selectedJobId.value)) {
      selectJob(jobs.value[0].id);
    }
    return;
  }
  selectJob(null);
}

async function fetchPage({ reset }) {
  const params = {
    offset: reset ? 0 : offset.value,
    limit: PAGE_SIZE,
  };
  const query = activeQuery.value.trim();
  if (query) params.q = query;

  const { data } = await axios.get('/api/job-market/explore/jobs', { params });
  const page = data || [];
  if (reset) {
    baseJobs.value = page;
    offset.value = page.length;
  } else {
    const seen = new Set(baseJobs.value.map((j) => j.id));
    const added = page.filter((j) => !seen.has(j.id));
    baseJobs.value = [...baseJobs.value, ...added];
    offset.value += page.length;
  }
  hasMore.value = page.length >= PAGE_SIZE;
  applyFilters();
}

async function search() {
  loading.value = true;
  error.value = null;
  activeQuery.value = q.value.trim();
  hasMore.value = true;
  try {
    await fetchPage({ reset: true });
  } catch (e) {
    error.value = e.response?.data?.detail || t('explore.list.errors.loadFailed');
    baseJobs.value = [];
    jobs.value = [];
    selectJob(null);
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value) return;
  loadingMore.value = true;
  try {
    await fetchPage({ reset: false });
  } catch (e) {
    error.value = e.response?.data?.detail || t('explore.list.errors.loadMoreFailed');
  } finally {
    loadingMore.value = false;
  }
}

function onScroll() {
  const el = scrollRoot;
  if (!el) return;
  const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
  if (remaining < 240) loadMore();
}

const listHint = computed(() =>
  activeQuery.value
    ? t('explore.list.hintSearch', { query: activeQuery.value })
    : t('explore.list.hintSuggest')
);

function companyLabel(job) {
  if (job.company_id) {
    return job.company_display_name || t('explore.list.companyFallback', { id: job.company_id });
  }
  return job.company_display_name || '';
}

function postedLine(job) {
  const posted = t('explore.list.posted', { date: formatPosted(job.created_at) });
  const expiry = daysLeftLabel(job.expires_at);
  let line = `${posted} · ${expiry}`;
  const count = job.application_count || 0;
  if (count > 0) {
    line += ` · ${t('explore.list.appliesCount', { count })}`;
  }
  return line;
}

watch(
  () => route.query.job,
  (jobQuery) => {
    const id = Number(jobQuery);
    if (!Number.isFinite(id) || !jobs.value.length) return;
    if (jobs.value.some((j) => j.id === id) && selectedJobId.value !== id) {
      selectedJobId.value = id;
    }
  }
);

onMounted(async () => {
  await search();
  await nextTick();
  scrollRoot = listEl.value;
  if (scrollRoot) scrollRoot.addEventListener('scroll', onScroll, { passive: true });
});

onBeforeUnmount(() => {
  if (scrollRoot) scrollRoot.removeEventListener('scroll', onScroll);
});
</script>

<template>
  <div class="ml-24 mr-6 mt-8 mb-8">
    <h1 class="text-3xl font-extrabold text-gray-900 mb-6">{{ t('explore.title') }}</h1>

    <div class="flex flex-wrap gap-3 items-center mb-4">
      <input
        v-model="q"
        type="search"
        :placeholder="t('explore.searchPlaceholder')"
        class="flex-1 min-w-[200px] border border-gray-300 rounded-xl px-4 py-2"
        @keyup.enter="search"
      />
      <button
        type="button"
        class="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-black"
        @click="showFilters = !showFilters"
      >
        {{ t('explore.filtersButton') }}
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-xl bg-red-600 text-white hover:bg-red-700"
        @click="search"
      >
        {{ t('explore.searchButton') }}
      </button>
    </div>

    <div
      v-if="showFilters"
      class="mb-6 p-4 border border-gray-200 rounded-2xl space-y-4"
    >
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <label class="text-sm">
          {{ t('explore.filters.yearsMin') }}
          <input v-model="yearsMin" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="text-sm">
          {{ t('explore.filters.yearsMax') }}
          <input v-model="yearsMax" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="text-sm">
          {{ t('explore.filters.salaryMin') }}
          <input v-model="salaryMin" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="text-sm">
          {{ t('explore.filters.salaryMax') }}
          <input v-model="salaryMax" type="number" min="0" class="w-full border rounded-lg px-3 py-2 mt-1" />
        </label>
        <label class="text-sm">
          {{ t('explore.filters.currency') }}
          <select v-model="currency" class="w-full border rounded-lg px-3 py-2 mt-1">
            <option value="">{{ t('explore.filters.currencyAny') }}</option>
            <option value="VND">{{ t('explore.filters.currencyVnd') }}</option>
            <option value="USD">{{ t('explore.filters.currencyUsd') }}</option>
          </select>
        </label>
        <label class="text-sm">
          {{ t('explore.filters.location') }}
          <input v-model="location" type="text" class="w-full border rounded-lg px-3 py-2 mt-1" :placeholder="t('explore.filters.locationPlaceholder')" />
        </label>
      </div>
      <div class="flex flex-wrap gap-4 text-sm">
        <label class="inline-flex items-center gap-2">
          <input v-model="filterRecent" type="checkbox" />
          {{ t('explore.filters.recent') }}
        </label>
        <label class="inline-flex items-center gap-2">
          <input v-model="filterExpiring" type="checkbox" />
          {{ t('explore.filters.expiringSoon') }}
        </label>
        <label class="inline-flex items-center gap-2">
          <input v-model="filterHot" type="checkbox" />
          {{ t('explore.filters.hot') }}
        </label>
      </div>
      <button
        type="button"
        class="px-4 py-2 rounded-xl bg-black text-white hover:bg-gray-800"
        @click="applyFilters"
      >
        {{ t('explore.filters.applyFilters') }}
      </button>
    </div>

    <p class="text-xs text-gray-500 mb-3">
      {{ listHint }} · {{ t('explore.list.shownLoaded', { shown: jobs.length, loaded: baseJobs.length }) }}
    </p>

    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6 min-h-[70vh]">
      <div class="lg:col-span-2">
        <p v-if="loading" class="text-gray-500">{{ t('explore.list.loading') }}</p>
        <p v-else-if="error" class="text-red-600">{{ error }}</p>
        <p v-else-if="!jobs.length" class="text-gray-500">{{ t('explore.list.noJobs') }}</p>
        <ul
          v-else
          ref="listEl"
          class="space-y-3 max-h-[80vh] overflow-y-auto pr-1"
        >
          <li
            v-for="job in jobs"
            :key="job.id"
            class="border rounded-2xl px-5 py-4 cursor-pointer transition-colors"
            :class="
              selectedJobId === job.id
                ? 'border-red-500 bg-red-50'
                : 'border-gray-200 hover:bg-gray-50'
            "
            @click="selectJob(job.id)"
            @mouseenter="prefetchJobDetail(job.id)"
          >
            <div class="flex justify-between gap-4 items-start">
              <div>
                <p class="text-lg font-bold text-gray-900">{{ job.title }}</p>
                <RouterLink
                  v-if="job.company_id"
                  :to="`/companies/${job.company_id}`"
                  class="text-sm text-gray-600 hover:underline"
                  @click.stop
                >
                  {{ companyLabel(job) }}
                </RouterLink>
                <p v-else class="text-sm text-gray-600">{{ companyLabel(job) }}</p>
              </div>
              <p class="text-sm text-gray-700 whitespace-nowrap">{{ formatSalary(job) }}</p>
            </div>
            <p class="text-sm text-gray-500 mt-2">
              {{ t('explore.list.yearsShort', { years: job.years_experience }) }} · {{ locationSummary(job) }}
            </p>
            <p class="text-xs text-gray-500 mt-1">
              {{ postedLine(job) }}
            </p>
          </li>
          <li v-if="loadingMore" class="text-center text-sm text-gray-500 py-2">{{ t('explore.list.loadingMore') }}</li>
          <li v-else-if="!hasMore && baseJobs.length" class="text-center text-xs text-gray-400 py-2">
            {{ t('explore.list.endOfList') }}
          </li>
        </ul>
      </div>

      <div class="lg:col-span-3 border border-gray-200 rounded-2xl p-6 bg-white sticky top-8 self-start max-h-[80vh] overflow-y-auto">
        <JobDetailPanel :job-id="selectedJobId" />
      </div>
    </div>
  </div>
</template>
