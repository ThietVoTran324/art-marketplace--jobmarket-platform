<script setup>
import { ref, reactive, nextTick, onMounted, computed, watch } from "vue";
import { useToast } from "vue-toastification";
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
import axios from 'axios'
import router from '@/router';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

import SearchBar from '@/components/Auth/SearchBar.vue';

import { useUnreadMessagesStore } from "@/stores/unreadMessages";
import { authUserStore } from "@/stores/authUserStore";

const unreadMessagesStore = useUnreadMessagesStore();
const authStore = authUserStore();

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();

const MAX_COLLECTION_IMAGES = 50;
/** @type {import('vue').Ref<Array<{ file: File, preview: string, isImage: boolean, isVideo: boolean, width: number, height: number }>>} */
const mediaItems = ref([]);
const isDragging = ref(false);

const mediaPreview = computed(() => mediaItems.value[0]?.preview || null);
const isImage = computed(() => !!mediaItems.value[0]?.isImage);
const isVideo = computed(() => !!mediaItems.value[0]?.isVideo);
const coverNaturalSize = computed(() => {
  const first = mediaItems.value[0];
  if (!first) return { width: 0, height: 0 };
  return { width: first.width || 0, height: first.height || 0 };
});

const routerBack = useRouter();

const toast = useToast();
const { t } = useI18n();

const color = ref('red')
const size = ref('100px')

const sendingPin = ref(false)

const listForSale = ref(false)
const listPriceMajor = ref('5.00')
const listCurrency = ref('USD')
const canListForSale = computed(
  () => authStore.hasRole('seller') && authStore.canSellOnMarketplace
)

const formPin = reactive({
  title: '',
  description: '',
  href: '',
});

const tagToAdd = ref('')
const available_tags = ref([])
const bgColors = ref(['bg-red-200', 'bg-orange-200', 'bg-amber-200', 'bg-lime-200', 'bg-green-200', 'bg-emerald-200', 'bg-teal-200', 'bg-sky-200', 'bg-blue-200', 'bg-indigo-200', 'bg-violet-200', 'bg-purple-200', 'bg-fuchsia-200', 'bg-pink-200', 'bg-rose-200'])

const tagSearchQuery = ref('')
/** Debounced filter key — live chips without filtering on every raw keystroke. */
const tagFilterKey = ref('')
let tagFilterTimer = null

/** Selected tags on the pin being created */
const tags = ref([])

/** Chips row: all tags when query empty; otherwise top matches (capped). */
const TAG_CHIP_LIMIT = 40
const TAG_FILTER_DEBOUNCE_MS = 80

/** Hashtags are single tokens: strip # and spaces for match/create (lets do → letsdo). */
function normalizeTagToken(raw) {
  return String(raw || '')
    .trim()
    .replace(/^#+/, '')
    .replace(/\s+/g, '')
    .toLowerCase()
}

watch(tagSearchQuery, (raw) => {
  // Strip spaces / keep typing fluid (hashtags are one token)
  const noSpace = String(raw || '').replace(/\s+/g, '')
  if (noSpace !== raw) {
    tagSearchQuery.value = noSpace
    return
  }
  if (tagFilterTimer) clearTimeout(tagFilterTimer)
  tagFilterTimer = setTimeout(() => {
    tagFilterKey.value = normalizeTagToken(raw)
  }, TAG_FILTER_DEBOUNCE_MS)
})

watch(tagToAdd, (raw) => {
  const noSpace = String(raw || '').replace(/\s+/g, '')
  if (noSpace !== raw) tagToAdd.value = noSpace
})

const filteredTags = computed(() => {
  const list = available_tags.value
  if (!list || !list.length) return []
  const q = tagFilterKey.value
  if (!q) return list.slice(0, TAG_CHIP_LIMIT)
  // Single pass — no nested loops / no API per keystroke
  const out = []
  for (let i = 0; i < list.length; i++) {
    const name = list[i].name
    if (!name) continue
    const compact = normalizeTagToken(name)
    if (compact.includes(q) || name.toLowerCase().includes(q)) {
      out.push(list[i])
      if (out.length >= TAG_CHIP_LIMIT) break
    }
  }
  return out
})

/** Block Space in tag fields — tags have no spaces; filter updates as you type. */
function onTagKeydownNoSpace(e) {
  if (e.key === ' ' || e.code === 'Space') {
    e.preventDefault()
  }
}

function onTagSearchEnter(e) {
  e.preventDefault()
  const matches = filteredTags.value
  const first = matches.find((t) => !tags.value.includes(t.name))
  if (first) {
    addTagToPin(first.name)
    tagSearchQuery.value = ''
    tagFilterKey.value = ''
    return
  }
  const token = normalizeTagToken(tagSearchQuery.value)
  if (!token) return
  const existing = available_tags.value.find((t) => normalizeTagToken(t.name) === token)
  const name = existing?.name || token
  if (!existing) {
    tagToAdd.value = name
    addTag()
  }
  addTagToPin(name)
  tagSearchQuery.value = ''
  tagFilterKey.value = ''
}
onMounted(async () => {
  if (!authStore.canCreatePin) {
    toast.error(t('createPin.toast.orgCannotCreate'))
    routerBack.push('/')
    return
  }
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = t('createPin.documentTitle.withUnread', { count: totalUnread });
  } else {
    document.title = t('createPin.documentTitle.default');
  }
  try {
    const response = await axios.get('/api/tags/', { withCredentials: true })
    available_tags.value = response.data
    for (let i = 0; i < response.data.length; i++) {
      const tag = response.data[i];
      tag.color = randomBgColor()
    }
  } catch (error) {
    console.log(error)
  }
})

