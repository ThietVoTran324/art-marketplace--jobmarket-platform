<script setup>
import { onMounted, ref, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { useI18n } from 'vue-i18n';
import { authUserStore } from '@/stores/authUserStore';

const userStore = authUserStore();
const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const activeTab = ref('email');
const canSellSettings = computed(() => userStore.canSellOnMarketplace);
const canHireSettings = computed(() => userStore.canSubmitHiringKyc);
function setTab(tab) {
  activeTab.value = tab;
  const nextQuery = { ...route.query, tab };
  router.replace({ path: '/settings', query: nextQuery });
}

function syncTabFromRoute() {
  const queryTab = String(route.query.tab || '');
  // payout kept as alias for payment methods
  if (queryTab === 'email' || queryTab === 'payment' || queryTab === 'payout' || queryTab === 'selling' || queryTab === 'hiring') {
    const tab = queryTab === 'payout' ? 'payment' : queryTab;
    if (tab === 'selling' && !canSellSettings.value) {
      activeTab.value = 'email';
      return;
    }
    if (tab === 'hiring' && !canHireSettings.value && userStore.accountKind !== 'organization') {
      activeTab.value = 'email';
      return;
    }
    activeTab.value = tab;
  } else {
    activeTab.value = 'email';
  }
}

const requests = ref([]);
const loading = ref(true);
const submitting = ref(false);
const error = ref(null);
const success = ref(null);
const uploadRequestId = ref(null);
const docFile = ref(null);
const docType = ref('business_registration_document');

const accountEmail = ref('');
const emailVerified = ref(false);
const emailDraft = ref('');
const emailBusy = ref(false);
const emailError = ref(null);
const emailSuccess = ref(null);

const payoutMethods = ref([]);
const payoutConfig = ref(null);
const myPayouts = ref([]);
const payoutError = ref(null);
const payoutSuccess = ref(null);
const payoutForm = ref({
  method_type: 'bank',
  display_name: '',
  account_identifier: '',
  bank_code: '',
  bank_name: '',
  account_holder: '',
  is_primary: false,
});

const sellEligibility = ref(null);
const sellError = ref(null);
const sellSuccess = ref(null);
const sellBusy = ref(false);

const form = ref({
  display_name: '',
  description: '',
  industry: '',
  size_min: null,
  size_max: null,
  website: '',
  domain: '',
  registration_country: 'VN',
  registration_authority: 'NATIONAL',
  registration_type: 'LLC',
  registration_number_raw: '',
  tax_id: '',
  vat_number: '',
  signer_full_name: '',
  primary_document_language: 'en',
  company_email: '',
  address_line: '',
  city: '',
  branch_country: 'VN',
  terms_version: 'hiring-rights-kyc-v1',
});

const docTypes = computed(() => [
  { value: 'business_registration_document', label: t('settings.hiring.docTypes.businessRegistration') },
  { value: 'tax_registration_document', label: t('settings.hiring.docTypes.taxRegistration') },
  { value: 'authorization_evidence', label: t('settings.hiring.docTypes.authorizationEvidence') },
  { value: 'identity_document', label: t('settings.hiring.docTypes.identityDocument') },
  { value: 'document_translation', label: t('settings.hiring.docTypes.documentTranslation') },
]);

const CRITERION_KEYS = {
  N: 'settings.selling.criteria.createdPins',
  M: 'settings.selling.criteria.totalPinViews',
  K: 'settings.selling.criteria.followers',
  P: 'settings.selling.criteria.verifiedPaymentMethods',
};

const PAYOUT_STATUS_KEYS = {
  pending: 'settings.payment.payoutStatus.pending',
  paid: 'settings.payment.payoutStatus.paid',
  failed: 'settings.payment.payoutStatus.failed',
  cancelled: 'settings.payment.payoutStatus.cancelled',
};

function criterionLabel(code) {
  const key = CRITERION_KEYS[code];
  return key ? t(key) : code;
}

function payoutStatusLabel(status) {
  const key = PAYOUT_STATUS_KEYS[status];
  return key ? t(key) : status;
}

function methodTypeLabel(type) {
  if (type === 'bank') return t('settings.payment.methodType.bank');
  if (type === 'e_wallet') return t('settings.payment.methodType.eWallet');
  return type;
}

function kycStatusLabel(status) {
  const map = {
    pending: 'settings.hiring.kycStatus.pending',
    approved: 'settings.hiring.kycStatus.approved',
    rejected: 'settings.hiring.kycStatus.rejected',
    need_more_info: 'settings.hiring.kycStatus.needMoreInfo',
  };
  const key = map[status];
  return key ? t(key) : status;
}

const REQUIRED_FIELDS = [
  ['display_name', 'companyDisplayName'],
  ['registration_country', 'registrationCountry'],
  ['registration_type', 'registrationType'],
  ['registration_number_raw', 'registrationNumber'],
  ['signer_full_name', 'signerFullName'],
  ['primary_document_language', 'documentLanguage'],
  ['company_email', 'companyEmail'],
];

function formatApiError(err, fallback) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  let message = fallback;

  if (typeof detail === 'string') {
    message = detail;
  } else if (Array.isArray(detail)) {
    message = detail
      .map((item) => {
        const loc = Array.isArray(item?.loc)
          ? item.loc.filter((p) => p !== 'body').join('.')
          : '';
        const msg = item?.msg || JSON.stringify(item);
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join('; ');
  } else if (detail != null) {
    message = JSON.stringify(detail);
  } else if (err?.message) {
    message = err.message;
  }

  if (status === 403 && /token has expired/i.test(message)) {
    message = t('settings.email.errors.sessionExpired');
  } else if (status === 403 && /csrf/i.test(message)) {
    message = t('settings.email.errors.csrfFailed');
  }

  const prefixed = status
    ? t('settings.errors.statusPrefix', { status, message })
    : message;
  console.error('[Settings]', prefixed, err?.response?.data || err);
  return prefixed;
}

function validateRequired() {
  const missing = REQUIRED_FIELDS.filter(
    ([key]) => !String(form.value[key] ?? '').trim()
  ).map(([, labelKey]) => t(`settings.hiring.requiredFieldLabels.${labelKey}`));
  if (missing.length) {
    return t('settings.hiring.errors.missingRequiredFields', { fields: missing.join(', ') });
  }
  return null;
}

async function loadAccountEmail(data) {
  accountEmail.value = data?.email || '';
  emailVerified.value = Boolean(data?.verified);
  emailDraft.value = data?.email || '';
  form.value.company_email = data?.email || form.value.company_email;
}

async function saveAccountEmail() {
  emailError.value = null;
  emailSuccess.value = null;
  const next = emailDraft.value.trim();
  if (!next) {
    emailError.value = t('settings.email.errors.enterEmail');
    return;
  }
  emailBusy.value = true;
  try {
    const { data } = await axios.patch('/api/users/information', { email: next });
    await loadAccountEmail(data);
    emailSuccess.value = emailVerified.value
      ? t('settings.email.success.emailUpdated')
      : t('settings.email.success.emailSavedUnverified');
  } catch (e) {
    emailError.value = formatApiError(e, t('settings.email.errors.couldNotUpdateEmail'));
  } finally {
    emailBusy.value = false;
  }
}

async function resendVerification() {
  emailError.value = null;
  emailSuccess.value = null;
  emailBusy.value = true;
  try {
    const next = emailDraft.value.trim();
    if (next && next !== accountEmail.value) {
      const { data: saved } = await axios.patch('/api/users/information', { email: next });
      await loadAccountEmail(saved);
    }
    const { data } = await axios.post('/api/users/me/resend-verification');
    if (data.message === 'already_verified') {
      emailVerified.value = true;
      emailSuccess.value = t('settings.email.success.alreadyVerified', { email: data.email });
    } else {
      emailSuccess.value = t('settings.email.success.verificationSent', { email: data.email });
    }
  } catch (e) {
    emailError.value = formatApiError(e, t('settings.email.errors.couldNotSendVerification'));
  } finally {
    emailBusy.value = false;
  }
}

async function loadPayout() {
  try {
    const [methodsRes, configRes, payoutsRes] = await Promise.all([
      axios.get('/api/marketplace/me/payment-methods'),
      axios.get('/api/marketplace/me/payout-config'),
      axios.get('/api/marketplace/me/payouts', { params: { limit: 20 } }),
    ]);
    payoutMethods.value = methodsRes.data || [];
    payoutConfig.value = configRes.data;
    myPayouts.value = payoutsRes.data || [];
  } catch (e) {
    payoutError.value = formatApiError(e, t('settings.payment.errors.loadFailed'));
  }
}

async function loadSelling() {
  sellError.value = null;
  try {
    const { data } = await axios.get('/api/marketplace/me/eligibility');
    sellEligibility.value = data;
  } catch (e) {
    sellError.value = formatApiError(e, t('settings.selling.errors.loadFailed'));
  }
}

async function enableSellingFromSettings() {
  sellBusy.value = true;
  sellError.value = null;
  sellSuccess.value = null;
  try {
    const { data } = await axios.post('/api/marketplace/me/enable-selling');
    userStore.setRoles(data.roles || []);
    sellSuccess.value = t('settings.selling.success.enabled');
    await loadSelling();
  } catch (e) {
    sellError.value = formatApiError(e, t('settings.selling.errors.eligibilityNotMet'));
    if (e.response?.data?.detail?.eligibility) {
      sellEligibility.value = e.response.data.detail.eligibility;
    }
  } finally {
    sellBusy.value = false;
  }
}

async function addPayoutMethod() {
  payoutError.value = null;
  payoutSuccess.value = null;
  if (!payoutForm.value.display_name.trim() || !payoutForm.value.account_identifier.trim()) {
    payoutError.value = t('settings.payment.errors.displayNameAndIdentifierRequired');
    return;
  }
  if (payoutForm.value.method_type === 'bank') {
    if (!payoutForm.value.bank_code.trim() || !payoutForm.value.account_holder.trim()) {
      payoutError.value = t('settings.payment.errors.bankBinAndHolderRequired');
      return;
    }
  }
  try {
    await axios.post('/api/marketplace/me/payment-methods', {
      method_type: payoutForm.value.method_type,
      display_name: payoutForm.value.display_name,
      account_identifier: payoutForm.value.account_identifier,
      bank_code: payoutForm.value.method_type === 'bank' ? payoutForm.value.bank_code : null,
      bank_name: payoutForm.value.bank_name || null,
      account_holder: payoutForm.value.account_holder || null,
      is_primary: payoutForm.value.is_primary,
    });
    payoutForm.value = {
      method_type: 'bank',
      display_name: '',
      account_identifier: '',
      bank_code: '',
      bank_name: '',
      account_holder: '',
      is_primary: false,
    };
    payoutSuccess.value = t('settings.payment.success.methodAdded');
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, t('settings.payment.errors.cannotAdd'));
  }
}

async function setPrimary(id) {
  payoutError.value = null;
  try {
    await axios.patch(`/api/marketplace/me/payment-methods/${id}`, { is_primary: true });
    payoutSuccess.value = t('settings.payment.success.primaryUpdated');
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, t('settings.payment.errors.cannotSetPrimary'));
  }
}

