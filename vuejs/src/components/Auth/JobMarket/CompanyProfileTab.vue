<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import axios from 'axios';
import { authUserStore } from '@/stores/authUserStore';
import { profilePath } from '@/utils/profileLinks';

const props = defineProps({
  companyId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
});

const userStore = authUserStore();
const company = ref(null);
const branches = ref([]);
const pending = ref([]);
const loading = ref(true);
const error = ref(null);
const saving = ref(false);
const form = ref({
  display_name: '',
  description: '',
  industry: '',
  size_min: null,
  size_max: null,
  website: '',
  domain: '',
  employees_public: true,
});
const branchForm = ref({
  label: '',
  address_line: '',
  city: '',
  country: '',
  is_primary: false,
});
const warnings = ref([]);

const canEdit = computed(
  () => props.isOwner && userStore.accountKind === 'organization'
);

async function loadPending() {
  if (!canEdit.value) {
    pending.value = [];
    return;
  }
  try {
    const { data } = await axios.get(
      '/api/job-market/me/company/work-experiences/pending'
    );
    pending.value = data;
  } catch {
    pending.value = [];
  }
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const [cRes, bRes] = await Promise.all([
      axios.get(`/api/job-market/companies/${props.companyId}`),
      axios.get(`/api/job-market/companies/${props.companyId}/branches`),
    ]);
    company.value = cRes.data;
    branches.value = bRes.data || [];
    form.value = {
      display_name: cRes.data.display_name || '',
      description: cRes.data.description || '',
      industry: cRes.data.industry || '',
      size_min: cRes.data.size_min,
      size_max: cRes.data.size_max,
      website: cRes.data.website || '',
      domain: cRes.data.domain || '',
      employees_public: cRes.data.employees_public !== false,
    };
    await loadPending();
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load company';
  } finally {
    loading.value = false;
  }
}

async function saveProfile() {
  if (!canEdit.value) return;
  saving.value = true;
  error.value = null;
  warnings.value = [];
  try {
    const payload = {
      ...form.value,
      size_min: form.value.size_min === '' || form.value.size_min == null
        ? null
        : Number(form.value.size_min),
      size_max: form.value.size_max === '' || form.value.size_max == null
        ? null
        : Number(form.value.size_max),
      employees_public: !!form.value.employees_public,
    };
    const { data } = await axios.patch('/api/job-market/me/company', payload);
    company.value = data;
    warnings.value = data.warnings || [];
  } catch (e) {
    error.value = e.response?.data?.detail || 'Save failed';
  } finally {
    saving.value = false;
  }
}

async function addBranch() {
  if (!canEdit.value || !branchForm.value.address_line.trim()) return;
  try {
    const { data } = await axios.post(
      '/api/job-market/me/company/branches',
      branchForm.value
    );
    branches.value.push(data);
    branchForm.value = {
      label: '',
      address_line: '',
      city: '',
      country: '',
      is_primary: false,
    };
  } catch (e) {
    error.value = e.response?.data?.detail || 'Branch create failed';
  }
}

async function decide(row, action) {
  try {
    await axios.post(
      `/api/job-market/me/company/work-experiences/${row.id}/${action}`
    );
    await loadPending();
  } catch (e) {
    error.value = e.response?.data?.detail || `${action} failed`;
  }
}

