<script setup>
import { onMounted, ref, onBeforeUnmount, nextTick, watch, computed, onActivated, onDeactivated } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';

import JSConfetti from 'js-confetti'

// import confetti from 'canvas-confetti'

import PinFeedCard from '@/components/Auth/PinFeedCard.vue';

import PinsByTag from '@/components/Auth/PinsByTag.vue';
import PinsBySearch from '@/components/Auth/PinsBySearch.vue';
import { prefetchFeedMeta } from '@/composables/usePinFeedMeta';
import { useAuthModal } from '@/composables/useAuthModal';
import { foldSearchText } from '@/utils/foldSearchText';

const confetti = new JSConfetti()

import { useUnreadMessagesStore } from "@/stores/unreadMessages";

const unreadMessagesStore = useUnreadMessagesStore();

const preLoadTags = ref(false)

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();
const { openAuthModal } = useAuthModal();

const tagsContainer = ref(null)

const route = useRoute();
const router = useRouter()

const redirecting = ref(false)

const emit = defineEmits(['createPinModelClose'])

const lottieLoaded = ref(false)

const pins = ref([]);
const offset = ref(0);
const limit = ref(15);

const stagged = ref('0.03s')
const duration = ref('0.4s')

const cntLoading = ref(0)

const isPinsLoading = ref(false);
const hasMorePins = ref(true);
const feedSentinel = ref(null);

let feedSentinelObserver = null;

const cntTagLoading = ref(0)
const limitTagLoading = ref(null)

const tagFromUrl = ref(null)
const registerQuery = ref(null)

const available_tags = ref(null)
const bgColors = ref(['bg-red-200', 'bg-orange-200', 'bg-amber-200', 'bg-lime-200', 'bg-green-200', 'bg-emerald-200', 'bg-teal-200', 'bg-sky-200', 'bg-blue-200', 'bg-indigo-200', 'bg-violet-200', 'bg-purple-200', 'bg-fuchsia-200', 'bg-pink-200', 'bg-rose-200'])

const props = defineProps({
  register: Boolean,
  guest: { type: Boolean, default: false },
})

const showCreatePin = ref(false)

const nearFeedBottom = () => {
  const scrollableHeight = document.documentElement.scrollHeight;
  const currentScrollPosition = window.innerHeight + window.scrollY;
  return currentScrollPosition + 500 >= scrollableHeight;
};

const fillViewportIfNeeded = async () => {
  await nextTick();
  // First page of short placeholders often does not fill the screen — no scroll
  // event ever fires, so infinite load stalls. Keep fetching until tall enough.
  if (!hasMorePins.value || isPinsLoading.value) return;
  if (nearFeedBottom()) {
    loadPins();
  }
};

const loadPins = async () => {
  if (isPinsLoading.value || !hasMorePins.value) {
    return;
  }

  isPinsLoading.value = true;

  try {
    const response = await axios.get('/api/pins/', {
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
      hasMorePins.value = false;
    }
    if (limit.value === 15) {
      limit.value = 5;
    }
  } catch (error) {
    console.log(error);
  } finally {
    isPinsLoading.value = false;
    fillViewportIfNeeded();
  }
};

const handleScroll = () => {
  if (nearFeedBottom()) {
    loadPins();
  }
};

const bindFeedSentinel = async () => {
  await nextTick();
  if (feedSentinelObserver) {
    feedSentinelObserver.disconnect();
    feedSentinelObserver = null;
  }
  if (!feedSentinel.value || typeof IntersectionObserver === 'undefined') return;
  feedSentinelObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadPins();
    },
    { root: null, rootMargin: '600px 0px', threshold: 0 }
  );
  feedSentinelObserver.observe(feedSentinel.value);
};

const randomBgColor = () => {
  const randomIndex = Math.floor(Math.random() * bgColors.value.length);
  return bgColors.value[randomIndex];
};

