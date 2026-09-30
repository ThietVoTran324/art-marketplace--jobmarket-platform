<script setup>
import { onMounted, ref, onBeforeUnmount, onActivated, onDeactivated } from 'vue';
import axios from 'axios';

import CreatedPin from './CreatedPin.vue';
import CreatedDeletedPin from './CreatedDeletedPin.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const pins = ref([]);
const offset = ref(0);
const limit = ref(10);

const cntLoading = ref(0)
const limitCntLoading = ref(null)

const isPinsLoading = ref(false);

const showNoPins = ref(false)

const props = defineProps({
  user_id: Number,
  auth_user_id: Number
})

const showDeleteCreatedPin = ref(null)

const loadPins = async () => {
  if (isPinsLoading.value) {
    return;
  }

  isPinsLoading.value = true;
  try {
    const response = await axios.get(`/api/pins/user_created_pins/${props.user_id}`, {
      params: { offset: offset.value, limit: limit.value },
      withCredentials: true,
    });

    // Append new pins to the existing ones
    pins.value.push({ pins: response.data, showAllPins: false });

    if (pins.value[0].pins.length === 0) {
      showNoPins.value = true
    }

    limitCntLoading.value = response.data.length

    limitCntLoading.value

    // Increment the offset
    offset.value += limit.value;

    if (limit.value === 10) {
      limit.value = 5;
    }

  } catch (error) {
    console.log(error);
  }

};

const handleScroll = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;

  // Trigger loadPins if user reaches bottom
  if (currentScrollPosition + 200 >= scrollableHeight) {
    loadPins();
  }
};

onMounted(() => {
  showDeleteCreatedPin.value = props.user_id === props.auth_user_id
  loadPins();  // Initial load
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

const removePin = (pinId) => {
  for (const group of pins.value) {
    const idx = group.pins.findIndex((p) => p.id === pinId)
    if (idx !== -1) {
      group.pins.splice(idx, 1)
      break
    }
  }
  const remaining = pins.value.reduce((n, g) => n + g.pins.length, 0)
  if (remaining === 0) {
    showNoPins.value = true
  }
}
</script>

<template>
  <div class="mt-10 ml-20" v-masonry transition-duration="0.4s" item-selector=".item" stagger="0.03s">
    <div v-for="pinGroup in pins" :key="pinGroup.id">
      <CreatedPin v-if="!showDeleteCreatedPin" v-masonry-tile class="item" v-for="pinem in pinGroup.pins"
        :key="pinem.id" :pin="pinem"
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        :showAllPins="pinGroup.showAllPins" />
      <CreatedDeletedPin v-if="showDeleteCreatedPin" v-masonry-tile class="item" v-for="pinem in pinGroup.pins"
        :key="pinem.id" :pin="pinem"
        @pinLoaded="() => { cntLoading++; if (cntLoading === limitCntLoading) { pinGroup.showAllPins = true; isPinsLoading = false; cntLoading = 0 } }"
        @deleted="removePin"
        :showAllPins="pinGroup.showAllPins" />
    </div>
  </div>
  <div v-show="showNoPins" class="mt-10 ml-20">
    <section class="text-center flex flex-col justify-center items-center relative">
      <h1 class="text-2xl font-bold mb-4">{{ t('boards.createdPins.emptyTitle') }}</h1>
    </section>
  </div>
</template>