onMounted(load);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <h2 class="text-2xl font-bold mb-4">Company</h2>
    <p v-if="loading" class="text-gray-500">Loading…</p>
    <p v-else-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

    <div v-if="company && !loading" class="space-y-4">
      <template v-if="canEdit">
        <label class="block text-sm font-medium">Display name
          <input v-model="form.display_name" class="mt-1 w-full border rounded-xl px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Description
          <textarea v-model="form.description" rows="4" class="mt-1 w-full border rounded-xl px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Industry
          <input v-model="form.industry" class="mt-1 w-full border rounded-xl px-3 py-2" />
        </label>
        <div class="flex gap-4">
          <label class="block text-sm font-medium flex-1">Size min
            <input v-model="form.size_min" type="number" class="mt-1 w-full border rounded-xl px-3 py-2" />
          </label>
          <label class="block text-sm font-medium flex-1">Size max
            <input v-model="form.size_max" type="number" class="mt-1 w-full border rounded-xl px-3 py-2" />
          </label>
        </div>
        <label class="block text-sm font-medium">Website
          <input v-model="form.website" class="mt-1 w-full border rounded-xl px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Domain
          <input v-model="form.domain" class="mt-1 w-full border rounded-xl px-3 py-2" />
        </label>
        <label class="flex items-center gap-2 text-sm font-medium">
          <input v-model="form.employees_public" type="checkbox" />
          Employees tab public
        </label>
        <ul v-if="warnings.length" class="text-amber-700 text-sm">
          <li v-for="w in warnings" :key="w.code">{{ w.message || w.code }}</li>
        </ul>
        <button
          type="button"
          class="px-5 py-2 rounded-full bg-black text-white disabled:opacity-50"
          :disabled="saving"
          @click="saveProfile"
        >
          {{ saving ? 'Saving…' : 'Save company profile' }}
        </button>

        <div class="border-t pt-4 mt-6">
          <h3 class="font-semibold mb-2">Pending work experience</h3>
          <p v-if="!pending.length" class="text-sm text-gray-500">No pending requests.</p>
          <ul v-else class="space-y-3 text-sm">
            <li v-for="row in pending" :key="row.id" class="border-b pb-2">
              <p class="font-medium">
                <RouterLink
                  v-if="row.artist_username"
                  :to="profilePath(row.artist_username, { tab: 'experience', workExpId: row.id })"
                  class="underline"
                >
                  {{ row.artist_username }}
                </RouterLink>
                <span v-else>User #{{ row.user_id }}</span>
                — {{ row.title }}
              </p>
              <p class="text-gray-600">{{ row.start_date }} → {{ row.end_date || 'Present' }}</p>
              <div class="flex gap-2 mt-1">
                <button
                  type="button"
                  class="px-3 py-1 bg-black text-white rounded-full text-xs"
                  @click="decide(row, 'approve')"
                >
                  Approve
                </button>
                <button
                  type="button"
                  class="px-3 py-1 border rounded-full text-xs"
                  @click="decide(row, 'reject')"
                >
                  Reject
                </button>
              </div>
            </li>
          </ul>
        </div>

        <div class="border-t pt-4 mt-6">
          <h3 class="font-semibold mb-2">Branches</h3>
          <ul class="text-sm space-y-1 mb-3">
            <li v-for="b in branches" :key="b.id">
              {{ b.label ? b.label + ' — ' : '' }}{{ b.address_line }}
              <span v-if="b.city">, {{ b.city }}</span>
            </li>
          </ul>
          <div class="grid gap-2">
            <input v-model="branchForm.label" placeholder="Label" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.address_line" placeholder="Address line" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.city" placeholder="City" class="border rounded-xl px-3 py-2" />
            <input v-model="branchForm.country" placeholder="Country" class="border rounded-xl px-3 py-2" />
            <button type="button" class="px-4 py-2 rounded-full border w-fit" @click="addBranch">
              Add branch
            </button>
          </div>
        </div>
      </template>

      <template v-else>
        <p class="text-xl font-semibold">{{ company.display_name }}</p>
        <p v-if="company.industry" class="text-sm text-gray-600">{{ company.industry }}</p>
        <p v-if="company.description" class="mt-2 whitespace-pre-wrap">{{ company.description }}</p>
        <p v-if="company.size_min != null || company.size_max != null" class="text-sm text-gray-600 mt-2">
          Size: {{ company.size_min ?? '?' }} – {{ company.size_max ?? '?' }}
        </p>
        <p v-if="company.website" class="text-sm mt-2">
          <a :href="company.website" class="underline" target="_blank" rel="noopener">{{ company.website }}</a>
        </p>
        <div v-if="branches.length" class="mt-4">
          <h3 class="font-semibold mb-1">Locations</h3>
          <ul class="text-sm space-y-1">
            <li v-for="b in branches" :key="b.id">
              {{ b.address_line }}<span v-if="b.city">, {{ b.city }}</span>
            </li>
          </ul>
        </div>
      </template>
    </div>
  </div>
</template>
