<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { authUserStore } from '@/stores/authUserStore';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  userId: { type: Number, required: true },
  isOwner: { type: Boolean, default: false },
  highlightId: { type: [Number, String], default: null },
});

const userStore = authUserStore();
const { t } = useI18n();
const items = ref([]);
const loading = ref(true);
const error = ref(null);
const formOpen = ref(false);
const editingId = ref(null);
const suggestions = ref([]);
/** idle | typing | loading | ready | empty | error */
const suggestStatus = ref('idle');
const suggestError = ref(null);
const activeSuggestIndex = ref(-1);
const suggestOpen = ref(false);
let suggestTimer = null;
let suggestSeq = 0;

const form = ref({
  company_name: '',
  company_id: null,
  employment_type: 'full-time',
  title: '',
  description: '',
  location: '',
  start_date: '',
  end_date: '',
  mode: 'free', // free | linked
});

const employmentTypes = [
  'full-time',
  'part-time',
  'hybrid',
  'outsourcing',
  'collaborator',
];

const employmentTypeI18nKey = {
  'full-time': 'fullTime',
  'part-time': 'partTime',
  hybrid: 'hybrid',
  outsourcing: 'outsourcing',
  collaborator: 'collaborator',
};

function employmentTypeLabel(type) {
  const key = employmentTypeI18nKey[type];
  return key ? t(`jobMarket.workExperienceTab.employmentTypes.${key}`) : type;
}

const myCompanyId = computed(() => userStore.companyId);
const showSuggestPanel = computed(
  () =>
    suggestOpen.value &&
    !form.value.company_id &&
    (suggestStatus.value === 'typing' ||
      suggestStatus.value === 'loading' ||
      suggestStatus.value === 'ready' ||
      suggestStatus.value === 'empty' ||
      suggestStatus.value === 'error' ||
      suggestStatus.value === 'idle')
);

const isCompanyConfirmed = (row) => row?.status === 'approved';

const confirmTooltip = (row) =>
  isCompanyConfirmed(row)
    ? t('jobMarket.workExperienceTab.confirmTooltip.verified')
    : t('jobMarket.workExperienceTab.confirmTooltip.unverified');

const canDecide = (row) =>
  row.status === 'pending' &&
  row.company_id != null &&
  myCompanyId.value != null &&
  Number(row.company_id) === Number(myCompanyId.value);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await axios.get(
      `/api/job-market/users/${props.userId}/work-experiences`
    );
    items.value = data;
    await nextTick();
    scrollHighlight();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.workExperienceTab.errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