onMounted(async () => {

  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = `(${totalUnread}) Pinterest`;
  } else {
    document.title = 'Pinterest';
  }

  loadPins();
  window.addEventListener('scroll', handleScroll, { passive: true });
  bindFeedSentinel();

  if (props.guest) {
    tagsLoaded.value = true;
    return;
  }

  try {
    const response = await axios.get('/api/tags/tags-with-first-pin', { withCredentials: true });
    available_tags.value = response.data;
    limitTagLoading.value = available_tags.value.length;
  } catch (error) {
    console.log(error);
  }

  for (let i = 0; i < available_tags.value.length; i++) {
    available_tags.value[i].color = randomBgColor();
  }

  preLoadTags.value = true

  for (let i = 0; i < available_tags.value.length; i++) {

    available_tags.value[i].file = null
    available_tags.value[i].isImage = null
    available_tags.value[i].videoPlayer = null

    if (!available_tags.value[i].pinId) {
      available_tags.value[i].file = 'https://i.pinimg.com/736x/40/f1/b0/40f1b01bf3df9bc24bdbad4589125023.jpg';
      available_tags.value[i].isImage = true
    } else {
      try {
        const pinResponse = await axios.get(`/api/tags/tags-with-first-pin/upload/${available_tags.value[i].pinId}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          available_tags.value[i].file = blobUrl;
          available_tags.value[i].isImage = true;
        } else {
          available_tags.value[i].file = blobUrl;
          available_tags.value[i].isImage = false;
          available_tags.value[i].videoPlayer = null;
        }
      } catch (error) {
        console.error(error);
      }
    }
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll);
  if (feedSentinelObserver) {
    feedSentinelObserver.disconnect();
    feedSentinelObserver = null;
  }
});

function closeCreatePin() {
  showCreatePin.value = false
  document.body.style.overflowY = 'auto'
  emit('createPinModelClose')
}

const clearQuery = () => {
  router.replace({ path: route.path, query: {} });
};

onActivated(() => {
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = `(${totalUnread}) Pinterest`;
  } else {
    document.title = 'Pinterest';
  }
  if (selectedTag.value === 'Everything' && searchValue.value === '') {
    window.addEventListener('scroll', handleScroll, { passive: true });
    bindFeedSentinel();
  }

  registerQuery.value = route.query.register || '';

  if (registerQuery.value) {
    setTimeout(() => {
      confetti.addConfetti({
        emojis: ['🌈', '⚡️', '💥', '✨', '💫', '🦄'],
        confettiColors: ['#ff0a54', '#ff477e', '#ff7096', '#ff85a1', '#fbb1bd', '#f9bec7'],
        confettiRadius: 6,
        confettiNumber: 100,
        emojiSize: 40,
        emojiNumber: 50,
        shapes: ['circle', 'square'],
        confettiGravity: 0.5,
        confettiDrift: 0.1,
        confettiStartVelocity: 30,
        confettiAngle: 90,
        confettiSpread: 180,
        confettiDuration: 5000
      });
    }, 2000);
    clearQuery()
  }

  if (available_tags.value) {
    tagFromUrl.value = route.query.tag || '';
    if (tagFromUrl.value) {
      if (available_tags.value.some(tagObj => tagObj.name === tagFromUrl.value)) {
        loadPinsByTag(tagFromUrl.value);
        clearQuery()
      }
    }
    let searchFromUrl = route.query.search || '';
    if (searchFromUrl) {
      searchInput.value = searchFromUrl
      searchValue.value = searchFromUrl
      clearQuery()
    }
  }
  if (!tagsLoaded.value) {
    tagFromUrl.value = route.query.tag || '';
    let searchFromUrl = route.query.search || '';
    if (tagFromUrl.value || searchFromUrl) {
      redirecting.value = true
    }
  }
});

onDeactivated(() => {
  window.removeEventListener('scroll', handleScroll);
  if (feedSentinelObserver) {
    feedSentinelObserver.disconnect();
    feedSentinelObserver = null;
  }
});

const selectedTag = ref('Everything')
const showPinsBytag = ref(false)

async function loadPinsByTag(name) {
  if (props.guest) {
    openAuthModal('login');
    return;
  }
  if (showSearchPins.value) {
    showSearchPins.value = false
  }
  if (name !== selectedTag.value) {
    showPinsBytag.value = false
    selectedTag.value = null
    if (name === 'Everything') {
      window.addEventListener('scroll', handleScroll, { passive: true });
      showPinsBytag.value = false
      selectedTag.value = 'Everything'
      searchInput.value = ''
      searchValue.value = ''
      searchStatus.value = 'idle'
      activeTagIndex.value = -1
      bindFeedSentinel();
      fillViewportIfNeeded();
    } else {
      window.removeEventListener('scroll', handleScroll);
      if (feedSentinelObserver) {
        feedSentinelObserver.disconnect();
        feedSentinelObserver = null;
      }
      await nextTick();
      selectedTag.value = name
      showPinsBytag.value = true
    }
  }
}

const canScrollLeft = ref(false);
const canScrollRight = ref(false);

const scrollAmount = 400;

const containerRef = ref(null);

function updateScrollState() {
  if (!containerRef.value) return;

  const { scrollLeft, scrollWidth, clientWidth } = containerRef.value;
  canScrollLeft.value = scrollLeft > 0;
  canScrollRight.value = scrollLeft < (scrollWidth - clientWidth - 1);
}

function customScroll(container, amount, duration = 300) {
  const start = container.scrollLeft;
  const startTime = performance.now();

  function ease(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  }

  function scrollStep(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeValue = ease(progress);

    container.scrollLeft = start + amount * easeValue;

    if (elapsed < duration) {
      requestAnimationFrame(scrollStep);
    }
  }

  requestAnimationFrame(scrollStep);
}

const scrollLeft = () => {
  if (containerRef.value) {
    // containerRef.value.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    customScroll(containerRef.value, -scrollAmount, 300);
  }
};

const scrollRight = () => {
  if (containerRef.value) {
    // containerRef.value.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    customScroll(containerRef.value, scrollAmount, 300);
  }
};

const tagsLoaded = ref(false)

function onTagLoad() {
  cntTagLoading.value += 1
  if (cntTagLoading.value === limitTagLoading.value) {
    tagsLoaded.value = true
  }
}

watch(tagsLoaded, (newTags) => {
  if (newTags) {
    redirecting.value = false
    tagFromUrl.value = route.query.tag || '';
    if (tagFromUrl.value) {
      if (available_tags.value.some(tagObj => tagObj.name === tagFromUrl.value)) {
        loadPinsByTag(tagFromUrl.value);
        clearQuery()
      }
    }
    let searchFromUrl = route.query.search || '';
    if (searchFromUrl) {
      searchInput.value = searchFromUrl
      searchValue.value = searchFromUrl
      clearQuery()
    }
  }
});

const showSearchPins = ref(false)
/** Debounced query sent to /pins/search */
const searchValue = ref('')
/** Live input bound to the search box */
const searchInput = ref('')
/** idle | typing | ready */
const searchStatus = ref('idle')
const activeTagIndex = ref(-1)
let searchDebounceTimer = null

function clearSearchDebounce() {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }
}

function commitSearch(query) {
  clearSearchDebounce()
  const trimmed = (query || '').trim()
  searchInput.value = trimmed ? searchInput.value : ''
  if (!trimmed) {
    searchValue.value = ''
    searchStatus.value = 'idle'
    activeTagIndex.value = -1
    return
  }
  searchStatus.value = 'ready'
  searchValue.value = trimmed
}

watch(searchInput, (newValue, oldValue) => {
  if (props.guest) {
    if (newValue) {
      searchInput.value = ''
      openAuthModal('login')
    }
    return
  }
  clearSearchDebounce()
  activeTagIndex.value = -1
  const trimmed = (newValue || '').trim()
  if (!trimmed) {
    searchStatus.value = 'idle'
    if ((oldValue || '').trim()) {
      searchValue.value = ''
    }
    return
  }
  searchStatus.value = 'typing'
  searchDebounceTimer = setTimeout(() => {
    commitSearch(trimmed)
  }, 280)
})

watch(searchValue, async (newValue, oldValue) => {
  if (props.guest) {
    return
  }
  if (newValue.trim() !== '') {
    selectedTag.value = ''
    showSearchPins.value = false
    showPinsBytag.value = false
    window.removeEventListener('scroll', handleScroll);
    await nextTick()
    showSearchPins.value = true
  } else {
    if ((oldValue || '').trim() !== '') {
      showSearchPins.value = false
      loadPinsByTag('Everything')
    }
  }
});

const filteredTags = computed(() => {
  const trimmedFold = foldSearchText(searchInput.value);
  let filtered = [];

  if (!trimmedFold) {
    filtered = available_tags.value || [];
  } else {
    const searchWords = trimmedFold.split(/\s+/).filter(Boolean);
    filtered = (available_tags.value || []).filter(tag => {
      const nameFold = foldSearchText(tag.name);
      return searchWords.some(word => nameFold.includes(word));
    });
  }

  const everythingTag = (available_tags.value || []).find(
    tag => foldSearchText(tag.name) === 'everything'
  );

  if (everythingTag && !filtered.some(tag => foldSearchText(tag.name) === 'everything')) {
    filtered.unshift(everythingTag);
  }

  return filtered;
});

function onSearchKeydown(e) {
  if (props.guest) return
  const tags = filteredTags.value || []
  if (e.key === 'Escape') {
    e.preventDefault()
    clearSearchDebounce()
    searchInput.value = ''
    searchValue.value = ''
    searchStatus.value = 'idle'
    activeTagIndex.value = -1
    return
  }
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    if (!tags.length) return
    e.preventDefault()
    activeTagIndex.value = (activeTagIndex.value + 1 + tags.length) % tags.length
    return
  }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    if (!tags.length) return
    e.preventDefault()
    activeTagIndex.value = (activeTagIndex.value - 1 + tags.length) % tags.length
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    if (activeTagIndex.value >= 0 && tags[activeTagIndex.value]) {
      const tag = tags[activeTagIndex.value]
      searchInput.value = ''
      searchValue.value = ''
      searchStatus.value = 'idle'
      activeTagIndex.value = -1
      loadPinsByTag(tag.name)
      return
    }
    commitSearch(searchInput.value)
  }
}

const isActive = ref(false)

</script>
<template>
  <nav :class="['fixed top-0 left-20 w-full  z-30', 'backdrop-blur-sm']">
    <div class="flex items-center justify-between px-6 py-2 gap-3">
      <div class="relative flex-1">
        <input
          v-model="searchInput"
          type="text"
          placeholder="Search"
          :readonly="guest"
          autocomplete="off"
          :class="[
            'transition-all duration-300 cursor-text bg-white bg-opacity-20 backdrop-blur-sm text-black',
            'text-md rounded-3xl block w-full py-3 pl-12 pr-10 outline-none border border-black',
            'focus:shadow-lg focus:shadow-blue-500/50',
          ]"
          @focus="guest && openAuthModal('login')"
          @click="guest && openAuthModal('login')"
          @keydown="onSearchKeydown"
        />
        <div class="absolute left-1 top-4 pl-3 flex items-center pointer-events-none">
          <i class="pi pi-search text-black"></i>
        </div>
        <p
          v-if="!guest && searchStatus === 'typing'"
          class="absolute left-12 -bottom-5 text-xs text-gray-500"
        >
          Searching…
        </p>
        <p
          v-else-if="!guest && !searchInput.trim() && searchStatus === 'idle'"
          class="absolute left-12 -bottom-5 text-xs text-gray-400"
        >
          Type to search…
        </p>
      </div>
      <button
        v-if="guest"
        type="button"
        class="shrink-0 mr-20 px-5 py-2.5 rounded-3xl bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
        @click="openAuthModal('login')"
      >
        Log in
      </button>
      <div v-else class="mr-20 w-0" />
    </div>
  </nav>

  <div v-if="redirecting"
    class="fixed inset-0 bg-black bg-opacity-40 z-50 items-center justify-center flex flex-col gap-20">
    <img src="/logo.png" alt="Logo" class="w-24 h-24 logo bg-white rounded-full" />
  </div>

  
  <div
    v-if="!guest"
    ref="tagsContainer"
    class="mt-16 ml-20 group fixed top-0 right-0 left-0 z-30 backdrop-blur-sm"
  >
    
    <button
      class="absolute left-5 top-1/2 transform -translate-y-1/2 z-20 bg-white rounded-full px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 active:scale-75"
      @click="scrollLeft(containerRef)">
      <i class="pi pi-chevron-left text-xl"></i>
    </button>

    
    <div v-if="preLoadTags" class="relative overflow-hidden">
      
      <div
        class="absolute top-0 left-0 w-32 h-full bg-gradient-to-r from-white via-white/50 to-transparent pointer-events-none z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
      </div>
      <div
        class="absolute top-0 right-0 w-32 h-full bg-gradient-to-l from-white via-white/50 to-transparent pointer-events-none z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
      </div>

      
      <div ref="containerRef" class="flex gap-2 overflow-x-auto whitespace-nowrap scrollbar-hide p-0.5 px-5"
        v-auto-animate>
        <div
          v-for="(tag, idx) in filteredTags"
          :key="tag.id"
          @click="loadPinsByTag(tag.name)"
          :class="[
            tag.name == selectedTag
              ? 'bg-black text-white shadow-lg scale-105'
              : `${tag.color}`,
            idx === activeTagIndex ? 'ring-2 ring-black scale-110' : '',
            'flex',
            'items-center',
            'gap-1',
            'text-sm',
            'rounded-3xl',
            'pl-2 pr-5',
            'py-1',
            'cursor-pointer',
            'transition-transform',
            'duration-100',
            'transform',
            'hover:scale-110',
          ]"
        >          
          <div class="w-9 h-9 flex-shrink-0">
            <img v-show="tagsLoaded" v-if="tag.isImage && tag.file" :src="tag.file" alt="Tag Image" @load="onTagLoad"
              class="w-full h-full object-cover rounded-full fade-in" :class="{ 'fade-in-animation': tagsLoaded }" />
            <video v-show="tagsLoaded" v-else-if="!tag.isImage && tag.file" :src="tag.file" @loadeddata="onTagLoad"
              @mouseover="tag.videoPlayer.play()" :ref="el => { if (el) tag.videoPlayer = el; }"
              class="w-full h-full object-cover rounded-full fade-in" :class="{ 'fade-in-animation': tagsLoaded }"
              autoplay loop muted />
            <div v-show="!tagsLoaded" class="bg-gray-100 w-full h-full object-cover rounded-full animate-pulse">
            </div>
          </div>
          
          <span class="truncate">{{ tag.name }}</span>
        </div>
      </div>
    </div>

    
    <button
      class="absolute right-5 top-1/2 transform -translate-y-1/2 z-20 bg-white rounded-full px-3 py-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 active:scale-75"
      @click="scrollRight(containerRef)">
      <i class="pi pi-chevron-right text-xl"></i>
    </button>
  </div>

  <div
    v-show="!showPinsBytag && !showSearchPins"
    :class="guest ? 'ml-20 mt-20 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5' : 'ml-20 mt-28 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5'"
  >
    <PinFeedCard class="item" v-for="pinem in pins" :key="pinem.id" :pin="pinem" />
  </div>
  <div
    v-show="!showPinsBytag && !showSearchPins"
    ref="feedSentinel"
    class="ml-20 h-8 w-full"
    aria-hidden="true"
  />
  <PinsByTag class="mt-28" v-if="showPinsBytag && selectedTag !== null && !showSearchPins" :tag="selectedTag" />
  <PinsBySearch class="mt-28" v-if="showSearchPins" :value="searchValue" />
</template>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  transform: scale(1);
}

input:focus {
  box-shadow: 0 0 8px rgba(199, 88, 151, 0.9);
}

/* Define transition animations */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
  /* Chrome, Safari, Opera */
}

.fade-in-animation {
  opacity: 0;
  transform: scale(0.95);
  animation: fadeIn 0.3s ease-in-out forwards;
}

@keyframes fadeIn {
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes pulse-scale {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.5);
  }

  100% {
    transform: scale(1);
  }
}

.logo {
  animation: pulse-scale 1.5s infinite ease-in-out;
}
</style>