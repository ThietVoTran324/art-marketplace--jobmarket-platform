<script setup>
import { onMounted, ref, watch, onActivated, onDeactivated, computed, nextTick, onBeforeUnmount } from 'vue';
import { useRoute, RouterLink, useRouter, onBeforeRouteUpdate } from 'vue-router';
import axios from 'axios'
import RelatedPins from '@/components/Auth/RelatedPins.vue';
import PinLikesPopover from '@/components/Auth/PinLikesPopover.vue';
import CommentSection from '@/components/Auth/CommentSection.vue';
import PinLikesSection from '@/components/Auth/PinLikesSection.vue';

import { useToast } from "vue-toastification";

import EmojiPicker from 'vue3-emoji-picker'

import SearchBar from '@/components/Auth/SearchBar.vue';
import SavePinSheet from '@/components/Auth/SavePinSheet.vue';
import SharePinSheet from '@/components/Auth/SharePinSheet.vue';
import { useI18n } from 'vue-i18n'

import { useUnreadMessagesStore } from "@/stores/unreadMessages";
import { useUnavailableContentStore } from '@/stores/unavailableContent';

const unreadMessagesStore = useUnreadMessagesStore();
const unavailableStore = useUnavailableContentStore();
const { t } = useI18n()

const relatedObserverTarget = ref(null)
const showMoreExplore = ref(true)

const showExplore = ref(false)

const toast = useToast();

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";
import { authUserStore } from "@/stores/authUserStore";

const unreadUpdatesStore = useUnreadUpdatesStore();
const authStore = authUserStore();

const route = useRoute();
const router = useRouter();

const pinId = route.params.id

const showPicker = ref(false)

const videoPlayer = ref(null);
const isPlaying = ref(true);
const volume = ref(0);
const oldVolume = ref(null)
const currentTime = ref(0);
const duration = ref(0);

const showLikeAnimation = ref(null)
const showDislikeAnimation = ref(null)

const isLoading = ref(null);

const sendComment = ref(false)

// onBeforeRouteUpdate(async (to, from, next) => {
//   if (to.name !== 'home') {
//     await router.push({ name: 'home' });

//     await nextTick();

//     router.push(to.fullPath);
//   } else {
//     next();
//   }
// });

const onVideoLoad = () => {
  pinVideoLoaded.value = true;
  if (videoPlayer.value) {
    videoPlayer.value.volume = volume.value;
    duration.value = videoPlayer.value.duration;
    videoPlayer.value.play();
  }
};

const togglePlayPause = () => {
  if (!videoPlayer.value) return;
  if (isPlaying.value) {
    videoPlayer.value.pause();
  } else {
    videoPlayer.value.play();
  }
  isPlaying.value = !isPlaying.value;
};

const changeVolume = () => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = volume.value;
  }
};

const muteUnmute = () => {
  if (videoPlayer.value.volume == 0) {
    volume.value = oldVolume.value
    videoPlayer.value.volume = volume.value
  } else {
    videoPlayer.value.volume = 0;
    oldVolume.value = volume.value;
    volume.value = 0;
  }
};

const inputAddComment = ref(null)

const updateProgress = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime;
  }
};

const seek = () => {
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = currentTime.value;
  }
};

