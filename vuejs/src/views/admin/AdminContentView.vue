<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const toast = useToast()
const { t } = useI18n()

const pinId = ref('')
const commentId = ref('')
const busy = ref(false)

async function deletePin() {
  const id = Number(pinId.value)
  if (!id) {
    toast.error(t('admin.content.deletePin.toast.enterPinId'))
    return
  }
  if (!window.confirm(t('admin.content.deletePin.confirm', { id }))) return
  busy.value = true
  try {
    await axios.delete(`/api/admin/pin/${id}`)
    toast.success(t('admin.content.deletePin.toast.success', { id }))
    pinId.value = ''
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}

async function deleteComment() {
  const id = Number(commentId.value)
  if (!id) {
    toast.error(t('admin.content.deleteComment.toast.enterCommentId'))
    return
  }
  if (!window.confirm(t('admin.content.deleteComment.confirm', { id }))) return
  busy.value = true
  try {
    await axios.delete(`/api/admin/comment/${id}`)
    toast.success(t('admin.content.deleteComment.toast.success', { id }))
    commentId.value = ''
  } catch (e) {
    toast.error(e?.response?.data?.detail || e.message)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-8 max-w-lg">
    <section class="space-y-3">
      <h2 class="text-lg font-medium">{{ t('admin.content.deletePin.title') }}</h2>
      <p class="text-sm text-gray-600">{{ t('admin.content.deletePin.description') }}</p>
      <div class="flex gap-2">
        <input
          v-model="pinId"
          type="number"
          min="1"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2"
          :placeholder="t('admin.content.deletePin.placeholder')"
        />
        <button
          type="button"
          class="px-4 py-2 rounded-md bg-red-700 text-white text-sm disabled:opacity-50"
          :disabled="busy"
          @click="deletePin"
        >
          {{ t('admin.content.deletePin.button') }}
        </button>
      </div>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">{{ t('admin.content.deleteComment.title') }}</h2>
      <p class="text-sm text-gray-600">{{ t('admin.content.deleteComment.description') }}</p>
      <div class="flex gap-2">
        <input
          v-model="commentId"
          type="number"
          min="1"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2"
          :placeholder="t('admin.content.deleteComment.placeholder')"
        />
        <button
          type="button"
          class="px-4 py-2 rounded-md bg-red-700 text-white text-sm disabled:opacity-50"
          :disabled="busy"
          @click="deleteComment"
        >
          {{ t('admin.content.deleteComment.button') }}
        </button>
      </div>
    </section>
  </div>
</template>