function scrollHighlight() {
  const id = props.highlightId;
  if (!id) return;
  const el = document.getElementById(`work-exp-${id}`);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearSuggestTimer() {
  if (suggestTimer) {
    clearTimeout(suggestTimer);
    suggestTimer = null;
  }
}

function resetSuggestUi() {
  clearSuggestTimer();
  suggestions.value = [];
  suggestStatus.value = 'idle';
  suggestError.value = null;
  activeSuggestIndex.value = -1;
  suggestOpen.value = false;
}

function resetForm() {
  editingId.value = null;
  resetSuggestUi();
  form.value = {
    company_name: '',
    company_id: null,
    employment_type: 'full-time',
    title: '',
    description: '',
    location: '',
    start_date: '',
    end_date: '',
    mode: 'free',
  };
}

function openCreate() {
  resetForm();
  formOpen.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  resetSuggestUi();
  form.value = {
    company_name: row.company_name,
    company_id: row.company_id,
    employment_type: row.employment_type,
    title: row.title,
    description: row.description || '',
    location: row.location || '',
    start_date: row.start_date,
    end_date: row.end_date || '',
    mode: row.company_id ? 'linked' : 'free',
  };
  formOpen.value = true;
}

function onCompanyInput() {
  // Typing means leave linked mode until user picks again.
  if (form.value.company_id) {
    form.value.company_id = null;
    form.value.mode = 'free';
  }
  suggestOpen.value = true;
  activeSuggestIndex.value = -1;
  const q = form.value.company_name?.trim() || '';
  clearSuggestTimer();
  if (!q) {
    suggestions.value = [];
    suggestStatus.value = 'idle';
    suggestError.value = null;
    return;
  }
  suggestStatus.value = 'typing';
  suggestTimer = setTimeout(() => {
    void runCompanySearch(q);
  }, 280);
}

async function runCompanySearch(q) {
  const seq = ++suggestSeq;
  suggestStatus.value = 'loading';
  suggestError.value = null;
  try {
    const { data } = await axios.get('/api/job-market/company-suggestions', {
      params: { q, limit: 8 },
    });
    if (seq !== suggestSeq) return;
    suggestions.value = Array.isArray(data) ? data : [];
    suggestStatus.value = suggestions.value.length ? 'ready' : 'empty';
    activeSuggestIndex.value = suggestions.value.length ? 0 : -1;
  } catch (e) {
    if (seq !== suggestSeq) return;
    suggestions.value = [];
    suggestStatus.value = 'error';
    suggestError.value =
      e?.response?.data?.detail || e?.message || t('jobMarket.workExperienceTab.errors.suggestFailed');
    activeSuggestIndex.value = -1;
  }
}

function pickCompany(c) {
  form.value.company_id = c.id;
  form.value.company_name = c.display_name;
  form.value.mode = 'linked';
  resetSuggestUi();
}

function clearLinkedCompany() {
  form.value.company_id = null;
  form.value.mode = 'free';
  suggestOpen.value = true;
  suggestStatus.value = form.value.company_name?.trim() ? 'typing' : 'idle';
  if (form.value.company_name?.trim()) {
    onCompanyInput();
  }
}

function onCompanyKeydown(e) {
  if (!suggestOpen.value || form.value.company_id) return;
  const n = suggestions.value.length;
  if (e.key === 'ArrowDown') {
    if (suggestStatus.value === 'ready' && n) {
      e.preventDefault();
      activeSuggestIndex.value = (activeSuggestIndex.value + 1 + n) % n;
    }
    return;
  }
  if (e.key === 'ArrowUp') {
    if (suggestStatus.value === 'ready' && n) {
      e.preventDefault();
      activeSuggestIndex.value = (activeSuggestIndex.value - 1 + n) % n;
    }
    return;
  }
  if (e.key === 'Escape') {
    e.preventDefault();
    resetSuggestUi();
    return;
  }
  if (e.key === 'Enter') {
    if (suggestStatus.value === 'ready' && n && activeSuggestIndex.value >= 0) {
      e.preventDefault();
      pickCompany(suggestions.value[activeSuggestIndex.value]);
      return;
    }
    if (
      suggestStatus.value === 'loading' ||
      suggestStatus.value === 'typing' ||
      suggestOpen.value
    ) {
      // Avoid accidental form submit while interacting with search.
      e.preventDefault();
    }
  }
}

function onCompanyFocus() {
  if (form.value.company_id) return;
  suggestOpen.value = true;
  if (!form.value.company_name?.trim()) {
    suggestStatus.value = 'idle';
  }
}

async function save() {
  const payload = {
    employment_type: form.value.employment_type,
    title: form.value.title,
    description: form.value.description?.trim() || '',
    location: form.value.location || null,
    start_date: form.value.start_date,
    end_date: form.value.end_date || null,
  };
  if (form.value.company_id) {
    payload.company_id = form.value.company_id;
  } else if (editingId.value) {
    payload.clear_company_id = true;
    payload.company_name = form.value.company_name;
  } else {
    payload.company_name = form.value.company_name;
  }
  try {
    if (editingId.value) {
      await axios.patch(
        `/api/job-market/me/work-experiences/${editingId.value}`,
        payload
      );
    } else {
      await axios.post('/api/job-market/me/work-experiences', payload);
    }
    formOpen.value = false;
    resetForm();
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.workExperienceTab.errors.saveFailed');
  }
}

async function remove(id) {
  if (!confirm(t('jobMarket.workExperienceTab.confirmDelete'))) return;
  try {
    await axios.delete(`/api/job-market/me/work-experiences/${id}`);
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.workExperienceTab.errors.deleteFailed');
  }
}

async function decide(row, action) {
  try {
    await axios.post(
      `/api/job-market/me/company/work-experiences/${row.id}/${action}`
    );
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || t('jobMarket.workExperienceTab.errors.actionFailed', { action });
  }
}

watch(() => props.highlightId, () => nextTick(scrollHighlight));
onMounted(load);
onBeforeUnmount(clearSuggestTimer);
</script>

<template>
  <div class="px-8 py-6 max-w-3xl mx-auto w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold">{{ t('jobMarket.workExperienceTab.title') }}</h2>
      <button
        v-if="isOwner"
        type="button"
        class="px-4 py-2 bg-black text-white rounded-full text-sm"
        @click="openCreate"
      >
        {{ t('jobMarket.shared.add') }}
      </button>
    </div>

    <p v-if="loading" class="text-gray-500">{{ t('jobMarket.shared.loading') }}</p>
    <p v-else-if="error" class="text-red-600 text-sm mb-3">{{ error }}</p>
    <p v-else-if="!items.length" class="text-gray-500">{{ t('jobMarket.workExperienceTab.empty') }}</p>

    <ul v-else class="space-y-4">
      <li
        v-for="row in items"
        :id="`work-exp-${row.id}`"
        :key="row.id"
        class="border-b border-gray-200 pb-4"
        :class="{
          'ring-2 ring-black rounded-lg p-3':
            highlightId != null && Number(highlightId) === Number(row.id),
        }"
      >
        <div class="flex justify-between gap-4">
          <div class="min-w-0">
            <p class="font-semibold text-lg">{{ row.title }}</p>
            <p class="text-gray-800">
              {{ row.company_name }} · {{ employmentTypeLabel(row.employment_type) }}
              <span v-if="row.company_id" class="text-xs text-gray-500">{{ t('jobMarket.workExperienceTab.verifiedCompany') }}</span>
            </p>
            <p class="text-sm text-gray-600">
              {{ row.start_date }}
              →
              {{ row.end_date || t('jobMarket.shared.present') }}
              <span v-if="row.location"> · {{ row.location }}</span>
            </p>
            <p
              v-if="row.description"
              class="text-sm text-gray-700 mt-2 whitespace-pre-wrap"
            >
              {{ row.description }}
            </p>
          </div>
          <div class="flex flex-col gap-2 text-sm shrink-0 items-end">
            <div class="flex items-center gap-2">
              <span
                class="inline-flex text-gray-500"
                :title="confirmTooltip(row)"
                :aria-label="confirmTooltip(row)"
              >
                <CircleCheck
                  v-if="isCompanyConfirmed(row)"
                  class="w-4 h-4 text-emerald-600"
                  aria-hidden="true"
                />
                <CircleQuestionMark
                  v-else
                  class="w-4 h-4 text-amber-500"
                  aria-hidden="true"
                />
              </span>
              <template v-if="isOwner">
                <button type="button" class="underline" @click="openEdit(row)">
                  {{ t('jobMarket.shared.edit') }}
                </button>
                <button type="button" class="underline text-red-600" @click="remove(row.id)">
                  {{ t('jobMarket.shared.delete') }}
                </button>
              </template>
            </div>
            <div v-if="canDecide(row)" class="flex gap-2">
              <button
                type="button"
                class="px-3 py-1 bg-black text-white rounded-full text-xs"
                @click="decide(row, 'approve')"
              >
                {{ t('jobMarket.shared.approve') }}
              </button>
              <button
                type="button"
                class="px-3 py-1 border rounded-full text-xs"
                @click="decide(row, 'reject')"
              >
                {{ t('jobMarket.shared.reject') }}
              </button>
            </div>
          </div>
        </div>      </li>
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
          {{ editingId ? t('jobMarket.workExperienceTab.form.editTitle') : t('jobMarket.workExperienceTab.form.addTitle') }}
        </h3>
        <div class="relative">
          <input
            v-model="form.company_name"
            required
            :placeholder="t('jobMarket.workExperienceTab.form.companyPlaceholder')"
            class="w-full border rounded-lg px-3 py-2"
            autocomplete="off"
            role="combobox"
            aria-autocomplete="list"
            :aria-expanded="showSuggestPanel ? 'true' : 'false'"
            @input="onCompanyInput"
            @keydown="onCompanyKeydown"
            @focus="onCompanyFocus"
          />
          <ul
            v-if="showSuggestPanel"
            class="absolute z-10 left-0 right-0 bg-white border rounded-lg mt-1 max-h-48 overflow-auto text-sm shadow-sm"
            role="listbox"
          >
            <li
              v-if="suggestStatus === 'idle'"
              class="px-3 py-2 text-gray-500"
            >
              {{ t('jobMarket.workExperienceTab.form.suggestIdle') }}
            </li>
            <li
              v-else-if="suggestStatus === 'typing' || suggestStatus === 'loading'"
              class="px-3 py-2 text-gray-500"
            >
              {{ t('jobMarket.workExperienceTab.form.suggestLoading') }}
            </li>
            <li
              v-else-if="suggestStatus === 'error'"
              class="px-3 py-2 text-red-600"
            >
              {{ suggestError || t('jobMarket.workExperienceTab.form.suggestErrorFallback') }}
            </li>
            <li
              v-else-if="suggestStatus === 'empty'"
              class="px-3 py-2 text-gray-500"
            >
              {{ t('jobMarket.workExperienceTab.form.suggestEmpty') }}
            </li>
            <template v-else-if="suggestStatus === 'ready'">
              <li
                v-for="(c, idx) in suggestions"
                :key="c.id"
                class="px-3 py-2 cursor-pointer"
                :class="idx === activeSuggestIndex ? 'bg-gray-100' : 'hover:bg-gray-50'"
                role="option"
                :aria-selected="idx === activeSuggestIndex ? 'true' : 'false'"
                @mousedown.prevent="pickCompany(c)"
                @mouseenter="activeSuggestIndex = idx"
              >
                <span class="font-medium">{{ c.display_name }}</span>
                <span v-if="c.domain" class="block text-xs text-gray-500">{{ c.domain }}</span>
              </li>
            </template>
          </ul>
          <p v-if="form.company_id" class="text-xs text-gray-600 mt-1">
            {{ t('jobMarket.workExperienceTab.form.linkedVerified') }}
            <button type="button" class="underline ml-2" @click="clearLinkedCompany">
              {{ t('jobMarket.workExperienceTab.form.useFreeText') }}
            </button>
          </p>
        </div>
        <select v-model="form.employment_type" class="w-full border rounded-lg px-3 py-2">
          <option v-for="empType in employmentTypes" :key="empType" :value="empType">{{ employmentTypeLabel(empType) }}</option>
        </select>
        <input
          v-model="form.title"
          required
          :placeholder="t('jobMarket.workExperienceTab.form.titlePlaceholder')"
          class="w-full border rounded-lg px-3 py-2"
        />
        <textarea
          v-model="form.description"
          rows="3"
          maxlength="2000"
          :placeholder="t('jobMarket.workExperienceTab.form.descriptionPlaceholder')"
          class="w-full border rounded-lg px-3 py-2 resize-y"
        />
        <input
          v-model="form.location"
          :placeholder="t('jobMarket.workExperienceTab.form.locationPlaceholder')"
          class="w-full border rounded-lg px-3 py-2"
        />
        <label class="block text-sm"
          >{{ t('jobMarket.workExperienceTab.form.startLabel') }}
          <input v-model="form.start_date" type="date" required class="w-full border rounded-lg px-3 py-2"
        /></label>
        <label class="block text-sm"
          >{{ t('jobMarket.workExperienceTab.form.endLabel') }}
          <input v-model="form.end_date" type="date" class="w-full border rounded-lg px-3 py-2"
        /></label>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" class="px-4 py-2" @click="formOpen = false">{{ t('jobMarket.shared.cancel') }}</button>
          <button type="submit" class="px-4 py-2 bg-black text-white rounded-full">{{ t('jobMarket.shared.save') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>
