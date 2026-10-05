<script setup>
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue';
import axios from 'axios';
import PinFeedCard from './PinFeedCard.vue';
import { prefetchFeedMeta } from '@/composables/usePinFeedMeta';
import { useI18n } from 'vue-i18n';

const PAGE_SIZE = 20;

const { t } = useI18n();

const pins = ref([]);
const isPinsLoading = ref(false);
const isLoadingMore = ref(false);
const offset = ref(0);
const exhausted = ref(false);
const sentinelEl = ref(null);
const scrollRoot = ref(null);
let observer = null;

const emit = defineEmits(['hasRelated']);

const props = defineProps({
  pin_id: Number,
  /** 'grid' below detail | 'sidebar' right panel */
  layout: {
    type: String,
    default: 'grid',
  },
});

async function fetchPage({ reset = false } = {}) {
  if (!props.pin_id) return;
  if (reset) {
    if (isPinsLoading.value) return;
    isPinsLoading.value = true;
    offset.value = 0;
    exhausted.value = false;
    pins.value = [];
  } else {
    if (isLoadingMore.value || exhausted.value || isPinsLoading.value) return;
    isLoadingMore.value = true;
  }

  try {
    const response = await axios.get(`/api/tags/${props.pin_id}`, {
      params: { offset: offset.value, limit: PAGE_SIZE },
      withCredentials: true,
    });
    const batch = response.data || [];
    if (reset) {
      pins.value = batch;
    } else {
      const seen = new Set(pins.value.map((p) => p.id));
      for (const p of batch) {
        if (!seen.has(p.id)) pins.value.push(p);
      }
    }
    offset.value += batch.length;
    if (batch.length < PAGE_SIZE) exhausted.value = true;
    if (pins.value.length) {
      emit('hasRelated');
      prefetchFeedMeta(batch.map((p) => p.id)).catch((e) => console.error(e));
    }
  } catch (error) {
    console.log(error);
    if (reset) pins.value = [];
  } finally {
    isPinsLoading.value = false;
    isLoadingMore.value = false;
  }
}

function setupObserver() {
  teardownObserver();
  if (!sentinelEl.value) return;
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        fetchPage({ reset: false });
      }
    },
    {
      root: props.layout === 'sidebar' ? scrollRoot.value : null,
      rootMargin: '240px',
      threshold: 0,
    }
  );
  observer.observe(sentinelEl.value);
}

function teardownObserver() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
}

async function reload() {
  teardownObserver();
  await fetchPage({ reset: true });
  await nextTick();
  setupObserver();
}

onMounted(reload);
watch(() => props.pin_id, reload);
onBeforeUnmount(teardownObserver);
</script>

<template>
  <div :class="layout === 'sidebar' ? 'h-full min-h-0 flex flex-col' : 'mt-10 ml-20 mr-6'">
    <h2
      v-if="layout === 'sidebar'"
      class="flex-shrink-0 px-3 py-2 text-sm font-semibold text-gray-700"
    >
      {{ t('pin.pinView.moreLikeThis') }}
    </h2>
    <div
      ref="scrollRoot"
      :class="
        layout === 'sidebar'
          ? 'flex-1 min-h-0 overflow-y-auto px-2 pb-4'
          : ''
      "
    >
      <p v-if="isPinsLoading" class="text-sm text-gray-500 px-2 py-4">{{ t('common.loading') }}</p>
      <div
        v-else
        :class="
          layout === 'sidebar'
            ? 'grid grid-cols-2 gap-2'
            : 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5'
        "
      >
        <PinFeedCard v-for="pinem in pins" :key="`${layout}-${pinem.id}`" :pin="pinem" />
      </div>
      <div ref="sentinelEl" class="h-8 w-full" />
      <p v-if="isLoadingMore" class="text-center text-xs text-gray-500 py-2">
        {{ t('common.loading') }}
      </p>
    </div>
  </div>
</template>
