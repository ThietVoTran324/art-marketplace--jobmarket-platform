<script setup>
import { RouterLink, useRoute } from 'vue-router';
import { useAuthModal } from '@/composables/useAuthModal';
import { useI18n } from 'vue-i18n';

const route = useRoute();
const { t } = useI18n();
const { openAuthModal } = useAuthModal();

function isActiveHome() {
  return route.path === '/';
}

function gate(e) {
  e.preventDefault();
  openAuthModal('login');
}
</script>

<template>
  <nav
    class="fixed top-0 left-0 h-full w-20 flex flex-col justify-between items-center z-30 border-r border-gray-300 py-4 bg-white"
  >
    <div class="flex flex-col items-center text-xl space-y-6">
      <RouterLink
        to="/"
        :class="[
          isActiveHome() ? 'bg-gray-200' : 'hover:scale-150',
          'transition-transform duration-100 transform cursor-pointer rounded-lg px-4 py-3 flex items-center',
        ]"
        :title="t('guest.nav.homeTitle')"
      >
        <i class="pi pi-home" />
      </RouterLink>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.profileTitle')"
        @click="gate"
      >
        <i class="pi pi-user" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.createTitle')"
        @click="gate"
      >
        <i class="pi pi-plus-circle" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.exploreTitle')"
        @click="gate"
      >
        <i class="pi pi-briefcase" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.updatesTitle')"
        @click="gate"
      >
        <i class="pi pi-bell" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.messagesTitle')"
        @click="gate"
      >
        <i class="pi pi-envelope" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.settingsTitle')"
        @click="gate"
      >
        <i class="pi pi-cog" />
      </button>
      <button
        type="button"
        class="transition-transform duration-100 transform hover:scale-150 cursor-pointer rounded-lg px-4 py-3"
        :title="t('guest.nav.loginTitle')"
        @click="openAuthModal('login')"
      >
        <i class="pi pi-sign-in" />
      </button>
    </div>
  </nav>
</template>
