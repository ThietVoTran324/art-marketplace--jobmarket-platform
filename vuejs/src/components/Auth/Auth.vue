<script setup>
import Aside from './Aside.vue';
import { RouterView } from 'vue-router';
import { ref, onMounted, computed } from 'vue';
import ClipLoader from 'vue-spinner/src/ClipLoader.vue'
import axios from 'axios'
import { useRoute, RouterLink, useRouter } from 'vue-router';
import MessagesView from '@/views/MessagesView.vue';
import HomeView from '@/views/HomeView.vue';
import UnavailableContentModal from '@/components/Auth/UnavailableContentModal.vue';

import { useUnreadMessagesStore } from "@/stores/unreadMessages";
import { useSelectedBoard } from "@/stores/userSelectedBoard";
import { authUserStore } from "@/stores/authUserStore";

const unreadMessagesStore = useUnreadMessagesStore();
const userSelectedBoardStroe = useSelectedBoard();
const userStore = authUserStore();

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();


const route = useRoute();

const emit = defineEmits(['logout', 'createPinModelClose'])

const me = ref(null)
const meImage = ref(null)
const loadingProfile = ref(true)

const color = ref('red')
const size = ref('100px')


const props = defineProps({
  access_token: String,
  register: Boolean,
})


onMounted(async () => {
  unreadMessagesStore.fetchUnreadMessages();
  userSelectedBoardStroe.fetchSelectedBoard()
  unreadUpdatesStore.fetchUnreadUpdates()
  try {
    // Prefer cookie session (/users/me) — access_token is HttpOnly after Phase0
    const response = await axios.get('/api/users/me', { withCredentials: true })
    me.value = response.data
    userStore.setUsername(me.value.username)
    userStore.setUserId(me.value.id)
    userStore.markAuthenticated()
    userStore.setAccountKind(me.value.account_kind || 'personal', me.value.company_id ?? null)

    try {
      const rolesRes = await axios.get('/api/users/me/roles')
      userStore.setRoles(rolesRes.data.roles || [])
    } catch (rolesErr) {
      console.log(rolesErr)
      userStore.setRoles([])
    }

    try {
      const imgRes = await axios.get(`/api/users/upload/${me.value.id}`, { responseType: 'blob' })
      meImage.value = URL.createObjectURL(imgRes.data)
      loadingProfile.value = false
    } catch (error) {
      console.log(error)
      loadingProfile.value = false
    }
  } catch (error) {
    console.error('Error loading session profile:', error)
    loadingProfile.value = false
  }
})


const homeProps = computed(() => {
  if (route.name === 'home') {
    return { register: props.register, guest: false };
  }
  return {};
});

const homeEvents = computed(() => {
  if (route.name === 'home') {
    return {
      createPinModelClose: handleCreatePinModelClose, // Replace with your actual handler
    };
  }
  return {};
});

function handleCreatePinModelClose() {
  emit('createPinModelClose')
}

const cachedViews = computed(() =>
  route.name === "home" ? ["HomeView", "PinView", "UserView"] : ["HomeView"]
);

</script>


<template>


  <!-- <ClipLoader v-if="loadingProfile" :color="color" :size="size" class="flex items-center justify-center h-screen" /> -->
  <div v-if="loadingProfile" class="flex items-center justify-center h-screen">
    <img src="/logo.png" alt="Logo" class="logo w-24 h-24" />
  </div>
  <Aside v-if="!loadingProfile" @logout="emit('logout')" :me="me" :meImage="meImage" />

  <UnavailableContentModal />

  <RouterView v-if="!loadingProfile" v-slot="{ Component }">
    <div v-show="$route.name === 'messages'">
      <component :is="MessagesView" :key="'messages'" />
    </div>

    <KeepAlive :include="['HomeView']">
      <component v-if="$route.name === 'home'" :is="Component" :key="$route.name" v-bind="homeProps"
        v-on="homeEvents" />
    </KeepAlive>

    <KeepAlive :max="10" :include="['PinView', 'UserView', 'RecommendationsView']">
      <component v-if="$route.name !== 'home' && $route.name !== 'messages'" :is="Component" :key="$route.fullPath" />
    </KeepAlive>
  </RouterView>


</template>

<style scoped>
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