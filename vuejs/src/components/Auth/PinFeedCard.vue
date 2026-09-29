<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import axios from 'axios';
import { fetchPinMediaUrl, getCachedPinMediaUrl } from '@/composables/usePinMediaCache';
import {
  getCachedFeedMeta,
  patchFeedMeta,
  prefetchFeedMeta,
} from '@/composables/usePinFeedMeta';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';

const props = defineProps({
  pin: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['pinLoaded']);

const router = useRouter();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();
const rootEl = ref(null);
const mediaUrl = ref(getCachedPinMediaUrl(props.pin.id));
const username = ref(null);
const likesCount = ref(0);
const commentsCount = ref(0);
const liked = ref(false);
const likeBusy = ref(false);
const mediaStarted = ref(!!mediaUrl.value);

let observer = null;

function applyMeta(meta) {
  if (!meta) return;
  username.value = meta.username ?? null;
  likesCount.value = Number(meta.likes_count) || 0;
  liked.value = !!meta.liked;
  commentsCount.value = Number(meta.comments_count) || 0;
}

async function ensureMeta() {
  const cached = getCachedFeedMeta(props.pin.id);
  if (cached) {
    applyMeta(cached);
    return;
  }
  try {
    await prefetchFeedMeta([props.pin.id]);
    applyMeta(getCachedFeedMeta(props.pin.id));
  } catch (e) {
    console.error(e);
  }
}

async function loadMedia() {
  if (mediaStarted.value && mediaUrl.value) return;
  mediaStarted.value = true;
  try {
    const url = await fetchPinMediaUrl(props.pin.id);
    mediaUrl.value = url;
  } catch (e) {
    console.error(e);
    mediaStarted.value = false;
    emit('pinLoaded');
  }
}

function onVisible(entries) {
  const entry = entries[0];
  if (!entry?.isIntersecting) return;
  loadMedia();
  if (observer && rootEl.value) {
    observer.unobserve(rootEl.value);
  }
}

async function toggleLike(e) {
  e.preventDefault();
  e.stopPropagation();
  if (!userStore.isAuthenticated) {
    openAuthModal('login');
    return;
  }
  if (likeBusy.value) return;
  likeBusy.value = true;
  try {
    if (liked.value) {
      await axios.delete(`/api/likes/pin/${props.pin.id}`);
      liked.value = false;
      likesCount.value = Math.max(0, likesCount.value - 1);
    } else {
      await axios.post(`/api/likes/pin/${props.pin.id}`);
      liked.value = true;
      likesCount.value += 1;
    }
    patchFeedMeta(props.pin.id, {
      liked: liked.value,
      likes_count: likesCount.value,
    });
  } catch (err) {
    if (err.response?.status === 409) {
      liked.value = true;
      patchFeedMeta(props.pin.id, { liked: true });
    } else {
      console.error(err);
    }
  } finally {
    likeBusy.value = false;
  }
}

function goProfile(e) {
  e.preventDefault();
  e.stopPropagation();
  if (!userStore.isAuthenticated) {
    openAuthModal('login');
    return;
  }
  if (username.value) {
    router.push(`/user/${username.value}`);
  }
}

function onPinNavigate(e) {
  if (!userStore.isAuthenticated) {
    e.preventDefault();
    openAuthModal('login');
  }
}

function onImgLoad() {
  emit('pinLoaded');
}

onMounted(() => {
  applyMeta(getCachedFeedMeta(props.pin.id));
  ensureMeta();

  if (mediaUrl.value) {
    return;
  }
  if (typeof IntersectionObserver === 'undefined') {
    loadMedia();
    return;
  }
  observer = new IntersectionObserver(onVisible, {
    root: null,
    rootMargin: '240px 0px',
    threshold: 0.01,
  });
  if (rootEl.value) observer.observe(rootEl.value);
});

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  // Do not revoke blob URL — shared cache reuses it.
});

watch(
  () => props.pin.id,
  (id) => {
    mediaUrl.value = getCachedPinMediaUrl(id);
    mediaStarted.value = !!mediaUrl.value;
    applyMeta(getCachedFeedMeta(id));
    ensureMeta();
  }
);
</script>

<template>
  <div ref="rootEl" class="w-full p-2">
    <RouterLink
      :to="`/pin/${pin.id}`"
      class="block group relative w-full aspect-[3/4] rounded-2xl overflow-hidden border border-gray-100"
      :style="{ backgroundColor: pin.rgb || '#ffffff' }"
      @click="onPinNavigate"
    >
      <div
        v-if="!mediaUrl"
        class="absolute inset-0 animate-pulse"
        :style="{ backgroundColor: pin.rgb || '#e5e7eb' }"
      />
      <img
        v-else
        :src="mediaUrl"
        :alt="pin.title || 'Pin'"
        class="absolute inset-0 w-full h-full object-contain"
        @load="onImgLoad"
      />

      <div
        class="absolute inset-x-0 bottom-0 px-3 py-2 flex items-center gap-3 text-white text-sm
               bg-black/50 backdrop-blur-[1px]
               opacity-0 group-hover:opacity-100 transition-opacity duration-150"
      >
        <button
          type="button"
          class="truncate font-medium hover:underline max-w-[45%] text-left"
          @click="goProfile"
        >
          {{ username || '…' }}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1 shrink-0 hover:scale-105 transition-transform"
          :disabled="likeBusy"
          @click="toggleLike"
        >
          <i :class="liked ? 'pi pi-heart-fill' : 'pi pi-heart'" />
          <span>{{ likesCount }}</span>
        </button>
        <span
          class="inline-flex items-center gap-1 shrink-0 ml-auto opacity-90"
          @click="onPinNavigate"
        >
          <i class="pi pi-comment" />
          <span>{{ commentsCount }}</span>
        </span>
      </div>
    </RouterLink>
  </div>
</template>
