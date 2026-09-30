<script setup>
import { onMounted, ref } from 'vue';
import axios from 'axios';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  userId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
});

const { t } = useI18n();
const items = ref([]);
const loading = ref(true);
const error = ref(null);
const formOpen = ref(false);
const editingId = ref(null);
const form = ref({
  kind: 'education',
  title: '',
  organization: '',
  occurred_on: '',
  description: '',
});

const kinds = ['education', 'licensing', 'award'];

const kindLabel = (kind) => t(`jobMarket.credentialsTab.kinds.${kind}`);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get(
      `/api/job-market/users/${props.userId}/credentials`
    );
    items.value = data;
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.credentialsTab.errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  editingId.value = null;
  form.value = {
    kind: 'education',
    title: '',
    organization: '',
    occurred_on: '',
    description: '',
  };
}

function openCreate() {
  resetForm();
  formOpen.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  form.value = {
    kind: row.kind,
    title: row.title,
    organization: row.organization || '',
    occurred_on: row.occurred_on || '',
    description: row.description || '',
  };
  formOpen.value = true;
}

async function save() {
  const payload = {
    kind: form.value.kind,
    title: form.value.title,
    organization: form.value.organization || null,
    occurred_on: form.value.occurred_on || null,
    description: form.value.description || null,
  };
  try {
    if (editingId.value) {
      await axios.patch(`/api/job-market/me/credentials/${editingId.value}`, payload);
    } else {
      await axios.post('/api/job-market/me/credentials', payload);
    }
    formOpen.value = false;
    resetForm();
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.credentialsTab.errors.saveFailed');
  }
}

async function remove(id) {
  if (!confirm(t('jobMarket.credentialsTab.confirmDelete'))) return;
  try {
    await axios.delete(`/api/job-market/me/credentials/${id}`);
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.credentialsTab.errors.deleteFailed');
  }
}

onMounted(load);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold">{{ t('jobMarket.credentialsTab.title') }}</h2>
      <button
        v-if="isOwner"
        type="button"
        class="px-4 py-2 bg-black text-white rounded-full text-sm"
        @click="openCreate"
      >
        {{ t('jobMarket.shared.add') }}
      </button>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      {{ t('jobMarket.credentialsTab.subtitle') }}
    </p>
    <p v-if="loading" class="text-gray-500">{{ t('jobMarket.shared.loading') }}</p>
    <p v-else-if="error" class="text-red-600 text-sm mb-3">{{ error }}</p>
    <p v-else-if="!items.length" class="text-gray-500">{{ t('jobMarket.credentialsTab.empty') }}</p>
    <ul v-else class="space-y-4">
      <li v-for="row in items" :key="row.id" class="border-b border-gray-200 pb-3">
        <div class="flex justify-between gap-4">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">
              {{ kindLabel(row.kind) || row.kind }}
            </p>
            <p class="font-semibold">{{ row.title }}</p>
            <p v-if="row.organization" class="text-gray-700">{{ row.organization }}</p>
            <p v-if="row.occurred_on" class="text-sm text-gray-600">{{ row.occurred_on }}</p>
            <p v-if="row.description" class="text-sm mt-1">{{ row.description }}</p>
          </div>
          <div v-if="isOwner" class="flex gap-2 text-sm shrink-0">
            <button type="button" class="underline" @click="openEdit(row)">{{ t('jobMarket.shared.edit') }}</button>
            <button type="button" class="underline text-red-600" @click="remove(row.id)">
              {{ t('jobMarket.shared.delete') }}
            </button>
          </div>
        </div>
      </li>
    </ul>

    <div
      v-if="formOpen"
      class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center"
      @click.self="formOpen = false"
    >
      <form
        class="bg-white rounded-2xl p-6 w-full max-w-md space-y-3"
        @submit.prevent="save"
      >
        <h3 class="text-lg font-bold">
          {{ editingId ? t('jobMarket.credentialsTab.form.editTitle') : t('jobMarket.credentialsTab.form.addTitle') }}
        </h3>
        <select v-model="form.kind" class="w-full border rounded-lg px-3 py-2">
          <option v-for="k in kinds" :key="k" :value="k">{{ kindLabel(k) }}</option>
        </select>
        <input
          v-model="form.title"
          required
          :placeholder="t('jobMarket.credentialsTab.form.titlePlaceholder')"
          class="w-full border rounded-lg px-3 py-2"
        />
        <input
          v-model="form.organization"
          :placeholder="t('jobMarket.credentialsTab.form.organizationPlaceholder')"
          class="w-full border rounded-lg px-3 py-2"
        />
        <label class="block text-sm"
          >{{ t('jobMarket.credentialsTab.form.dateOptional') }}
          <input v-model="form.occurred_on" type="date" class="w-full border rounded-lg px-3 py-2"
        /></label>
        <textarea
          v-model="form.description"
          rows="3"
          :placeholder="t('jobMarket.credentialsTab.form.descriptionPlaceholder')"
          class="w-full border rounded-lg px-3 py-2"
        />
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="px-4 py-2" @click="formOpen = false">{{ t('jobMarket.shared.cancel') }}</button>
          <button type="submit" class="px-4 py-2 bg-black text-white rounded-full">{{ t('jobMarket.shared.save') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
