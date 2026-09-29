import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const authUserStore = defineStore("authUserStore", () => {
  const authUsername = ref(null);
  const authUserId = ref(null);
  const roles = ref([]);
  const accountKind = ref("personal");
  const companyId = ref(null);
  /** null = resolving, true = logged in, false = guest */
  const sessionKnown = ref(null);

  const isGuest = computed(() => sessionKnown.value === false);
  const isAuthenticated = computed(() => sessionKnown.value === true);

  const setUsername = async (username) => {
    authUsername.value = username;
  };

  const setUserId = (id) => {
    authUserId.value = id ?? null;
  };

  const setRoles = (nextRoles) => {
    roles.value = Array.isArray(nextRoles) ? [...nextRoles] : [];
  };

  const setAccountKind = (kind, nextCompanyId = null) => {
    accountKind.value = kind || "personal";
    companyId.value = nextCompanyId ?? null;
  };

  const markAuthenticated = () => {
    sessionKnown.value = true;
  };

  const markGuest = () => {
    sessionKnown.value = false;
  };

  const hasRole = (role) => roles.value.includes(role);

  const isAdmin = computed(() => roles.value.includes("admin"));
  const isOrganization = computed(() => accountKind.value === "organization");

  /** Soft-live product gates (mirror app/api/rest/role_gates.py). */
  const canApplyToJobs = computed(() => !isAdmin.value && !isOrganization.value);
  const canManageCv = computed(() => !isOrganization.value);
  const canSubmitHiringKyc = computed(() => !isAdmin.value && !isOrganization.value);
  const canSellOnMarketplace = computed(() => !isAdmin.value && !isOrganization.value);
  const canBuyLicense = computed(() => !isAdmin.value && !isOrganization.value);
  const canCreatePin = computed(() => !isOrganization.value);

  const clearAuth = () => {
    authUsername.value = null;
    authUserId.value = null;
    roles.value = [];
    accountKind.value = "personal";
    companyId.value = null;
    sessionKnown.value = false;
  };

  return {
    authUsername,
    authUserId,
    roles,
    accountKind,
    companyId,
    sessionKnown,
    isGuest,
    isAuthenticated,
    isAdmin,
    isOrganization,
    canApplyToJobs,
    canManageCv,
    canSubmitHiringKyc,
    canSellOnMarketplace,
    canBuyLicense,
    canCreatePin,
    setUsername,
    setUserId,
    setRoles,
    setAccountKind,
    markAuthenticated,
    markGuest,
    hasRole,
    clearAuth,
  };
});
