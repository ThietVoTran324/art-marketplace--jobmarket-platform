<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue';
import axios from 'axios';
import PinFeedCard from './PinFeedCard.vue';
import { prefetchFeedMeta } from '@/composables/usePinFeedMeta';

const pins = ref([]);
const offset = ref(0);
const limit = ref(10);
const isPinsLoading = ref(false);
const hasMore = ref(true);
const loadError = ref(null);
const hasLoadedOnce = ref(false);

const props = defineProps({
  value: String,
});

const loadPins = async () => {
  if (isPinsLoading.value || !hasMore.value) return;
  if (!props.value?.trim()) {
    pins.value = [];
    hasMore.value = false;
    hasLoadedOnce.value = true;
    return;
  }

  isPinsLoading.value = true;
  loadError.value = null;
  try {
    const response = await axios.get(`/api/pins/search`, {
      params: { offset: offset.value, limit: limit.value, value: props.value },
      withCredentials: true,
    });
    const batch = response.data || [];
    pins.value.push(...batch);
    if (batch.length) {
      prefetchFeedMeta(batch.map((p) => p.id)).catch((e) => console.error(e));
    }
    offset.value += limit.value;
    if (batch.length < limit.value) {
      hasMore.value = false;
    }
    if (limit.value === 10) {
      limit.value = 5;
    }
  } catch (error) {
    console.log(error);
    loadError.value =
      error?.response?.data?.detail || error?.message || 'Error loading search results';
    hasMore.value = false;
  } finally {
    isPinsLoading.value = false;
    hasLoadedOnce.value = true;
  }
};

const resetAndLoad = () => {
  pins.value = [];
  offset.value = 0;
  limit.value = 10;
  hasMore.value = true;
  isPinsLoading.value = false;
  loadError.value = null;
  hasLoadedOnce.value = false;
  loadPins();
};

const handleScroll = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;
  if (currentScrollPosition + 200 >= scrollableHeight) {
    loadPins();
  }
};

onMounted(() => {
  loadPins();
  window.addEventListener('scroll', handleScroll);
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll);
});

onActivated(() => {
  window.addEventListener('scroll', handleScroll);
});

onDeactivated(() => {
  window.removeEventListener('scroll', handleScroll);
});

watch(() => props.value, resetAndLoad);
</script>

<template>
  <div>
    <p v-if="isPinsLoading && !pins.length" class="ml-20 mt-28 text-gray-500">Loading…</p>
    <p v-else-if="loadError" class="ml-20 mt-28 text-red-600 text-sm">{{ loadError }}</p>
    <p
      v-else-if="hasLoadedOnce && !pins.length && !isPinsLoading"
      class="ml-20 mt-28 text-gray-500"
    >
      No results found
    </p>
    <div
      v-else-if="pins.length"
      class="ml-20 mt-10 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
    >
      <PinFeedCard
        v-for="pinem in pins"
        :key="pinem.id"
        :pin="pinem"
      />
    </div>
    <p v-if="isPinsLoading && pins.length" class="ml-20 mt-4 text-gray-400 text-sm">Loading…</p>
  </div>
</template>
