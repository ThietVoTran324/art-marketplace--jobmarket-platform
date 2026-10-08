<script setup>
import { onMounted, ref, nextTick, watch } from 'vue';
import axios from 'axios';
import ReplyCommentSection from '../ReplyCommentSection.vue';
import CommentLikesPopover from '../CommentLikesPopover.vue';
import EmojiPicker from 'vue3-emoji-picker';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import 'dayjs/locale/en';
import { useToast } from 'vue-toastification';
import { useI18n } from 'vue-i18n';
import { authUserStore } from '@/stores/authUserStore';
import { useAuthModal } from '@/composables/useAuthModal';

const toast = useToast();
const { t } = useI18n();
const userStore = authUserStore();
const { openAuthModal } = useAuthModal();

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale('en');

const props = defineProps({
  companyId: { type: Number, required: true },
});

const commentSection = ref(null);
const comments = ref([]);
const offset = ref(0);
const limit = ref(5);
const isLoading = ref(false);
const canLoad = ref(true);
const draft = ref('');
const posting = ref(false);

const formatTime = (createdAt) => {
  const now = dayjs();
  const createdTime = dayjs.utc(createdAt).local();
  const diffMinutes = now.diff(createdTime, 'minute');
  return diffMinutes < 30 ? t('comments.time.justNow') : createdTime.fromNow();
};

function requireAuth() {
  if (userStore.isAuthenticated) return true;
  openAuthModal('login', { redirectTo: `/companies/${props.companyId}` });
  return false;
}

async function hydrateComment(commentData) {
  let commentImage = null;
  let isImage = false;
  let isVideo = false;
  if (commentData.image) {
    try {
      const response = await axios.get(`/api/comments/upload/${commentData.id}`, {
        responseType: 'blob',
      });
      commentImage = URL.createObjectURL(response.data);
      const contentType = response.headers['content-type'] || '';
      if (contentType.startsWith('image/')) isImage = true;
      else isVideo = true;
    } catch (error) {
      console.error(error);
    }
  }

  let commentUser = null;
  let commentUserImage = null;
  try {
    const response = await axios.get(`/api/users/user_id/${commentData.user_id}`);
    commentUser = response.data;
    try {
      const img = await axios.get(`/api/users/upload/${commentUser.id}`, {
        responseType: 'blob',
      });
      commentUserImage = URL.createObjectURL(img.data);
    } catch (error) {
      console.error(error);
    }
  } catch (error) {
    console.error(error);
    return null;
  }

  let checkUserLike = false;
  try {
    const response = await axios.get(`/api/likes/comment/user_like/${commentData.id}`);
    checkUserLike = response.data;
  } catch (error) {
    console.error(error);
  }

  let cntLikes = 0;
  try {
    const response = await axios.get(`/api/likes/comment/likes/cnt/${commentData.id}`);
    cntLikes = response.data ?? 0;
  } catch (error) {
    console.error(error);
  }

  let cntReplies = 0;
  try {
    const response = await axios.get(`/api/comments/cnt/replies/${commentData.id}`);
    cntReplies = response.data ?? 0;
  } catch (error) {
    console.error(error);
  }

  return {
    id: commentData.id,
    content: commentData.content,
    created_at: commentData.created_at,
    image: commentImage,
    employment_status: commentData.employment_status || null,
    user: commentUser,
    userImage: commentUserImage,
    showReply: false,
    replyContent: '',
    showReplies: cntReplies > 0,
    checkUserLike,
    cntLikes,
    showPopover: false,
    insidePopover: false,
    cntReplies,
    isImage,
    isVideo,
    replyIsImage: false,
    replyIsVideo: false,
    replyMediaPreview: null,
    replyMediaFile: null,
    showLikeAnimation: null,
    showDislikeAnimation: null,
    sendComment: false,
    sendCommentError: false,
    inputAddComment: null,
    showPicker: false,
    isTop: false,
    likesPopoverEl: null,
    likesIsTop: null,
  };
}

