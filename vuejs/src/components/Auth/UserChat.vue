<script setup>
import axios from 'axios';
import { computed } from 'vue';
import double_check from '@/assets/double_check.png';
import single_check from '@/assets/single_check.png';

import dayjs from 'dayjs';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import 'dayjs/locale/en';

import { useChatStore } from '@/stores/useChatStore';

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(isToday);
dayjs.extend(isYesterday);
dayjs.locale('en');

const chatStore = useChatStore();

const formattedTime = (timestamp) => {
  const date = dayjs.utc(timestamp).local();
  const now = dayjs();
  return date.isToday()
    ? date.format('HH:mm')
    : date.isYesterday()
      ? 'Yesterday'
      : now.diff(date.startOf('day'), 'days') > 7
        ? date.format('MMM D')
        : date.format('ddd');
};

const props = defineProps({
  chat: Object,
  auth_user_id: Number,
});

const pinned = computed(() => chatStore.isPinned(props.chat?.id));
const muted = computed(() => chatStore.isMuted(props.chat?.id));
</script>

<template>
  <div
    class="msg-row flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-colors border-l-[3px]"
    :class="[
      props.chat.selected
        ? 'bg-gray-100 border-[var(--msg-accent)]'
        : 'border-transparent hover:bg-gray-50',
    ]"
  >
    <div class="relative flex-none">
      <img
        v-if="chat.userImage"
        :src="chat.userImage"
        alt=""
        class="w-12 h-12 rounded-full object-cover bg-gray-200"
      />
      <div
        v-else
        class="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center text-gray-600"
      >
        <i :class="chat.isGroup || chat.kind === 'group' ? 'pi pi-users' : 'pi pi-user'" />
      </div>
      <span
        v-if="chat.online && !(chat.isGroup || chat.kind === 'group')"
        class="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white bg-[var(--msg-accent)]"
      />
    </div>

    <div class="flex flex-col flex-1 min-w-0 gap-0.5">
      <div class="flex items-center justify-between gap-2 min-w-0">
        <div class="flex items-center gap-1.5 min-w-0">
          <i v-if="pinned" class="pi pi-thumbtack text-xs text-gray-400 flex-none" />
          <i v-if="muted" class="pi pi-volume-off text-xs text-gray-400 flex-none" />
          <span class="font-semibold text-[15px] text-gray-900 truncate">
            {{ chat.user.username }}
          </span>
        </div>
        <span
          v-if="chat.last_message"
          class="text-xs text-gray-500 flex-none tabular-nums"
        >
          {{ formattedTime(chat.last_message.created_at) }}
        </span>
      </div>

      <div v-show="!chat.typing && !chat.isSendingMedia" class="flex items-center gap-1.5 min-w-0">
        <template v-if="chat.last_message?.user_id_ === auth_user_id">
          <img
            v-if="chat.last_message.is_read === false"
            :src="single_check"
            alt=""
            class="h-3.5 w-3.5 flex-none opacity-70"
          />
          <img
            v-else-if="chat.last_message.is_read === true"
            :src="double_check"
            alt=""
            class="h-3.5 w-3.5 flex-none opacity-70"
          />
        </template>

        <img
          v-if="chat.last_message?.media && chat.last_message.isImage"
          :src="chat.last_message.media"
          class="w-4 h-4 rounded flex-none object-cover"
        />
        <video
          v-if="chat.last_message?.media && !chat.last_message.isImage"
          :src="chat.last_message.media"
          class="w-4 h-4 rounded flex-none object-cover"
          autoplay
          muted
          loop
        />

        <span
          v-if="chat.last_message?.content"
          class="truncate text-sm"
          :class="chat.cntUnreadMessages ? 'text-gray-900 font-medium' : 'text-gray-500'"
        >
          {{ chat.last_message.content }}
        </span>
        <span
          v-else-if="chat.last_message?.media && chat.last_message.isImage && !chat.last_message.isGif"
          class="text-sm text-gray-500"
        >Photo</span>
        <span
          v-else-if="chat.last_message?.media && chat.last_message.isGif"
          class="text-sm text-gray-500"
        >Gif</span>
        <span
          v-else-if="chat.last_message?.media && !chat.last_message.isImage"
          class="text-sm text-gray-500"
        >Video</span>
        <span v-else class="text-sm text-gray-400">No messages yet</span>

        <span
          v-if="chat.cntUnreadMessages"
          class="ml-auto flex-none min-w-[20px] h-5 px-1.5 flex items-center justify-center text-white text-[11px] font-bold rounded-full bg-[var(--msg-accent)]"
        >
          {{ chat.cntUnreadMessages > 99 ? '99+' : chat.cntUnreadMessages }}
        </span>
      </div>

      <div v-show="chat.typing && !chat.isSendingMedia" class="text-sm text-[var(--msg-accent)] typing-animation">
        typing
      </div>
      <div v-show="chat.isSendingMedia" class="text-sm text-gray-500 flex items-center gap-1">
        <i class="pi pi-image text-sm" />
        sending media…
      </div>
    </div>
  </div>
</template>

<style scoped>
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
</style>
