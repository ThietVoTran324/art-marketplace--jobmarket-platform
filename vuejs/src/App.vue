<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useToast } from 'vue-toastification'
import { useRoute, useRouter, RouterView } from 'vue-router'
import axios from 'axios'
import PortfolioView from '@/views/PortfolioView.vue'
import { authUserStore } from '@/stores/authUserStore'
import { onSessionExpired, resetSessionExpiredFlag } from '@/api/sessionRefresh'
import { useAuthModal } from '@/composables/useAuthModal'
import AuthModal from '@/components/Auth/AuthModal.vue'
import GuestAside from '@/components/Auth/GuestAside.vue'
import Auth from '@/components/Auth/Auth.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const route = useRoute()
const router = useRouter()
const userStore = authUserStore()
const { openAuthModal } = useAuthModal()
const { t } = useI18n()

const has_token = ref(null)
const access_token = ref(null)
const register = ref(false)

function isPublicPath(path) {
  return path === '/' || path === '/portfolio' || path.startsWith('/portfolio')
}

async function resolveSession() {
  try {
    const { data } = await axios.get('/api/users/me', { withCredentials: true })
    userStore.setUserId(data.id)
    userStore.setUsername(data.username)
    userStore.markAuthenticated()
    has_token.value = true
    if (route.query.register === 'true') {
      register.value = true
      router.replace({ path: route.path, query: {} })
    }
  } catch {
    access_token.value = null
    userStore.clearAuth()
    const leftProtected = !isPublicPath(route.path)
    if (leftProtected) {
      await router.replace('/')
    }
    has_token.value = false
    if (leftProtected) {
      openAuthModal('login')
    }
  }
}

/** Leave protected screens before flipping to guest shell. No auto login popup. */
async function logout() {
  access_token.value = null
  userStore.clearAuth()
  try {
    await router.replace('/')
  } catch {
    /* ignore */
  }
  has_token.value = false
}

async function login(token) {
  resetSessionExpiredFlag()
  access_token.value = token
  await resolveSession()
}

async function signup(token) {
  resetSessionExpiredFlag()
  access_token.value = token
  register.value = true
  await resolveSession()
}

let unsubscribeSessionExpired = null

onMounted(() => {
  unsubscribeSessionExpired = onSessionExpired(() => {
    const wasLoggedIn = has_token.value === true
    logout().then(() => {
      if (wasLoggedIn) {
        toast.error(t('auth.sessionExpired'))
      }
    })
  })
  resolveSession()
})

onBeforeUnmount(() => {
  if (unsubscribeSessionExpired) unsubscribeSessionExpired()
})
</script>

<template>
  <LanguageSwitcher />
  <PortfolioView v-if="route.path === '/portfolio'" />

  <Auth
    v-else-if="has_token === true"
    :access_token="access_token"
    :register="register"
    @logout="logout()"
    @createPinModelClose="register = false"
  />

  <template v-else-if="has_token === false">
    <GuestAside />
    <!-- Guest: RouterView only (guard keeps path on /). Pass guest so Home gates actions. -->
    <RouterView v-slot="{ Component }">
      <component :is="Component" :guest="true" />
    </RouterView>
    <AuthModal @login="(token) => login(token)" @signup="(token) => signup(token)" />
  </template>

  <div v-else class="flex items-center justify-center h-screen">
    <img src="/logo.png" alt="Logo" class="w-24 h-24" />
  </div>
</template>