async function loadComments() {
  if (isLoading.value || !canLoad.value) return;
  isLoading.value = true;
  try {
    const response = await axios.get(`/api/job-market/companies/${props.companyId}/comments`, {
      params: { offset: offset.value, limit: limit.value },
    });
    if (response.data.length < limit.value) canLoad.value = false;
    for (const commentData of response.data) {
      const hydrated = await hydrateComment(commentData);
      if (hydrated) comments.value.push(hydrated);
    }
    offset.value += limit.value;
  } catch (error) {
    console.error(error);
  } finally {
    isLoading.value = false;
  }
}

async function resetAndLoad() {
  comments.value = [];
  offset.value = 0;
  canLoad.value = true;
  await loadComments();
}

const handleScroll = (event) => {
  const container = event.target;
  if (container.scrollTop + container.clientHeight >= container.scrollHeight - 10) {
    loadComments();
  }
};

async function submitTopLevel() {
  if (!requireAuth()) return;
  const text = draft.value.trim();
  if (!text || posting.value) return;
  posting.value = true;
  try {
    const { data } = await axios.post(`/api/job-market/companies/${props.companyId}/comments`, {
      content: text,
    });
    draft.value = '';
    const hydrated = await hydrateComment(data);
    if (hydrated) comments.value.unshift(hydrated);
  } catch (error) {
    console.error(error);
  } finally {
    posting.value = false;
  }
}

function loadPicker(comment) {
  if (comment.showPicker === false) {
    const element = comment.inputAddComment;
    const commentsContainer = commentSection.value;
    if (element && commentsContainer) {
      const rect = element.getBoundingClientRect();
      const distanceToBottom = commentsContainer.clientHeight - rect.bottom;
      comment.isTop = distanceToBottom >= -100;
    }
  }
}

function loadLikesPopover(comment) {
  const element = comment.likesPopoverEl;
  const commentsContainer = commentSection.value;
  if (element && commentsContainer) {
    const rect = element.getBoundingClientRect();
    const distanceToBottom = commentsContainer.clientHeight - rect.bottom;
    comment.likesIsTop = distanceToBottom >= -100;
  }
}

function onSelectEmoji(emoji, comment) {
  comment.replyContent += emoji.i;
}

function toggleReply(comment) {
  if (!requireAuth()) return;
  comment.showReply = !comment.showReply;
}

async function addComment(comment) {
  if (!requireAuth()) return;

  if (comment.replyContent.trim() !== '' && !comment.replyMediaFile) {
    comment.sendComment = true;
    comment.showPicker = false;
    try {
      await axios.post(`/api/comments/comment/${comment.id}`, {
        content: comment.replyContent.trim(),
      });
      comment.replyContent = '';
      comment.cntReplies += 1;
      comment.showReplies = false;
      await nextTick();
      comment.showReplies = true;
      comment.showReply = false;
      comment.sendComment = false;
      return;
    } catch (error) {
      console.error(error);
      comment.sendComment = false;
    }
  }

  if (comment.replyMediaFile) {
    comment.sendComment = true;
    comment.showPicker = false;
    try {
      const formData = new FormData();
      formData.append('file', comment.replyMediaFile);
      formData.append(
        'comment_model',
        JSON.stringify({ content: comment.replyContent.trim() })
      );
      await axios.post(`/api/comments/create-comment-on-comment-entity/${comment.id}`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      comment.replyContent = '';
      comment.replyMediaPreview = null;
      comment.replyMediaFile = null;
      comment.replyIsImage = false;
      comment.replyIsVideo = false;
      comment.cntReplies += 1;
      comment.showReplies = false;
      await nextTick();
      comment.showReplies = true;
      comment.showReply = false;
      comment.sendComment = false;
    } catch (error) {
      if (error.response?.status === 415) {
        comment.sendComment = false;
        comment.sendCommentError = true;
      } else {
        comment.sendComment = false;
        console.error(error);
      }
    }
  }
}

function handleMediaUpload(event, comment) {
  const file = event.target.files[0];
  const allowedTypes = [
    'image/jpeg',
    'image/jpg',
    'image/gif',
    'image/webp',
    'image/png',
    'image/bmp',
    'video/mp4',
    'video/webm',
  ];

  if (!file) return;
  if (!allowedTypes.includes(file.type)) {
    toast.warning(t('comments.commentSection.toastInvalidMedia'), {
      position: 'top-center',
      bodyClassName: ['cursor-pointer', 'text-black', 'font-bold'],
    });
    return;
  }

  if (file.type.startsWith('video/')) {
    const video = document.createElement('video');
    video.preload = 'metadata';
    const fileURL = URL.createObjectURL(file);
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(fileURL);
      if (video.duration > 30) {
        toast.warning(t('comments.commentSection.toastVideoMaxDuration'), {
          position: 'top-center',
          bodyClassName: ['cursor-pointer', 'text-black', 'font-bold'],
        });
        return;
      }
      previewFile(file, comment);
    };
    video.src = fileURL;
  } else {
    previewFile(file, comment);
  }
}

