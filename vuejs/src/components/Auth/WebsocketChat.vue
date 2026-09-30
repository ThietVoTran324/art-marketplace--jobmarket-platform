<script setup>
import axios from 'axios';
import { onMounted, onBeforeUnmount, ref, nextTick, watch, computed } from 'vue';
import FollowersSection from './FollowersSection.vue';
import FollowingSection from './FollowingSection.vue';
import { RouterLink, useRoute } from 'vue-router';
import double_check from '@/assets/double_check.png';
import single_check from '@/assets/single_check.png';
import EmojiPicker from 'vue3-emoji-picker'
import 'vue3-emoji-picker/css'

import { useToast } from "vue-toastification";
import { useI18n } from 'vue-i18n';
const toast = useToast();
const { t } = useI18n();

import { useUnreadMessagesStore } from "@/stores/unreadMessages";
const unreadMessagesStore = useUnreadMessagesStore();

import { useChatStore } from "@/stores/useChatStore";

const isNewDay = (index) => {
  const list = displayedMessages.value
  if (index === list.length - 1) return true;
  const currentDate = dayjs.utc(list[index].created_at).local().format('YYYY-MM-DD');
  const previousDate = dayjs.utc(list[index + 1].created_at).local().format('YYYY-MM-DD');
  return currentDate !== previousDate;
};

const chatStore = useChatStore();

const route = useRoute()

const imageLoaded = ref(false)
const sectionLoaded = ref(false)

import ClipLoader from 'vue-spinner/src/ClipLoader.vue'

const color = ref('red')
const size = ref('100px')

function onSelectEmoji(emoji) {
  message.value += emoji.i
}

const showPicker = ref(false)

const colorMap = {
  red: { track: "#f3f4f6", thumb: "#e11d48" },
  blue: { track: "#f3f4f6", thumb: "#2563eb" },
  lime: { track: "#f3f4f6", thumb: "#65a30d" },
  yellow: { track: "#f3f4f6", thumb: "#ca8a04" },
  purple: { track: "#f3f4f6", thumb: "#7c3aed" },
};

watch(() => chatStore.bgColor, (newColor) => {
  if (colorMap[newColor]) {
    document.documentElement.style.setProperty("--scrollbar-track-bg", colorMap[newColor].track);
    document.documentElement.style.setProperty("--scrollbar-thumb-bg", colorMap[newColor].thumb);
    document.documentElement.style.setProperty("--selection-bg", colorMap[newColor].thumb);
  }
}, { immediate: true });

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc"; // Adding UTC support
import timezone from "dayjs/plugin/timezone"; // Adding timezone support
import "dayjs/locale/en"; // Use the English locale

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale("en"); // Set the English locale

const emit = defineEmits(['updateLastMessage', 'back'])

const showThreadSearch = ref(false)
const threadSearch = ref('')

function toggleThreadSearch() {
  showThreadSearch.value = !showThreadSearch.value
  if (!showThreadSearch.value) threadSearch.value = ''
}

let socket;

const chatBox = ref(null);

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight;
    }
  });
};

const cntUnreadMessages = ref(null)

const messages = ref([]);
const message = ref("");
const isTyping = ref(false)
let typingTimeout = null;

const isSendingMedia = ref(false)

const formatTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

const formattedTimeRemaining = (message) => {
  return computed(() => {
    if (!message.videoDuration) return "0:00";
    const timeRemaining = Math.max(message.videoDuration - message.currentTime, 0);
    return formatTime(timeRemaining);
  });
};

const onTimeUpdate = (message, event) => {
  message.currentTime = event.target.currentTime;
};

const onVideoLoad = (message, event) => {
  message.videoDuration = event.target.duration;
};

watch(message, (newValue, oldValue) => {
  if (newValue.trim() !== '') {
    isTyping.value = true;

    if (typingTimeout) clearTimeout(typingTimeout);

    typingTimeout = setTimeout(() => {
      isTyping.value = false;
    }, 2000);
  } else {
    if (oldValue.trim() !== '') {
      isTyping.value = false;
    }
  }
});

watch(isTyping, (newValue) => {
  if (newValue) {
    socket.send(JSON.stringify({ 'user_start_typing': true }));
  } else {
    socket.send(JSON.stringify({ 'user_stop_typing': true }));
  }
});

const messageInput = ref(null)

const offset = ref(0);
const limit = ref(10);

const isPinsLoading = ref(false);

const messagesTemp = ref(null)

const canLoad = ref(true)

