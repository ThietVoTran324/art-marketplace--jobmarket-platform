<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated } from 'vue';
import axios from 'axios';

import SavedPin from './SavedPin.vue';
import DeleteSavedPin from './DeleteSavedPin.vue';
import { bus, PIN_SAVED } from '@/events/bus';

const pins = ref([]);
const offset = ref(0);
const limit = ref(10);

const cntLoading = ref(0)
const limitCntLoading = ref(null)

const isPinsLoading = ref(false);

const showNoPins = ref(false)

const props = defineProps({
  user_id: Number,
  auth_user_id: Number,
  embedded: { type: Boolean, default: false },
  hideEmpty: { type: Boolean, default: false },
})

const loadPins = async () => {
  if (isPinsLoading.value) {
    return;
  }

  isPinsLoading.value = true;
  try {
    const response = await axios.get(`/api/pins/user_saved_pins/${props.user_id}`, {
      params: { offset: offset.value, limit: limit.value },
      withCredentials: true,
    });

    pins.value.push({ pins: response.data, showAllPins: false });

    if (pins.value[0]?.pins?.length === 0) {
      showNoPins.value = true
    } else {
      showNoPins.value = false
    }

    limitCntLoading.value = response.data.length

    offset.value += limit.value;

    if (limit.value === 10) {
      limit.value = 5;
    }

  } catch (error) {
    console.log(error);
  } finally {
    isPinsLoading.value = false;
  }
};

const resetAndLoad = async () => {
  pins.value = [];
  offset.value = 0;
  limit.value = 10;
  showNoPins.value = false;
  cntLoading.value = 0;
  isPinsLoading.value = false;
  await loadPins();
};

const onPinSaved = (payload) => {
  // Loose saved list only cares about saves without a board.
  if (payload?.boardId != null) return;
  if (props.auth_user_id && props.user_id !== props.auth_user_id) return;
  resetAndLoad();
};

const handleScroll = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;

  if (currentScrollPosition + 200 >= scrollableHeight) {
    loadPins();
  }
};

const showDeleteSavePin = ref(null)

onMounted(() => {
  showDeleteSavePin.value = props.user_id === props.auth_user_id
  loadPins();
  window.addEventListener('scroll', handleScroll);
  bus.on(PIN_SAVED, onPinSaved);
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll);
  bus.off(PIN_SAVED, onPinSaved);
});

onActivated(() => {
  window.addEventListener('scroll', handleScroll);
  resetAndLoad();
});

onDeactivated(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<template>
  <div
    :class="embedded ? 'mt-4' : 'mt-10 ml-20'"
    v-masonry
    transition-duration="0.4s"
    item-selector=".item"
    stagger="0.03s"
  >
    <div v-for="pinGroup in pins" :key="pinGroup.id">
      <SavedPin v-if="!showDeleteSavePin" v-masonry-tile class="item" v-for="pinem in pinGroup.pins" :key="pinem.id"
        :pin="pinem" 
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        :showAllPins="pinGroup.showAllPins" />
      <DeleteSavedPin v-if="showDeleteSavePin" v-masonry-tile class="item" v-for="pinem in pinGroup.pins"
        :key="pinem.id" :pin="pinem" 
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        :showAllPins="pinGroup.showAllPins" />
    </div>
  </div>

  <div
    v-show="showNoPins && !hideEmpty"
    :class="embedded ? 'mt-4' : 'mt-10 ml-20'"
  >
    <section class="text-center flex flex-col justify-center items-center relative">
      <h1 class="text-2xl font-bold mb-4">No saved pins</h1>
    </section>
  </div>
</template>
