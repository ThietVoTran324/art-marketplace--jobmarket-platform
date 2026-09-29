<script setup>
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';
import PinFeedCard from './PinFeedCard.vue';
import { prefetchFeedMeta } from '@/composables/usePinFeedMeta';

const RELATED_LIMIT = 10;

const pins = ref([]);
const isPinsLoading = ref(false);

const emit = defineEmits(['hasRelated']);

const props = defineProps({
  pin_id: Number,
});

const loadPins = async () => {
  if (isPinsLoading.value || !props.pin_id) return;

  isPinsLoading.value = true;
  pins.value = [];
  try {
    const response = await axios.get(`/api/tags/${props.pin_id}`, {
      params: { offset: 0, limit: RELATED_LIMIT },
      withCredentials: true,
    });
    const batch = (response.data || []).slice(0, RELATED_LIMIT);
    pins.value = batch;
    if (batch.length) {
      emit('hasRelated');
      prefetchFeedMeta(batch.map((p) => p.id)).catch((e) => console.error(e));
    }
  } catch (error) {
    console.log(error);
  } finally {
    isPinsLoading.value = false;
  }
};

onMounted(loadPins);
watch(() => props.pin_id, loadPins);
</script>

<template>
  <div class="mt-10 ml-20 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
    <PinFeedCard v-for="pinem in pins" :key="pinem.id" :pin="pinem" />
  </div>
</template>
