import { ref } from 'vue';

const isOpen = ref(false);
const mode = ref('login'); // login | signup | reset
/** Path (+ optional query) to open after successful login/signup */
const pendingRedirect = ref(null);

export function useAuthModal() {
  function openAuthModal(nextMode = 'login', options = {}) {
    mode.value = nextMode;
    if (options && typeof options.redirectTo === 'string' && options.redirectTo) {
      pendingRedirect.value = options.redirectTo;
    }
    isOpen.value = true;
  }

  function closeAuthModal() {
    isOpen.value = false;
  }

  function clearPendingRedirect() {
    pendingRedirect.value = null;
  }

  function consumePendingRedirect() {
    const path = pendingRedirect.value;
    pendingRedirect.value = null;
    return path;
  }

  function requireAuth(redirectTo) {
    openAuthModal('login', redirectTo ? { redirectTo } : {});
    return false;
  }

  return {
    isOpen,
    mode,
    pendingRedirect,
    openAuthModal,
    closeAuthModal,
    clearPendingRedirect,
    consumePendingRedirect,
    requireAuth,
  };
}
