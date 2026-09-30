<script setup>
import { onMounted, ref, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { authUserStore } from '@/stores/authUserStore';

const userStore = authUserStore();
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
  const t = String(route.query.tab || '');
  // payout kept as alias for payment methods
  if (t === 'email' || t === 'payment' || t === 'payout' || t === 'selling' || t === 'hiring') {
    const tab = t === 'payout' ? 'payment' : t;
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

const docTypes = [
  { value: 'business_registration_document', label: 'Business registration' },
  { value: 'tax_registration_document', label: 'Tax registration' },
  { value: 'authorization_evidence', label: 'Authorization evidence' },
  { value: 'identity_document', label: 'Identity document' },
  { value: 'document_translation', label: 'Document translation' },
];

const CRITERION_LABELS = {
  N: 'Created pins',
  M: 'Total pin views',
  K: 'Followers',
  P: 'Verified payment methods',
};

const PAYOUT_STATUS_LABELS = {
  pending: 'Pending',
  paid: 'Paid',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

function criterionLabel(code) {
  return CRITERION_LABELS[code] || code;
}

function payoutStatusLabel(status) {
  return PAYOUT_STATUS_LABELS[status] || status;
}

function kycStatusLabel(status) {
  const map = {
    pending: 'Pending',
    approved: 'Approved',
    rejected: 'Rejected',
    need_more_info: 'Needs more info',
  };
  return map[status] || status;
}

const REQUIRED_FIELDS = [
  ['display_name', 'Company display name'],
  ['registration_country', 'Registration country'],
  ['registration_type', 'Registration type'],
  ['registration_number_raw', 'Registration number'],
  ['signer_full_name', 'Signer full name'],
  ['primary_document_language', 'Document language'],
  ['company_email', 'Company email'],
];

function formatApiError(err, fallback = 'Request failed') {
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
    message =
      'Session expired (Token has expired). Log out and log in again, then resubmit.';
  } else if (status === 403 && /csrf/i.test(message)) {
    message = 'CSRF validation failed. Refresh the page, then try again.';
  }

  const prefixed = status ? `[${status}] ${message}` : message;
  console.error('[Settings]', prefixed, err?.response?.data || err);
  return prefixed;
}

function validateRequired() {
  const missing = REQUIRED_FIELDS.filter(
    ([key]) => !String(form.value[key] ?? '').trim()
  ).map(([, label]) => label);
  if (missing.length) {
    return `Missing required fields: ${missing.join(', ')}`;
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
    emailError.value = 'Enter an email address.';
    return;
  }
  emailBusy.value = true;
  try {
    const { data } = await axios.patch('/api/users/information', { email: next });
    await loadAccountEmail(data);
    emailSuccess.value = emailVerified.value
      ? 'Email updated.'
      : 'Email saved. Send a verification link below.';
  } catch (e) {
    emailError.value = formatApiError(e, 'Could not update email.');
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
      emailSuccess.value = `Email ${data.email} is already verified.`;
    } else {
      emailSuccess.value = `Verification link sent to ${data.email}. Check inbox and spam.`;
    }
  } catch (e) {
    emailError.value = formatApiError(e, 'Could not send verification email.');
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
    payoutError.value = formatApiError(e, 'Failed to load payment methods');
  }
}

async function loadSelling() {
  sellError.value = null;
  try {
    const { data } = await axios.get('/api/marketplace/me/eligibility');
    sellEligibility.value = data;
  } catch (e) {
    sellError.value = formatApiError(e, 'Failed to load selling eligibility');
  }
}

async function enableSellingFromSettings() {
  sellBusy.value = true;
  sellError.value = null;
  sellSuccess.value = null;
  try {
    const { data } = await axios.post('/api/marketplace/me/enable-selling');
    userStore.setRoles(data.roles || []);
    sellSuccess.value = 'Selling enabled. List pins from each pin page.';
    await loadSelling();
  } catch (e) {
    sellError.value = formatApiError(e, 'Eligibility not met');
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
    payoutError.value = 'Display name and account identifier are required.';
    return;
  }
  if (payoutForm.value.method_type === 'bank') {
    if (!payoutForm.value.bank_code.trim() || !payoutForm.value.account_holder.trim()) {
      payoutError.value = 'Bank code (BIN) and account holder are required for bank methods.';
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
    payoutSuccess.value = 'Payment method added.';
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, 'Cannot add payout method');
  }
}

async function setPrimary(id) {
  payoutError.value = null;
  try {
    await axios.patch(`/api/marketplace/me/payment-methods/${id}`, { is_primary: true });
    payoutSuccess.value = 'Primary method updated.';
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, 'Cannot set primary');
  }
}