async function loadMessages() {
  if (isPinsLoading.value) {
    return;
  }

  if (!canLoad.value) {
    return
  }

  isPinsLoading.value = true;

  try {
    const response = await axios.get(`/api/messages/history/${props.chat_id}`, { params: { offset: offset.value, limit: limit.value } })
    messagesTemp.value = response.data
    if (messagesTemp.value.length < limit.value) {
      canLoad.value = false
    }
    for (let i = 0; i < messagesTemp.value.length; i++) {
      if (messagesTemp.value[i].user_id_ !== props.auth_user_id && messagesTemp.value[i].is_read === false) {
        try {
          const response = await axios.patch(`/api/messages/read/${messagesTemp.value[i].id}`)
        } catch (error) {
          console.log(error)
        }
        cntUnreadMessages.value -= 1
        props.chat.cntUnreadMessages -= 1
        if (unreadMessagesStore.count > 0) {
          unreadMessagesStore.decrement()
          if (cntUnreadMessages.value === 0) {
            socket.send(JSON.stringify({ 'user_read_messages': true }));
          }
        }
      }
      if (messagesTemp.value[i].image) {
        try {
          const response = await axios.get(`/api/messages/upload/${messagesTemp.value[i].id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(response.data);
          messagesTemp.value[i].media = blobUrl
          const contentType = response.headers['content-type'];
          if (contentType.startsWith('image/')) {
            messagesTemp.value[i].isImage = true;
          } else {
            messagesTemp.value[i].isImage = false;
            messagesTemp.value[i].videPlayer = null
            messagesTemp.value[i].videoLoaded = false
            messagesTemp.value[i].videoDuration = 0
            messagesTemp.value[i].currentTime = 0
          }
        } catch (error) {
          console.error(error);
        }
      }
      if (messagesTemp.value[i].pin_id) {
        messagesTemp.value[i].pinMeta = await ensurePinMeta(messagesTemp.value[i].pin_id)
      }
      messages.value.push(messagesTemp.value[i])
    }
  } catch (error) {
    console.error(error)
  }

  offset.value += limit.value;
  isPinsLoading.value = false;
  if (cntUnreadMessages.value !== 0) {
    loadMessages()
  }
}

const handleScroll = (event) => {
  const container = event.target;

  if (container.scrollHeight + container.scrollTop < 700) {

    loadMessages();
  }
};

const isOnline = ref(false)

const typing = ref(false)

const connectWebSocket = async () => {
  return new Promise((resolve, reject) => {
    socket = new WebSocket(`/ws/${props.chat_id}/${props.auth_user_id}`);

    socket.onopen = () => {
      resolve();
    };

    socket.onerror = (error) => {
      reject(error);
    };

    socket.onmessage = async (event) => {
      let showToast = false
      try {
        const messageObj = JSON.parse(event.data);
        if ("online" in messageObj) {
          if (messageObj.online == true) {
            isOnline.value = true
            props.chat.last_message.is_read = true
          } else {
            isOnline.value = false
          }
          for (let i = 0; i < messages.value.length; i++) {
            if (messages.value[i].user_id_ === props.auth_user_id) {
              if (messages.value[i].is_read === false) {
                messages.value[i].is_read = true
              } else {
                break
              }
            }
          }
          return
        }
        if ("user_start_sending_media" in messageObj) {
          isSendingMedia.value = true
          return
        }
        if ("user_stop_sending_media" in messageObj) {
          isSendingMedia.value = false
          return
        }
        if ("user_start_typing" in messageObj) {
          typing.value = true
          return
        }
        if ("user_stop_typing" in messageObj) {
          typing.value = false
          return
        }
        try {
          await axios.patch(`/api/messages/read/${messageObj.id}`)
        } catch (error) {
          console.log(error)
        }
        if (messageObj.image) {
          try {
            const response = await axios.get(`/api/messages/upload/${messageObj.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            messageObj.media = blobUrl
          } catch (error) {
            console.error(error);
          }
        }
        messages.value.unshift(messageObj);
        if (route.name !== 'messages') {
          showToast = true
        }
      } catch (error) {
        console.error("Failed to parse JSON:", error);
      }
      scrollToBottom();
      emit('updateLastMessage', showToast, props.chat_id)
    };
  });
};

// const connectWebSocket = async () => {
//   socket = new WebSocket(`/ws/${props.chat_id}/${props.auth_user_id}`);

//   socket.onmessage = async (event) => {
//     let showToast = false
//     try {
//       const messageObj = JSON.parse(event.data);
//       if ("online" in messageObj) {
//         if (messageObj.online == true) {
//           isOnline.value = true
//           props.chat.last_message.is_read = true
//         } else {
//           isOnline.value = false
//         }
//         for (let i = 0; i < messages.value.length; i++) {
//           if (messages.value[i].user_id_ === props.auth_user_id) {
//             if (messages.value[i].is_read === false) {
//               messages.value[i].is_read = true
//             } else {
//               break
//             }
//           }
//         }
//         return
//       }
//       if ("user_start_sending_media" in messageObj) {
//         isSendingMedia.value = true
//         return
//       }
//       if ("user_stop_sending_media" in messageObj) {
//         isSendingMedia.value = false
//         return
//       }
//       if ("user_start_typing" in messageObj) {
//         typing.value = true
//         return
//       }
//       if ("user_stop_typing" in messageObj) {
//         typing.value = false
//         return
//       }
//       try {
//         await axios.patch(`/api/messages/read/${messageObj.id}`)
//       } catch (error) {
//         console.log(error)
//       }
//       if (messageObj.image) {
//         try {
//           const response = await axios.get(`/api/messages/upload/${messageObj.id}`, { responseType: 'blob' });
//           const blobUrl = URL.createObjectURL(response.data);
//           messageObj.media = blobUrl
//         } catch (error) {
//           console.error(error);
//         }
//       }
//       messages.value.unshift(messageObj);
//       if (route.name !== 'messages') {
//         showToast = true
//       }
//     } catch (error) {
//     }
//     scrollToBottom();
//     emit('updateLastMessage', showToast, props.chat_id)
//   };
// };

const sendingMessage = ref(false)

