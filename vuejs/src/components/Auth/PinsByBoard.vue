<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated, watch } from 'vue';
import axios from 'axios';

import CreatedPinBoard from './CreatedPinBoard.vue';
import CreatedDeletedPinBoard from './CreatedDeletedPinBoard.vue';
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
  boardId: Number,
  canEdit: Boolean,
  boardName: String
})

const loadPins = async () => {
  if (isPinsLoading.value) {
    return;
  }

  isPinsLoading.value = true;
  try {
    const response = await axios.get(`/api/boards/${props.boardId}`, {
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
  if (payload?.boardId == null) return;
  if (Number(payload.boardId) !== Number(props.boardId)) return;
  resetAndLoad();
};

const handleScroll = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;

  if (currentScrollPosition + 200 >= scrollableHeight) {
    loadPins();
  }
};

const showAddPins = ref(false)

onMounted(() => {
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

watch(() => props.boardId, () => {
  resetAndLoad();
});

const closeModal = () => {
  showAddPins.value = false;
  window.addEventListener('scroll', handleScroll);
  document.body.classList.remove("overflow-hidden");
};

const openModal = () => {
  document.body.classList.add("overflow-hidden");
  showAddPins.value = true;
  window.removeEventListener('scroll', handleScroll);
}
</script>

<template>
  <div class="mt-4" v-masonry transition-duration="0.4s" item-selector=".item" stagger="0.03s">
    <div v-for="pinGroup in pins" :key="pinGroup.id">
      <CreatedPinBoard v-if="!canEdit" v-masonry-tile class="item" v-for="pinem in pinGroup.pins" :key="pinem.id"
        :pin="pinem"
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        :showAllPins="pinGroup.showAllPins" />
      <CreatedDeletedPinBoard v-if="canEdit" v-masonry-tile class="item" v-for="pinem in pinGroup.pins" :key="pinem.id"
        :pin="pinem"
        :board_id="boardId"
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        :showAllPins="pinGroup.showAllPins" />
    </div>
  </div>
  <div v-show="showNoPins" class="mt-4 px-2">
    <p class="text-sm text-gray-500">No pins in this board yet</p>
  </div>
</template>