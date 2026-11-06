<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue';
import axios from 'axios';
import { useI18n } from 'vue-i18n';
import PinFeedCard from './PinFeedCard.vue';
import { seedFeedMetaFromPins } from '@/composables/usePinFeedMeta';

const { t } = useI18n();
const pins = ref([]);
const offset = ref(0);
const limit = ref(10);
const isPinsLoading = ref(false);
const hasMore = ref(true);
const loadError = ref(null);
const hasLoadedOnce = ref(false);
const skeletonCount = ref(10);

const props = defineProps({
  value: { type: String, default: '' },
  tagId: { type: Number, default: null },
  authorId: { type: Number, default: null },
});

const hasQuery = () =>
  Boolean(props.tagId || props.authorId || (props.value && props.value.trim()));

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
    seedFeedMetaFromPins(batch);
    pins.value.push(...batch);
    offset.value += limit.value;
    if (batch.length < limit.value) {
      hasMore.value = false;
    }
    if (limit.value === 10) {
      limit.value = 5;
      skeletonCount.value = 5;
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
  skeletonCount.value = 10;
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

watch(() => [props.value, props.tagId, props.authorId], resetAndLoad);
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
  </div>
</template>