async function deactivateMethod(id) {
  payoutError.value = null;
  try {
    await axios.patch(`/api/marketplace/me/payment-methods/${id}`, { is_active: false });
    payoutSuccess.value = 'Method deactivated.';
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, 'Cannot deactivate');
  }
}

async function deleteMethod(id) {
  payoutError.value = null;
  try {
    await axios.delete(`/api/marketplace/me/payment-methods/${id}`);
    payoutSuccess.value = 'Method deleted.';
    await loadPayout();
  } catch (e) {
    payoutError.value = formatApiError(e, 'Cannot delete');
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
    error.value = formatApiError(e, 'Failed to load requests');
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
    success.value = `Request #${data.id} submitted. Confirm company email, then upload documents.`;
    uploadRequestId.value = data.id;
    if (data.warnings?.length) {
      const msgs = data.warnings.map((w) => w.message || w.code).filter(Boolean);
      if (msgs.length) success.value += ` Note: ${msgs.join('; ')}`;
    }
    await loadRequests();
  } catch (e) {
    error.value = formatApiError(e, 'Submit failed');
  } finally {
    submitting.value = false;
  }
}

async function uploadDoc() {
  if (!uploadRequestId.value || !docFile.value) {
    error.value = 'Select a request and choose a file before upload.';
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
    success.value = 'Document uploaded.';
    docFile.value = null;
  } catch (e) {
    error.value = formatApiError(e, 'Upload failed');
  }
}

