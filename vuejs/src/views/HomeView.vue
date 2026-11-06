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
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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

const tagFromUrl = ref(null)
const registerQuery = ref(null)

const available_tags = ref(null)
/** Idle tag bar: Everything + this many hottest tags (full catalog stays in available_tags). */
const TAG_BAR_IDLE_LIMIT = 15
const bgColors = ref(['bg-red-200', 'bg-orange-200', 'bg-amber-200', 'bg-lime-200', 'bg-green-200', 'bg-emerald-200', 'bg-teal-200', 'bg-sky-200', 'bg-blue-200', 'bg-indigo-200', 'bg-violet-200', 'bg-purple-200', 'bg-fuchsia-200', 'bg-pink-200', 'bg-rose-200'])
const tagMediaInflight = new Set()

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
    // Personalized home by default; ?mode=chrono opt-out to legacy timeline
    const feedMode = route.query.mode === 'chrono' ? 'chrono' : 'home';
    const response = await axios.get('/api/pins/', {
      params: { offset: offset.value, limit: limit.value, mode: feedMode },
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
    available_tags.value = (response.data || []).map((tag) => ({
      ...tag,
      color: randomBgColor(),
      file: null,
      isImage: null,
      videoPlayer: null,
      pin_count: Number(tag.pin_count) || 0,
    }));
  } catch (error) {
    console.log(error);
  }

  preLoadTags.value = true
  tagsLoaded.value = true
  await nextTick()
  ensureTagMediaForVisible()
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

  tagFromUrl.value = route.query.tag || '';
  let searchFromUrl = route.query.search || '';
  if (tagFromUrl.value) {
    // Deep link works even if tag is outside idle top-15 bar.
    loadPinsByTag(tagFromUrl.value);
    clearQuery()
  }
  if (searchFromUrl) {
    commitSearch(searchFromUrl)
    clearQuery()
  }
  redirecting.value = false
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
      clearConfirmedSearch()
      searchStatus.value = 'idle'
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

watch(tagsLoaded, (newTags) => {
  if (newTags) {
    redirecting.value = false
  }
});

const showSearchPins = ref(false)
/** Confirmed query → one /pins/search request (no realtime suggest API). */
const searchValue = ref('')
const searchTagId = ref(null)
const searchAuthorId = ref(null)
const searchInput = ref('')
/** idle | ready */
const searchStatus = ref('idle')

function clearConfirmedSearch() {
  searchValue.value = ''
  searchTagId.value = null
  searchAuthorId.value = null
}

function commitSearch(query, opts = {}) {
  const trimmed = (query || '').trim()
  if (!trimmed && !opts.tagId && !opts.authorId) {
    clearConfirmedSearch()
    searchStatus.value = 'idle'
    return
  }
  searchStatus.value = 'ready'
  searchValue.value = trimmed
  searchTagId.value = opts.tagId || null
  searchAuthorId.value = opts.authorId || null
  if (opts.label) {
    searchInput.value = opts.label
  }
}

watch(searchInput, (newValue, oldValue) => {
  if (props.guest) {
    if (newValue) {
      searchInput.value = ''
      openAuthModal('login')
    }
    return
  }
  const trimmed = (newValue || '').trim()
  if (!trimmed && (oldValue || '').trim()) {
    clearConfirmedSearch()
    searchStatus.value = 'idle'
  }
})

watch(
  () => [searchValue.value, searchTagId.value, searchAuthorId.value],
  async ([value, tagId, authorId], oldTuple = []) => {
    if (props.guest) return
    const [oldValue] = oldTuple || []
    const has = Boolean(tagId || authorId || (value && String(value).trim()))
    if (has) {
      selectedTag.value = ''
      showSearchPins.value = false
      showPinsBytag.value = false
      window.removeEventListener('scroll', handleScroll)
      await nextTick()
      showSearchPins.value = true
    } else if ((oldValue || '').trim()) {
      showSearchPins.value = false
      loadPinsByTag('Everything')
    }
  }
)

/** Rank vs confirmed needle: exact → prefix → contains (Enter-only; not while typing). */
function tagMatchRank(nameFold, needle) {
  if (!needle || !nameFold || nameFold === 'everything') return 0
  if (nameFold === needle) return 300
  if (nameFold.startsWith(needle)) return 200
  if (needle.length >= 2 && nameFold.includes(needle)) return 100
  return 0
}

const filteredTags = computed(() => {
  const tags = available_tags.value || []
  const everythingTag = tags.find(
    (tag) => foldSearchText(tag.name) === 'everything'
  )
  const rest = tags.filter(
    (tag) => foldSearchText(tag.name) !== 'everything'
  )
  // Confirmed search: mount matching chips from full catalog (may be outside idle top-N).
  const needle = foldSearchText((searchValue.value || '').trim())

  let filtered
  if (!needle) {
    // Idle: Everything + hottest tags only (API already ordered by pin_count desc).
    const top = [...rest]
      .sort(
        (a, b) =>
          (Number(b.pin_count) || 0) - (Number(a.pin_count) || 0) ||
          String(a.name || '').localeCompare(String(b.name || ''))
      )
      .slice(0, TAG_BAR_IDLE_LIMIT)
    filtered = top
  } else {
    const scored = []
    for (const tag of rest) {
      const nameFold = foldSearchText(tag.name)
      const rank = tagMatchRank(nameFold, needle)
      if (rank <= 0) continue
      scored.push({ rank, nameFold, tag })
    }
    scored.sort((a, b) => b.rank - a.rank || a.nameFold.localeCompare(b.nameFold))
    // Cap mounted chips so a broad Enter match cannot rebuild the whole catalog DOM.
    filtered = scored.slice(0, TAG_BAR_IDLE_LIMIT).map((s) => s.tag)
  }

  if (everythingTag) {
    filtered = [
      everythingTag,
      ...filtered.filter((tag) => foldSearchText(tag.name) !== 'everything'),
    ]
  }

  return filtered
})

async function ensureTagMedia(tag) {
  if (!tag || tag.file || tagMediaInflight.has(tag.id)) return
  tagMediaInflight.add(tag.id)
  try {
    if (!tag.pinId) {
      tag.file =
        'https://i.pinimg.com/736x/40/f1/b0/40f1b01bf3df9bc24bdbad4589125023.jpg'
      tag.isImage = true
      return
    }
    const pinResponse = await axios.get(
      `/api/tags/tags-with-first-pin/upload/${tag.pinId}`,
      { responseType: 'blob' }
    )
    const blobUrl = URL.createObjectURL(pinResponse.data)
    const contentType = pinResponse.headers['content-type'] || ''
    tag.file = blobUrl
    tag.isImage = contentType.startsWith('image/')
    tag.videoPlayer = null
  } catch (error) {
    console.error(error)
  } finally {
    tagMediaInflight.delete(tag.id)
  }
}

function ensureTagMediaForVisible() {
  for (const tag of filteredTags.value || []) {
    ensureTagMedia(tag)
  }
}

watch(
  filteredTags,
  () => {
    ensureTagMediaForVisible()
  },
  { flush: 'post' }
)

function onSearchFocus() {
  if (props.guest) openAuthModal('login')
}

function onSearchKeydown(e) {
  if (props.guest) return
  if (e.key === 'Escape') {
    e.preventDefault()
    searchInput.value = ''
    clearConfirmedSearch()
    searchStatus.value = 'idle'
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    commitSearch(searchInput.value)
  }
}

const isActive = ref(false)

</script>
<template>
  <nav :class="['fixed top-0 left-20 w-full z-50', 'backdrop-blur-sm']">
    <div class="flex items-center justify-between px-6 py-2 gap-3">
      <div class="relative flex-1 overflow-visible">
        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('home.search.placeholder')"
          :readonly="guest"
          autocomplete="off"
          :class="[
            'transition-all duration-300 cursor-text bg-white bg-opacity-20 backdrop-blur-sm text-black',
            'text-md rounded-3xl block w-full py-3 pl-12 pr-10 outline-none border border-black',
            'focus:shadow-lg focus:shadow-blue-500/50',
          ]"
          @focus="onSearchFocus"
          @click="guest && openAuthModal('login')"
          @keydown="onSearchKeydown"
        />
        <div class="absolute left-1 top-4 pl-3 flex items-center pointer-events-none">
          <i class="pi pi-search text-black"></i>
        </div>
      </div>
      <button
        v-if="!guest"
        type="button"
        class="shrink-0 mr-20 px-5 py-2.5 rounded-3xl bg-black text-white text-sm font-semibold hover:bg-gray-800"
        @click="commitSearch(searchInput)"
      >
        {{ t('home.search.searchButton') }}
      </button>
      <button
        v-else
        type="button"
        class="shrink-0 mr-20 px-5 py-2.5 rounded-3xl bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
        @click="openAuthModal('login')"
      >
        {{ t('home.loginButton') }}
      </button>
    </div>
  </nav>

  <div v-if="redirecting"
    class="fixed inset-0 bg-black bg-opacity-40 z-50 items-center justify-center flex flex-col gap-20">
    <img src="/logo.png" alt="Logo" class="w-24 h-24 logo bg-white rounded-full" />
  </div>

  
  <div
    v-if="!guest"
    ref="tagsContainer"
    class="mt-16 ml-20 group fixed top-0 right-0 left-0 z-20 backdrop-blur-sm"
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
            <img
              v-if="tag.isImage && tag.file"
              :src="tag.file"
              :alt="t('home.tagImageAlt')"
              class="w-full h-full object-cover rounded-full fade-in fade-in-animation"
            />
            <video
              v-else-if="tag.file && tag.isImage === false"
              :src="tag.file"
              @mouseover="tag.videoPlayer && tag.videoPlayer.play()"
              :ref="(el) => { if (el) tag.videoPlayer = el }"
              class="w-full h-full object-cover rounded-full fade-in fade-in-animation"
              autoplay
              loop
              muted
            />
            <div
              v-else
              class="bg-gray-100 w-full h-full object-cover rounded-full animate-pulse"
            />
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
    :class="guest ? 'ml-20 mt-20 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 feed-density-gap' : 'ml-20 mt-28 mr-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 feed-density-gap'"
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
  <PinsBySearch
    class="mt-28"
    v-if="showSearchPins"
    :value="searchValue"
    :tag-id="searchTagId"
    :author-id="searchAuthorId"
  />
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