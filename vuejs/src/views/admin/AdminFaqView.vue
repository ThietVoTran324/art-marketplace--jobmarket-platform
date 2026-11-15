<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const items = ref([])
const loading = ref(false)
const busy = ref(false)
const editingId = ref(null)
const form = ref({
  slug: '',
  title: '',
  body: '',
  status: 'draft',
})

function resetForm() {
  editingId.value = null
  form.value = { slug: '', title: '', body: '', status: 'draft' }
}

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/admin/faq', { withCredentials: true })
    items.value = data || []
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function startEdit(row) {
  editingId.value = row.id
  form.value = {
    slug: row.slug,
    title: row.title,
    body: row.body,
    status: row.status,
  }
}

async function save() {
  busy.value = true
  try {
    const payload = {
      slug: form.value.slug.trim(),
      title: form.value.title.trim(),
      body: form.value.body,
      status: form.value.status,
    }
    if (editingId.value) {
      await axios.patch(`/api/admin/faq/${editingId.value}`, payload, {
        withCredentials: true,
      })
      toast.success(t('admin.faq.toast.updated'))
    } else {
      await axios.post('/api/admin/faq', payload, { withCredentials: true })
      toast.success(t('admin.faq.toast.created'))
    }
    resetForm()
    await load()
  } catch (e) {
    const detail = e?.response?.data?.detail
    toast.error(typeof detail === 'string' ? detail : e.message)
  } finally {
    busy.value = false
  }
}

async function setStatus(row, status) {
  busy.value = true
  try {
    await axios.patch(
      `/api/admin/faq/${row.id}`,
      { status },
      { withCredentials: true }
    )
    toast.success(t('admin.faq.toast.status', { status }))
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

async function reindexOne(row) {
  busy.value = true
  try {
    await axios.post(`/api/admin/faq/${row.id}/reindex`, null, {
      withCredentials: true,
    })
    toast.success(t('admin.faq.toast.reindexOne'))
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

async function reindexAll() {
  if (!window.confirm(t('admin.faq.confirmReindexAll'))) return
  busy.value = true
  try {
    await axios.post('/api/admin/faq/reindex-all', null, { withCredentials: true })
    toast.success(t('admin.faq.toast.reindexAll'))
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-8 max-w-5xl">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-medium">{{ t('admin.faq.title') }}</h2>
        <p class="text-sm text-gray-600">{{ t('admin.faq.description') }}</p>
      </div>
      <button
        type="button"
        class="px-3 py-2 rounded-md bg-gray-900 text-white text-sm disabled:opacity-50"
        :disabled="busy"
        @click="reindexAll"
      >
        {{ t('admin.faq.reindexAll') }}
      </button>
    </div>

    <section class="space-y-3 border border-gray-200 rounded-lg p-4">
      <h3 class="font-medium">
        {{ editingId ? t('admin.faq.form.edit') : t('admin.faq.form.create') }}
      </h3>
      <div class="grid gap-3 md:grid-cols-2">
        <label class="text-sm block">
          {{ t('admin.faq.form.slug') }}
          <input
            v-model="form.slug"
            class="mt-1 w-full border border-gray-300 rounded-md px-3 py-2"
            :placeholder="t('admin.faq.form.slugPh')"
          />
        </label>
        <label class="text-sm block">
          {{ t('admin.faq.form.status') }}
          <select
            v-model="form.status"
            class="mt-1 w-full border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="draft">draft</option>
            <option value="published">published</option>
          </select>
        </label>
      </div>
      <label class="text-sm block">
        {{ t('admin.faq.form.titleLabel') }}
        <input
          v-model="form.title"
          class="mt-1 w-full border border-gray-300 rounded-md px-3 py-2"
        />
      </label>
      <label class="text-sm block">
        {{ t('admin.faq.form.body') }}
        <textarea
          v-model="form.body"
          rows="10"
          class="mt-1 w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm"
          :placeholder="t('admin.faq.form.bodyPh')"
        />
      </label>
      <div class="flex gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-md bg-gray-900 text-white text-sm disabled:opacity-50"
          :disabled="busy"
          @click="save"
        >
          {{ t('admin.faq.form.save') }}
        </button>
        <button
          v-if="editingId"
          type="button"
          class="px-4 py-2 rounded-md border text-sm"
          :disabled="busy"
          @click="resetForm"
        >
          {{ t('admin.faq.form.cancel') }}
        </button>
      </div>
    </section>

    <section>
      <p v-if="loading" class="text-sm text-gray-500">{{ t('admin.faq.loading') }}</p>
      <div v-else class="overflow-x-auto border border-gray-200 rounded-lg">
        <table class="min-w-full text-sm">
          <thead class="bg-gray-50 text-left">
            <tr>
              <th class="px-3 py-2">ID</th>
              <th class="px-3 py-2">{{ t('admin.faq.form.slug') }}</th>
              <th class="px-3 py-2">{{ t('admin.faq.form.titleLabel') }}</th>
              <th class="px-3 py-2">{{ t('admin.faq.form.status') }}</th>
              <th class="px-3 py-2">{{ t('admin.faq.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.id" class="border-t">
              <td class="px-3 py-2">{{ row.id }}</td>
              <td class="px-3 py-2 font-mono">{{ row.slug }}</td>
              <td class="px-3 py-2">{{ row.title }}</td>
              <td class="px-3 py-2">{{ row.status }}</td>
              <td class="px-3 py-2">
                <div class="flex flex-wrap gap-2">
                  <button type="button" class="underline" @click="startEdit(row)">
                    {{ t('admin.faq.edit') }}
                  </button>
                  <button
                    v-if="row.status !== 'published'"
                    type="button"
                    class="underline"
                    :disabled="busy"
                    @click="setStatus(row, 'published')"
                  >
                    {{ t('admin.faq.publish') }}
                  </button>
                  <button
                    v-else
                    type="button"
                    class="underline"
                    :disabled="busy"
                    @click="setStatus(row, 'draft')"
                  >
                    {{ t('admin.faq.unpublish') }}
                  </button>
                  <button
                    type="button"
                    class="underline"
                    :disabled="busy"
                    @click="reindexOne(row)"
                  >
                    {{ t('admin.faq.reindex') }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="5" class="px-3 py-6 text-gray-500">
                {{ t('admin.faq.empty') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