const sendMessage = async () => {
  if (message.value.trim() && socket.readyState === WebSocket.OPEN) {
    sendingMessage.value = true
    showPicker.value = false
    const response = await axios.post('/api/messages/', {
      content: message.value.trim(),
      chat_id: props.chat_id
    }, { withCredentials: true })
    const messageResp = response.data
    const contentType = response.headers['content-type'];
    if (contentType.startsWith('image/')) {
      messageResp.isImage = true;
    } else {
      messageResp.isImage = false;
    }
    if (isOnline.value === true) {
      messageResp.is_read = true
    }
    messages.value.unshift(messageResp)
    socket.send(JSON.stringify(messageResp));
    message.value = "";
    scrollToBottom();
    sendingMessage.value = false
    await nextTick()
    messageInput.value.focus()
    emit('updateLastMessage', false, props.chat_id, isOnline.value)
  }
};

const props = defineProps({
  chat_id: Number,
  auth_user_id: Number,
  user_to_load: Number,
  chat: Object,
})

const displayedMessages = computed(() => {
  const q = threadSearch.value.trim().toLowerCase()
  if (!q) return messages.value
  return messages.value.filter((m) => (m.content || '').toLowerCase().includes(q))
})

const chatMuted = computed(() => chatStore.isMuted(props.chat?.id))
const chatPinned = computed(() => chatStore.isPinned(props.chat?.id))
const isGroupChat = computed(
  () => props.chat?.kind === 'group' || props.chat?.isGroup === true
)

const historyTab = ref('media') // media | links
const historyItems = ref([])
const historyLoading = ref(false)
const inviteCode = ref(null)
const pinCache = ref({})

async function loadHistory(tab = historyTab.value) {
  if (!props.chat_id) return
  historyLoading.value = true
  historyTab.value = tab
  try {
    const path = tab === 'media'
      ? `/api/messages/${props.chat_id}/media`
      : `/api/messages/${props.chat_id}/links`
    const { data } = await axios.get(path, {
      params: { offset: 0, limit: 40 },
      withCredentials: true,
    })
    historyItems.value = data || []
    for (const m of historyItems.value) {
      if (m.image) {
        try {
          const res = await axios.get(`/api/messages/upload/${m.id}`, { responseType: 'blob' })
          m.media = URL.createObjectURL(res.data)
          m.isImage = (res.headers['content-type'] || '').startsWith('image/')
        } catch { /* ignore */ }
      }
    }
  } catch (e) {
    console.error(e)
    historyItems.value = []
  } finally {
    historyLoading.value = false
  }
}

async function loadInviteCode() {
  if (!isGroupChat.value) return
  try {
    const { data } = await axios.get(`/api/messages/groups/${props.chat_id}/invite-code`, {
      withCredentials: true,
    })
    inviteCode.value = data.invite_code
  } catch (e) {
    console.error(e)
  }
}

async function copyInviteCode() {
  if (!inviteCode.value) await loadInviteCode()
  if (!inviteCode.value) return
  try {
    await navigator.clipboard.writeText(inviteCode.value)
    toast.success(t('chat.websocketChat.toastGroupCodeCopied'))
  } catch {
    toast.error(t('chat.websocketChat.toastCopyFailed'))
  }
}

async function ensurePinMeta(pinId) {
  if (!pinId || pinCache.value[pinId]) return pinCache.value[pinId]
  try {
    const { data } = await axios.get(`/api/pins/${pinId}`)
    pinCache.value = { ...pinCache.value, [pinId]: data }
    return data
  } catch {
    return null
  }
}

const user = ref(null)
const userImage = ref(null)
const cntUserFollowers = ref(null)
const cntUserFollowing = ref(null)
const checkUserFollow = ref(null)
const showFollowers = ref(null)
const showFollowing = ref(null)

onMounted(async () => {
  try {
    const response = await axios.get(`/api/messages/unread/cnt/${props.chat_id}`, { withCredentials: true })
    cntUnreadMessages.value = response.data
  } catch (error) {
    console.log(error)
  }
  await connectWebSocket();
  loadMessages();

  if (!isGroupChat.value && props.chat?.user?.id) {
    try {
      const response = await axios.get(`/api/subscription/followers/cnt/${props.chat.user.id}`, { withCredentials: true });
      cntUserFollowers.value = response.data;
    } catch (error) {
      console.error(error);
    }
    try {
      const response = await axios.get(`/api/subscription/following/cnt/${props.chat.user.id}`, { withCredentials: true });
      cntUserFollowing.value = response.data;
    } catch (error) {
      console.error(error);
    }
    try {
      const response = await axios.get(`/api/subscription/check_user_follow/${props.chat.user.id}`, { withCredentials: true });
      checkUserFollow.value = response.data;
    } catch (error) {
      console.error(error);
    }
  }

  if (isGroupChat.value) {
    await loadInviteCode()
  }
  await loadHistory('media')
  sectionLoaded.value = true
})

onBeforeUnmount(() => {
  if (socket) {
    socket.close();
  }
});

const mediaFile = ref(null)
const mediaPreview = ref(null)
const isImage = ref(false)
const isVideo = ref(false)