const formatTime = (time) => {
  const minutes = Math.floor(time / 60);
  const seconds = Math.floor(time % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
};

const onVideoEnd = () => {
  isPlaying.value = false;
};

onActivated(() => {
  createObserver()
  if (authStore.authUserId) {
    loadMarketplace()
  }
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;
  let name = null
  if (pin.value.title) {
    name = pin.value.title
  } else {
    name = t('pin.pinView.documentTitleFallback')
  }
  if (totalUnread > 0) {
    document.title = `(${totalUnread}) ${name}`;
  } else {
    document.title = name;
  }

  if (videoPlayer.value) {
    videoPlayer.value.volume = volume.value;
    var playPromise = videoPlayer.value.play()
    if (playPromise !== undefined) {
      playPromise.then(_ => {
        // Automatic playback started!
        // Show playing UI.
      })
        .catch(error => {
          // Auto-play was prevented
          // Show paused UI.
        });
    }
    isPlaying.value = true;
    showControls.value = true
    timeoutWorking.value = true
    timeoutId.value = setTimeout(() => {
      showControls.value = false
      timeoutWorking.value = false
    }, 2000);
  }
});

onDeactivated(() => {
  destroyObserver()
  if (videoPlayer.value) {
    videoPlayer.value.pause();
    isPlaying.value = false;
  }
});

const pin = ref({
  id: null,
  user_id: null,
  title: '',
  description: '',
  href: '',
  image: '',
  rgb: '',
  height: '',
});

const pinImage = ref(null)
const pinImageLoaded = ref(false)
const pinVideoLoaded = ref(false)
const pinVideo = ref(null)
const pinUser = ref(null)
const pinUserImage = ref(null)

const cntLikes = ref(null)
const checkUserLike = ref(null)

const cntComments = ref(null)

const showCommets = ref(false)

const showPopover = ref(false); // State to control the popover visibility

const insidePopover = ref(false)

const bgSave = ref('bg-red-700')
const saveText = ref('')
const isSaveSheetOpen = ref(false)
const isShareSheetOpen = ref(false)

function openSaveSheet() {
  if (!authStore.authUserId) return
  saveText.value = t('common.save')
  isSaveSheetOpen.value = true
}

function openShareSheet() {
  if (!authStore.authUserId) return
  isShareSheetOpen.value = true
}

function onSaveDone() {
  saveText.value = t('pin.saved')
  cntSaves.value = (Number(cntSaves.value) || 0) + 1
}

function onSaveError(error) {
  if (error?.response?.status === 409) {
    saveText.value = t('pin.alreadySaved')
  } else {
    saveText.value = t('common.save')
    console.error(error)
  }
}

const isPinOwner = computed(() => {
  return pin.value && authStore.authUserId && pin.value.user_id === authStore.authUserId
})

async function downloadOriginal() {
  if (!pin.value) return
  try {
    const meta = await axios.get(`/api/pins/original/${pin.value.id}`)
    const url = meta.data.url
    const response = await axios.get(`/api${url}`, { responseType: 'blob' })
    const blobUrl = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `pin-${pin.value.id}-original`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(blobUrl)
  } catch (error) {
    console.error(error)
    toast.error(t('pin.pinView.toastCannotDownload'))
  }
}

const eligibility = ref(null)
const listing = ref(null)
const purchaseState = ref({ state: 'none' })
const buying = ref(false)
const listPriceMajor = ref('5.00')
const listCurrency = ref('USD')
const listAttestation = ref(false)
const copyrightReason = ref('')
const showCopyrightReport = ref(false)
const showSellFieldsModal = ref(false)
const showSellerGateModal = ref(false)
const cntSaves = ref(0)
const cntViews = ref(0)

const isSeller = computed(() => authStore.hasRole('seller'))
const isListed = computed(() => listing.value && listing.value.status === 'listed')
const canSell = computed(
  () => isPinOwner.value && authStore.canSellOnMarketplace
)
const canBuy = computed(
  () =>
    isListed.value &&
    !isPinOwner.value &&
    authStore.authUserId &&
    authStore.canBuyLicense &&
    purchaseState.value.state !== 'owned'
)
const hasPendingPurchase = computed(() => purchaseState.value.state === 'pending')
const buyCtaLabel = computed(() => {
  if (buying.value) return t('pin.opening')
  if (hasPendingPurchase.value) return t('pin.continuePayment')
  return t('pin.buyLicense')
})
const saveButtonLabel = computed(() => saveText.value || t('common.save'))

async function loadEngagement() {
  if (!pin.value?.id) return
  try {
    const r = await axios.get(`/api/pins/${pin.value.id}/engagement`)
    cntLikes.value = r.data.likes_count ?? cntLikes.value
    cntSaves.value = r.data.saves_count ?? 0
    cntViews.value = r.data.views_count ?? 0
  } catch (error) {
    console.error(error)
  }
}

async function onSellDollarClick() {
  if (!eligibility.value) {
    try {
      const r = await axios.get('/api/marketplace/me/eligibility')
      eligibility.value = r.data
    } catch (error) {
      console.error(error)
    }
  }
  if (eligibility.value?.eligible) {
    if (!isSeller.value) {
      await enableSelling()
      if (!authStore.hasRole('seller')) return
    }
    showSellFieldsModal.value = true
    return
  }
  showSellerGateModal.value = true
}

function agreeGoSellerSettings() {
  showSellerGateModal.value = false
  router.push({ path: '/settings', query: { tab: 'selling' } })
}

function formatListingPrice(row) {
  if (!row) return ''
  return `${row.currency} ${(row.price_minor / 100).toFixed(2)}`
}

async function loadMarketplace() {
  try {
    const r = await axios.get(`/api/marketplace/pins/${pinId}/listing`)
    listing.value = r.data
  } catch (error) {
    listing.value = null
  }
  if (authStore.authUserId) {
    try {
      const r = await axios.get(`/api/marketplace/pins/${pinId}/purchase-state`)
      purchaseState.value = r.data || { state: 'none' }
    } catch (error) {
      purchaseState.value = { state: 'none' }
    }
  }
  if (authStore.authUserId && pin.value && pin.value.user_id === authStore.authUserId) {
    try {
      const r = await axios.get('/api/marketplace/me/eligibility')
      eligibility.value = r.data
    } catch (error) {
      console.error(error)
    }
  }
}

async function buyLicense() {
  if (!pin.value || buying.value) return
  buying.value = true
  try {
    const url = router.resolve({
      name: 'checkout-pin',
      params: { pinId: String(pin.value.id) },
    }).href
    const opened = window.open(url, '_blank', 'noopener,noreferrer')
    if (!opened) {
      await router.push({ name: 'checkout-pin', params: { pinId: String(pin.value.id) } })
    }
  } catch (error) {
    console.error(error)
    toast.error(t('pin.pinView.toastCannotCheckout'))
  } finally {
    buying.value = false
  }
}

async function enableSelling() {
  try {
    const r = await axios.post('/api/marketplace/me/enable-selling')
    authStore.setRoles(r.data.roles)
    await loadMarketplace()
    toast.success(t('pin.pinView.toastSellingEnabled'))
  } catch (error) {
    console.error(error)
    toast.error(t('pin.eligibilityNotMet'))
    if (error.response?.data?.detail?.eligibility) {
      eligibility.value = error.response.data.detail.eligibility
    }
  }
}

async function listPinForSale() {
  if (!listAttestation.value) {
    toast.error(t('pin.pinView.toastConfirmSellRights'))
    return
  }
  try {
    const price_minor = Math.round(parseFloat(listPriceMajor.value) * 100)
    const r = await axios.post(`/api/marketplace/pins/${pin.value.id}/listing`, {
      price_minor,
      currency: listCurrency.value,
      attestation_accepted: true,
    })
    listing.value = r.data
    showSellFieldsModal.value = false
    toast.success(t('pin.pinView.toastListed'))
  } catch (error) {
    console.error(error)
    toast.error(error.response?.data?.detail || t('pin.pinView.toastCannotList'))
  }
}

async function unlistPin() {
  try {
    const r = await axios.patch(`/api/marketplace/listings/${listing.value.id}`, {
      status: 'unlisted',
    })
    listing.value = r.data
    showSellFieldsModal.value = false
    toast.success(t('pin.pinView.toastUnlisted'))
  } catch (error) {
    console.error(error)
    toast.error(t('pin.pinView.toastCannotUnlist'))
  }
}

async function submitCopyrightReport() {
  if (!copyrightReason.value.trim()) {
    toast.error(t('pin.pinView.toastEnterReason'))
    return
  }
  try {
    await axios.post(`/api/marketplace/pins/${pin.value.id}/copyright-reports`, {
      reason: copyrightReason.value.trim(),
    })
    copyrightReason.value = ''
    showCopyrightReport.value = false
    toast.success(t('pin.pinView.toastReportSubmitted'))
  } catch (error) {
    console.error(error)
    toast.error(error.response?.data?.detail || t('pin.pinView.toastReportFailed'))
  }
}

const comment = ref('')

const mediaFile = ref(null)
const mediaPreview = ref(null);
const isImage = ref(false);
const isVideo = ref(false);

const bgColors = ref(['bg-red-200', 'bg-orange-200', 'bg-amber-200', 'bg-lime-200', 'bg-green-200', 'bg-emerald-200', 'bg-teal-200', 'bg-sky-200', 'bg-blue-200', 'bg-indigo-200', 'bg-violet-200', 'bg-purple-200', 'bg-fuchsia-200', 'bg-pink-200', 'bg-rose-200'])
const tags = ref([])

const timeoutId = ref(null)
const timeoutWorking = ref(false)

const auth_user_id = ref(null)

let observer

const createObserver = () => {
  observer = new IntersectionObserver(
    ([entry]) => {
      showMoreExplore.value = entry.intersectionRatio < 0.2
    },
    { threshold: [0, 0.2, 1] }
  )

  if (relatedObserverTarget.value) {
    observer.observe(relatedObserverTarget.value)
  }
}

const destroyObserver = () => {
  if (observer && relatedObserverTarget.value) {
    observer.unobserve(relatedObserverTarget.value)
    observer.disconnect()
    observer = null
  }
}

onMounted(async () => {

  createObserver()

  try {
    const response = await axios.get(`/api/pins/${pinId}`);
    pin.value = response.data;

    let unreadMessagesCount = unreadMessagesStore.count;
    let unreadUpdatesCount = unreadUpdatesStore.count;
    let totalUnread = unreadMessagesCount + unreadUpdatesCount;
    let name = null
    if (pin.value.title) {
      name = pin.value.title
    } else {
      name = t('pin.pinView.documentTitleFallback')
    }
    if (totalUnread > 0) {
      document.title = `(${totalUnread}) ${name}`;
    } else {
      document.title = name;
    }

    try {
      const response = await axios.get(`/api/pins/upload/${pinId}`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(response.data);
      const contentType = response.headers['content-type'];
      if (contentType.startsWith('image/')) {
        pinImage.value = blobUrl;
      } else {
        pinVideo.value = blobUrl;
      }

    } catch (error) {
      console.error(error);
    }

    isLoading.value = true;

    await loadMarketplace()

    try {
      const response = await axios.get(`/api/users/user_id/${pin.value.user_id}`);
      pinUser.value = response.data;

      try {
        const response = await axios.get(`/api/users/upload/${pinUser.value.id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(response.data);
        pinUserImage.value = blobUrl;
      } catch (error) {
        console.log(error);
      }
    } catch (error) {
      console.log(error);
    }
  } catch (error) {
    unavailableStore.show();
    router.back();
  }

  showControls.value = true;
  timeoutWorking.value = true;
  timeoutId.value = setTimeout(() => {
    showControls.value = false;
    timeoutWorking.value = false;
  }, 2000);

  try {
    const response = await axios.get(`/api/likes/pin/likes/cnt/${pin.value.id}`);
    cntLikes.value = response.data;

  } catch (error) {
    console.error(error);
  }

  await loadEngagement()
  // Unique view is recorded async on GET /pins/{id}; refresh once more shortly
  setTimeout(() => {
    loadEngagement()
  }, 800)

  try {
    const response = await axios.get(`/api/likes/pin/user_like/${pin.value.id}`);
    checkUserLike.value = response.data;

  } catch (error) {
    console.error(error);
  }

  try {
    const response = await axios.get(`/api/tags/pin/tags/${pin.value.id}`, { withCredentials: true });
    tags.value = response.data;
    for (let i = 0; i < response.data.length; i++) {
      const tag = response.data[i];
      tag.color = randomBgColor();
    }

  } catch (error) {
    console.log(error);
  }

  try {
    const response = await axios.get(`/api/comments/cnt/comments/${pin.value.id}`);
    cntComments.value = response.data;

  } catch (error) {
    console.error(error);
  }

  if (cntComments.value) {
    showCommets.value = true;
  }

  // End the loading process
  isLoading.value = false;
});

onBeforeUnmount(() => {
  destroyObserver()
  document.removeEventListener('visibilitychange', onPinVisibility)
  document.removeEventListener('keydown', onFullscreenKeydown)
  document.removeEventListener('wheel', onLightboxWheel, { capture: true })
  document.body.style.overflow = ''
})

function onPinVisibility() {
  if (document.visibilityState === 'visible' && authStore.authUserId) {
    loadMarketplace()
  }
}

document.addEventListener('visibilitychange', onPinVisibility)

const isTop = ref(false)

function loadPicker() {
  if (showPicker.value === false) {
    const element = inputAddComment.value;
    if (element) {
      const rect = element.getBoundingClientRect();
      const distanceToBottom = window.innerHeight - rect.bottom;
      if (distanceToBottom < 320) {
        isTop.value = false
      } else {
        isTop.value = true
      }
    }
  }
}

const goBack = () => {
  // Prefer in-app history; otherwise land on main feed (no empty-stack / leave-site).
  if (window.history.state?.back != null) {
    router.back()
    return
  }
  router.push({ name: 'home' })
}

function goForward() {
  router.go(1);
}

const randomBgColor = () => {
  const randomIndex = Math.floor(Math.random() * bgColors.value.length);
  return bgColors.value[randomIndex];
};

async function likePin() {
  if (checkUserLike.value) {
    try {
      await axios.delete(`/api/likes/pin/${pin.value.id}`)
      showDislikeAnimation.value = true
      showLikeAnimation.value = false
      checkUserLike.value = false
      cntLikes.value -= 1
    } catch (error) {
      console.log(error)
    }
  } else {
    try {
      await axios.post(`/api/likes/pin/${pin.value.id}`)
      showLikeAnimation.value = true
      showDislikeAnimation.value = false
      checkUserLike.value = true
      cntLikes.value += 1
    } catch (error) {
      console.log(error)
    }
  }
}

function handleMediaUpload(event) {
  const file = event.target.files[0];

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp', 'video/mp4', 'video/webm'];
  if (file) {

    if (!allowedTypes.includes(file.type)) {
      toast.warning(t('pin.pinView.toastInvalidMedia'), { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
      return;
    }

    if (file.type.startsWith("video/")) {
      const video = document.createElement("video");
      video.preload = "metadata";

      video.onloadedmetadata = () => {
        window.URL.revokeObjectURL(video.src);

        if (video.duration > 30) {
          toast.warning(t('pin.pinView.toastVideoMaxDuration'), {
            position: "top-center",
            bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
          });
          return;
        }

        previewFile(file);
      };

      video.src = URL.createObjectURL(file);
    } else {
      previewFile(file);
    }
  }
}

const previewFile = (file) => {
  mediaFile.value = file;
  const reader = new FileReader();

  reader.onload = (e) => {
    mediaPreview.value = e.target.result;
  };

  reader.readAsDataURL(file);

  if (file.type.startsWith("image/")) {
    isImage.value = true;
    isVideo.value = false;
  } else if (file.type.startsWith("video/")) {
    isImage.value = false;
    isVideo.value = true;
  }
};

const sendCommentError = ref(false)

async function addComment() {
  if (comment.value.trim() !== '' && !mediaFile.value) {
    sendComment.value = true
    showPicker.value = false
    try {
      const response = await axios.post(`/api/comments/${pin.value.id}`, {
        content: comment.value.trim()
      })
      comment.value = ''

      cntComments.value += 1
      showCommets.value = false
      await nextTick()
      showCommets.value = true
      sendComment.value = false
      return;

    } catch (error) {
      console.error(error)
    }
  }

  if (mediaFile.value) {
    sendComment.value = true
    showPicker.value = false
    try {
      const formData = new FormData();
      formData.append("file", mediaFile.value);

      const jsonData = JSON.stringify({
        content: comment.value.trim()
      });

      formData.append("comment_model", jsonData);

      const response = await axios.post(`/api/comments/create-comment-on-pin-entity/${pin.value.id}`, formData, {
        withCredentials: true,
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      comment.value = ''
      cntComments.value += 1
      showCommets.value = false
      await nextTick()
      showCommets.value = true
      resetFile()
      sendComment.value = false

    } catch (error) {
      if (error.response.status === 415) {
        sendComment.value = false
        sendCommentError.value = true
      }
    }
  }
}

const showControls = ref(false)

function showTagsPin(tag) {
  router.push(`/?tag=${tag.name}`);
}

function resetFile() {
  mediaPreview.value = null
  mediaFile.value = null
  isImage.value = false
  isVideo.value = false
}

function onSelectEmoji(emoji) {
  comment.value += emoji.i
}

async function showVideoControls() {
  if (timeoutWorking.value) {
    clearTimeout(timeoutId.value)
  }
  showControls.value = true;
}

const pinImageRef = ref(null)

const showFollowing = ref(false)

const fullscreen = ref(false)
const lightboxZoom = ref(1)

function openImageFullScreen() {
  lightboxZoom.value = 1
  fullscreen.value = true
}

function closeFullscreen() {
  fullscreen.value = false
  lightboxZoom.value = 1
}

function onFullscreenKeydown(e) {
  if (e.key === 'Escape') closeFullscreen()
}

function onLightboxWheel(e) {
  if (!fullscreen.value) return
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  e.stopPropagation()
  const step = e.deltaY > 0 ? -0.12 : 0.12
  const next = Math.round((lightboxZoom.value + step) * 100) / 100
  lightboxZoom.value = Math.min(4, Math.max(0.5, next))
}

watch(fullscreen, (open) => {
  if (open) {
    document.addEventListener('keydown', onFullscreenKeydown)
    document.addEventListener('wheel', onLightboxWheel, { passive: false, capture: true })
    document.body.style.overflow = 'hidden'
  } else {
    document.removeEventListener('keydown', onFullscreenKeydown)
    document.removeEventListener('wheel', onLightboxWheel, { capture: true })
    document.body.style.overflow = ''
  }
})

const scrollToRelated = () => {
  relatedObserverTarget.value?.scrollIntoView({ behavior: 'smooth' })
}

const hoverImage = ref(false)
</script>

<template>

  <div v-if="showExplore === true && showMoreExplore" class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-30">
    <button @click="scrollToRelated"
      class="flex items-center gap-2 px-3 py-3 bg-white/60 backdrop-blur text-black rounded-full hover:bg-white transition-all duration-300 text-sm font-medium">
      {{ t('pin.moreToExplore') }}
      <svg class="w-4 h-4 text-black transition-transform group-hover:translate-y-1" fill="none" stroke="currentColor"
        stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  </div>

  <div v-if="sendCommentError" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black">{{ t('pin.pinView.invalidFileModal') }}</h3>
          <button @click="sendCommentError = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            {{ t('pin.pinView.okUnderstand') }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <SavePinSheet
    v-if="pin?.id"
    v-model:open="isSaveSheetOpen"
    :pin-id="pin.id"
    @saved="onSaveDone"
    @error="onSaveError"
  />
  <SharePinSheet
    v-if="pin?.id"
    v-model:open="isShareSheetOpen"
    :pin-id="pin.id"
  />

  <transition name="fade" appear>
    <div v-if="showFollowing" class="fixed inset-0 bg-black bg-opacity-75 z-50 p-6">
      <div class="flex justify-center items-center min-h-screen" @click.self="showFollowing = false">
        <PinLikesSection :pin_id="pin.id" :cnt_likes="cntLikes" />
        <i @click="showFollowing = false"
          class="absolute right-20 top-20 pi pi-times text-white text-4xl cursor-pointer transition-transform duration-200 transform hover:scale-150"
          style="text-shadow: 0 0 20px rgba(255, 255, 255, 0.9), 0 0 40px rgba(255, 255, 255, 0.8), 0 0 80px rgba(255, 255, 255, 0.7);"></i>
      </div>
    </div>
  </transition>
  <Teleport to="body">
    <div
      v-if="fullscreen && pinImage"
      class="fixed inset-0 z-[80] flex items-center justify-center"
      role="dialog"
      :aria-label="t('pin.pinView.expandedPinAria')"
    >
      <div class="absolute inset-0 bg-black/90" @click="closeFullscreen" />
      <button
        type="button"
        class="absolute top-4 left-4 z-50 w-11 h-11 rounded-full bg-white/90 hover:bg-white flex items-center justify-center shadow"
        :aria-label="t('pin.pinView.closeExpandedAria')"
        @click.stop="closeFullscreen"
      >
        <i class="pi pi-times text-2xl font-bold text-gray-800" />
      </button>
      <div class="absolute top-4 right-4 z-50 flex flex-row gap-2 items-center">
        <span class="px-3 py-1.5 text-xs font-medium bg-black/50 text-white rounded-full tabular-nums">
          {{ Math.round(lightboxZoom * 100) }}%
        </span>
        <button
          v-if="authStore.authUserId"
          type="button"
          class="px-4 py-2.5 text-sm bg-white/90 text-gray-900 rounded-3xl transition hover:scale-105 shadow"
          @click.stop="openShareSheet"
        >
          {{ t('common.share') }}
        </button>
        <button
          type="button"
          class="px-6 py-2.5 text-sm text-white rounded-3xl transition hover:scale-105 shadow"
          :style="{ backgroundColor: pin.rgb }"
          @click.stop="openSaveSheet"
        >
          {{ saveButtonLabel }}
        </button>
      </div>
      <!-- 80% viewport box: image scales up to hit height and/or width limit -->
      <div
        class="relative z-10 w-[80vw] h-[80vh] flex items-center justify-center overflow-visible pointer-events-none"
      >
        <img
          :src="pinImage"
          :alt="t('pin.pinView.expandedPinAlt')"
          class="max-w-full max-h-full w-full h-full object-contain rounded-3xl shadow-2xl select-none transition-transform duration-100 origin-center pointer-events-auto"
          :style="{ transform: `scale(${lightboxZoom})` }"
          draggable="false"
          @click.stop
        />
      </div>
    </div>
  </Teleport>
  <SearchBar />
  <button
    type="button"
    @click="goBack"
    class="fixed top-20 left-24 z-50 p-2 rounded-full text-gray-600 hover:bg-gray-100 hover:text-black hover:-translate-x-1 transition"
    :aria-label="t('pin.backToFeed')"
  >
    <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
    </svg>
  </button>
  <div class="ml-20 mt-20 pr-6">
    <div v-show="pinImageLoaded || pinVideoLoaded" class="grid grid-cols-2 gap-6 w-full h-[75vh] bg-gray-100 rounded-3xl overflow-hidden" :style="{
      boxShadow: `0 0 30px 15px ${pin.rgb}`
    }">
      <!-- Left Column: Image or Video — fills detail frame -->
      <div class="h-full min-h-0 flex flex-col items-center justify-center overflow-hidden p-3">
        <div
          v-if="pinImage"
          class="relative h-full w-full flex items-center justify-center"
          @mouseenter="hoverImage = true"
          @mouseleave="hoverImage = false"
        >
          <img ref="pinImageRef" :src="pinImage" :alt="t('pin.pinView.pinImageAlt')"
            class="max-h-full max-w-full w-auto h-auto object-contain rounded-3xl block"
            @load="pinImageLoaded = true" />
          <div v-if="pinImageLoaded" class="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            <div class="relative flex items-center justify-center w-12 h-12">
              <transition name="flash2">
                <i v-if="showDislikeAnimation"
                  class="absolute pi pi-heart text-8xl text-white glowing-icon opacity-0"></i>
              </transition>
              <transition name="flash2">
                <i v-if="showLikeAnimation"
                  class="absolute pi pi-heart-fill text-8xl text-white glowing-icon opacity-0"></i>
              </transition>
            </div>
          </div>
          <button
            v-if="pinImageLoaded && hoverImage"
            type="button"
            :title="t('pin.expand')"
            class="absolute top-3 right-3 z-10 w-10 h-10 rounded-full bg-white/90 hover:bg-white shadow flex items-center justify-center transition"
            @click.stop="openImageFullScreen"
          >
            <i class="pi pi-arrow-up-right-and-arrow-down-left-from-center rotate-90 text-lg text-gray-800" />
          </button>

          <div v-if="!isLoading && pin.href && hoverImage"
            class="absolute left-2 bottom-2 cursor-pointer font-semibold z-10">
            <a :href="pin.href" target="_blank" class="w-full inline-block">
              <div
                class="bg-white rounded-full bg-opacity-80 hover:bg-opacity-100 p-4 flex items-center justify-center transition-all duration-200 ease-in origin-right h-12">
                <i class="pi pi-arrow-up-right mr-2"></i>
                <span class="mr-2 transition-opacity duration-300 ease-in-out text-md text-nowrap truncate">
                {{ t('pin.visitSite') }}
                </span>
              </div>
            </a>
          </div>
        </div>
        <div
          v-if="pinVideo"
          class="relative h-full w-full flex items-center justify-center"
          @mouseover="showVideoControls"
          @mouseleave="showControls = false"
        >
          <!-- Video Element -->
          <video @click="togglePlayPause" :src="pinVideo" ref="videoPlayer"
            class="max-h-full max-w-full w-auto h-auto object-contain rounded-3xl block" loop @loadeddata="onVideoLoad" @timeupdate="updateProgress"
            @ended="onVideoEnd">
          </video>

          <!-- Gradient Overlay (cloud-like fade effect) -->
          <div v-if="pinVideoLoaded && showControls"
            class="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-red-900 to-transparent rounded-3xl">
          </div>

          <!-- Custom Controls -->
          <div v-if="pinVideoLoaded && showControls"
            class="absolute bottom-10 left-4 right-4 flex items-center justify-between text-white">
            <!-- Left Controls (Play/Pause and Time Info) -->
            <div class="flex items-center gap-3">
              <i v-if="isPlaying" @click="togglePlayPause" class="pi pi-pause cursor-pointer text-xl"></i>
              <i v-if="!isPlaying" @click="togglePlayPause" class="pi pi-play cursor-pointer text-xl"></i>
              <span class="text-md">
                {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
              </span>
            </div>

            <!-- Right Controls (Mute/Unmute and Volume Slider) -->
            <div class="flex items-center gap-3 text-white">
              <i v-if="volume == 0" @click="muteUnmute" class="pi pi-volume-off  text-xl"></i>
              <i v-if="volume != 0" @click="muteUnmute" class="pi pi-volume-up  text-xl"></i>
              <input type="range" class="w-20 h-0.5 bg-black rounded-lg cursor-pointer accent-white " min="0" max="1"
                step="0.0005" v-model="volume" @input="changeVolume" />
            </div>
          </div>

          <!-- Progress Bar -->
          <div v-if="showControls && pinVideoLoaded" class="absolute bottom-4 left-4 right-4">
            <input type="range" class="w-full h-0.5 bg-black rounded-lg cursor-pointer accent-white" :max="duration"
              min="0" step="0.01" v-model="currentTime" @input="seek" />
          </div>

          <!-- Center Play/Pause Button with Gradient Overlay -->
          <div v-if="showControls && pinVideoLoaded"
            class="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div class="relative flex items-center justify-center w-12 h-12">
              <transition name="flash">
                <i v-if="isPlaying" @click="togglePlayPause"
                  class="absolute pi pi-pause text-5xl text-white glowing-icon"></i>
              </transition>
              <transition name="flash">
                <i v-if="!isPlaying" @click="togglePlayPause"
                  class="absolute pi pi-play text-5xl text-white glowing-icon"></i>
              </transition>
            </div>
          </div>

          <div v-if="pinVideoLoaded" @click="togglePlayPause"
            class="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div class="relative flex items-center justify-center w-12 h-12">
              <transition name="flash2">
                <i v-if="showDislikeAnimation"
                  class="absolute pi pi-heart text-8xl text-white glowing-icon opacity-0"></i>
              </transition>
              <transition name="flash2">
                <i v-if="showLikeAnimation"
                  class="absolute pi pi-heart-fill text-8xl text-white glowing-icon opacity-0"></i>
              </transition>
            </div>
          </div>
        </div>

      </div>

      <!-- Right Column: User Information -->

      <div v-if="pinImageLoaded || pinVideoLoaded" v-show="isLoading" class="flex flex-col">
        <div class="flex items-center justify-center w-full h-full p-2">
          <span class="text-center loader2"></span>
        </div>
      </div>

      <div v-show="!isLoading" class="flex flex-col min-h-0 h-full overflow-hidden">
        <div class="flex-shrink-0 flex items-center justify-between w-full p-2">
          <!-- Engagement: likes / saves / unique views -->
          <div class="flex items-center gap-5 relative flex-wrap">
            <div class="flex items-center gap-2 relative">
              <i v-if="checkUserLike" @click="likePin" :style="{ color: pin.rgb }"
                class="pi pi-heart-fill text-2xl cursor-pointer transition-transform duration-200 transform hover:scale-150"></i>
              <i v-if="!checkUserLike" @click="likePin" :style="{ color: pin.rgb }"
                class="pi pi-heart text-2xl cursor-pointer transition-transform duration-200 transform hover:scale-150"></i>
              <div @click="showFollowing = !showFollowing"
                class="font-bold text-xl relative cursor-pointer tabular-nums" @mouseover="showPopover = true"
                @mouseleave="if (!insidePopover) showPopover = false;">
                <span :style="{ color: pin.rgb }">{{ cntLikes ?? 0 }}</span>
                <div v-if="showPopover && cntLikes" @mouseover="insidePopover = true"
                  @mouseleave="insidePopover = false; showPopover = false" class="absolute top-[30px] left-[-50px] z-50">
                  <PinLikesPopover :pin_id="pin.id" />
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 text-gray-800" :title="t('pin.pinView.savesTitle')">
              <i class="pi pi-bookmark text-xl" />
              <span class="font-bold text-xl tabular-nums">{{ cntSaves ?? 0 }}</span>
            </div>
            <div class="flex items-center gap-2 text-gray-800" :title="t('pin.pinView.uniqueViewsTitle')">
              <i class="pi pi-eye text-xl" />
              <span class="font-bold text-xl tabular-nums">{{ cntViews ?? 0 }}</span>
            </div>
          </div>

          <div class="flex flex-row gap-1 items-center">
            <button
              v-if="canSell"
              type="button"
              class="p-2 rounded-full text-gray-700 hover:bg-emerald-50 hover:text-emerald-700 transition"
              :title="isListed ? t('pin.pinView.listedTitle', { price: formatListingPrice(listing) }) : t('pin.pinView.sellLicenseTitle')"
              @click="onSellDollarClick"
            >
              <CircleDollarSign class="w-5 h-5" />
            </button>
            <button
              v-if="authStore.authUserId"
              type="button"
              @click="openShareSheet"
              class="px-4 py-3 text-sm bg-white text-gray-900 rounded-3xl border border-gray-300 hover:bg-gray-50 transition"
            >
              {{ t('common.share') }}
            </button>
            <button @click="openSaveSheet" :style="{
              backgroundColor: pin.rgb,
            }" :class="`px-6 py-3 text-sm text-white rounded-3xl transition transform hover:scale-105`">
              {{ saveButtonLabel }}
            </button>
            <button
              v-if="isPinOwner && pin.has_original"
              @click="downloadOriginal"
              class="px-6 py-3 text-sm bg-white text-gray-900 rounded-3xl border border-gray-300 hover:bg-gray-50 transition"
            >
              {{ t('pin.downloadOriginal') }}
            </button>
            <button
              v-if="authStore.authUserId && !isPinOwner"
              type="button"
              :title="t('pin.pinView.reportTitle')"
              class="relative group ml-1 w-8 h-8 flex items-center justify-center rounded-full hover:bg-red-50 transition"
              @click="showCopyrightReport = !showCopyrightReport"
            >
              <svg viewBox="0 0 24 24" class="w-5 h-5 text-red-600" aria-hidden="true">
                <path fill="currentColor" d="M12 2L1 21h22L12 2zm0 4.5l7.5 13H4.5L12 6.5z" />
                <rect x="11" y="10" width="2" height="5" fill="white" />
                <rect x="11" y="16.5" width="2" height="2" fill="white" />
              </svg>
              <span
                class="pointer-events-none absolute top-full mt-1 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black text-white text-xs px-2 py-0.5 opacity-0 group-hover:opacity-100 transition"
              >
                Report
              </span>
            </button>
          </div>

        </div>
        <div class="flex-1 min-h-0 overflow-y-auto pr-2">
        <div v-if="pin.title">
          <span :style="{ color: pin.rgb }" class="font-bold text-2xl">{{ pin.title }}</span>
        </div>
        <div v-if="isListed" class="mt-2 flex flex-wrap items-center gap-2">
          <span class="inline-block px-3 py-1 rounded-full bg-emerald-100 text-emerald-900 text-sm font-medium">
            {{ t('pin.forSale') }} · {{ formatListingPrice(listing) }} · {{ t('pin.personalUse') }}
          </span>
          <button
            v-if="canBuy"
            type="button"
            :disabled="buying"
            class="px-3 py-1 text-sm rounded-full bg-gray-900 text-white hover:bg-black disabled:opacity-50"
            @click="buyLicense"
          >
            {{ buyCtaLabel }}
          </button>
          <span
            v-if="!isPinOwner && hasPendingPurchase"
            class="text-sm text-amber-700"
          >
            {{ t('pin.paymentPending') }}
          </span>
          <span
            v-if="!isPinOwner && purchaseState.state === 'owned'"
            class="text-sm text-emerald-700"
          >
            {{ t('pin.licenseOwned') }}
          </span>
          <button
            v-if="!isPinOwner && purchaseState.state === 'owned' && pin.has_original"
            type="button"
            class="px-3 py-1 text-sm rounded-full bg-white border border-gray-300"
            @click="downloadOriginal"
          >
            {{ t('pin.downloadOriginal') }}
          </button>
        </div>

        <!-- Eligible: set listing fields -->
        <div
          v-if="showSellFieldsModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          @click.self="showSellFieldsModal = false"
        >
          <div class="w-full max-w-md bg-white rounded-2xl border border-gray-200 p-5 space-y-3 shadow-xl">
            <div class="flex items-center justify-between">
              <h4 class="font-semibold text-lg">{{ t('pin.listForSale') }}</h4>
              <button type="button" class="p-1 rounded-full hover:bg-gray-100" @click="showSellFieldsModal = false">
                <i class="pi pi-times" />
              </button>
            </div>
            <div class="flex gap-2 items-center flex-wrap">
              <input v-model="listPriceMajor" type="number" min="0.01" step="0.01" class="border rounded-lg px-3 py-2 w-28" />
              <select v-model="listCurrency" class="border rounded-lg px-3 py-2">
                <option value="USD">USD</option>
                <option value="VND">VND</option>
              </select>
            </div>
            <label class="flex items-start gap-2 text-xs text-gray-700">
              <input v-model="listAttestation" type="checkbox" class="mt-0.5" />
              <span>
                {{ t('pin.pinView.listAttestation') }}
              </span>
            </label>
            <div class="flex flex-wrap gap-2 pt-1">
              <button type="button" @click="listPinForSale" class="px-4 py-2 bg-emerald-700 text-white rounded-xl text-sm">
                {{ isListed ? t('pin.updateListing') : t('pin.listForSale') }}
              </button>
              <button
                v-if="listing"
                type="button"
                @click="unlistPin"
                class="px-4 py-2 bg-white border rounded-xl text-sm"
              >
                {{ t('pin.pinView.unlist') }}
              </button>
              <button
                type="button"
                class="px-4 py-2 bg-white border rounded-xl text-sm"
                @click="showSellFieldsModal = false"
              >
                {{ t('pin.pinView.cancel') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Not eligible: ask to open seller settings -->
        <div
          v-if="showSellerGateModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          @click.self="showSellerGateModal = false"
        >
          <div class="w-full max-w-sm bg-white rounded-2xl border border-gray-200 p-5 space-y-4 shadow-xl">
            <h4 class="font-semibold text-lg">{{ t('pin.pinView.sellerGateTitle') }}</h4>
            <p class="text-sm text-gray-600">
              {{ t('pin.pinView.sellerGateBody') }}
            </p>
            <div class="flex justify-end gap-2">
              <button
                type="button"
                class="px-4 py-2 border rounded-xl text-sm"
                @click="showSellerGateModal = false"
              >
                {{ t('pin.pinView.cancel') }}
              </button>
              <button
                type="button"
                class="px-4 py-2 bg-gray-900 text-white rounded-xl text-sm"
                @click="agreeGoSellerSettings"
              >
                {{ t('pin.pinView.agree') }}
              </button>
            </div>
          </div>
        </div>
        <div
          v-if="authStore.authUserId && !isPinOwner && showCopyrightReport"
          class="mt-3 mr-5 p-3 bg-white rounded-2xl border border-red-200 space-y-2"
        >
          <textarea
            v-model="copyrightReason"
            rows="2"
            class="w-full border rounded-lg px-3 py-2 text-sm"
            :placeholder="t('pin.pinView.copyrightPlaceholder')"
          />
          <div class="flex gap-2">
            <button
              type="button"
              class="px-3 py-1.5 text-sm rounded-xl bg-red-600 text-white"
              @click="submitCopyrightReport"
            >
              {{ t('pin.pinView.submit') }}
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-sm rounded-xl border"
              @click="showCopyrightReport = false"
            >
              {{ t('pin.pinView.cancel') }}
            </button>
          </div>
        </div>

        <div class="mt-2" v-if="pin.description">
          <span class="">
            {{ pin.description }}
          </span>
        </div>
        <div class="mt-4 mr-5" v-if="pin.href">
          <a target="_blank" :href="pin.href"
            class="w-full inline-block text-center  py-3 bg-neutral-200  text-black font-medium rounded-full hover:bg-neutral-300 transition duration-300">
            {{ t('pin.visitSite') }}
          </a>
        </div>
        <div class="flex flex-wrap gap-2 my-2" v-auto-animate>
          <div v-for="tag in tags" :key="tag.id" @click="showTagsPin(tag)"
            :class="[`${tag.color}`, 'text-sm', 'font-medium', 'rounded-3xl', 'px-3', 'py-2', 'cursor-pointer', 'transition-transform', 'duration-200', 'transform', 'hover:scale-110']">
            {{ tag.name }}
          </div>
        </div>
        <div>
          <RouterLink v-if="pinUser" :to="`/user/${pinUser.username}`"
            class="inline-flex items-center mt-2 hover:underline cursor-pointer">
            <img v-if="pinUserImage" :src="pinUserImage" :alt="t('pin.pinView.userProfileAlt')"
              class="w-10 h-10 rounded-full object-cover" />
            <span class="ml-2 text-md font-medium">@{{ pinUser.username }}</span>
          </RouterLink>
        </div>
        </div>

        <div class="flex-shrink-0 flex flex-col mt-2 min-h-0">
          <div class="mb-2 flex-shrink-0 flex items-center justify-between cursor-pointer" v-if="cntComments != 0"
            @click="showCommets = !showCommets">
            <h1 class="text-xl">
              {{ t('pin.pinView.commentsHeader', { count: cntComments }) }}
            </h1>
            <span class="transition-transform duration-300 mr-5" :class="{ 'rotate-180': showCommets }">
              <i class="pi pi-angle-down text-xl"></i>
            </span>
          </div>
          <div v-else class="mb-1 flex-shrink-0">
            <h1 class="text-md  text-black ml-1">{{ t('pin.pinView.yourOpinion') }}</h1>
          </div>
          <div v-if="showCommets" class="h-[min(40vh,320px)] overflow-hidden pr-2 mb-2">
            <CommentSection :pin_id="pin.id" class="h-full" />
          </div>
          <div class="flex-shrink-0">
        <div v-if="isImage && !sendComment" class="relative">
          <div class="absolute top-0 left-[-10px]" @click="resetFile">
            <i class="pi pi-times text-xs cursor-pointer p-2 text-white bg-black rounded-full"></i>
          </div>
          <img :src="mediaPreview" class="mt-2 h-28 w-28 object-cover rounded-lg" :alt="t('pin.pinView.mediaPreviewAlt')" />
        </div>
        <div v-if="isVideo && !sendComment" class="relative">
          <div class="absolute top-0 left-[-10px] z-20" @click="resetFile">
            <i class="pi pi-times text-xs cursor-pointer p-2 text-white bg-black rounded-full"></i>
          </div>
          <video :src="mediaPreview" class="mt-2 h-28 w-28 object-cover rounded-lg" autoplay loop muted />
        </div>
        <div v-if="sendComment" class="flex items-center space-x-2 mb-4 mr-6 mt-2 justify-center">
          <span class="loader"></span>
        </div>
        <div v-if="!sendComment" class="flex items-center justify-center space-x-2 mb-4 mr-6 mt-2">
          <!-- Input for Comment -->
          <div ref="inputAddComment" class="relative w-full">
            <input v-model="comment" type="text" name="comment" id="commentPin" autocomplete="off"
              @keydown.enter="addComment"
              class="transition cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl py-3 px-5 pr-20 w-full focus:ring-black focus:border-black"
              :placeholder="t('pin.pinView.addCommentPlaceholder')" />

            <!-- Emoji Picker Button -->
            <button @click="loadPicker(); showPicker = !showPicker"
              class="absolute bottom-0.5 right-12 p-1 transition transform hover:scale-105">
              <i class="pi pi-face-smile text-2xl" :style="{ color: pin.rgb }"></i>
            </button>

            <!-- Media Upload Icon -->
            <label for="mediaComment" class="absolute bottom-0.5 right-4 p-1">
              <i :style="{ color: pin.rgb }"
                class="pi pi-images text-2xl cursor-pointer transition transform hover:scale-105"></i>
            </label>

            <input type="file" id="mediaComment" name="mediaPin" accept=".jpg,.jpeg,.gif,.webp,.png,.bmp,.mp4,.webm"
              @change="handleMediaUpload" class="hidden" />

            <EmojiPicker v-show="showPicker" :theme="'dark'" :hide-search="true" :native="true" @select="onSelectEmoji"
              class="absolute right-0 z-40"
              :style="{ top: isTop ? '50px' : 'auto', bottom: isTop ? 'auto' : '50px' }" />
          </div>

          <!-- Emoji Picker -->
        </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div ref="relatedObserverTarget">
    <RelatedPins v-if="pinImageLoaded || pinVideoLoaded" :pin_id="pin.id" @hasRelated="showExplore = true" />
  </div>
</template>

<style scoped>
.loader {
  width: 48px;
  height: 48px;
  display: inline-block;
  position: relative;
  border-width: 3px 2px 3px 2px;
  border-style: solid dotted solid dotted;
  border-color: #c50000 rgba(10, 255, 39, 0.3) #1c589e rgba(255, 101, 101, 0.836);
  border-radius: 50%;
  box-sizing: border-box;
  animation: 1s rotate linear infinite;
}

.loader:before,
.loader:after {
  content: '';
  top: 0;
  left: 0;
  position: absolute;
  border: 10px solid transparent;
  border-bottom-color: #a309d27a;
  transform: translate(-10px, 19px) rotate(-35deg);
}

.loader:after {
  border-color: #de3500 #670e6d00 #7b090900 #0000;
  transform: translate(32px, 3px) rotate(-35deg);
}

@keyframes rotate {
  100% {
    transform: rotate(360deg)
  }
}

.flash-enter-active,
.flash-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.flash-enter-from,
.flash-leave-to {
  opacity: 0;
  transform: scale(3);
}

.flash-enter-to,
.flash-leave-from {
  opacity: 1;
  transform: scale(1);
}

.glowing-icon {
  text-shadow: 0 0 15px rgba(255, 0, 0, 0.7), 0 0 25px rgba(255, 0, 0, 0.6), 0 0 35px rgba(255, 0, 0, 0.5);
}

.flash2-enter-active,
.flash2-leave-active {
  transition: opacity 0.5s ease-out, transform 0.5s cubic-bezier(0.3, 0.8, 0.2, 1);
}

.flash2-enter-from,
.flash2-leave-to {
  opacity: 0;
  transform: scale(3);
}

.flash2-enter-to,
.flash2-leave-from {
  opacity: 1;
  transform: scale(1);
}

.loader2 {
  width: 48px;
  height: 48px;
  background: #f3f4f6;
  border-radius: 50%;
  display: inline-block;
  position: relative;
  box-sizing: border-box;
  animation: rotation 1s linear infinite;
}

.loader2::after {
  content: '';
  box-sizing: border-box;
  position: absolute;
  left: 6px;
  top: 10px;
  width: 12px;
  height: 12px;
  color: #FF3D00;
  background: currentColor;
  border-radius: 50%;
  box-shadow: 25px 2px, 10px 22px;
}

@keyframes rotation {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.loader3 {
  width: 48px;
  height: 48px;
  background: #ffffff;
  border-radius: 50%;
  display: inline-block;
  position: relative;
  box-sizing: border-box;
  animation: rotation 1s linear infinite;
}

.loader3::after {
  content: '';
  box-sizing: border-box;
  position: absolute;
  left: 6px;
  top: 10px;
  width: 12px;
  height: 12px;
  color: #FF3D00;
  background: currentColor;
  border-radius: 50%;
  box-shadow: 25px 2px, 10px 22px;
}

@keyframes rotation {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

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
</style>