<script setup>
import {
  onMounted,
  ref,
  onBeforeUnmount,
  onActivated,
  onDeactivated,
  watch,
  nextTick,
} from 'vue';
import axios from 'axios';
import { useI18n } from 'vue-i18n';
import PinFeedCard from './PinFeedCard.vue';
import { seedFeedMetaFromPins } from '@/composables/usePinFeedMeta';
import { prefetchPinPreviewUrls } from '@/composables/usePinMediaCache';
import {
  estimateSearchPageSize,
  nextSearchPageSize,
} from '@/composables/useSearchViewportPage';

const { t } = useI18n();
const pins = ref([]);
const offset = ref(0);
const limit = ref(10);
const isPinsLoading = ref(false);
const hasMore = ref(true);
const loadError = ref(null);
const hasLoadedOnce = ref(false);
const skeletonCount = ref(10);
const searchSentinel = ref(null);

let searchSentinelObserver = null;
/** Optional override: pass explicit pin count to fill one screen (tests / tuning). */
const props = defineProps({
  value: { type: String, default: '' },
  tagId: { type: Number, default: null },
  authorId: { type: Number, default: null },
  /** When set, used as first-page size instead of viewport estimate. */
  pageSize: { type: Number, default: null },
});

const hasQuery = () =>
  Boolean(props.tagId || props.authorId || (props.value && props.value.trim()));

const nearSearchBottom = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;
  return currentScrollPosition + 500 >= scrollableHeight;
};

const fillViewportIfNeeded = async () => {
  await nextTick();
  if (!hasMore.value || isPinsLoading.value) return;
  if (nearSearchBottom()) {
    loadPins();
  }
};

const bindSearchSentinel = async () => {
  await nextTick();
  if (searchSentinelObserver) {
    searchSentinelObserver.disconnect();
    searchSentinelObserver = null;
  }
  if (!searchSentinel.value || typeof IntersectionObserver === 'undefined') return;
  searchSentinelObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadPins();
    },
    { root: null, rootMargin: '600px 0px', threshold: 0 }
  );
  searchSentinelObserver.observe(searchSentinel.value);
};

const loadPins = async () => {
  if (isPinsLoading.value || !hasMore.value) return;
  if (!hasQuery()) {
    pins.value = [];
    hasMore.value = false;
    hasLoadedOnce.value = true;
    return;
  }

  isPinsLoading.value = true;
  loadError.value = null;
  try {
    const params = {
      offset: offset.value,
      limit: limit.value,
      value: props.value || '',
    };
    if (props.tagId) params.tag_id = props.tagId;
    if (props.authorId) params.author_id = props.authorId;

    const response = await axios.get(`/api/pins/search`, {
      params,
      withCredentials: true,
    });
    const batch = response.data || [];
    const firstPage = pins.value.length === 0;
    const pageLimit = limit.value;
    seedFeedMetaFromPins(batch);
    // Above-fold: warm same preview URLs cards will use (no encode change / detail untouched).
    prefetchPinPreviewUrls(
      batch.map((p) => p.id),
      { limit: pageLimit }
    );
    pins.value.push(...batch);
    offset.value += pageLimit;
    if (batch.length < pageLimit) {
      hasMore.value = false;
    }
    // After first viewport page, smaller follow-up batches (like home feed).
    if (firstPage) {
      const next = nextSearchPageSize(pageLimit);
      limit.value = next;
      skeletonCount.value = next;
    }
  } catch (error) {
    console.log(error);
    loadError.value =
      error?.response?.data?.detail || error?.message || 'Error loading search results';
    hasMore.value = false;
  } finally {
    isPinsLoading.value = false;
    hasLoadedOnce.value = true;
    fillViewportIfNeeded();
  }
};

const resetAndLoad = () => {
  pins.value = [];
  offset.value = 0;
  const first = estimateSearchPageSize({}, props.pageSize);
  limit.value = first;
  skeletonCount.value = first;
  hasMore.value = true;
  isPinsLoading.value = false;
  loadError.value = null;
  hasLoadedOnce.value = false;
  loadPins();
  bindSearchSentinel();
};

const handleScroll = () => {
  if (nearSearchBottom()) {
    loadPins();
  }
};

onMounted(() => {
  resetAndLoad();
  window.addEventListener('scroll', handleScroll, { passive: true });
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll);
  if (searchSentinelObserver) {
    searchSentinelObserver.disconnect();
    searchSentinelObserver = null;
  }
});

onActivated(() => {
  window.addEventListener('scroll', handleScroll, { passive: true });
  bindSearchSentinel();
});

onDeactivated(() => {
  window.removeEventListener('scroll', handleScroll);
  if (searchSentinelObserver) {
    searchSentinelObserver.disconnect();
    searchSentinelObserver = null;
  }
});

watch(() => [props.value, props.tagId, props.authorId, props.pageSize], resetAndLoad);
</script>

<template>
  <div>
    <p v-if="loadError" class="ml-20 mt-28 text-red-600 text-sm">{{ loadError }}</p>
    <p
      v-else-if="hasLoadedOnce && !pins.length && !isPinsLoading"
      class="ml-20 mt-28 text-gray-500"
    >
      {{ t('home.search.noResults') }}
    </p>
    <div
      v-else-if="pins.length || isPinsLoading"
      class="ml-20 mt-10 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
    >
      <PinFeedCard
        v-for="pinem in pins"
        :key="pinem.id"
        :pin="pinem"
      />
      <div
        v-for="n in isPinsLoading ? skeletonCount : 0"
        :key="`sk-${n}`"
        class="w-full p-2"
      >
        <div class="w-full aspect-[3/4] rounded-2xl bg-gray-200 animate-pulse" />
      </div>
    </div>
    <div
      v-show="hasMore && pins.length"
      ref="searchSentinel"
      class="ml-20 h-8 w-full"
      aria-hidden="true"
    />
  </div>
</template>