async function deactivateMethod(id) {
  payoutError.value = null;
  try {
    await axios.patch(`/api/marketplace/me/payment-methods/${id}`, { is_active: false });
    payoutSuccess.value = t('settings.payment.success.methodDeactivated');
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, t('settings.payment.errors.cannotDeactivate'));
  }
}

async function deleteMethod(id) {
  payoutError.value = null;
  try {
    await axios.delete(`/api/marketplace/me/payment-methods/${id}`);
    payoutSuccess.value = t('settings.payment.success.methodDeleted');
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, t('settings.payment.errors.cannotDelete'));
  }
}

async function loadRequests() {
  loading.value = true;
  try {
    const { data } = await axios.get('/api/job-market/me/hiring-rights-requests');
    requests.value = data || [];
    if (requests.value.length && !uploadRequestId.value) {
      uploadRequestId.value = requests.value[0].id;
    }
  } catch (e) {
    error.value = formatApiError(e, t('settings.hiring.errors.loadRequestsFailed'));
  } finally {
    loading.value = false;
  }
}

async function submitKyc() {
  submitting.value = true;
  error.value = null;
  success.value = null;

  const localErr = validateRequired();
  if (localErr) {
    error.value = localErr;
    submitting.value = false;
    return;
  }

  try {
    const email =
      form.value.company_email?.trim() ||
      (await axios.get('/api/users/me')).data.email;
    const payload = {
      ...form.value,
      company_email: email,
      size_min:
        form.value.size_min === '' || form.value.size_min == null
          ? null
          : Number(form.value.size_min),
      size_max:
        form.value.size_max === '' || form.value.size_max == null
          ? null
          : Number(form.value.size_max),
    };
    const { data } = await axios.post('/api/job-market/me/hiring-rights-requests', payload);
    success.value = t('settings.hiring.success.requestSubmitted', { id: data.id });
    uploadRequestId.value = data.id;
    if (data.warnings?.length) {
      const msgs = data.warnings.map((w) => w.message || w.code).filter(Boolean);
      if (msgs.length) {
        success.value = t('settings.hiring.success.requestSubmittedWithWarnings', {
          id: data.id,
          warnings: msgs.join('; '),
        });
      }
    }
    await loadRequests();
  } catch (e) {
    error.value = formatApiError(e, t('settings.hiring.errors.submitFailed'));
  } finally {
    submitting.value = false;
  }
}