/** Reference column width used when deriving feed placeholder height from aspect ratio (not source pixels). */
const PIN_FEED_REF_WIDTH = 271.84;
const MIN_IMAGE_W = 200;
const MIN_IMAGE_H = 300;

const naturalMediaSize = ref({ width: 0, height: 0 });

function heightFromAspect(width, height) {
  if (!width || !height) return null;
  return (PIN_FEED_REF_WIDTH * (height / width)).toFixed(2);
}

function loadImageElement(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };
    img.src = url;
  });
}

/** Upscale small images to at least MIN_IMAGE_W × MIN_IMAGE_H while keeping aspect ratio. */
async function normalizeImageFile(file) {
  const img = await loadImageElement(file);
  naturalMediaSize.value = { width: img.width, height: img.height };

  if (img.width >= MIN_IMAGE_W && img.height >= MIN_IMAGE_H) {
    return file;
  }

  // Keep animated GIFs as-is (canvas would flatten frames); still accept without blocking
  if (file.type === 'image/gif') {
    return file;
  }

  const scale = Math.max(MIN_IMAGE_W / img.width, MIN_IMAGE_H / img.height);
  const w = Math.ceil(img.width * scale);
  const h = Math.ceil(img.height * scale);
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(img, 0, 0, w, h);

  const outType = file.type === 'image/png' || file.type === 'image/webp'
    ? 'image/png'
    : 'image/jpeg';
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, outType, 0.92));
  if (!blob) return file;

  naturalMediaSize.value = { width: w, height: h };
  const ext = outType === 'image/png' ? 'png' : 'jpg';
  const base = (file.name || 'pin').replace(/\.[^.]+$/, '');
  return new File([blob], `${base}.${ext}`, { type: outType });
}

function readPreviewDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function pushImageItem(file) {
  if (mediaItems.value.some((m) => m.isVideo)) {
    toast.warning(t('createPin.toast.videoOnlyAlone'), {
      position: "top-center",
      bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
    });
    return;
  }
  if (mediaItems.value.length >= MAX_COLLECTION_IMAGES) {
    toast.warning(t('createPin.toast.maxImages', { max: MAX_COLLECTION_IMAGES }), {
      position: "top-center",
      bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
    });
    return;
  }
  try {
    const normalized = await normalizeImageFile(file);
    const preview = await readPreviewDataUrl(normalized);
    mediaItems.value.push({
      file: normalized,
      preview,
      isImage: true,
      isVideo: false,
      width: naturalMediaSize.value.width || 0,
      height: naturalMediaSize.value.height || 0,
    });
  } catch (e) {
    console.error(e);
    toast.warning(t('createPin.toast.imageProcessFailed'), {
      position: "top-center",
      bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
    });
  }
}

