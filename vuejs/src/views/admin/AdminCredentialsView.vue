<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const targetUserId = ref('')
const rows = ref([])
const busy = ref(false)
const editingId = ref(null)
const form = ref({
  kind: 'education',
  title: '',
  organization: '',
  occurred_on: '',
  description: '',
})

const KIND_OPTIONS = ['education', 'licensing', 'award']

function resetForm() {
  editingId.value = null
  form.value = {
    kind: 'education',
    title: '',
    organization: '',
    occurred_on: '',
    description: '',
  }
}

async function load() {
  const uid = Number(targetUserId.value)
  if (!uid) {
    toast.error(t('admin.credentials.toast.enterUserId'))
    return
  }
  busy.value = true
  try {
    const { data } = await axios.get(`/api/job-market/users/${uid}/credentials`)
    rows.value = data
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

function startEdit(row) {
  editingId.value = row.id
  form.value = {
    kind: row.kind,
    title: row.title || '',
    organization: row.organization || '',
    occurred_on: row.occurred_on || '',
    description: row.description || '',
  }
}

async function save() {
  const uid = Number(targetUserId.value)
  if (!uid) {
    toast.error(t('admin.credentials.toast.enterUserId'))
    return
  }
  if (!form.value.title.trim()) {
    toast.error(t('admin.credentials.toast.titleRequired'))
    return
  }
  const payload = {
    kind: form.value.kind,
    title: form.value.title.trim(),
    organization: form.value.organization.trim() || null,
    occurred_on: form.value.occurred_on || null,
    description: form.value.description.trim() || null,
  }
  busy.value = true
  try {
    if (editingId.value) {
      await axios.patch(
        `/api/job-market/admin/users/${uid}/credentials/${editingId.value}`,
        payload
      )
      toast.success(t('admin.credentials.toast.updated'))
    } else {
      await axios.post(`/api/job-market/admin/users/${uid}/credentials`, payload)
      toast.success(t('admin.credentials.toast.created'))
    }
    resetForm()
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

async function remove(row) {
  const uid = Number(targetUserId.value)
  if (!window.confirm(t('admin.credentials.confirmDelete', { id: row.id }))) return
  busy.value = true
  try {
    await axios.delete(`/api/job-market/admin/users/${uid}/credentials/${row.id}`)
    toast.success(t('admin.credentials.toast.deleted'))
    if (editingId.value === row.id) resetForm()
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-6 max-w-2xl">
    <div class="flex gap-2 items-end">
      <label class="flex-1 text-sm">
        <span class="text-gray-700">{{ t('admin.credentials.userId') }}</span>
        <input
          v-model="targetUserId"
          type="number"
          min="1"
          class="mt-1 w-full border rounded-md px-3 py-2"
        />
      </label>
      <button
        type="button"
        class="px-4 py-2 rounded-md bg-gray-900 text-white text-sm disabled:opacity-50"
        :disabled="busy"
        @click="load"
      >
        {{ t('admin.credentials.load') }}
      </button>
    </div>

    <div class="border border-gray-200 rounded-lg overflow-hidden">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left">
          <tr>
            <th class="px-3 py-2">{{ t('admin.credentials.table.id') }}</th>
            <th class="px-3 py-2">{{ t('admin.credentials.table.kind') }}</th>
            <th class="px-3 py-2">{{ t('admin.credentials.table.title') }}</th>
            <th class="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-t border-gray-100">
            <td class="px-3 py-2">{{ row.id }}</td>
            <td class="px-3 py-2">{{ row.kind }}</td>
            <td class="px-3 py-2">{{ row.title }}</td>
            <td class="px-3 py-2 text-right space-x-2">
              <button type="button" class="underline" @click="startEdit(row)">{{ t('admin.credentials.table.edit') }}</button>
              <button type="button" class="underline text-red-700" @click="remove(row)">{{ t('admin.credentials.table.delete') }}</button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="4" class="px-3 py-4 text-center text-gray-500">{{ t('admin.credentials.table.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <form class="space-y-3 border border-gray-200 rounded-lg p-4" @submit.prevent="save">
      <h2 class="font-medium">
        {{ editingId ? t('admin.credentials.form.editTitle', { id: editingId }) : t('admin.credentials.form.createTitle') }}
      </h2>
      <label class="block text-sm">
        {{ t('admin.credentials.form.kind') }}
        <select v-model="form.kind" class="mt-1 w-full border rounded-md px-3 py-2">
          <option v-for="k in KIND_OPTIONS" :key="k" :value="k">{{ t(`admin.credentials.form.kindOptions.${k}`) }}</option>
        </select>
      </label>
      <label class="block text-sm">
        {{ t('admin.credentials.form.title') }}
        <input v-model="form.title" class="mt-1 w-full border rounded-md px-3 py-2" required />
      </label>
      <label class="block text-sm">
        {{ t('admin.credentials.form.organization') }}
        <input v-model="form.organization" class="mt-1 w-full border rounded-md px-3 py-2" />
      </label>
      <label class="block text-sm">
        {{ t('admin.credentials.form.occurredOn') }}
        <input v-model="form.occurred_on" type="date" class="mt-1 w-full border rounded-md px-3 py-2" />
      </label>
      <label class="block text-sm">
        {{ t('admin.credentials.form.description') }}
        <textarea v-model="form.description" rows="2" class="mt-1 w-full border rounded-md px-3 py-2" />
      </label>
      <div class="flex gap-2">
        <button type="submit" class="px-4 py-2 rounded-md bg-gray-900 text-white text-sm" :disabled="busy">
          {{ t('admin.credentials.form.save') }}
        </button>
        <button type="button" class="px-4 py-2 rounded-md border text-sm" @click="resetForm">
          {{ t('admin.credentials.form.reset') }}
        </button>
      </div>
    </form>
  </div>
</template>
