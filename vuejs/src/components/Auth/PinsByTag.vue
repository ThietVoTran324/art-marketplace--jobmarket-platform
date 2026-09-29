<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated, watch, nextTick } from 'vue';
import axios from 'axios';
import PinFeedCard from './PinFeedCard.vue';
import { prefetchFeedMeta } from '@/composables/usePinFeedMeta';

const pins = ref([]);
const offset = ref(0);
const limit = ref(10);
const isPinsLoading = ref(false);
const hasMore = ref(true);

const props = defineProps({
  tag: String,
});

const loadPins = async () => {
  if (isPinsLoading.value || !hasMore.value) return;

  isPinsLoading.value = true;
  try {
    const response = await axios.get(`/api/pins/tag/${props.tag}`, {
      params: { offset: offset.value, limit: limit.value },
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
  } finally {
    isPinsLoading.value = false;
    await nextTick();
    const scrollableHeight = document.documentElement.scrollHeight;
    if (hasMore.value && window.innerHeight + window.scrollY + 500 >= scrollableHeight) {
      loadPins();
    }
  }
};

const resetAndLoad = () => {
  pins.value = [];
  offset.value = 0;
  limit.value = 10;
  hasMore.value = true;
  isPinsLoading.value = false;
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

watch(() => props.tag, resetAndLoad);
</script>

<template>
  <div class="ml-20 mt-10 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
    <PinFeedCard v-for="pinem in pins" :key="pinem.id" :pin="pinem" />
  </div>
</template>
