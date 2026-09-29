<script setup>
import { onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router';
import { useUnavailableContentStore } from '@/stores/unavailableContent';

const route = useRoute();
const router = useRouter();
const unavailableStore = useUnavailableContentStore();
const data = ref(null);
const loading = ref(true);
const error = ref(null);

const appId = () => Number(route.params.id);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const res = await axios.get(`/api/job-market/applications/${appId()}/cv-view`);
    data.value = res.data;
  } catch (e) {
    error.value = e.response?.data?.detail || 'Not found';
    const status = e.response?.status;
    if (status === 404 || status === 403) {
      unavailableStore.show();
      router.back();
    }
  } finally {
    loading.value = false;
  }
}

async function downloadCv() {
  const res = await axios.get(`/api/job-market/applications/${appId()}/cv/file`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = data.value?.cv_original_filename || 'cv';
  a.click();
  URL.revokeObjectURL(url);
  await load();
}

async function downloadCover() {
  const res = await axios.get(`/api/job-market/applications/${appId()}/cover/file`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'cover';
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(load);
watch(() => route.params.id, load);
</script>

<template>
  <div class="ml-24 mr-8 mt-8 max-w-2xl">
    <button type="button" class="text-sm text-gray-600 hover:underline mb-4" @click="router.back()">
      ← Back
    </button>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="text-red-600">{{ error }}</p>
    <template v-else-if="data">
      <h1 class="text-2xl font-bold">Application CV</h1>
      <p class="text-gray-600 mt-1">
        {{ data.job_title }} ·
        <button
          type="button"
          class="underline"
          @click="router.push(`/user/${data.applicant_username}`)"
        >
          {{ data.applicant_username }}
        </button>
        · <span class="uppercase">{{ data.status }}</span>
      </p>
      <p v-if="data.cover_note" class="mt-4 whitespace-pre-line border rounded-xl p-3">
        {{ data.cover_note }}
      </p>
      <div class="mt-6 flex gap-3 flex-wrap">
        <button type="button" class="px-4 py-2 rounded-xl bg-red-600 text-white" @click="downloadCv">
          Download CV ({{ data.cv_original_filename }})
        </button>
        <button
          v-if="data.has_cover_file"
          type="button"
          class="px-4 py-2 rounded-xl bg-gray-800 text-white"
          @click="downloadCover"
        >
          Download cover file
        </button>
      </div>
    </template>
  </div>
</template>