function pushVideoItem(file) {
  if (mediaItems.value.length > 0) {
    toast.warning(t('createPin.toast.videoOnlyAlone'), {
      position: "top-center",
      bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
    });
    return;
  }
  const video = document.createElement("video");
  video.preload = "metadata";

  video.onloadedmetadata = async () => {
    window.URL.revokeObjectURL(video.src);

    if (video.duration > 30) {
      toast.warning(t('createPin.toast.videoMaxDuration'), {
        position: "top-center",
        bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
      });
      return;
    }

    const preview = await readPreviewDataUrl(file);
    mediaItems.value = [{
      file,
      preview,
      isImage: false,
      isVideo: true,
      width: video.videoWidth || 0,
      height: video.videoHeight || 0,
    }];
  };

  video.src = URL.createObjectURL(file);
}

async function addMediaFiles(fileList) {
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp', 'video/mp4', 'video/webm'];
  const files = Array.from(fileList || []);
  for (const file of files) {
    if (!allowedTypes.includes(file.type)) {
      toast.warning(t('createPin.toast.invalidMediaType'), {
        position: "top-center",
        bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
      });
      continue;
    }
    if (file.type.startsWith("image/")) {
      await pushImageItem(file);
    } else if (file.type.startsWith("video/")) {
      pushVideoItem(file);
    }
  }
}

function removeMediaAt(index) {
  mediaItems.value.splice(index, 1);
}

function handleMediaUpload(event) {
  addMediaFiles(event.target.files);
  event.target.value = '';
}

const onDrop = (event) => {
  isDragging.value = false;
  addMediaFiles(event.dataTransfer.files);
};

// Handle drag over
const onDragOver = () => {
  isDragging.value = true;
};

// Handle drag leave
const onDragLeave = () => {
  isDragging.value = false;
};

const goBack = () => {
  routerBack.back();
};

const fileError = ref(false)

