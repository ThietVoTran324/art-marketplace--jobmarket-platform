<script setup>
import dayjs from 'dayjs';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
import 'dayjs/locale/ru';
import { RouterLink } from 'vue-router';

import { useChatStore } from "@/stores/useChatStore";
import { useI18n } from 'vue-i18n';

const chatStore = useChatStore();
const { t } = useI18n();

const emit = defineEmits(['MyClick']);

dayjs.extend(isToday);
dayjs.extend(isYesterday);

const formattedTime = (timestamp) => {
    const date = dayjs(timestamp);
    const now = dayjs();

    return date.isToday()
        ? date.format('HH:mm')
        : date.isYesterday()
            ? t('chat.newMessageToast.yesterday')
            : now.diff(date.startOf('day'), 'days') > 7
                ? date.format('DD.MM') 
                : date.format('dddd');
};

const props = defineProps({
  chat: Object
});

</script>

<template>
  <div class="flex items-center space-x-1 cursor-pointer" @click="emit('MyClick')"
  :class="`bg-${chatStore.bgColor}-400`">

    
    <RouterLink
      v-if="chat?.user?.username"
      :to="`/user/${chat.user.username}`"
      class="relative flex-none"
      @click.stop
    >
      <img :src="chat.userImage" :alt="t('chat.newMessageToast.userImageAlt')"
        class="w-[60px] h-[60px] min-w-[60px] min-h-[60px] rounded-full object-cover m-2" />
      <div :class="`bg-${chatStore.bgColor}-500`" v-if="chat.online"
        class="absolute bottom-2 right-3  w-3 h-3 rounded-full border-2 border-white">
      </div>
    </RouterLink>
    <div v-else class="relative flex-none">
      <img :src="chat.userImage" :alt="t('chat.newMessageToast.userImageAlt')"
        class="w-[60px] h-[60px] min-w-[60px] min-h-[60px] rounded-full object-cover m-2" />
    </div>

    
    <div class="flex flex-col w-full min-w-0 gap-1">
      <div class="flex justify-between items-center w-full min-w-0">
        
        <span class="w-0 flex-1 truncate">{{ chat.user.username }}</span>

        
        <span v-if="chat.last_message" class="text-sm text-gray-700 text-nowrap mr-1">
          {{ formattedTime(chat.last_message.created_at) }}
        </span>
      </div>

      <div v-show="!chat.typing" class="flex items-center min-w-0">
        
        <img v-if="chat.last_message?.media && chat.last_message.isImage" :src="chat.last_message.media"
          class="w-5 h-5 min-w-5 min-h-5 flex-none" />

        
        <video v-if="chat.last_message?.media && !chat.last_message.isImage" :src="chat.last_message.media"
          class="w-5 h-5 min-w-5 min-h-5 flex-none" autoplay muted loop></video>

        
        <span v-if="chat.last_message?.content" :class="chat.last_message?.media ? 'ml-1' : ''"
          class="w-0 flex-1 truncate text-sm text-gray-700">
          {{ chat.last_message.content }}
        </span>

        
        <span
          v-if="chat.last_message?.media && chat.last_message.isImage && !chat.last_message.content && !chat.last_message.isGif"
          class="ml-1 text-sm text-gray-700">{{ t('chat.newMessageToast.photo') }}</span>

        <span
          v-if="chat.last_message?.media && chat.last_message.isImage && !chat.last_message.content && chat.last_message.isGif"
          class="ml-1 text-sm text-gray-700">{{ t('chat.newMessageToast.gif') }}</span>

        
        <span v-if="chat.last_message?.media && !chat.last_message.isImage && !chat.last_message.content"
          class="ml-1 text-sm text-gray-700">{{ t('chat.newMessageToast.video') }}</span>

        
        <span v-if="chat.cntUnreadMessages" :class="`bg-${chatStore.bgColor}-500`"
          class="ml-auto flex items-center justify-center text-white text-xs font-bold rounded-full h-5 w-5 mr-3">
          {{ chat.cntUnreadMessages }}
        </span>
      </div>
    </div>
  </div>
</template>
