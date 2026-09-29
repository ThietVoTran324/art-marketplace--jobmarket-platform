<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const pinId = ref('')
const commentId = ref('')
const busy = ref(false)

async function deletePin() {
  const id = Number(pinId.value)
  if (!id) {
    toast.error('Enter pin id')
    return
  }
  if (!window.confirm(`Delete pin #${id}? This cannot be undone.`)) return
  busy.value = true
  try {
    await axios.delete(`/api/admin/pin/${id}`)
    toast.success(`Pin #${id} deleted`)
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
    toast.error('Enter comment id')
    return
  }
  if (!window.confirm(`Delete comment #${id}? This cannot be undone.`)) return
  busy.value = true
  try {
    await axios.delete(`/api/admin/comment/${id}`)
    toast.success(`Comment #${id} deleted`)
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
      <h2 class="text-lg font-medium">Delete pin</h2>
      <p class="text-sm text-gray-600">Permanently delete a pin by id.</p>
      <div class="flex gap-2">
        <input
          v-model="pinId"
          type="number"
          min="1"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2"
          placeholder="Pin id"
        />
        <button
          type="button"
          class="px-4 py-2 rounded-md bg-red-700 text-white text-sm disabled:opacity-50"
          :disabled="busy"
          @click="deletePin"
        >
          Delete pin
        </button>
      </div>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">Delete comment</h2>
      <p class="text-sm text-gray-600">Permanently delete a comment by id.</p>
      <div class="flex gap-2">
        <input
          v-model="commentId"
          type="number"
          min="1"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2"
          placeholder="Comment id"
        />
        <button
          type="button"
          class="px-4 py-2 rounded-md bg-red-700 text-white text-sm disabled:opacity-50"
          :disabled="busy"
          @click="deleteComment"
        >
          Delete comment
        </button>
      </div>
    </section>
  </div>
</template>