const previewFile = (file, comment) => {
  comment.replyMediaFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    comment.replyMediaPreview = e.target.result;
  };
  reader.readAsDataURL(file);
  if (file.type.startsWith('image/')) {
    comment.replyIsImage = true;
    comment.replyIsVideo = false;
  } else if (file.type.startsWith('video/')) {
    comment.replyIsImage = false;
    comment.replyIsVideo = true;
  }
};

async function likeComment(comment) {
  if (!requireAuth()) return;
  if (comment.checkUserLike) {
    try {
      await axios.delete(`/api/likes/comment/${comment.id}`);
      comment.showDislikeAnimation = true;
      comment.showLikeAnimation = false;
      comment.checkUserLike = false;
      comment.cntLikes -= 1;
    } catch (error) {
      console.log(error);
    }
  } else {
    try {
      await axios.post(`/api/likes/comment/${comment.id}`);
      comment.showDislikeAnimation = false;
      comment.showLikeAnimation = true;
      comment.checkUserLike = true;
      comment.cntLikes += 1;
    } catch (error) {
      console.log(error);
    }
  }
}

function resetFile(comment) {
  comment.replyIsImage = false;
  comment.replyIsVideo = false;
  comment.replyMediaPreview = null;
  comment.replyMediaFile = null;
}

async function deleteComment(id) {
  try {
    await axios.delete(`/api/admin/comment/${id}`, { withCredentials: true });
    comments.value = comments.value.filter((c) => c.id !== id);
  } catch (error) {
    console.error(error);
  }
}

watch(
  () => props.companyId,
  () => resetAndLoad(),
  { immediate: false }
);

onMounted(resetAndLoad);
</script>