function handleMediaUpload(event) {
  const file = event.target.files[0];
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp', 'video/mp4', 'video/webm'];

  if (file) {
    if (!allowedTypes.includes(file.type)) {
      toast.warning(t('chat.websocketChat.toastInvalidMedia'), { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
      return;
    }
    previewFile(file);
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
  openSendMedia.value = true
};

const messageContent = ref('')

const sendingMessageMedia = ref(false)

const fileError = ref(false)

async function sendMediaMessage() {

  sendingMessageMedia.value = true

  socket.send(JSON.stringify({ 'user_start_sending_media': true }));

  const formData = new FormData();
  formData.append("file", mediaFile.value);

  const jsonData = JSON.stringify({
    content: messageContent.value.trim(),
    chat_id: props.chat_id
  });

  formData.append("message", jsonData);

  let response = null;
  try {
    response = await axios.post("/api/messages/create-message-entity", formData, {
      withCredentials: true,
      headers: {
        "Content-Type": "multipart/form-data"
      }
    });
  } catch (error) {
    if (error.response.status === 415) {
      fileError.value = true
      sendingMessageMedia.value = false
      socket.send(JSON.stringify({ 'user_stop_sending_media': true }));
      return;
    }
  }

  const messageResp = response.data

  // const response = await axios.post('/api/messages/', {
  //   content: messageContent.value,
  //   chat_id: props.chat_id
  // }, { withCredentials: true })

  // const messageResp = response.data

  // const formData = new FormData();
  // formData.append('file', mediaFile.value);

  // const response = await axios.post(`/api/messages/upload/${messageResp.id}`, formData, {
  //   headers: {
  //     'Content-Type': 'multipart/form-data',
  //   },
  // });

  // const data = response.data
  // messageResp.image = data.image

  try {
    const response = await axios.get(`/api/messages/upload/${messageResp.id}`, { responseType: 'blob' });
    const blobUrl = URL.createObjectURL(response.data);
    messageResp.media = blobUrl
    const contentType = response.headers['content-type'];
    if (contentType.startsWith('image/')) {
      messageResp.isImage = true;
    } else {
      messageResp.isImage = false;
    }
  } catch (error) {
    console.error(error);
  }

  messages.value.unshift(messageResp)
  socket.send(JSON.stringify(messageResp));
  socket.send(JSON.stringify({ 'user_stop_sending_media': true }));
  messageContent.value = "";

  openSendMedia.value = false
  mediaPreview.value = null;
  showPreview.value = false

  if (isOnline.value === true) {
    messageResp.is_read = true
    props.chat.last_message.is_read = true
  }
  scrollToBottom();
  sendingMessageMedia.value = false
  emit('updateLastMessage', false, props.chat_id, isOnline.value)
}

const openSendMedia = ref(false)

async function follow() {
  try {
    const response = await axios.post(`/api/subscription/${props.chat.user.id}`, { withCredentials: true })
  } catch (error) {
    console.log(error)
  }
  checkUserFollow.value = true
  cntUserFollowers.value += 1
}

async function unfollow() {
  try {
    const response = await axios.delete(`/api/subscription/${props.chat.user.id}`, { withCredentials: true })
  } catch (error) {
    console.log(error)
  }
  checkUserFollow.value = false
  cntUserFollowers.value -= 1
}

async function updateColor(color) {
  try {
    await axios.patch(`/api/chats/color?color=${color}`)
    chatStore.setChatColor(color)
  } catch (error) {
    console.log(error)
  }
}

const startResize = (event) => {
  const startX = event.clientX;
  const startWidth = chatStore.size;

  document.body.style.userSelect = "none";

  const onMouseMove = (moveEvent) => {
    let newWidth = startWidth + (moveEvent.clientX - startX);
    newWidth = Math.max(200, Math.min(newWidth, 800));

    if (newWidth === 200) {
      newWidth = 80;
    }

    chatStore.size = newWidth;
  };

  const onMouseUp = async () => {
    try {
      await axios.patch(`/api/chats/size?size=${chatStore.size}`)
    } catch (error) {
      console.log(error)
    }
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);

    document.body.style.userSelect = "";
  };

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
};

async function updateSide(side) {
  try {
    await axios.patch(`/api/chats/side?side=${side}`)
    chatStore.setSide(side)
  } catch (error) {
    console.log(error)
  }
}

const showPreview = ref(false)

const fullscreenImage = ref(null);

const videoElement = ref(null);

const openFullscreen = (imageSrc) => {
  fullscreenImage.value = imageSrc;
};

const closeFullscreen = () => {
  fullscreenImage.value = null;
};

const fullscreenVideo = ref(null);

const openFullscreenVideo = (videoSrc) => {
  fullscreenVideo.value = videoSrc;
};

const closeFullscreenVideo = () => {
  fullscreenVideo.value = null;
};

const setVolume = () => {
  if (videoElement.value) {
    videoElement.value.volume = 0.5;
  }
};

function showVideo(message) {
  message.loaded = true
}

</script>

<template>

  <div v-if="fileError" class="fixed inset-0 flex items-center justify-center bg-black/50 z-[60]">
    <div class="relative p-4 w-full max-w-md">
      <div class="bg-white rounded-2xl shadow p-5 text-center">
        <h3 class="mb-4 text-base text-gray-800">
          {{ t('chat.websocketChat.fileErrorTitle') }}
        </h3>
        <button
          type="button"
          class="text-white bg-[var(--msg-accent)] hover:opacity-90 font-medium rounded-full text-sm px-5 py-2"
          @click="fileError = false"
        >
          {{ t('chat.websocketChat.ok') }}
        </button>
      </div>
    </div>
  </div>

  <transition name="fade" appear>
    <div v-if="showFollowers" class="fixed inset-0 bg-black/75 z-40 p-6">
      <div class="flex justify-center items-center min-h-screen" @click.self="showFollowers = false">
        <FollowersSection :user_id="chat.user.id" :cntUserFollowers="cntUserFollowers" />
        <i
          class="absolute right-20 top-20 pi pi-times text-white text-3xl cursor-pointer"
          @click="showFollowers = false"
        />
      </div>
    </div>
  </transition>

  <transition name="fade" appear>
    <div v-if="showFollowing" class="fixed inset-0 bg-black/75 z-40 p-6">
      <div class="flex justify-center items-center min-h-screen" @click.self="showFollowing = false">
        <FollowingSection :user_id="chat.user.id" :cntUserFollowing="cntUserFollowing" />
        <i
          class="absolute right-20 top-20 pi pi-times text-white text-3xl cursor-pointer"
          @click="showFollowing = false"
        />
      </div>
    </div>
  </transition>

  <transition name="fade2" appear>
    <div v-if="openSendMedia" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <ClipLoader v-show="sendingMessageMedia" color="var(--msg-accent)" :size="size"
        class="flex items-center justify-center min-h-screen font-extrabold" />
      <div
        v-show="!sendingMessageMedia"
        class="flex flex-col bg-white rounded-2xl max-h-[90vh] w-[min(420px,92vw)] overflow-hidden shadow-xl"
      >
        <div v-if="isImage">
          <img
            v-show="showPreview === true"
            :src="mediaPreview"
            class="w-full max-h-[520px] object-contain bg-gray-50"
            :alt="t('chat.websocketChat.mediaPreviewAlt')"
            @load="showPreview = true"
          />
        </div>
        <div v-if="isVideo">
          <video
            v-show="showPreview === true"
            :src="mediaPreview"
            class="w-full max-h-[520px] object-contain bg-gray-50"
            autoplay
            loop
            muted
            @loadeddata="showPreview = true"
          />
        </div>
        <input
          id="messageInputMedia"
          v-model="messageContent"
          :placeholder="t('chat.websocketChat.mediaCaptionPlaceholder')"
          autofocus
          autocomplete="off"
          class="mx-4 mt-3 py-2 border-b border-gray-200 outline-none"
        />
        <div class="flex justify-end gap-2 p-3">
          <button
            type="button"
            class="px-4 py-2 rounded-full text-sm text-gray-600 hover:bg-gray-100"
            @click="openSendMedia = false; mediaPreview = null; showPreview = false"
          >
            {{ t('chat.websocketChat.cancel') }}
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-full text-sm text-white bg-[var(--msg-accent)]"
            @click="sendMediaMessage"
          >
            {{ t('chat.websocketChat.send') }}
          </button>
        </div>
      </div>
    </div>
  </transition>

  <div
    v-if="fullscreenImage"
    class="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
    @click="closeFullscreen"
  >
    <img :src="fullscreenImage" class="max-w-full max-h-full" @click.stop />
    <button
      type="button"
      class="absolute top-4 right-4 text-gray-300 text-3xl font-bold hover:text-white"
      @click="closeFullscreen"
    >
      ✕
    </button>
  </div>

  <div
    v-if="fullscreenVideo"
    class="fixed inset-0 bg-black/80 flex items-center justify-center z-50"
    @click="closeFullscreenVideo"
  >
    <video
      ref="videoElement"
      :src="fullscreenVideo"
      class="w-auto h-auto max-w-full max-h-full rounded-lg"
      autoplay
      loop
      controls
      @click.stop
    />
    <button
      type="button"
      class="absolute top-4 right-4 text-gray-300 text-3xl font-bold hover:text-white"
      @click="closeFullscreenVideo"
    >
      ✕
    </button>
  </div>

  <div class="flex h-full w-full min-h-0 bg-[#f0f2f5]">
    <!-- Thread column -->
    <div class="flex flex-col flex-1 min-w-0 min-h-0">
      <!-- Header -->
      <header class="h-14 shrink-0 flex items-center gap-2 px-3 bg-white border-b border-gray-200">
        <button
          type="button"
          class="md:hidden w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center"
          :aria-label="t('chat.websocketChat.backToChatsAria')"
          @click="emit('back')"
        >
          <i class="pi pi-arrow-left text-lg text-gray-700" />
        </button>

        <RouterLink
          v-if="!isGroupChat"
          :to="`/user/${chat.user.username}`"
          class="flex-none"
        >
          <img
            :src="chat.userImage"
            alt=""
            class="w-10 h-10 rounded-full object-cover bg-gray-200"
          />
        </RouterLink>
        <div
          v-else
          class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-none"
        >
          <i class="pi pi-users text-gray-600" />
        </div>

        <div class="flex flex-col min-w-0 flex-1">
          <component
            :is="isGroupChat ? 'span' : RouterLink"
            v-bind="isGroupChat ? {} : { to: `/user/${chat.user.username}` }"
            class="font-semibold text-gray-900 truncate"
            :class="isGroupChat ? '' : 'hover:underline'"
          >
            {{ isGroupChat ? (chat.title || chat.user?.username || t('messages.defaults.groupName')) : chat.user.username }}
          </component>
          <span
            v-show="!typing && !isSendingMedia"
            class="text-xs"
            :class="isOnline ? 'text-[var(--msg-accent)]' : 'text-gray-500'"
          >
            {{ isOnline ? t('chat.websocketChat.activeNow') : t('chat.websocketChat.lastSeenRecently') }}
          </span>
          <span
            v-show="typing && !isSendingMedia"
            class="text-xs text-[var(--msg-accent)] typing-animation"
          >{{ t('chat.websocketChat.typing') }}</span>
          <span
            v-show="isSendingMedia"
            class="text-xs text-[var(--msg-accent)]"
          >{{ t('chat.websocketChat.sendingMedia') }}</span>
        </div>

        <button
          type="button"
          class="w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center"
          :class="showThreadSearch ? 'bg-gray-100' : ''"
          :title="t('chat.websocketChat.searchInConversationTitle')"
          @click="toggleThreadSearch"
        >
          <i class="pi pi-search text-gray-600" />
        </button>
        <button
          type="button"
          class="w-9 h-9 rounded-full hover:bg-gray-100 flex items-center justify-center"
          :class="chatStore.side ? 'bg-gray-100' : ''"
          :title="t('chat.websocketChat.chatInfoTitle')"
          @click="updateSide(!chatStore.side)"
        >
          <i class="pi pi-info-circle text-gray-600" />
        </button>
      </header>

      <!-- In-thread search -->
      <div v-if="showThreadSearch" class="shrink-0 px-3 py-2 bg-white border-b border-gray-100">
        <input
          v-model="threadSearch"
          type="search"
          :placeholder="t('chat.websocketChat.searchInConversationPlaceholder')"
          class="w-full px-3 py-2 text-sm rounded-full bg-gray-100 outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
        />
        <p v-if="threadSearch.trim()" class="text-xs text-gray-500 mt-1 px-1">
          {{ displayedMessages.length === 1 ? t('chat.websocketChat.matchOne', { count: displayedMessages.length }) : t('chat.websocketChat.matchMany', { count: displayedMessages.length }) }}
        </p>
      </div>

      <!-- Messages -->
      <div
        id="chatBox"
        ref="chatBox"
        class="flex-1 min-h-0 overflow-y-auto px-3 py-3 flex flex-col-reverse gap-0.5"
        @scroll="handleScroll"
      >
        <div v-for="(message, index) in displayedMessages" :key="message.id" class="w-full">
          <div v-if="isNewDay(index)" class="text-center my-3">
            <span class="inline-block bg-white/90 text-gray-600 text-xs px-3 py-1 rounded-full shadow-sm">
              {{ dayjs.utc(message.created_at).local().format('DD MMM YYYY') }}
            </span>
          </div>

          <div
            class="flex my-0.5"
            :class="message.user_id_ === auth_user_id ? 'justify-end' : 'justify-start'"
          >
            <div
              class="relative flex flex-col max-w-[min(420px,78%)] shadow-sm overflow-hidden"
              :class="[
                message.user_id_ === auth_user_id
                  ? 'bg-[var(--msg-accent)] text-white rounded-2xl rounded-br-md'
                  : 'bg-white text-gray-900 rounded-2xl rounded-bl-md',
              ]"
            >
              <img
                v-if="message.media && message.isImage"
                :src="message.media"
                class="w-auto h-auto max-h-[420px] cursor-pointer"
                :class="message.content ? '' : 'rounded-2xl'"
                @click="openFullscreen(message.media)"
              />

              <div class="relative">
                <div
                  v-if="message.videoDuration"
                  class="absolute top-2 left-2 bg-black/50 text-white rounded-full px-2 py-0.5 text-xs z-10"
                >
                  {{ formattedTimeRemaining(message).value }}
                </div>
                <video
                  v-if="message.media && !message.isImage"
                  :ref="el => { if (el) message.videoPlayer = el; }"
                  :src="message.media"
                  class="w-auto h-auto max-h-[420px] cursor-pointer"
                  autoplay
                  loop
                  muted
                  @loadeddata="onVideoLoad(message, $event)"
                  @timeupdate="onTimeUpdate(message, $event)"
                  @click="openFullscreenVideo(message.media)"
                />
              </div>

              <div v-if="message.pin_id" class="p-2">
                <RouterLink
                  :to="`/pin/${message.pin_id}`"
                  class="block rounded-xl overflow-hidden bg-black/10 hover:opacity-95"
                >
                  <div class="px-3 py-2 text-sm font-medium">
                    {{ t('chat.websocketChat.sharedPinLabel') }}
                  </div>
                  <div class="px-3 pb-2 text-xs opacity-80 truncate">
                    {{ message.pinMeta?.title || message.content || t('chat.websocketChat.openPinFallback') }}
                  </div>
                </RouterLink>
              </div>

              <div v-else-if="message.content" class="px-3 pt-2 pb-0.5">
                <span class="text-[15px] leading-snug whitespace-pre-wrap break-words">{{ message.content }}</span>
              </div>

              <div
                class="flex items-center gap-1 px-3 pb-1.5 pt-0.5"
                :class="message.user_id_ === auth_user_id ? 'text-white/80' : 'text-gray-400'"
              >
                <span class="text-[11px] ml-auto tabular-nums">
                  {{ dayjs.utc(message.created_at).local().format('HH:mm') }}
                </span>
                <template v-if="message.user_id_ === auth_user_id">
                  <img
                    v-if="message.is_read === false"
                    :src="single_check"
                    alt=""
                    class="h-3.5 w-3.5 brightness-0 invert opacity-80"
                  />
                  <img
                    v-else-if="message.is_read === true"
                    :src="double_check"
                    alt=""
                    class="h-3.5 w-3.5 brightness-0 invert opacity-90"
                  />
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Composer -->
      <div class="shrink-0 bg-white border-t border-gray-200 px-3 py-2">
        <div v-show="!sendingMessage" class="flex items-end gap-2">
          <label
            for="mediaChats"
            class="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 cursor-pointer text-gray-600"
            :title="t('chat.websocketChat.attachTitle')"
          >
            <i class="pi pi-paperclip text-xl" />
          </label>
          <input
            id="mediaChats"
            type="file"
            name="media"
            accept=".jpg,.jpeg,.gif,.webp,.png,.bmp,.mp4,.webm"
            class="hidden"
            @change="handleMediaUpload"
          />

          <div class="flex-1 relative">
            <input
              id="messageInput"
              ref="messageInput"
              v-model="message"
              type="text"
              :placeholder="t('chat.websocketChat.messagePlaceholder')"
              autocomplete="off"
              autofocus
              class="w-full rounded-full bg-gray-100 px-4 py-2.5 text-[15px] outline-none focus:ring-2 focus:ring-[var(--msg-accent)]"
              @keyup.enter="sendMessage"
            />
            <EmojiPicker
              v-show="showPicker"
              :theme="'light'"
              :hide-search="true"
              :native="true"
              class="absolute bottom-12 right-0 z-20"
              @select="onSelectEmoji"
            />
          </div>

          <button
            type="button"
            class="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-600"
            @click="showPicker = !showPicker"
          >
            <i class="pi pi-face-smile text-xl" />
          </button>
          <button
            type="button"
            class="w-10 h-10 flex items-center justify-center rounded-full text-white bg-[var(--msg-accent)] disabled:opacity-40"
            :disabled="!message.trim()"
            :title="t('chat.websocketChat.sendTitle')"
            @click="sendMessage"
          >
            <i class="pi pi-send text-sm" />
          </button>
        </div>
        <div v-show="sendingMessage" class="h-11 flex items-center justify-center">
          <span class="loader" />
        </div>
      </div>
    </div>

    <!-- Info panel -->
    <aside
      v-show="chatStore.side"
      class="hidden md:flex w-[300px] shrink-0 flex-col bg-white border-l border-gray-200 min-h-0 overflow-y-auto"
    >
      <div class="p-5 flex flex-col items-center text-center border-b border-gray-100">
        <RouterLink v-if="!isGroupChat" :to="`/user/${chat.user.username}`">
          <img
            :src="chat.userImage"
            class="w-24 h-24 rounded-full object-cover bg-gray-200"
            alt=""
          />
        </RouterLink>
        <div
          v-else
          class="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center"
        >
          <i class="pi pi-users text-3xl text-gray-500" />
        </div>
        <component
          :is="isGroupChat ? 'span' : RouterLink"
          v-bind="isGroupChat ? {} : { to: `/user/${chat.user.username}` }"
          class="mt-3 text-lg font-semibold text-gray-900"
          :class="isGroupChat ? '' : 'hover:underline'"
        >
          {{ isGroupChat ? (chat.title || t('messages.defaults.groupName')) : chat.user.username }}
        </component>
        <span
          v-if="!isGroupChat"
          class="text-sm"
          :class="isOnline ? 'text-[var(--msg-accent)]' : 'text-gray-500'"
        >
          {{ isOnline ? t('chat.websocketChat.activeNow') : t('chat.websocketChat.lastSeenRecently') }}
        </span>
      </div>

      <div v-show="sectionLoaded" class="p-4 space-y-3">
        <template v-if="!isGroupChat">
          <div
            v-if="cntUserFollowers || cntUserFollowing"
            class="flex items-center justify-center gap-3 text-sm text-gray-600"
          >
            <button
              v-if="cntUserFollowers"
              type="button"
              class="hover:underline hover:text-[var(--msg-accent)]"
              @click="showFollowers = true"
            >
              {{ t('chat.websocketChat.followersCount', { count: cntUserFollowers }) }}
            </button>
            <button
              v-if="cntUserFollowing"
              type="button"
              class="hover:underline hover:text-[var(--msg-accent)]"
              @click="showFollowing = true"
            >
              {{ t('chat.websocketChat.followingCount', { count: cntUserFollowing }) }}
            </button>
          </div>

          <p
            v-if="chat.user.description"
            class="text-sm text-gray-600 line-clamp-3 text-left"
          >
            {{ chat.user.description }}
          </p>

          <button
            v-if="!checkUserFollow"
            type="button"
            class="w-full py-2 rounded-full text-sm font-medium text-white bg-[var(--msg-accent)]"
            @click="follow"
          >
            {{ t('chat.websocketChat.follow') }}
          </button>
          <button
            v-else
            type="button"
            class="w-full py-2 rounded-full text-sm font-medium bg-gray-100 text-gray-800 hover:bg-gray-200"
            @click="unfollow"
          >
            {{ t('chat.websocketChat.followingButton') }}
          </button>
        </template>

        <div v-else class="space-y-2">
          <button
            type="button"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left text-sm"
            @click="copyInviteCode"
          >
            <i class="pi pi-copy text-gray-500" />
            <span class="flex-1">{{ t('chat.websocketChat.copyGroupCode') }}</span>
            <code v-if="inviteCode" class="text-xs font-mono text-gray-500">{{ inviteCode }}</code>
          </button>
        </div>

        <!-- Media / links history -->
        <div class="pt-2 border-t border-gray-100">
          <p class="text-xs font-medium text-gray-500 mb-2 px-1">{{ t('chat.websocketChat.sharedMediaLinks') }}</p>
          <div class="flex gap-1 mb-2">
            <button
              type="button"
              class="flex-1 py-1.5 text-xs rounded-full"
              :class="historyTab === 'media' ? 'bg-[var(--msg-accent)] text-white' : 'bg-gray-100'"
              @click="loadHistory('media')"
            >
              {{ t('chat.websocketChat.imagesTab') }}
            </button>
            <button
              type="button"
              class="flex-1 py-1.5 text-xs rounded-full"
              :class="historyTab === 'links' ? 'bg-[var(--msg-accent)] text-white' : 'bg-gray-100'"
              @click="loadHistory('links')"
            >
              {{ t('chat.websocketChat.linksTab') }}
            </button>
          </div>
          <div v-if="historyLoading" class="text-xs text-gray-400 py-4 text-center">{{ t('chat.websocketChat.loading') }}</div>
          <div v-else-if="!historyItems.length" class="text-xs text-gray-400 py-4 text-center">{{ t('chat.websocketChat.nothingYet') }}</div>
          <div v-else class="grid grid-cols-3 gap-1 max-h-48 overflow-y-auto">
            <template v-if="historyTab === 'media'">
              <div v-for="m in historyItems" :key="m.id" class="aspect-square bg-gray-100 rounded overflow-hidden">
                <img v-if="m.media && m.isImage" :src="m.media" class="w-full h-full object-cover" alt="" />
                <video v-else-if="m.media" :src="m.media" class="w-full h-full object-cover" muted />
              </div>
            </template>
            <template v-else>
              <a
                v-for="m in historyItems"
                :key="m.id"
                :href="(m.content || '').match(/https?:\/\/[^\s]+/)?.[0] || '#'"
                target="_blank"
                rel="noopener"
                class="col-span-3 text-xs text-[var(--msg-accent)] truncate px-1 py-1 hover:underline"
              >
                {{ m.content }}
              </a>
            </template>
          </div>
        </div>

        <div class="pt-2 space-y-1 border-t border-gray-100">
          <button
            type="button"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left text-sm"
            @click="chatStore.togglePin(chat.id)"
          >
            <i class="pi pi-thumbtack text-gray-500" />
            <span>{{ chatPinned ? t('chat.websocketChat.unpinConversation') : t('chat.websocketChat.pinConversation') }}</span>
          </button>
          <button
            type="button"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left text-sm"
            @click="chatStore.toggleMute(chat.id)"
          >
            <i :class="chatMuted ? 'pi pi-volume-up' : 'pi pi-volume-off'" class="text-gray-500" />
            <span>{{ chatMuted ? t('chat.websocketChat.unmuteNotifications') : t('chat.websocketChat.muteNotifications') }}</span>
          </button>
        </div>

        <div class="pt-3 border-t border-gray-100">
          <p class="text-xs font-medium text-gray-500 mb-2 px-1">{{ t('chat.websocketChat.accentColor') }}</p>
          <div class="flex gap-2 justify-center">
            <button
              v-for="c in ['red', 'blue', 'lime', 'yellow', 'purple']"
              :key="c"
              type="button"
              class="w-7 h-7 rounded-full ring-offset-2"
              :class="[
                c === 'red' ? 'bg-rose-500' : '',
                c === 'blue' ? 'bg-blue-600' : '',
                c === 'lime' ? 'bg-lime-600' : '',
                c === 'yellow' ? 'bg-yellow-500' : '',
                c === 'purple' ? 'bg-violet-600' : '',
                chatStore.bgColor === c ? 'ring-2 ring-gray-800' : '',
              ]"
              @click="updateColor(c)"
            />
          </div>
        </div>
      </div>

      <ClipLoader
        v-show="!sectionLoaded"
        :color="color"
        :size="size"
        class="flex items-center justify-center h-40"
      />
    </aside>
  </div>
</template>

<style scoped>
.loader {
  width: 28px;
  height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: var(--msg-accent, #2563eb);
  border-radius: 50%;
  animation: rotate 0.8s linear infinite;
}

@keyframes rotate {
  100% { transform: rotate(360deg); }
}

.typing-animation::after {
  content: ' .';
  animation: dots 1.5s infinite steps(3);
}

@keyframes dots {
  0% { content: ' .'; }
  33% { content: ' ..'; }
  66% { content: ' ...'; }
  100% { content: ' .'; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade2-enter-active,
.fade2-leave-active {
  transition: opacity 0.3s ease;
}
.fade2-enter-from,
.fade2-leave-to {
  opacity: 0;
}

#chatBox::-webkit-scrollbar {
  width: 6px;
}
#chatBox::-webkit-scrollbar-track {
  background: transparent;
}
#chatBox::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb-bg, #c4c4c4);
  border-radius: 8px;
}
</style>
