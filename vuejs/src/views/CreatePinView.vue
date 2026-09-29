<script setup>
import { ref, reactive, nextTick, onMounted, computed, watch } from "vue";
import { useToast } from "vue-toastification";
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
import axios from 'axios'
import router from '@/router';
import { useRoute, useRouter } from 'vue-router';

import SearchBar from '@/components/Auth/SearchBar.vue';

import { useUnreadMessagesStore } from "@/stores/unreadMessages";
import { authUserStore } from "@/stores/authUserStore";

const unreadMessagesStore = useUnreadMessagesStore();
const authStore = authUserStore();

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();

const mediaFile = ref(null);
const mediaPreview = ref(null);
const isImage = ref(false);
const isVideo = ref(false);

const isDragging = ref(false);

const routerBack = useRouter();

const toast = useToast();

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
const tagDropdownOpen = ref(false)

/** Selected tags on the pin being created */
const tags = ref([])

/** Chips row: all tags when query empty; otherwise top matches (capped). */
const TAG_CHIP_LIMIT = 40
const TAG_DROPDOWN_LIMIT = 12

const filteredTags = computed(() => {
  const list = available_tags.value
  if (!list || !list.length) return []
  const q = tagSearchQuery.value.trim().toLowerCase()
  if (!q) return list.slice(0, TAG_CHIP_LIMIT)
  // Single pass — no nested loops / no API per keystroke
  const out = []
  for (let i = 0; i < list.length; i++) {
    const name = list[i].name
    if (name && name.toLowerCase().includes(q)) {
      out.push(list[i])
      if (out.length >= TAG_CHIP_LIMIT) break
    }
  }
  return out
})

const tagDropdownMatches = computed(() => {
  const q = tagSearchQuery.value.trim().toLowerCase()
  if (!q || !available_tags.value?.length) return []
  const out = []
  const list = available_tags.value
  for (let i = 0; i < list.length; i++) {
    const name = list[i].name
    if (!name) continue
    const lower = name.toLowerCase()
    if (!lower.includes(q)) continue
    if (tags.value.includes(name)) continue
    out.push(list[i])
    if (out.length >= TAG_DROPDOWN_LIMIT) break
  }
  return out
})

function onTagSearchFocus() {
  tagDropdownOpen.value = true
}

function onTagSearchBlur() {
  // Delay so mousedown on option can fire
  setTimeout(() => {
    tagDropdownOpen.value = false
  }, 150)
}

