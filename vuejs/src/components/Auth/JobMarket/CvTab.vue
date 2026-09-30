<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { authUserStore } from '@/stores/authUserStore';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  isOwner: { type: Boolean, default: false },
});

const router = useRouter();
const userStore = authUserStore();
const { t } = useI18n();
const items = ref([]);
const loading = ref(true);
const error = ref(null);
const emailGate = ref(false);
const fileInput = ref(null);

async function load() {
  if (!props.isOwner) {
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get('/api/job-market/me/cvs');
    items.value = data;
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.cvTab.errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

async function onFile(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  emailGate.value = false;
  error.value = null;
  const form = new FormData();
  form.append('file', file);
  try {
    await axios.post('/api/job-market/me/cvs', form);
    await load();
  } catch (err) {
    const detail = err?.response?.data?.detail;
    if (detail === 'email_required') {
      emailGate.value = true;
    } else {
      error.value = detail || t('jobMarket.cvTab.errors.uploadFailed');
    }
  } finally {
    if (fileInput.value) fileInput.value.value = '';
  }
}

async function remove(id) {
  if (!confirm(t('jobMarket.cvTab.confirmDelete'))) return;
  try {
    await axios.delete(`/api/job-market/me/cvs/${id}`);
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.cvTab.errors.deleteFailed');
  }
}

async function download(id, name) {
  const { data } = await axios.get(`/api/job-market/me/cvs/${id}/file`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = name || t('jobMarket.cvTab.defaultFilename');
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(load);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold">{{ t('jobMarket.cvTab.title') }}</h2>
      <label
        v-if="isOwner"
        class="px-4 py-2 bg-black text-white rounded-full text-sm cursor-pointer"
      >
        {{ t('jobMarket.cvTab.upload') }}
        <input
          ref="fileInput"
          type="file"
          class="hidden"
          accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          @change="onFile"
        />
      </label>
    </div>

    <p v-if="!isOwner" class="text-gray-500">{{ t('jobMarket.cvTab.notOwner') }}</p>
    <template v-else>
      <p class="text-sm text-gray-500 mb-3">{{ t('jobMarket.cvTab.limitHint') }}</p>
      <div
        v-if="emailGate"
        class="mb-4 p-4 border border-amber-300 bg-amber-50 rounded-xl text-sm"
      >
        <p class="mb-2">{{ t('jobMarket.cvTab.emailGate.message') }}</p>
        <div class="flex gap-3">
          <button
            type="button"
            class="underline font-medium"
            @click="router.push(`/user/${userStore.authUsername}`)"
          >
            {{ t('jobMarket.cvTab.emailGate.goAddEmail') }}
          </button>
          <button type="button" class="underline" @click="emailGate = false">{{ t('jobMarket.cvTab.emailGate.skip') }}</button>
        </div>
      </div>
      <p v-if="loading" class="text-gray-500">{{ t('jobMarket.shared.loading') }}</p>
      <p v-else-if="error" class="text-red-600 text-sm mb-2">{{ error }}</p>
      <p v-else-if="!items.length" class="text-gray-500">{{ t('jobMarket.cvTab.empty') }}</p>
      <ul v-else class="space-y-3">
        <li
          v-for="row in items"
          :key="row.id"
          class="flex justify-between items-center border-b border-gray-200 pb-2"
        >
          <span>{{ row.original_filename }}</span>
          <div class="flex gap-3 text-sm">
            <button type="button" class="underline" @click="download(row.id, row.original_filename)">
              {{ t('jobMarket.cvTab.download') }}
            </button>
            <button type="button" class="underline text-red-600" @click="remove(row.id)">
              {{ t('jobMarket.shared.delete') }}
            </button>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>
