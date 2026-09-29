<script setup>
import { onMounted, ref, nextTick, watch, computed, onBeforeUnmount, onActivated, reactive } from 'vue';
import axios from 'axios'
import UserChat from '@/components/Auth/UserChat.vue';
import WebsocketChat from '@/components/Auth/WebsocketChat.vue';
import { useRoute, useRouter } from 'vue-router';
import { useUnreadMessagesStore } from "@/stores/unreadMessages";

import { useChatStore } from "@/stores/useChatStore";

import NewMessageToastWebsocket from '@/components/Auth/NewMessageToastWebsocket.vue';
import NewMessageToast from '@/components/Auth/NewMessageToast.vue';
import CreateGroupSheet from '@/components/Auth/CreateGroupSheet.vue';
import JoinGroupModal from '@/components/Auth/JoinGroupModal.vue';

import { useToast } from "vue-toastification";

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();

const toast = useToast();

const chatStore = useChatStore();

const unreadMessagesStore = useUnreadMessagesStore();

import ClipLoader from 'vue-spinner/src/ClipLoader.vue'

const searchValue = ref('')
const mobileShowThread = ref(false)

const filteredChats = computed(() => {
  let list = sortedChats.value || [];
  if (searchValue.value.trim()) {
    const q = searchValue.value.trim().toLowerCase();
    list = list.filter((chat) => {
      const name = chat.isGroup
        ? (chat.title || chat.user?.username || '')
        : (chat.user?.username || '')
      return name.toLowerCase().includes(q)
    });
  }
  return [...list].sort((a, b) => {
    const pa = chatStore.isPinned(a.id) ? 1 : 0;
    const pb = chatStore.isPinned(b.id) ? 1 : 0;
    if (pa !== pb) return pb - pa;
    const ia = a.last_message?.id || 0;
    const ib = b.last_message?.id || 0;
    return ib - ia;
  });
});

const colorMap = {
  red: { track: "#f3f4f6", thumb: "#e11d48" },
  blue: { track: "#f3f4f6", thumb: "#2563eb" },
  lime: { track: "#f3f4f6", thumb: "#65a30d" },
  yellow: { track: "#f3f4f6", thumb: "#ca8a04" },
  purple: { track: "#f3f4f6", thumb: "#7c3aed" },
};

watch(() => chatStore.bgColor, (newColor) => {
  if (colorMap[newColor]) {
    document.documentElement.style.setProperty("--scrollbar-thumb-bg-chats", colorMap[newColor].thumb);
  }
}, { immediate: true });

const color = ref('red')
const size = ref('100px')

const route = useRoute();
const router = useRouter()

const chats = ref(null)
const auth_user_id = ref(null)

const sortedChats = computed(() => {
  return chats.value
    ? [...chats.value].sort((a, b) => (b.last_message?.id || 0) - (a.last_message?.id || 0))
    : [];
});

const clearQuery = () => {
  router.replace({ path: route.path, query: {} });
};

let openingChatFromQuery = false

async function openChatFromRouteQuery() {
  if (route.name !== 'messages' || openingChatFromQuery) return;
  const chat_id_redirect = route.query.chat_id || null;
  if (chat_id_redirect === null || chat_id_redirect === '') return;

  openingChatFromQuery = true
  try {
    const new_chat = route.query.new_chat || null;
    if (new_chat !== null && !userConnected.value) {
      await addChat(chat_id_redirect)
    }
    if (!userConnected.value && sortedChats.value?.length) {
      let index = 0;
      let chatObj = null;
      for (let i = 0; i < sortedChats.value.length; i++) {
        if (sortedChats.value[i].id == chat_id_redirect) {
          index = i;
          chatObj = sortedChats.value[i]
          break;
        }
      }
      if (chatObj) {
        if (new_chat !== null) {
          await loadChat2(chatObj, index)
        } else {
          await loadChat(chatObj, index)
        }
      }
    }
    clearQuery()
  } finally {
    openingChatFromQuery = false
  }
}

watch(
  () => route.name,
  async (newName) => {
    if (newName === "messages") {
      let unreadMessagesCount = unreadMessagesStore.count;
      let unreadUpdatesCount = unreadUpdatesStore.count;
      let totalUnread = unreadMessagesCount + unreadUpdatesCount;

      if (totalUnread > 0) {
        document.title = `(${totalUnread}) Pinterest`;
      } else {
        document.title = 'Pinterest';
      }
      await openChatFromRouteQuery()
    }
  }
);

