<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import axios from 'axios';
import { profilePath } from '@/utils/profileLinks';

const props = defineProps({
  companyId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
});

const data = ref(null);
const loading = ref(true);
const error = ref(null);
const privateBlocked = ref(false);
const headForm = ref({ user_id: '', title: '', note: '', sort_order: 0 });

const headUserIds = computed(() => new Set((data.value?.heads || []).map((h) => h.user_id)));
const bodyEmployees = computed(() =>
  (data.value?.employees || []).filter((e) => !headUserIds.value.has(e.user_id))
);

async function load() {
  loading.value = true;
  error.value = null;
  privateBlocked.value = false;
  try {
    const res = await axios.get(`/api/job-market/companies/${props.companyId}/employees`);
    data.value = res.data;
  } catch (e) {
    if (e?.response?.status === 403) {
      privateBlocked.value = true;
      data.value = null;
    } else {
      error.value = e?.response?.data?.detail || 'Failed to load employees';
    }
  } finally {
    loading.value = false;
  }
}

async function addHead() {
  if (!props.isOwner) return;
  try {
    await axios.post('/api/job-market/me/company/employee-heads', {
      user_id: Number(headForm.value.user_id),
      title: headForm.value.title,
      note: headForm.value.note || null,
      sort_order: Number(headForm.value.sort_order) || 0,
    });
    headForm.value = { user_id: '', title: '', note: '', sort_order: 0 };
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Add head failed';
  }
}

async function removeHead(id) {
  if (!props.isOwner || !confirm('Remove head?')) return;
  try {
    await axios.delete(`/api/job-market/me/company/employee-heads/${id}`);
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Delete failed';
  }
}

onMounted(load);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <h2 class="text-xl font-bold mb-4">Employees</h2>
    <p v-if="loading" class="text-gray-500">Loading…</p>
    <p v-else-if="privateBlocked" class="text-gray-600">This employee list is private.</p>
    <p v-else-if="error" class="text-red-600 text-sm mb-3">{{ error }}</p>

    <template v-else-if="data">
      <p class="text-sm text-gray-500 mb-4">
        Visibility: {{ data.employees_public ? 'Public' : 'Private' }}
      </p>

      <section v-if="data.heads?.length" class="mb-6">
        <h3 class="font-semibold mb-2">Leadership</h3>
        <ul class="space-y-3">
          <li v-for="h in data.heads" :key="h.id" class="border-b pb-2">
            <div class="flex justify-between gap-3">
              <div>
                <RouterLink
                  v-if="h.username"
                  :to="profilePath(h.username, { tab: 'experience' })"
                  class="font-medium underline"
                >
                  {{ h.username }}
                </RouterLink>
                <span v-else>User #{{ h.user_id }}</span>
                <p class="text-sm">{{ h.title }}</p>
                <p v-if="h.note" class="text-xs text-gray-600">{{ h.note }}</p>
              </div>
              <button
                v-if="isOwner"
                type="button"
                class="text-sm text-red-600 underline"
                @click="removeHead(h.id)"
              >
                Remove
              </button>
            </div>
          </li>
        </ul>
      </section>

      <section>
        <h3 class="font-semibold mb-2">Team</h3>
        <p v-if="!bodyEmployees.length" class="text-gray-500 text-sm">No present employees.</p>
        <ul v-else class="space-y-2">
          <li v-for="e in bodyEmployees" :key="e.user_id" class="text-sm">
            <RouterLink
              v-if="e.username"
              :to="profilePath(e.username, { tab: 'experience' })"
              class="underline font-medium"
            >
              {{ e.username }}
            </RouterLink>
            <span v-else>User #{{ e.user_id }}</span>
            <span v-if="e.title"> · {{ e.title }}</span>
            <span v-if="e.start_date" class="text-gray-500"> · since {{ e.start_date }}</span>
          </li>
        </ul>
      </section>

      <section v-if="isOwner" class="mt-8 border-t pt-4 space-y-2">
        <h3 class="font-semibold">Add head</h3>
        <select v-model="headForm.user_id" class="w-full border rounded-lg px-3 py-2">
          <option value="">Select employee</option>
          <option
            v-for="e in data.employees"
            :key="e.user_id"
            :value="e.user_id"
          >
            {{ e.username || e.user_id }} — {{ e.title }}
          </option>
        </select>
        <input
          v-model="headForm.title"
          placeholder="Head title"
          class="w-full border rounded-lg px-3 py-2"
        />
        <input
          v-model="headForm.note"
          placeholder="Note (optional)"
          class="w-full border rounded-lg px-3 py-2"
        />
        <button
          type="button"
          class="px-4 py-2 bg-black text-white rounded-full text-sm"
          :disabled="!headForm.user_id || !headForm.title"
          @click="addHead"
        >
          Add head
        </button>
      </section>
    </template>
  </div>
</template>