async function resendConfirm(id) {
  try {
    await axios.post(`/api/job-market/me/hiring-rights-requests/${id}/resend-confirm`);
    success.value = 'Confirmation email resent.';
  } catch (e) {
    error.value = formatApiError(e, 'Resend failed');
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
    error.value = formatApiError(
      e,
      'Cannot load session. Log in again before submitting KYC.'
    );
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
    <h1 class="text-3xl font-bold mb-2">Settings</h1>
    <p class="text-gray-600 mb-6 text-sm">
      Signed in as {{ userStore.authUsername }}
      <span v-if="userStore.accountKind === 'organization'"> · Company account</span>
      <span v-else-if="userStore.accountKind"> · Personal account</span>
    </p>

    <div class="flex items-center justify-start space-x-2 sm:space-x-4 flex-wrap mb-8 border-b border-gray-200">
      <button
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'email' }"
        @click="setTab('email')"
      >
        Email
      </button>
      <button
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'payment' }"
        @click="setTab('payment')"
      >
        Payment methods
      </button>
      <button
        v-if="canSellSettings"
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'selling' }"
        @click="setTab('selling')"
      >
        Selling
      </button>
      <button
        v-if="canHireSettings || userStore.accountKind === 'organization'"
        type="button"
        class="relative px-5 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
        :class="{ 'active scale-105': activeTab === 'hiring' }"
        @click="setTab('hiring')"
      >
        Hiring rights
      </button>
    </div>

    <section v-show="activeTab === 'email'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">Email verification</h2>
      <p class="text-sm text-gray-600 mb-3">
        Needed for some features (marketplace buy, hiring KYC). You can still use the app while unverified.
      </p>
      <p class="text-sm mb-3">
        Status:
        <span v-if="emailVerified" class="font-medium text-emerald-700">Verified</span>
        <span v-else-if="accountEmail" class="font-medium text-amber-700">Not verified</span>
        <span v-else class="font-medium text-gray-600">No email on account</span>
      </p>
      <p v-if="emailError" class="text-red-600 text-sm mb-2 whitespace-pre-wrap">{{ emailError }}</p>
      <p v-if="emailSuccess" class="text-green-700 text-sm mb-2">{{ emailSuccess }}</p>
      <div class="grid gap-2 text-sm">
        <input v-model="emailDraft" type="email" placeholder="Account email" class="border rounded-xl px-3 py-2" />
        <div class="flex flex-wrap gap-2">
          <button type="button" class="px-4 py-2 rounded-full border disabled:opacity-50" :disabled="emailBusy" @click="saveAccountEmail">
            Save email
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-full bg-black text-white disabled:opacity-50"
            :disabled="emailBusy || emailVerified || !(emailDraft || accountEmail)"
            @click="resendVerification"
          >
            {{ emailBusy ? 'Sending…' : 'Send verification email' }}
          </button>
        </div>
      </div>
    </section>

    <section v-show="activeTab === 'payment'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">Payment methods</h2>
      <p class="text-sm text-gray-600 mb-3">
        Bank or e-wallet destinations for marketplace sales. New methods stay
        <strong>unverified</strong> until confirmed. Only verified methods count toward selling eligibility.
        Use an account you own — incorrect details may send funds elsewhere.
      </p>
      <p v-if="payoutConfig" class="text-sm mb-3">
        Platform commission:
        <strong>{{ payoutConfig.commission_percent }}%</strong>
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
            >Verified</span>
            <span
              v-else
              class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-900"
            >Unverified</span>
            <span v-if="m.is_primary" class="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-800">primary</span>
            <span v-if="!m.is_active" class="text-xs text-gray-500">(inactive)</span>
          </div>
          <div class="text-gray-600">
            {{ m.method_type }} · {{ m.account_identifier }}
            <span v-if="m.bank_code"> · BIN {{ m.bank_code }}</span>
            <span v-if="m.bank_name"> · {{ m.bank_name }}</span>
            <span v-if="m.account_holder"> · {{ m.account_holder }}</span>
          </div>
          <p v-if="m.verification_status !== 'verified'" class="text-xs text-amber-800">
            Waiting for verification — does not count toward selling eligibility yet.
          </p>
          <div class="flex gap-2 mt-1">
            <button v-if="m.is_active && !m.is_primary" type="button" class="underline text-xs" @click="setPrimary(m.id)">
              Set primary
            </button>
            <button v-if="m.is_active" type="button" class="underline text-xs" @click="deactivateMethod(m.id)">
              Deactivate
            </button>
            <button type="button" class="underline text-xs text-red-600" @click="deleteMethod(m.id)">
              Delete
            </button>
          </div>
        </li>
        <li v-if="!payoutMethods.length" class="text-gray-500">No payment methods yet.</li>
      </ul>

      <div class="grid gap-2 text-sm">
        <select v-model="payoutForm.method_type" class="border rounded-xl px-3 py-2">
          <option value="bank">Bank</option>
          <option value="e_wallet">E-wallet</option>
        </select>
        <input v-model="payoutForm.display_name" placeholder="Display name *" class="border rounded-xl px-3 py-2" />
        <input v-model="payoutForm.account_identifier" placeholder="Account / wallet id *" class="border rounded-xl px-3 py-2" />
        <input
          v-if="payoutForm.method_type === 'bank'"
          v-model="payoutForm.bank_code"
          placeholder="Bank BIN * (e.g. 970415 VietinBank)"
          class="border rounded-xl px-3 py-2"
        />
        <input v-model="payoutForm.bank_name" placeholder="Bank name (optional if BIN known)" class="border rounded-xl px-3 py-2" />
        <input
          v-model="payoutForm.account_holder"
          :placeholder="payoutForm.method_type === 'bank' ? 'Account holder *' : 'Account holder (optional)'"
          class="border rounded-xl px-3 py-2"
        />
        <label class="flex items-center gap-2 text-xs">
          <input v-model="payoutForm.is_primary" type="checkbox" />
          Set as primary
        </label>
        <button type="button" class="px-4 py-2 rounded-full bg-black text-white w-fit" @click="addPayoutMethod">
          Add payment method
        </button>
      </div>

      <div class="mt-8">
        <h3 class="font-semibold mb-2">Recent payouts</h3>
        <ul class="text-sm space-y-2">
          <li v-for="p in myPayouts" :key="p.order_id" class="border rounded-xl px-3 py-2 flex flex-wrap gap-x-3 gap-y-1">
            <span>Order #{{ p.order_id }}</span>
            <span>Pin #{{ p.pin_id }}</span>
            <span class="tabular-nums">{{ p.payout_amount_vnd ?? '—' }} VND</span>
            <span class="font-medium">{{ payoutStatusLabel(p.payout_status) }}</span>
          </li>
          <li v-if="!myPayouts.length" class="text-gray-500">No paid sales yet.</li>
        </ul>
      </div>
    </section>

    <section v-show="activeTab === 'selling'" class="border border-gray-200 rounded-2xl p-6">
      <h2 class="text-lg font-semibold mb-2">Selling</h2>
      <p class="text-sm text-gray-600 mb-3">
        Requirements to sell licenses. You need a
        <strong>verified</strong> payment method, then list each pin from its page.
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
            {{ c.current }} / {{ c.threshold }}
          </span>
        </div>
        <p class="text-xs text-gray-500 mt-2">
          <span v-if="sellEligibility.has_seller_role" class="text-emerald-700 font-medium">Selling enabled</span>
          <span v-else-if="sellEligibility.eligible" class="text-amber-700 font-medium">Eligible — enable selling below</span>
          <span v-else class="font-medium">Not eligible yet</span>
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
          {{ sellBusy ? 'Enabling…' : 'Enable selling' }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-full border text-sm"
          @click="setTab('payment')"
        >
          Go to Payment methods
        </button>
      </div>
    </section>

    <div v-show="activeTab === 'hiring'" class="space-y-6">
      <section
        v-if="userStore.accountKind === 'organization'"
        class="border border-gray-200 rounded-2xl p-6"
      >
        <h2 class="text-lg font-semibold mb-2">Hiring rights</h2>
        <p class="text-sm text-gray-600">
          This is a company account. Manage the company profile from your profile page.
        </p>
      </section>

      <section
        v-else-if="userStore.isAdmin"
        class="border border-gray-200 rounded-2xl p-6"
      >
        <h2 class="text-lg font-semibold mb-2">Hiring rights</h2>
        <p class="text-sm text-gray-600">
          Admin accounts are ops-only and cannot submit hiring KYC.
        </p>
      </section>

      <section v-else class="border border-gray-200 rounded-2xl p-6">
        <h2 class="text-lg font-semibold mb-2">Request hiring rights</h2>
        <p class="text-sm text-gray-600 mb-4">
          Submit company KYC. Company email must match your verified account email.
        </p>

        <p v-if="error" class="text-red-600 text-sm mb-3 whitespace-pre-wrap break-words bg-red-50 border border-red-200 rounded-xl px-3 py-2">
          {{ error }}
        </p>
        <p v-if="success" class="text-green-700 text-sm mb-3">{{ success }}</p>

        <div class="grid gap-3 text-sm">
          <input v-model="form.display_name" placeholder="Company display name *" class="border rounded-xl px-3 py-2" />
          <textarea v-model="form.description" placeholder="Description" rows="3" class="border rounded-xl px-3 py-2" />
          <input v-model="form.industry" placeholder="Industry" class="border rounded-xl px-3 py-2" />
          <div class="flex gap-2">
            <input v-model="form.size_min" type="number" placeholder="Size min" class="border rounded-xl px-3 py-2 w-1/2" />
            <input v-model="form.size_max" type="number" placeholder="Size max" class="border rounded-xl px-3 py-2 w-1/2" />
          </div>
          <input v-model="form.website" placeholder="Website" class="border rounded-xl px-3 py-2" />
          <input v-model="form.domain" placeholder="Domain" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_country" placeholder="Registration country *" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_authority" placeholder="Registration authority (e.g. National)" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_type" placeholder="Registration type *" class="border rounded-xl px-3 py-2" />
          <input v-model="form.registration_number_raw" placeholder="Registration number *" class="border rounded-xl px-3 py-2" />
          <input v-model="form.tax_id" placeholder="Tax ID (optional)" class="border rounded-xl px-3 py-2" />
          <input v-model="form.vat_number" placeholder="VAT (optional)" class="border rounded-xl px-3 py-2" />
          <input v-model="form.address_line" placeholder="Primary address" class="border rounded-xl px-3 py-2" />
          <input v-model="form.city" placeholder="City" class="border rounded-xl px-3 py-2" />
          <input v-model="form.signer_full_name" placeholder="Signer full name *" class="border rounded-xl px-3 py-2" />
          <input v-model="form.primary_document_language" placeholder="Document language (e.g. en) *" class="border rounded-xl px-3 py-2" />
          <input v-model="form.company_email" placeholder="Company email (must match account email) *" class="border rounded-xl px-3 py-2" />
        </div>

        <button
          type="button"
          class="mt-4 px-5 py-2 rounded-full bg-black text-white disabled:opacity-50"
          :disabled="submitting"
          @click="submitKyc"
        >
          {{ submitting ? 'Submitting…' : 'Submit hiring request' }}
        </button>

        <div class="mt-8 border-t pt-4">
          <h3 class="font-semibold mb-2">Upload documents</h3>
          <select v-model="uploadRequestId" class="border rounded-xl px-3 py-2 mb-2 w-full">
            <option :value="null" disabled>Select request</option>
            <option v-for="r in requests" :key="r.id" :value="r.id">
              Request #{{ r.id }} — {{ kycStatusLabel(r.status) }}
              {{ r.company_email_confirmed_at ? '(email confirmed)' : '(confirm email)' }}
            </option>
          </select>
          <select v-model="docType" class="border rounded-xl px-3 py-2 mb-2 w-full">
            <option v-for="t in docTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png" class="mb-2" @change="onFileChange" />
          <button type="button" class="px-4 py-2 rounded-full border" @click="uploadDoc">
            Upload document
          </button>
        </div>
      </section>

      <section class="border border-gray-200 rounded-2xl p-6">
        <h2 class="text-lg font-semibold mb-3">My hiring requests</h2>
        <p v-if="loading" class="text-sm text-gray-500">Loading…</p>
        <ul v-else class="space-y-3 text-sm">
          <li v-for="r in requests" :key="r.id" class="border rounded-xl p-3">
            <div class="font-medium">Request #{{ r.id }} · {{ kycStatusLabel(r.status) }}</div>
            <div class="text-gray-600">{{ r.company_email }}</div>
            <div v-if="!r.company_email_confirmed_at" class="mt-2">
              <button type="button" class="underline" @click="resendConfirm(r.id)">
                Resend confirmation email
              </button>
            </div>
            <div v-if="r.rejection_reason" class="text-red-600 mt-1">{{ r.rejection_reason }}</div>
            <div v-if="r.admin_note" class="text-amber-700 mt-1">Admin: {{ r.admin_note }}</div>
          </li>
          <li v-if="!requests.length" class="text-gray-500">No requests yet.</li>
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