async function uploadDoc() {
  if (!uploadRequestId.value || !docFile.value) {
    error.value = t('settings.hiring.errors.selectRequestAndFile');
    return;
  }
  error.value = null;
  const fd = new FormData();
  fd.append('doc_type', docType.value);
  fd.append('file', docFile.value);
  try {
    await axios.post(
      `/api/job-market/me/hiring-rights-requests/${uploadRequestId.value}/documents`,
      fd
    );
    success.value = t('settings.hiring.success.documentUploaded');
    docFile.value = null;
  } catch (e) {
    error.value = formatApiError(e, t('settings.hiring.errors.uploadFailed'));
  }
}

async function resendConfirm(id) {
  try {
    await axios.post(`/api/job-market/me/hiring-rights-requests/${id}/resend-confirm`);
    success.value = t('settings.hiring.success.confirmationEmailResent');
  } catch (e) {
    error.value = formatApiError(e, t('settings.hiring.errors.resendFailed'));
  }
}

function onFileChange(e) {
  docFile.value = e.target.files?.[0] || null;
}

onMounted(async () => {
  syncTabFromRoute();
  try {
    const { data } = await axios.get('/api/users/me');
    await loadAccountEmail(data);
    if (!form.value.signer_full_name) {
      form.value.signer_full_name = data.username || '';
    }
    userStore.setAccountKind(data.account_kind || 'personal', data.company_id ?? null);
  } catch (e) {
    error.value = formatApiError(e, t('settings.hiring.errors.cannotLoadSession'));
  }
  await Promise.all([loadRequests(), loadPayout(), loadSelling()]);
});