function pickTagFromDropdown(name) {
  addTagToPin(name)
  tagSearchQuery.value = ''
  tagDropdownOpen.value = false
}
onMounted(async () => {
  if (!authStore.canCreatePin) {
    toast.error('Organization accounts cannot create pins')
    routerBack.push('/')
    return
  }
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = `(${totalUnread}) Pinterest`;
  } else {
    document.title = 'Pinterest';
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

async function acceptImageFile(file) {
  try {
    const normalized = await normalizeImageFile(file);
    previewFile(normalized);
  } catch (e) {
    console.error(e);
    toast.warning('Could not process image. Please try another file.', {
      position: "top-center",
      bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
    });
  }
}

function acceptVideoFile(file) {
  const video = document.createElement("video");
  video.preload = "metadata";

  video.onloadedmetadata = () => {
    window.URL.revokeObjectURL(video.src);

    if (video.duration > 30) {
      toast.warning('Video must be 30 seconds or less.', {
        position: "top-center",
        bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
      });
      return;
    }

    naturalMediaSize.value = {
      width: video.videoWidth || 0,
      height: video.videoHeight || 0,
    };
    previewFile(file);
  };

  video.src = URL.createObjectURL(file);
}

function handleMediaUpload(event) {
  const file = event.target.files[0];

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp', 'video/mp4', 'video/webm'];

  if (file) {
    if (!allowedTypes.includes(file.type)) {
      toast.warning('Please select a valid media file (.jpg, .jpeg, .gif, .webp, .png, .bmp, .mp4, .webm).', {
        position: "top-center",
        bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
      });
      return;
    }

    if (file.type.startsWith("image/")) {
      acceptImageFile(file);
    } else if (file.type.startsWith("video/")) {
      acceptVideoFile(file);
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

const onDrop = (event) => {
  isDragging.value = false;
  const file = event.dataTransfer.files[0];

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp', 'video/mp4', 'video/webm'];

  if (file) {
    if (!allowedTypes.includes(file.type)) {
      toast.warning('Please select a valid media file (.jpg, .jpeg, .gif, .webp, .png, .bmp, .mp4, .webm).', {
        position: "top-center",
        bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
      });
      return;
    }

    if (file.type.startsWith("image/")) {
      acceptImageFile(file);
    } else if (file.type.startsWith("video/")) {
      acceptVideoFile(file);
    }
  }
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

  if (!mediaFile.value) {
    toast.warning('Please, upload file', { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
    return
  }

  sendingPin.value = true

  try {
    // Feed placeholder height = aspect ratio × ref column width (never raw source pixels)
    let height = heightFromAspect(naturalMediaSize.value.width, naturalMediaSize.value.height);
    if (!height) {
      const el = document.getElementById(isImage.value ? 'imagePreview' : 'videoPreview');
      if (el) {
        const rect = el.getBoundingClientRect();
        height = heightFromAspect(rect.width, rect.height) || rect.height.toFixed(2);
      }
    }
    const formData = new FormData();
    formData.append("file", mediaFile.value);

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
        toast.warning('Pin created but listing failed — you can list from the pin page')
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
  if (tagToAdd.value.trim()) {
    available_tags.value.unshift({ id: available_tags.value.length, name: tagToAdd.value, color: randomBgColor() });
    tagToAdd.value = '';
  }
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
          <h3 class="mb-5 text-lg font-normal text-black"> Invalid file type. Allowed types: .jpg, .jpeg, .gif, .webp,
            .png, .bmp, .mp4, .webm </h3>
          <button @click="fileError = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            Ok, understand
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
          <!-- Media Preview -->
          <div id="mediaPreview" v-if="mediaPreview"
            class="mt-2 border border-dashed border-gray-400 rounded-3xl hover:border-purple-500 hover:bg-purple-100 transition duration-100"
            :class="{ 'border-purple-500 bg-purple-100': isDragging }">
            <img id="imagePreview" v-if="isImage" :src="mediaPreview"
              class="h-auto w-[271.84px] rounded-3xl mx-auto my-8" alt="Media Preview" />
            <video id="videoPreview" v-if="isVideo" :src="mediaPreview"
              class="h-auto w-[271.84px] rounded-3xl mx-auto my-8" autoplay loop muted />
          </div>

          <!-- Placeholder for no preview -->
          <div v-else
            class="mt-2 border border-dashed border-gray-900 rounded-3xl hover:border-purple-500 hover:bg-purple-100 transition duration-100 overflow-hidden"
            :class="{ 'border-purple-500 bg-purple-100': isDragging }">
            <div
              class="relative  h-96 w-[271.84px] flex justify-center items-center text-center rounded-3xl mx-auto my-8">
              <div class="absolute flex flex-col items-center space-y-4">
                <i class="pi pi-arrow-up text-4xl text-gray-400"></i>
                <p class="mt-2 text-xl text-black">Drag & Drop or Click to Upload</p>
                <p class="mt-2 text-sm text-gray-700">Small images are upscaled to fit (min 200×300)</p>
                <p class="mt-2 text-sm text-gray-700">Videos must be 30 seconds or less</p>
                <p class="mt-2 text-xs text-gray-700">.jpg .jpeg .gif .webp .png .bmp .mp4 .webm</p>
              </div>
            </div>
          </div>
        </label>
        <input type="file" id="mediacreate" name="media" accept=".jpg,.jpeg,.gif,.webp,.png,.bmp,.mp4,.webm"
          @change="handleMediaUpload" class="hidden" />

        <div v-if="canListForSale" class="mt-6 p-4 border border-gray-300 rounded-2xl space-y-2">
          <label class="flex items-center gap-2 text-sm font-medium cursor-pointer">
            <input v-model="listForSale" type="checkbox" class="rounded" />
            List for sale (personal-use license)
          </label>
          <div v-if="listForSale" class="space-y-2">
            <div class="flex gap-2 items-center">
              <input v-model="listPriceMajor" type="number" min="0.01" step="0.01"
                class="border rounded-xl px-3 py-2 w-28 text-sm" />
              <select v-model="listCurrency" class="border rounded-xl px-3 py-2 text-sm">
                <option value="USD">USD</option>
                <option value="VND">VND</option>
              </select>
            </div>
            <p class="text-xs text-gray-600">
              Listing confirms you have the right to sell a personal-use license for this pin.
            </p>
          </div>
        </div>
        <p v-else class="mt-4 text-xs text-gray-500">
          Enable selling from a pin you own once you meet selling requirements and add a payment method.
        </p>

        <button @click="submitPin"
          class="w-full mt-10 transition duration-100 text-white bg-purple-500 hover:bg-purple-600 font-medium rounded-3xl text-sm px-5 py-2.5 text-center">
          Create Pin
        </button>
      </div>

      <div>
        <div class="space-y-7 mt-2 mb-10">
          <!-- Title Field -->
          <div>
            <input v-model="formPin.title" type="text" name="title" id="titleCreate" autocomplete="off"
              class="hover:bg-purple-100 transition duration-100  cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Add title" />
          </div>
          <!-- Description Field -->
          <div>
            <textarea v-model="formPin.description" name="description" id="descriptionCreate"
              class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Add description"></textarea>
          </div>
          <!-- Href Field -->
          <div>
            <input v-model="formPin.href" type="url" name="href" id="href" autocomplete="off"
              class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl block w-full py-4 px-5 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Add link (any website link)" />
          </div>
          <!-- Tags Field -->

          <div>
            <div class="mt-5">
              <!-- Heading -->

              <h3 class="text-md mb-2 text-gray-600">Add Tags to Pin</h3>

              <div class="flex items-center space-x-2 mb-4">
                <button type="button" @click="addTag"
                  class="bg-purple-500 hover:bg-purple-600 transition duration-100 text-white font-medium rounded-3xl text-sm px-4 py-2">
                  Create
                </button>

                <input v-model="tagToAdd" type="text" name="tags" id="tags" autocomplete="off" @keydown.enter="addTag"
                  class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl flex-grow py-3 px-5 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Create Tag" />
              </div>

              <div class="relative mb-4">
                <input
                  v-model="tagSearchQuery"
                  type="text"
                  placeholder="Search tags…"
                  autocomplete="off"
                  class="hover:bg-purple-100 transition duration-100 cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl w-full py-3 px-5 focus:ring-purple-500 focus:border-purple-500"
                  @focus="onTagSearchFocus"
                  @blur="onTagSearchBlur"
                  @keydown.enter.prevent="tagDropdownMatches[0] && pickTagFromDropdown(tagDropdownMatches[0].name)"
                />
                <ul
                  v-if="tagDropdownOpen && tagSearchQuery.trim() && tagDropdownMatches.length"
                  class="absolute z-20 left-0 right-0 mt-1 max-h-56 overflow-y-auto rounded-2xl border border-gray-200 bg-white shadow-lg"
                >
                  <li
                    v-for="tag in tagDropdownMatches"
                    :key="'dd-' + tag.id"
                    class="px-4 py-2 text-sm cursor-pointer hover:bg-purple-50"
                    @mousedown.prevent="pickTagFromDropdown(tag.name)"
                  >
                    {{ tag.name }}
                  </li>
                </ul>
                <p
                  v-else-if="tagDropdownOpen && tagSearchQuery.trim() && !tagDropdownMatches.length"
                  class="absolute z-20 left-0 right-0 mt-1 px-4 py-2 text-sm text-gray-500 rounded-2xl border border-gray-200 bg-white shadow"
                >
                  No matching tags — create one above
                </p>
              </div>

              <!-- Tags List (chips) -->
              <div class="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                <div v-for="tag in filteredTags" :key="tag.id" @click="addTagToPin(tag.name)"
                  :class="[checkPinAded(tag.name) ? 'bg-black text-white shadow-lg scale-110' : `${tag.color}`, 'text-sm', 'font-medium', 'rounded-3xl', 'px-3', 'py-2', 'cursor-pointer', 'transition-transform', 'duration-200', 'transform', 'hover:scale-110']">
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