watch(
  () => route.query.chat_id,
  async (chatId) => {
    if (route.name !== 'messages' || chatId == null || chatId === '') return;
    await openChatFromRouteQuery()
  }
);

async function addChat(chat_id) {
  try {
    const response = await axios.get(`/api/messages/get_chat_by_id/${chat_id}`, { withCredentials: true });
    const chat = response.data

    const userId = auth_user_id.value === chat.user_1_id ? chat.user_2_id : chat.user_1_id
    try {
      const response = await axios.get(`/api/users/user_id/${userId}`, { withCredentials: true })
      chat.user = response.data
    } catch (error) {
      console.error(error)
    }

    try {
      const userResponse = await axios.get(`/api/users/upload/${userId}`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(userResponse.data);
      chat.userImage = blobUrl;
    } catch (error) {
      console.error(error);
    }

    chat.online = false

    chat.socket = new WebSocket(`/ws/${chat.id}/${auth_user_id.value}?chat_connection=true`);
    chat.socket.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      if ("online" in message) {
        if (message.online == true) {
          chat.online = true
        } else {
          chat.online = false
        }
        chats.value = [...chats.value];
        return
      }
      if ("user_start_sending_media" in message) {
        chat.isSendingMedia = true
        chats.value = [...chats.value];
        return
      }
      if ("user_stop_sending_media" in message) {
        chat.isSendingMedia = false
        chats.value = [...chats.value];
        return
      }
      if ("user_read_messages" in message) {
        chat.last_message.is_read = true
        chats.value = [...chats.value];
        return
      }
      if ("user_start_typing" in message) {
        chat.typing = true
        chats.value = [...chats.value];
        return
      }
      if ("user_stop_typing" in message) {
        chat.typing = false
        chats.value = [...chats.value];
        return
      }
      unreadMessagesStore.increment()
      updateChat2(message.chat_id)
    }

    try {
      const response = await axios.get(`/api/messages/last/${chat.id}`, { withCredentials: true })
      chat.last_message = response.data
      if (chat.last_message.image !== null) {
        try {
          const response = await axios.get(`/api/messages/upload/${chat.last_message.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(response.data);
          chat.last_message.media = blobUrl
          const contentType = response.headers['content-type'];
          if (contentType.startsWith('image/')) {
            chat.last_message.isImage = true;
          } else {
            chat.last_message.isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }
    } catch (error) {
      console.error(error)
    }

    try {
      const response = await axios.get(`/api/messages/unread/cnt/${chat.id}`, { withCredentials: true })
      chat.cntUnreadMessages = response.data
    } catch (error) {
      console.log(error)
    }

    chats.value.push(reactive(chat));

    if (route.name !== 'messages' && !chatStore.isMuted(chat.id)) {
      toast({
        component: NewMessageToast,
        props: { chat: JSON.parse(JSON.stringify(chat)) },
        listeners: {
          MyClick: () => router.push(`/messages?chat_id=${chat.id}`)
        }
      }, {
        position: "bottom-left",
        timeout: 5041,
        closeOnClick: true,
        pauseOnFocusLoss: true,
        pauseOnHover: true,
        draggable: true,
        draggablePercent: 0.6,
        showCloseButtonOnHover: false,
        hideProgressBar: false,
        closeButton: false,
        icon: false,
        rtl: false,
        toastClassName: "my-custom-toast-class",
      });
    }

  } catch (error) {
    console.error(error);
  }

}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

const chat_id_redirect = ref(null)

const showLoading = ref(null)

onBeforeUnmount(() => {
  if (eventSource) {
    eventSource.close();
  }

  for (let i = 0; i < chats.value.length; i++) {
    if (chats.value[i].socket) {
      chats.value[i].socket.close()
    }
  }
});

const userConnected = ref(null)

let eventSource = null;

function connectSSE() {
  eventSource = new EventSource(`/api/sse/messages/stream/${auth_user_id.value}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    addChat(data.message.chat_id);
    unreadMessagesStore.increment();
    chat_selected.value += 1;
  };

  eventSource.onerror = () => {
    console.warn("Messages SSE disconnected. Reconnecting...")
    eventSource.close();
    setTimeout(() => {
      connectSSE();
    }, 5000);
  };
}

onMounted(async () => {
  showLoading.value = true
  chatStore.fetchChatColor();
  chatStore.fetchChatSize();
  chatStore.fetchSide()
  try {
    const meRes = await axios.get('/api/users/me', { withCredentials: true })
    auth_user_id.value = meRes.data.id
  } catch (error) {
    console.error(error)
  }

  try {
    const response = await axios.get('/api/messages/user_chats', { withCredentials: true })
    chats.value = response.data
    if (Array.isArray(chats.value) && chats.value.length > 0) {
      try {
        const response = await axios.get(`/api/chats/check_connection/${chats.value[0].id}/${auth_user_id.value}`);

        if (response.data.active) {
          userConnected.value = true
        } else {
          userConnected.value = false
        }
      } catch (error) {
        console.error("Error checking connection:", error);
      }
    }

    if (!userConnected.value) {
      connectSSE();
    }

    for (let i = 0; i < chats.value.length; i++) {
      const chatRow = chats.value[i]
      if (chatRow.kind === 'group') {
        chatRow.user = { username: chatRow.title || 'Group', id: null }
        chatRow.userImage = null
        chatRow.isGroup = true
      } else {
        const userId = auth_user_id.value === chatRow.user_1_id ? chatRow.user_2_id : chatRow.user_1_id
        try {
          const response = await axios.get(`/api/users/user_id/${userId}`, { withCredentials: true })
          chatRow.user = response.data
        } catch (error) {
          console.error(error)
        }
        try {
          const userResponse = await axios.get(`/api/users/upload/${userId}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          chatRow.userImage = blobUrl;
        } catch (error) {
          console.error(error);
        }
        chatRow.isGroup = false
      }
      chatRow.online = false
      if (!userConnected.value) {
        chatRow.socket = new WebSocket(`/ws/${chatRow.id}/${auth_user_id.value}?chat_connection=true`);
        chatRow.socket.onmessage = async (event) => {
          const message = JSON.parse(event.data);
          if ("online" in message) {
            chatRow.online = !!message.online
            return
          }
          if ("user_start_sending_media" in message) {
            chatRow.isSendingMedia = true
            return
          }
          if ("user_stop_sending_media" in message) {
            chatRow.isSendingMedia = false
            return
          }
          if ("user_read_messages" in message) {
            if (chatRow.last_message) chatRow.last_message.is_read = true
            return
          }
          if ("user_start_typing" in message) {
            chatRow.typing = true
            return
          }
          if ("user_stop_typing" in message) {
            chatRow.typing = false
            return
          }
          unreadMessagesStore.increment()
          updateChat2(message.chat_id)
        }
      }
      try {
        const response = await axios.get(`/api/messages/last/${chatRow.id}`, { withCredentials: true })
        chatRow.last_message = response.data
        if (chatRow.last_message?.image !== null && chatRow.last_message?.image) {
          try {
            const response = await axios.get(`/api/messages/upload/${chatRow.last_message.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            chatRow.last_message.media = blobUrl
            const contentType = response.headers['content-type'];
            if (contentType.startsWith('image/')) {
              chatRow.last_message.isImage = true;
            } else {
              chatRow.last_message.isImage = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error)
      }
      try {
        const response = await axios.get(`/api/messages/unread/cnt/${chatRow.id}`, { withCredentials: true })
        chatRow.cntUnreadMessages = response.data
      } catch (error) {
        console.log(error)
      }
    }
  } catch (error) {
    console.error(error)
  }

  showLoading.value = false
})

const showChat = ref(false)
const chat_id = ref(null)
const chat_selected = ref(null)
const user_to_load = ref(null)
const chatObject = ref(null)

async function loadChat(chat, _index) {
  searchValue.value = ''
  const index = sortedChats.value.findIndex((c) => c.id === chat.id)
  if (index < 0) return
  let id = chat.id
  if (id !== chat_id.value) {
    if (chat_selected.value !== null && sortedChats.value[chat_selected.value]) {
      sortedChats.value[chat_selected.value].selected = false
    }
    // also clear selected flags on filtered/pinned order
    for (const c of chats.value || []) c.selected = false
    chatObject.value = chat
    chat.selected = true
    chat_selected.value = index
    showChat.value = false
    await nextTick()
    chat_id.value = id
    if (chat.kind === 'group' || chat.isGroup) {
      user_to_load.value = null
    } else {
      user_to_load.value = chat.user_1_id === auth_user_id.value ? chat.user_2_id : chat.user_1_id
    }
    showChat.value = true
    mobileShowThread.value = true
  }
}

async function loadChat2(chat, _index) {
  searchValue.value = ''
  const index = sortedChats.value.findIndex((c) => c.id === chat.id)
  if (index < 0) return
  let id = chat.id
  if (id !== chat_id.value) {
    for (const c of chats.value || []) c.selected = false
    chatObject.value = chat
    chat.selected = true
    chat_selected.value = index
    showChat.value = false
    await nextTick()
    chat_id.value = id
    if (chat.kind === 'group' || chat.isGroup) {
      user_to_load.value = null
    } else {
      user_to_load.value = chat.user_1_id === auth_user_id.value ? chat.user_2_id : chat.user_1_id
    }
    showChat.value = true
    mobileShowThread.value = true
  }
}

const showCreateGroup = ref(false)
const showJoinGroup = ref(false)
const showFabMenu = ref(false)

async function hydrateChatRow(chatRow) {
  if (chatRow.kind === 'group') {
    chatRow.user = { username: chatRow.title || 'Group', id: null }
    chatRow.userImage = null
    chatRow.isGroup = true
  } else {
    const userId = auth_user_id.value === chatRow.user_1_id ? chatRow.user_2_id : chatRow.user_1_id
    try {
      const response = await axios.get(`/api/users/user_id/${userId}`, { withCredentials: true })
      chatRow.user = response.data
    } catch (error) {
      console.error(error)
    }
    try {
      const userResponse = await axios.get(`/api/users/upload/${userId}`, { responseType: 'blob' });
      chatRow.userImage = URL.createObjectURL(userResponse.data);
    } catch (error) {
      console.error(error);
    }
    chatRow.isGroup = false
  }
  chatRow.online = false
  try {
    const response = await axios.get(`/api/messages/last/${chatRow.id}`, { withCredentials: true })
    chatRow.last_message = response.data
  } catch (error) {
    console.error(error)
  }
  try {
    const response = await axios.get(`/api/messages/unread/cnt/${chatRow.id}`, { withCredentials: true })
    chatRow.cntUnreadMessages = response.data
  } catch (error) {
    console.log(error)
  }
  return chatRow
}

async function onGroupCreated(data) {
  showFabMenu.value = false
  try {
    const response = await axios.get(`/api/messages/get_chat_by_id/${data.id}`, { withCredentials: true })
    const chat = reactive(await hydrateChatRow(response.data))
    if (!userConnected.value) {
      chat.socket = new WebSocket(`/ws/${chat.id}/${auth_user_id.value}?chat_connection=true`);
    }
    chats.value = [chat, ...(chats.value || [])]
    await loadChat(chat)
  } catch (e) {
    console.error(e)
  }
}

async function onGroupJoined(data) {
  showFabMenu.value = false
  await onGroupCreated(data)
}

const scrollToTop = () => {
  nextTick(() => {
    if (chatsContainer.value) {
      chatsContainer.value.scrollTop = 0;
    }
  });
};

const chatsContainer = ref(null);

async function updateChat2(chat_id) {
  try {
    const response = await axios.get(`/api/messages/last/${chat_id}`, { withCredentials: true })
    const chatObj = sortedChats.value.find(el => el.id === chat_id);
    const chatIndex = sortedChats.value.findIndex(el => el.id === chat_id);
    if (chat_selected.value !== null && chatIndex > chat_selected.value) {
      chat_selected.value += 1
    }
    chatObj.last_message = response.data
    if (chatObj.last_message.image !== null) {
      try {
        const response = await axios.get(`/api/messages/upload/${chatObj.last_message.id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(response.data);
        chatObj.last_message.media = blobUrl
        const contentType = response.headers['content-type'];
        if (contentType.startsWith('image/')) {
          chatObj.last_message.isImage = true;
          if (contentType === 'image/gif') {
            chatObj.last_message.isGif = true;
          }
        } else {
          chatObj.last_message.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }
    try {
      const response = await axios.get(`/api/messages/unread/cnt/${chatObj.id}`, { withCredentials: true })
      chatObj.cntUnreadMessages = response.data
    } catch (error) {
      console.log(error)
    }
    if (route.name !== 'messages' && !chatStore.isMuted(chatObj.id)) {
      toast({
        component: NewMessageToast,
        props: { chat: JSON.parse(JSON.stringify(chatObj)) },
        listeners: {
          MyClick: () => router.push(`/messages?chat_id=${chatObj.id}`)
        }
      }, {
        position: "bottom-left",
        timeout: 5041,
        closeOnClick: true,
        pauseOnFocusLoss: true,
        pauseOnHover: true,
        draggable: true,
        draggablePercent: 0.6,
        showCloseButtonOnHover: false,
        hideProgressBar: false,
        closeButton: false,
        icon: false,
        rtl: false,
        toastClassName: "my-custom-toast-class",
      });
    }
  } catch (error) {
    console.error(error)
  }
}

async function updateChat(showToast, chat_id, online) {
  scrollToTop()
  try {
    const response = await axios.get(`/api/messages/last/${chat_id}`, { withCredentials: true })
    sortedChats.value[chat_selected.value].last_message = response.data
    sortedChats.value[chat_selected.value].last_message.is_read = online
    chat_selected.value = 0
    if (sortedChats.value[chat_selected.value].last_message.image !== null) {
      try {
        const response = await axios.get(`/api/messages/upload/${sortedChats.value[chat_selected.value].last_message.id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(response.data);
        sortedChats.value[chat_selected.value].last_message.media = blobUrl
        const contentType = response.headers['content-type'];
        if (contentType.startsWith('image/')) {
          sortedChats.value[chat_selected.value].last_message.isImage = true;
          if (contentType === 'image/gif') {
            sortedChats.value[chat_selected.value].last_message.isGif = true;
          }
        } else {
          sortedChats.value[chat_selected.value].last_message.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }
    if (showToast === true && !chatStore.isMuted(sortedChats.value[chat_selected.value]?.id)) {
      toast({
        component: NewMessageToastWebsocket,
        props: { chat: JSON.parse(JSON.stringify(sortedChats.value[chat_selected.value])) },
        listeners: {
          MyClick: () => router.push(`/messages?chat_id=${sortedChats.value[chat_selected.value]?.id}`)
        }
      }, {
        position: "bottom-left",
        timeout: 5041,
        closeOnClick: true,
        pauseOnFocusLoss: true,
        pauseOnHover: true,
        draggable: true,
        draggablePercent: 0.6,
        showCloseButtonOnHover: false,
        hideProgressBar: false,
        closeButton: false,
        icon: false,
        rtl: false,
        toastClassName: "my-custom-toast-class",
      });
    }
  } catch (error) {
    console.error(error)
  }
}

const startResize = (event) => {
  const startX = event.clientX;
  const startWidth = chatStore.size;

  document.body.style.userSelect = "none";

  const onMouseMove = (moveEvent) => {
    let newWidth = startWidth + (moveEvent.clientX - startX);
    newWidth = Math.max(280, Math.min(newWidth, 480));
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

const showScroll = ref(false)

function setScrollbarColor(color) {
  document.documentElement.style.setProperty('--scrollbar-thumb-bg-chats', color);
}

</script>

<template>
  <div
    v-if="userConnected"
    class="fixed inset-0 left-20 z-50 flex items-center justify-center bg-black/40"
  >
    <div class="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md mx-4">
      <h2 class="text-2xl font-semibold text-gray-900 mb-2">Already connected</h2>
      <p class="text-gray-600 mb-4">
        You already have an active Messages session in another tab, or you are on a test profile.
      </p>
      <p class="text-sm text-gray-500">Check your open tabs, or refresh if this looks wrong.</p>
    </div>
  </div>

  <div
    v-else
    class="msg-shell fixed inset-0 left-20 z-20 flex bg-[#f0f2f5]"
  >
    <aside
      class="msg-list relative flex flex-col bg-white border-r border-gray-200 shrink-0"
      :class="mobileShowThread ? 'hidden md:flex' : 'flex'"
      :style="{ width: `${Math.max(chatStore.size || 320, 280)}px` }"
    >
      <div class="h-14 px-4 flex items-center border-b border-gray-100 shrink-0">
        <h1 class="text-xl font-bold text-gray-900 tracking-tight">Chats</h1>
      </div>

      <div class="px-3 py-2 shrink-0">
        <div class="relative">
          <i class="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
          <input
            v-model="searchValue"
            type="search"
            placeholder="Search chats"
            class="w-full pl-9 pr-3 py-2 text-sm rounded-full bg-gray-100 border-0 outline-none focus:ring-2 focus:ring-[var(--msg-accent)] focus:bg-white transition"
          />
        </div>
      </div>

      <div
        id="chats"
        ref="chatsContainer"
        class="flex-1 overflow-y-auto overflow-x-hidden min-h-0"
      >
        <div v-if="showLoading" class="p-3 space-y-3">
          <div v-for="n in 8" :key="n" class="flex items-center gap-3 animate-pulse">
            <div class="w-12 h-12 rounded-full bg-gray-200" />
            <div class="flex-1 space-y-2">
              <div class="h-3 bg-gray-200 rounded w-1/3" />
              <div class="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          </div>
        </div>

        <template v-else-if="chats && chats.length">
          <UserChat
            v-for="(chat, index) in filteredChats"
            :key="chat.id"
            :chat="chat"
            :auth_user_id="auth_user_id"
            @click="loadChat(chat, index)"
          />
          <p
            v-if="filteredChats.length === 0"
            class="text-center text-sm text-gray-500 py-8 px-4"
          >
            No chats match "{{ searchValue }}"
          </p>
        </template>

        <div
          v-else
          class="flex flex-col items-center justify-center h-full px-6 text-center text-gray-500"
        >
          <i class="pi pi-comments text-4xl text-gray-300 mb-3" />
          <p class="font-medium text-gray-700">No conversations yet</p>
          <p class="text-sm mt-1">Open a profile and send a message to start chatting.</p>
        </div>
      </div>

      <div
        class="absolute top-0 right-0 bottom-0 w-1 cursor-ew-resize hover:bg-[var(--msg-accent)]/30 z-10"
        @mousedown="startResize"
      />

      <!-- FAB: create / join group -->
      <div class="absolute bottom-5 right-5 z-20">
        <div
          v-if="showFabMenu"
          class="mb-2 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden min-w-[160px]"
        >
          <button
            type="button"
            class="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50"
            @click="showFabMenu = false; showCreateGroup = true"
          >
            Create group
          </button>
          <button
            type="button"
            class="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50"
            @click="showFabMenu = false; showJoinGroup = true"
          >
            Join group
          </button>
        </div>
        <button
          type="button"
          class="w-12 h-12 rounded-full bg-[var(--msg-accent)] text-white shadow-lg flex items-center justify-center hover:opacity-90"
          aria-label="New"
          @click="showFabMenu = !showFabMenu"
        >
          <i class="pi pi-plus text-lg" />
        </button>
      </div>
    </aside>

    <CreateGroupSheet v-model:open="showCreateGroup" @created="onGroupCreated" />
    <JoinGroupModal v-model:open="showJoinGroup" @joined="onGroupJoined" />

    <main
      class="flex-1 min-w-0 flex flex-col bg-[#f0f2f5]"
      :class="mobileShowThread ? 'flex' : 'hidden md:flex'"
    >
      <WebsocketChat
        v-if="showChat && chat_id"
        :chat_id="chat_id"
        :auth_user_id="auth_user_id"
        :user_to_load="user_to_load"
        :chat="chatObject"
        @updateLastMessage="(showToast, chat_id_, online) => updateChat(showToast, chat_id_, online)"
        @back="backToList"
      />

      <div
        v-else
        class="flex-1 flex items-center justify-center px-6"
      >
        <div class="text-center max-w-sm">
          <div
            class="mx-auto mb-4 w-16 h-16 rounded-full bg-white shadow-sm flex items-center justify-center"
          >
            <i class="pi pi-send text-2xl text-[var(--msg-accent)]" />
          </div>
          <h2 class="text-xl font-semibold text-gray-900">Your messages</h2>
          <p class="text-sm text-gray-500 mt-2">
            Select a conversation from the left to start messaging.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.msg-shell {
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

#chats::-webkit-scrollbar {
  width: 6px;
}
#chats::-webkit-scrollbar-track {
  background: transparent;
}
#chats::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb-bg-chats, #c4c4c4);
  border-radius: 8px;
}

.my-custom-toast-class {
  background-color: transparent !important;
  box-shadow: none !important;
  border: none !important;
}
</style>