watch(
  () => route.query.tab,
  () => syncTabFromRoute()
);

watch(activeTab, (tab, prev) => {
  if (tab === 'payment' && prev !== 'payment') {
    loadPayout();
  }
  if (tab === 'selling' && prev !== 'selling') {
    loadSelling();
  }
});
</script>
<template>
  <div class="ml-20 min-h-screen px-10 py-10 max-w-3xl">
    <h1 class="text-3xl font-bold mb-2">{{ t('settings.pageTitle') }}</h1>
    <p class="text-gray-600 mb-6 text-sm">
      {{ t('settings.signedInAs', { username: userStore.authUsername }) }}
      <span v-if="userStore.accountKind === 'organization'">{{ t('settings.signedInSuffixCompany') }}</span>
      <span v-else-if="userStore.accountKind">{{ t('settings.signedInSuffixPersonal') }}</span>
    </p>

    <div class="flex items-center justify-start space-x-2 sm:space-x-4 flex-wrap mb-8 border-b border-gray-200">
      <button
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'email' }"
        @click="setTab('email')"
      >
        {{ t('settings.tabs.email') }}
      </button>
      <button
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'payment' }"
        @click="setTab('payment')"
      >
        {{ t('settings.tabs.paymentMethods') }}
      </button>
      <button
        v-if="canSellSettings"
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'selling' }"
        @click="setTab('selling')"
      >
        {{ t('settings.tabs.selling') }}
      </button>
      <button
        v-if="canHireSettings || userStore.accountKind === 'organization'"
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'hiring' }"
        @click="setTab('hiring')"
      >
        {{ t('settings.tabs.hiringRights') }}
      </button>
    </div>

    <section v-show="activeTab === 'email'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">{{ t('settings.email.sectionTitle') }}</h2>
      <p class="text-sm text-gray-600 mb-3">
        {{ t('settings.email.intro') }}
      </p>
      <p class="text-sm mb-3">
        {{ t('settings.email.statusLabel') }}
        <span v-if="emailVerified" class="font-medium text-emerald-700">{{ t('settings.email.statusVerified') }}</span>
        <span v-else-if="accountEmail" class="font-medium text-amber-700">{{ t('settings.email.statusNotVerified') }}</span>
        <span v-else class="font-medium text-gray-600">{{ t('settings.email.statusNoEmail') }}</span>
      </p>
      <p v-if="emailError" class="text-red-600 text-sm mb-2 whitespace-pre-wrap">{{ emailError }}</p>
      <p v-if="emailSuccess" class="text-green-700 text-sm mb-2">{{ emailSuccess }}</p>
      <div class="grid gap-2 text-sm">
        <input v-model="emailDraft" type="email" :placeholder="t('settings.email.placeholderAccountEmail')" class="border rounded-xl px-3 py-2" />
        <div class="flex flex-wrap gap-2">
          <button type="button" class="px-4 py-2 rounded-full border disabled:opacity-50" :disabled="emailBusy" @click="saveAccountEmail">
            {{ t('settings.email.saveEmail') }}
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-full bg-black text-white disabled:opacity-50"
            :disabled="emailBusy || emailVerified || !(emailDraft || accountEmail)"
            @click="resendVerification"
          >
            {{ emailBusy ? t('settings.email.sending') : t('settings.email.sendVerificationEmail') }}
          </button>
        </div>
      </div>
    </section>

    <section v-show="activeTab === 'payment'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">{{ t('settings.payment.sectionTitle') }}</h2>
      <p class="text-sm text-gray-600 mb-3">
        {{ t('settings.payment.intro') }}
      </p>
      <p v-if="payoutConfig" class="text-sm mb-3">
        {{ t('settings.payment.platformCommission') }}
        <strong>{{ t('settings.payment.commissionPercentSuffix', { percent: payoutConfig.commission_percent }) }}</strong>
        <span v-if="payoutConfig.estimate_note" class="text-gray-500"> — {{ payoutConfig.estimate_note }}</span>
      </p>
      <p v-if="payoutError" class="text-red-600 text-sm mb-2">{{ payoutError }}</p>
      <p v-if="payoutSuccess" class="text-green-700 text-sm mb-2">{{ payoutSuccess }}</p>

      <ul class="space-y-2 text-sm mb-4">
        <li v-for="m in payoutMethods" :key="m.id" class="border rounded-xl p-3 flex flex-col gap-1">
          <div class="font-medium flex flex-wrap items-center gap-2">
            <span>{{ m.display_name }}</span>
            <span
              v-if="m.verification_status === 'verified'"
              class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800"
            >{{ t('settings.payment.badges.verified') }}</span>
            <span
              v-else
              class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-900"
            >{{ t('settings.payment.badges.unverified') }}</span>
            <span v-if="m.is_primary" class="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-800">{{ t('settings.payment.badges.primary') }}</span>
            <span v-if="!m.is_active" class="text-xs text-gray-500">{{ t('settings.payment.badges.inactive') }}</span>
          </div>
          <div class="text-gray-600">
            {{ methodTypeLabel(m.method_type) }} · {{ m.account_identifier }}
            <span v-if="m.bank_code"> · {{ t('settings.payment.binPrefix') }} {{ m.bank_code }}</span>
            <span v-if="m.bank_name"> · {{ m.bank_name }}</span>
            <span v-if="m.account_holder"> · {{ m.account_holder }}</span>
          </div>
          <p v-if="m.verification_status !== 'verified'" class="text-xs text-amber-800">
            {{ t('settings.payment.waitingVerification') }}
          </p>
          <div class="flex gap-2 mt-1">
            <button v-if="m.is_active && !m.is_primary" type="button" class="underline text-xs" @click="setPrimary(m.id)">
              {{ t('settings.payment.actions.setPrimary') }}
            </button>
            <button v-if="m.is_active" type="button" class="underline text-xs" @click="deactivateMethod(m.id)">
              {{ t('settings.payment.actions.deactivate') }}
            </button>
            <button type="button" class="underline text-xs text-red-600" @click="deleteMethod(m.id)">
              {{ t('settings.payment.actions.delete') }}
            </button>
          </div>
        </li>
        <li v-if="!payoutMethods.length" class="text-gray-500">{{ t('settings.payment.emptyMethods') }}</li>
      </ul>

      <div class="grid gap-2 text-sm">
        <select v-model="payoutForm.method_type" class="border rounded-xl px-3 py-2">
          <option value="bank">{{ t('settings.payment.methodType.bank') }}</option>
          <option value="e_wallet">{{ t('settings.payment.methodType.eWallet') }}</option>
        </select>
        <input v-model="payoutForm.display_name" :placeholder="t('settings.payment.placeholders.displayName')" class="border rounded-xl px-3 py-2" />
        <input v-model="payoutForm.account_identifier" :placeholder="t('settings.payment.placeholders.accountIdentifier')" class="border rounded-xl px-3 py-2" />
        <input
          v-if="payoutForm.method_type === 'bank'"
          v-model="payoutForm.bank_code"
          :placeholder="t('settings.payment.placeholders.bankBin')"
          class="border rounded-xl px-3 py-2"
        />
        <input v-model="payoutForm.bank_name" :placeholder="t('settings.payment.placeholders.bankName')" class="border rounded-xl px-3 py-2" />
        <input
          v-model="payoutForm.account_holder"
          :placeholder="payoutForm.method_type === 'bank' ? t('settings.payment.placeholders.accountHolderRequired') : t('settings.payment.placeholders.accountHolderOptional')"
          class="border rounded-xl px-3 py-2"
        />
        <label class="flex items-center gap-2 text-xs">
          <input v-model="payoutForm.is_primary" type="checkbox" />
          {{ t('settings.payment.setAsPrimary') }}
        </label>
        <button type="button" class="px-4 py-2 rounded-full bg-black text-white w-fit" @click="addPayoutMethod">
          {{ t('settings.payment.addPaymentMethod') }}
        </button>
      </div>

      <div class="mt-8">
        <h3 class="font-semibold mb-2">{{ t('settings.payment.recentPayoutsTitle') }}</h3>
        <ul class="text-sm space-y-2">
          <li v-for="p in myPayouts" :key="p.order_id" class="border rounded-xl px-3 py-2 flex flex-wrap gap-x-3 gap-y-1">
            <span>{{ t('settings.payment.payoutOrder', { orderId: p.order_id }) }}</span>
            <span>{{ t('settings.payment.payoutPin', { pinId: p.pin_id }) }}</span>
            <span class="tabular-nums">{{
              p.payout_amount_vnd != null
                ? t('settings.payment.payoutAmountVnd', { amount: p.payout_amount_vnd })
                : t('settings.payment.payoutAmountMissing')
            }}</span>
            <span class="font-medium">{{ payoutStatusLabel(p.payout_status) }}</span>
          </li>
          <li v-if="!myPayouts.length" class="text-gray-500">{{ t('settings.payment.emptyPayouts') }}</li>
        </ul>
      </div>
    </section>

    <section v-show="activeTab === 'selling'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">{{ t('settings.selling.sectionTitle') }}</h2>
      <p class="text-sm text-gray-600 mb-3">
        {{ t('settings.selling.intro') }}
      </p>
      <p v-if="sellError" class="text-red-600 text-sm mb-2">{{ sellError }}</p>
      <p v-if="sellSuccess" class="text-green-700 text-sm mb-2">{{ sellSuccess }}</p>
      <div v-if="sellEligibility" class="text-sm space-y-1 mb-4">
        <div
          v-for="c in sellEligibility.criteria"
          :key="c.code"
          class="flex justify-between gap-4 border-b border-gray-100 py-1"
        >
          <span>{{ criterionLabel(c.code) }}</span>
          <span :class="c.passed ? 'text-emerald-700' : 'text-red-600'" class="tabular-nums shrink-0">
            {{ t('settings.selling.criteriaProgress', { current: c.current, threshold: c.threshold }) }}
          </span>
        </div>
        <p class="text-xs text-gray-500 mt-2">
          <span v-if="sellEligibility.has_seller_role" class="text-emerald-700 font-medium">{{ t('settings.selling.statusSellingEnabled') }}</span>
          <span v-else-if="sellEligibility.eligible" class="text-amber-700 font-medium">{{ t('settings.selling.statusEligible') }}</span>
          <span v-else class="font-medium">{{ t('settings.selling.statusNotEligible') }}</span>
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-if="!sellEligibility?.has_seller_role"
          type="button"
          class="px-4 py-2 rounded-full bg-red-600 text-white text-sm disabled:opacity-40"
          :disabled="sellBusy || !(sellEligibility && sellEligibility.eligible)"
          @click="enableSellingFromSettings"
        >
          {{ sellBusy ? t('settings.selling.enabling') : t('settings.selling.enableSelling') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-full border text-sm"
          @click="setTab('payment')"
        >
          {{ t('settings.selling.goToPaymentMethods') }}
        </button>
      </div>
    </section>

    <div v-show="activeTab === 'hiring'" class="space-y-6">
      <section
        v-if="userStore.accountKind === 'organization'"
        class="border border-gray-200 rounded-2xl p-6"
      >
        <h2 class="text-lg font-semibold mb-2">{{ t('settings.hiring.sectionTitle') }}</h2>
        <p class="text-sm text-gray-600">
          {{ t('settings.hiring.organizationMessage') }}
        </p>
      </section>

      <section
        v-else-if="userStore.isAdmin"
        class="border border-gray-200 rounded-2xl p-6"
      >
        <h2 class="text-lg font-semibold mb-2">{{ t('settings.hiring.sectionTitle') }}</h2>
        <p class="text-sm text-gray-600">
          {{ t('settings.hiring.adminMessage') }}
        </p>
      </section>

      <section v-else class="border border-gray-200 rounded-2xl p-6">
        <h2 class="text-lg font-semibold mb-2">{{ t('settings.hiring.requestTitle') }}</h2>
        <p class="text-sm text-gray-600 mb-4">
          {{ t('settings.hiring.requestIntro') }}
        </p>

        <p v-if="error" class="text-red-600 text-sm mb-3 whitespace-pre-wrap break-words bg-red-50 border border-red-200 rounded-xl px-3 py-2">
          {{ error }}
        </p>
        <p v-if="success" class="text-green-700 text-sm mb-3">{{ success }}</p>

        <div class="grid gap-3 text-sm">
          <input v-model="form.display_name" :placeholder="t('settings.hiring.placeholders.companyDisplayName')" class="border rounded-xl px-3 py-2" />
          <textarea v-model="form.description" :placeholder="t('settings.hiring.placeholders.description')" rows="3" class="border rounded-xl px-3 py-2" />
          <input v-model="form.industry" :placeholder="t('settings.hiring.placeholders.industry')" class="border rounded-xl px-3 py-2" />
          <div class="flex gap-2">
            <input v-model="form.size_min" type="number" :placeholder="t('settings.hiring.placeholders.sizeMin')" class="border rounded-xl px-3 py-2 w-1/2" />
            <input v-model="form.size_max" type="number" :placeholder="t('settings.hiring.placeholders.sizeMax')" class="border rounded-xl px-3 py-2 w-1/2" />
          </div>
          <input v-model="form.website" :placeholder="t('settings.hiring.placeholders.website')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.domain" :placeholder="t('settings.hiring.placeholders.domain')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_country" :placeholder="t('settings.hiring.placeholders.registrationCountry')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_authority" :placeholder="t('settings.hiring.placeholders.registrationAuthority')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_type" :placeholder="t('settings.hiring.placeholders.registrationType')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_number_raw" :placeholder="t('settings.hiring.placeholders.registrationNumber')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.tax_id" :placeholder="t('settings.hiring.placeholders.taxId')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.vat_number" :placeholder="t('settings.hiring.placeholders.vat')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.address_line" :placeholder="t('settings.hiring.placeholders.primaryAddress')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.city" :placeholder="t('settings.hiring.placeholders.city')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.signer_full_name" :placeholder="t('settings.hiring.placeholders.signerFullName')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.primary_document_language" :placeholder="t('settings.hiring.placeholders.documentLanguage')" class="border rounded-xl px-3 py-2" />
          <input v-model="form.company_email" :placeholder="t('settings.hiring.placeholders.companyEmail')" class="border rounded-xl px-3 py-2" />
        </div>

        <button
          type="button"
          class="mt-4 px-5 py-2 rounded-full bg-black text-white disabled:opacity-50"
          :disabled="submitting"
          @click="submitKyc"
        >
          {{ submitting ? t('settings.hiring.submitting') : t('settings.hiring.submitHiringRequest') }}
        </button>

        <div class="mt-8 border-t pt-4">
          <h3 class="font-semibold mb-2">{{ t('settings.hiring.uploadDocumentsTitle') }}</h3>
          <select v-model="uploadRequestId" class="border rounded-xl px-3 py-2 mb-2 w-full">
            <option :value="null" disabled>{{ t('settings.hiring.selectRequest') }}</option>
            <option v-for="r in requests" :key="r.id" :value="r.id">
              {{ t('settings.hiring.requestOption', {
                id: r.id,
                status: kycStatusLabel(r.status),
                emailStatus: r.company_email_confirmed_at ? t('settings.hiring.emailConfirmedSuffix') : t('settings.hiring.confirmEmailSuffix'),
              }) }}
            </option>
          </select>
          <select v-model="docType" class="border rounded-xl px-3 py-2 mb-2 w-full">
            <option v-for="docOpt in docTypes" :key="docOpt.value" :value="docOpt.value">{{ docOpt.label }}</option>
          </select>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png" class="mb-2" @change="onFileChange" />
          <button type="button" class="px-4 py-2 rounded-full border" @click="uploadDoc">
            {{ t('settings.hiring.uploadDocument') }}
          </button>
        </div>
      </section>

      <section class="border border-gray-200 rounded-2xl p-6">
        <h2 class="text-lg font-semibold mb-3">{{ t('settings.hiring.myRequestsTitle') }}</h2>
        <p v-if="loading" class="text-sm text-gray-500">{{ t('settings.hiring.loading') }}</p>
        <ul v-else class="space-y-3 text-sm">
          <li v-for="r in requests" :key="r.id" class="border rounded-xl p-3">
            <div class="font-medium">{{ t('settings.hiring.requestLine', { id: r.id, status: kycStatusLabel(r.status) }) }}</div>
            <div class="text-gray-600">{{ r.company_email }}</div>
            <div v-if="!r.company_email_confirmed_at" class="mt-2">
              <button type="button" class="underline" @click="resendConfirm(r.id)">
                {{ t('settings.hiring.resendConfirmationEmail') }}
              </button>
            </div>
            <div v-if="r.rejection_reason" class="text-red-600 mt-1">{{ r.rejection_reason }}</div>
            <div v-if="r.admin_note" class="text-amber-700 mt-1">{{ t('settings.hiring.adminNotePrefix') }} {{ r.admin_note }}</div>
          </li>
          <li v-if="!requests.length" class="text-gray-500">{{ t('settings.hiring.emptyRequests') }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.animated-border {
  position: relative;
}

.animated-border::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background-color: red;
  transition: width 0.3s ease-out, transform 0.3s ease-out;
  transform: translateX(-50%);
}

.active::after {
  width: 100%;
  left: 50%;
  transform: translateX(-50%);
}

.animated-border:hover {
  color: red;
  transform: scale(1.05);
}

.animated-border:hover::after {
  width: 100%;
  left: 50%;
  transform: translateX(-50%);
}
</style>