<template>
  <section class="border border-gray-200 rounded-2xl bg-white p-6">
    <h2 class="text-xl font-bold text-gray-900 mb-4">
      {{ t('jobMarket.companyView.commentsTitle') }}
    </h2>

    <div class="flex gap-3 mb-6">
      <textarea
        v-model="draft"
        rows="2"
        class="flex-1 border border-gray-300 rounded-xl px-3 py-2 text-sm"
        :placeholder="t('jobMarket.companyView.commentPlaceholder')"
        @focus="!userStore.isAuthenticated && openAuthModal('login', { redirectTo: `/companies/${companyId}` })"
      />
      <button
        type="button"
        class="self-end px-4 py-2 rounded-xl bg-red-600 text-white text-sm disabled:opacity-50"
        :disabled="posting || !draft.trim()"
        @click="submitTopLevel"
      >
        {{ t('jobMarket.companyView.commentSubmit') }}
      </button>
    </div>

    <div
      ref="commentSection"
      class="flex flex-col gap-1 bg-gray-100 text-sm font-medium text-black min-h-[12rem] max-h-[32rem] w-full overflow-y-auto border-2 border-gray-300 rounded-3xl p-3"
      @scroll="handleScroll"
    >
      <div v-for="comment in comments" :key="comment.id" class="flex flex-col mb-2">
        <div
          v-if="comment.sendCommentError"
          class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]"
        >
          <div class="relative p-4 w-full max-w-md max-h-full">
            <div class="relative bg-white rounded-3xl shadow">
              <div class="p-5 text-center">
                <h3 class="mb-5 text-lg font-normal text-black">
                  {{ t('comments.commentSection.invalidFileModal') }}
                </h3>
                <button
                  type="button"
                  class="text-white bg-red-600 hover:bg-red-800 font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center"
                  @click="comment.sendCommentError = false"
                >
                  {{ t('comments.commentSection.okUnderstand') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <RouterLink
          :to="`/user/${comment.user.username}`"
          class="flex items-center space-x-2 hover:underline cursor-pointer flex-wrap"
        >
          <img
            :src="comment.userImage"
            :alt="t('comments.commentSection.userImageAlt')"
            class="w-10 h-10 rounded-full object-cover bg-gray-200"
          />
          <span class="font-bold">{{ comment.user.username }}</span>
          <span
            v-if="comment.employment_status === 'current'"
            class="inline-flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full no-underline"
            :title="t('jobMarket.companyView.badgeCurrent')"
          >
            <i class="pi pi-briefcase text-[10px]" />
            {{ t('jobMarket.companyView.badgeCurrent') }}
          </span>
          <span
            v-else-if="comment.employment_status === 'former'"
            class="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full no-underline"
            :title="t('jobMarket.companyView.badgeFormer')"
          >
            <i class="pi pi-briefcase text-[10px]" />
            {{ t('jobMarket.companyView.badgeFormer') }}
          </span>
        </RouterLink>

        <div class="relative">
          <div class="absolute top-[-20px] left-10">
            <transition name="flash2">
              <i
                v-if="comment.showDislikeAnimation"
                class="pi pi-heart text-5xl text-white glowing-icon opacity-0"
              />
            </transition>
            <transition name="flash2">
              <i
                v-if="comment.showLikeAnimation"
                class="pi pi-heart-fill text-5xl text-white glowing-icon opacity-0"
              />
            </transition>
          </div>
        </div>

        <span class="font-medium ml-12 mr-12 text-wrap truncate">{{ comment.content }}</span>
        <div class="flex flex-row ml-12">
          <img
            v-if="comment.image && comment.isImage"
            :src="comment.image"
            :alt="t('comments.commentSection.commentImageAlt')"
            class="h-32 w-32 object-cover rounded-lg"
          />
          <video
            v-if="comment.image && comment.isVideo"
            :src="comment.image"
            class="h-32 w-32 object-cover rounded-lg"
            autoplay
            loop
            muted
          />
        </div>

        <div v-if="comment.showReply && !comment.sendComment">
          <div v-if="comment.replyIsImage" class="relative ml-12">
            <div class="absolute top-0 left-[-10px]" @click="resetFile(comment)">
              <i class="pi pi-times text-xs cursor-pointer p-2 text-white bg-black rounded-full" />
            </div>
            <img
              :src="comment.replyMediaPreview"
              class="mt-2 h-28 w-28 object-cover rounded-lg"
              :alt="t('comments.commentSection.mediaPreviewAlt')"
            />
          </div>
          <div v-if="comment.replyIsVideo" class="relative ml-12">
            <div class="absolute top-0 left-[-10px] z-20" @click="resetFile(comment)">
              <i class="pi pi-times text-xs cursor-pointer p-2 text-white bg-black rounded-full" />
            </div>
            <video
              :src="comment.replyMediaPreview"
              class="mt-2 h-32 w-32 object-cover rounded-lg"
              autoplay
              loop
              muted
            />
          </div>
        </div>

        <div
          v-if="comment.showReply && !comment.sendComment"
          class="flex items-center space-x-2 ml-12 mr-4 mt-2"
        >
          <i
            class="pi pi-times text-xs cursor-pointer p-2 text-white bg-black rounded-full"
            @click="comment.showReply = false"
          />
          <div :ref="(el) => (comment.inputAddComment = el)" class="relative w-full">
            <input
              v-model="comment.replyContent"
              type="text"
              autocomplete="off"
              class="transition cursor-pointer bg-gray-50 border border-gray-900 text-black text-sm rounded-3xl py-3 px-5 pr-20 w-full focus:ring-black focus:border-black"
              :placeholder="t('comments.commentSection.addReplyPlaceholder')"
              @keydown.enter="addComment(comment)"
            />
            <button
              type="button"
              class="absolute bottom-0.5 right-12 p-1 transition transform hover:scale-105"
              @click="
                loadPicker(comment);
                comment.showPicker = !comment.showPicker;
              "
            >
              <i class="pi pi-face-smile text-2xl" />
            </button>
            <label :for="`company-reply-${comment.id}`" class="absolute bottom-0.5 right-4 p-1">
              <i class="pi pi-images text-2xl cursor-pointer transition transform hover:scale-105" />
            </label>
            <input
              type="file"
              :id="`company-reply-${comment.id}`"
              accept=".jpg,.jpeg,.gif,.webp,.png,.bmp,.mp4,.webm"
              class="hidden"
              @change="(event) => handleMediaUpload(event, comment)"
            />
            <EmojiPicker
              v-show="comment.showPicker"
              :theme="'dark'"
              :hide-search="true"
              :native="true"
              class="absolute right-0 z-40"
              :style="{
                top: comment.isTop ? '50px' : 'auto',
                bottom: comment.isTop ? 'auto' : '50px',
              }"
              @select="(event) => onSelectEmoji(event, comment)"
            />
          </div>
        </div>

        <div
          v-if="comment.showReply && comment.sendComment"
          class="flex items-center space-x-2 ml-12 mr-4 mt-2 justify-center"
        >
          <span class="loader" />
        </div>

        <div class="flex items-center space-x-2 ml-12 mt-2">
          <span class="font-medium text-gray-600">{{ formatTime(comment.created_at) }}</span>
          <span
            class="text-md hover:underline hover:text-rose-400 cursor-pointer"
            @click="toggleReply(comment)"
          >
            {{ t('comments.commentSection.reply') }}
          </span>
          <div class="flex items-center space-x-2">
            <i
              v-if="comment.checkUserLike"
              class="text-red-600 pi pi-heart-fill text-md cursor-pointer transition-transform duration-200 transform hover:scale-150"
              @click="likeComment(comment)"
            />
            <i
              v-else
              class="text-red-600 pi pi-heart text-md cursor-pointer transition-transform duration-200 transform hover:scale-150"
              @click="likeComment(comment)"
            />
            <div
              v-if="comment.cntLikes != 0"
              class="font-medium text-md relative cursor-pointer"
              @mouseover="
                loadLikesPopover(comment);
                comment.showPopover = true;
              "
              @mouseleave="
                if (!comment.insidePopover) comment.showPopover = false;
              "
            >
              <span :ref="(el) => (comment.likesPopoverEl = el)">{{ comment.cntLikes }}</span>
              <div
                v-if="comment.showPopover"
                class="absolute left-[-100px]"
                :style="{
                  top: comment.likesIsTop ? '20px' : 'auto',
                  bottom: comment.likesIsTop ? 'auto' : '20px',
                }"
                @mouseover="comment.insidePopover = true"
                @mouseleave="
                  comment.insidePopover = false;
                  comment.showPopover = false;
                "
              >
                <CommentLikesPopover :comment_id="comment.id" />
              </div>
            </div>
          </div>
          <span
            v-if="userStore.hasRole('admin')"
            class="text-md hover:underline hover:text-rose-400 cursor-pointer"
            @click="deleteComment(comment.id)"
          >
            {{ t('comments.commentSection.delete') }}
          </span>
        </div>

        <div
          v-if="comment.cntReplies != 0"
          class="ml-12 text-gray-700 text-sm mt-4 italic cursor-pointer mb-2 flex items-center justify-between"
          @click="comment.showReplies = !comment.showReplies"
        >
          <h1 v-if="!comment.showReplies">
            {{ t('comments.commentSection.viewReplies', { count: comment.cntReplies }) }}
          </h1>
          <h1 v-else>{{ t('comments.commentSection.hideReplies') }}</h1>
          <span
            class="transition-transform duration-300 mr-5"
            :class="{ 'rotate-180': comment.showReplies }"
          >
            <i class="pi pi-angle-down text-sm" />
          </span>
        </div>
        <div class="ml-12">
          <ReplyCommentSection v-if="comment.showReplies" :comment_id="comment.id" />
        </div>
      </div>

    </div>
  </section>
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
    transform: rotate(360deg);
  }
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

.glowing-icon {
  text-shadow:
    0 0 15px rgba(255, 0, 0, 0.7),
    0 0 25px rgba(255, 0, 0, 0.6),
    0 0 35px rgba(255, 0, 0, 0.5);
}
</style>