async function submitPin() {
  const title = formPin.title.trim()
  const description = formPin.description.trim()
  const href = formPin.href.trim()

  if (!mediaItems.value.length) {
    toast.warning(t('createPin.toast.uploadRequired'), { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
    return
  }

  sendingPin.value = true

  try {
    // Feed placeholder height = aspect ratio × ref column width (cover / first file)
    const cover = coverNaturalSize.value;
    let height = heightFromAspect(cover.width, cover.height);
    if (!height) {
      const el = document.getElementById(isImage.value ? 'imagePreview' : 'videoPreview');
      if (el) {
        const rect = el.getBoundingClientRect();
        height = heightFromAspect(rect.width, rect.height) || rect.height.toFixed(2);
      }
    }
    const formData = new FormData();
    for (const item of mediaItems.value) {
      formData.append("files", item.file);
    }

    const jsonData = JSON.stringify({
      title: title,
      description: description,
      href: href,
      height: `${height}`
    });

    formData.append("pin_model", jsonData);

    const response = await axios.post("/api/pins/create-pin-entity", formData, {
      withCredentials: true,
      headers: {
        "Content-Type": "multipart/form-data"
      }
    });

    const pin_id = response.data.id

    if (listForSale.value && canListForSale.value) {
      try {
        const price_minor = Math.round(parseFloat(listPriceMajor.value) * 100)
        await axios.post(`/api/marketplace/pins/${pin_id}/listing`, {
          price_minor,
          currency: listCurrency.value,
          attestation_accepted: true,
        })
      } catch (error) {
        console.error(error)
        toast.warning(t('createPin.toast.listingFailedAfterCreate'))
      }
    }

    if (tags.value.length !== 0) {
      try {
        const response = await axios.post(`/api/tags/`, {
          pin_id: pin_id,
          tags: tags.value
        })
        sendingPin.value = false
        router.push(`/pin/${pin_id}`);
      } catch (error) {
        console.error(error)
      }
    } else {
      sendingPin.value = false
      router.push(`/pin/${pin_id}`);
    }
  } catch (error) {
    if (error.response.status === 415) {
      fileError.value = true
    }
  }
}

const randomBgColor = () => {
  const randomIndex = Math.floor(Math.random() * bgColors.value.length);
  return bgColors.value[randomIndex];
};

function addTag() {
  const name = normalizeTagToken(tagToAdd.value)
  if (!name) return
  const exists = available_tags.value.some(
    (t) => normalizeTagToken(t.name) === name
  )
  if (!exists) {
    available_tags.value.unshift({
      id: `new-${Date.now()}`,
      name,
      color: randomBgColor(),
    })
  }
  tagToAdd.value = ''
}

function addTagToPin(name) {
  if (checkPinAded(name)) {
    tags.value = tags.value.filter((el) => el !== name);
  }
  else {
    tags.value.push(name)
  }
}

function checkPinAded(name) {
  return tags.value.includes(name);
}

</script>

<template>
  <div v-if="fileError" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black">{{ t('createPin.fileErrorModal.title') }}</h3>
          <button @click="fileError = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            {{ t('createPin.fileErrorModal.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <SearchBar />
  <div class="ml-20 mt-20">
    <ClipLoader v-if="sendingPin" :color="color" :size="size"
      class="flex items-center justify-center h-96 font-extrabold" />
    <div v-else class="grid grid-cols-2 mt-10 mr-72 gap-10">
      <button @click="goBack" class="absolute top-4 left-20 text-gray-500 ml-20 mt-20 hover:-translate-x-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div class="ml-56">
        <label for="mediacreate" class="cursor-pointer" @dragover.prevent="onDragOver" @dragleave="onDragLeave"
          @drop.prevent="onDrop">
          <!-- Media Preview (cover = first) -->
          <div id="mediaPreview" v-if="mediaPreview"
            class="mt-2 border border-dashed border-gray-400 rounded-3xl hover:border-purple-500 hover:bg-purple-100 transition duration-100"
            :class="{ 'border-purple-500 bg-purple-100': isDragging }">
            <img id="imagePreview" v-if="isImage" :src="mediaPreview"
              class="h-auto w-[271.84px] rounded-3xl mx-auto my-8" :alt="t('createPin.upload.altMediaPreview')" />
            <video id="videoPreview" v-if="isVideo" :src="mediaPreview"
              class="h-auto w-[271.84px] rounded-3xl mx-auto my-8" autoplay loop muted />
          </div>

          <!-- Placeholder for no preview -->
          <div v-else
            class="mt-2 border border-dashed border-gray-900 rounded-3xl hover:border-purple-500 hover:bg-purple-100 transition duration-100 overflow-hidden"
            :class="{ 'border-purple-500 bg-purple-100': isDragging }">
            <div
              class="relative  h-96 w-[271.84px] flex justify-center items-center text-center rounded-3xl mx-auto my-8">
              <div class="absolute flex flex-col items-center space-y-4 px-4">
                <i class="pi pi-arrow-up text-4xl text-gray-400"></i>
                <p class="mt-2 text-xl text-black">{{ t('createPin.upload.dragDropOrClick') }}</p>
                <p class="mt-2 text-sm text-gray-700">{{ t('createPin.upload.collectionHint') }}</p>
                <p class="mt-2 text-sm text-gray-700">{{ t('createPin.upload.upscaleHint') }}</p>
                <p class="mt-2 text-sm text-gray-700">{{ t('createPin.upload.videoDurationHint') }}</p>
                <p class="mt-2 text-xs text-gray-700">{{ t('createPin.upload.extensionsLine') }}</p>
              </div>
            </div>
          </div>
        </label>
        <input type="file" id="mediacreate" name="media" multiple
          accept=".jpg,.jpeg,.gif,.webp,.png,.bmp,.mp4,.webm"
          @change="handleMediaUpload" class="hidden" />

        <div v-if="mediaItems.length" class="mt-4 space-y-2">
          <p class="text-sm text-gray-600">{{ t('createPin.upload.imageCount', { count: mediaItems.length }) }}</p>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="(item, idx) in mediaItems"
              :key="idx"
              class="relative w-16 h-16 rounded-xl overflow-hidden border border-gray-300"
            >
              <img v-if="item.isImage" :src="item.preview" class="w-full h-full object-cover" alt="" />
              <video v-else :src="item.preview" class="w-full h-full object-cover" muted />
              <span
                v-if="idx === 0"
                class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] text-center py-0.5"
              >{{ t('createPin.upload.coverBadge') }}</span>
              <button
                type="button"
                class="absolute top-0 right-0 bg-black/70 text-white text-xs w-5 h-5 leading-5"
                :title="t('createPin.upload.removeImage')"
                @click.stop.prevent="removeMediaAt(idx)"
              >×</button>
            </div>
          </div>
        </div>

        <div v-if="canListForSale" class="mt-6 p-4 border border-gray-300 rounded-2xl space-y-2">
          <label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
            <input v-model="listForSale" type="checkbox" class="rounded" />
            {{ t('createPin.marketplace.listForSaleLabel') }}
          </label>
          <div v-if="listForSale" class="space-y-2">
            <div class="flex gap-2 items-center">
              <input v-model="listPriceMajor" type="number" min="0.01" step="0.01"
                class="border rounded-xl px-3 py-2 w-28 text-sm" />
              <select v-model="listCurrency" class="border rounded-xl px-3 py-2 text-sm">
                <option value="USD">{{ t('createPin.marketplace.currencyUsd') }}</option>
                <option value="VND">{{ t('createPin.marketplace.currencyVnd') }}</option>
              </select>
            </div>
            <p class="text-xs text-gray-600">
              {{ t('createPin.marketplace.listingAttestation') }}
            </p>
          </div>
        </div>
        <p v-else class="mt-4 text-xs text-gray-500">
          {{ t('createPin.marketplace.sellingRequirementsHint') }}
        </p>

        <button @click="submitPin"
          class="w-full mt-10 transition duration-100 text-white bg-purple-500 hover:bg-purple-600 font-medium rounded-3xl text-sm px-5 py-2.5 text-center">
          {{ t('createPin.actions.createPin') }}
        </button>
      </div>

      <div>
        <div class="space-y-7 mt-2 mb-10">
          <!-- Title Field -->
          <div>
            <input v-model="formPin.title" type="text" name="title" id="titleCreate" autocomplete="off"
              class="hover:bg-purple-100 transition duration-100  cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              :placeholder="t('createPin.fields.titlePlaceholder')" />
          </div>
          <!-- Description Field -->
          <div>
            <textarea v-model="formPin.description" name="description" id="descriptionCreate"
              class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              :placeholder="t('createPin.fields.descriptionPlaceholder')"></textarea>
          </div>
          <!-- Href Field -->
          <div>
            <input v-model="formPin.href" type="url" name="href" id="href" autocomplete="off"
              class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              :placeholder="t('createPin.fields.hrefPlaceholder')" />
          </div>
          <!-- Tags Field -->

          <div>
            <div class="mt-5">
              <!-- Heading -->

              <h3 class="text-md mb-2 text-gray-600">{{ t('createPin.fields.tagsHeading') }}</h3>

              <div class="flex items-center space-x-2 mb-4">
                <button type="button" @click="addTag"
                  class="bg-purple-500 hover:bg-purple-600 transition duration-100 text-white font-medium rounded-3xl text-sm px-4 py-2">
                  {{ t('createPin.fields.createTagButton') }}
                </button>

                <input
                  v-model="tagToAdd"
                  type="text"
                  name="tags"
                  id="tags"
                  autocomplete="off"
                  @keydown="onTagKeydownNoSpace"
                  @keydown.enter.prevent="addTag"
                  class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl flex-grow py-3 px-5 focus:ring-purple-500 focus:border-purple-500"
                  :placeholder="t('createPin.fields.createTagPlaceholder')"
                />
              </div>

              <div class="mb-2">
                <input
                  v-model="tagSearchQuery"
                  type="text"
                  :placeholder="t('createPin.fields.searchTagsPlaceholder')"
                  autocomplete="off"
                  class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl w-full py-3 px-5 focus:ring-purple-500 focus:border-purple-500"
                  @keydown="onTagKeydownNoSpace"
                  @keydown.enter="onTagSearchEnter"
                />
                <p
                  v-if="tagFilterKey && !filteredTags.length"
                  class="mt-2 text-xs text-gray-500"
                >
                  {{ t('createPin.fields.noMatchingTags') }}
                </p>
              </div>

              <!-- Tags List (chips) — only suggestion surface -->
              <div class="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                <div
                  v-for="tag in filteredTags"
                  :key="tag.id"
                  @click="addTagToPin(tag.name)"
                  :class="[checkPinAded(tag.name) ? 'bg-black text-white shadow-lg scale-110' : `${tag.color}`, 'text-sm', 'font-medium', 'rounded-3xl', 'px-3', 'py-2', 'cursor-pointer', 'transition-transform', 'duration-200', 'transform', 'hover:scale-110']"
                >
                  {{ tag.name }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>