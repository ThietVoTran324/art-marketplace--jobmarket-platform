<script setup>
import { ref, watch } from 'vue';
import axios from 'axios';

import { bus, PIN_SAVED } from '@/events/bus';

const props = defineProps({
  open: { type: Boolean, default: false },
  pinId: { type: Number, required: true },
});

const emit = defineEmits(['update:open', 'saved', 'error']);

const boards = ref([]);
const loading = ref(false);
const saving = ref(false);
/** null = save without board */
const selectedBoardId = ref(null);

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return;
    selectedBoardId.value = null;
    loading.value = true;
    try {
      const { data } = await axios.get('/api/boards/me', { withCredentials: true });
      boards.value = Array.isArray(data) ? data : [];
    } catch (e) {
      console.error(e);
      boards.value = [];
    } finally {
      loading.value = false;
    }
  }
);

function close() {
  emit('update:open', false);
}

async function confirmSave() {
  if (!props.pinId || saving.value) return;
  saving.value = true;
  try {
    if (selectedBoardId.value == null) {
      await axios.post(`/api/pins/user_saved_pins/${props.pinId}`, null, {
        withCredentials: true,
      });
    } else {
      await axios.post(
        `/api/boards/${selectedBoardId.value}/pins/${props.pinId}`,
        null,
        { withCredentials: true }
      );
    }
    emit('saved', { pinId: props.pinId, boardId: selectedBoardId.value });
    bus.emit(PIN_SAVED, {
      pinId: props.pinId,
      boardId: selectedBoardId.value,
    });
    close();
  } catch (e) {
    emit('error', e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div
    v-if="open"
    class="z-[60] fixed inset-0 bg-black/50 flex items-center justify-center px-4"
    @click.self="close"
  >
    <div
      class="bg-white p-5 rounded-2xl shadow-lg max-w-md w-full relative max-h-[80vh] flex flex-col"
    >
      <h2 class="text-lg font-semibold text-center text-black mb-3">Save to</h2>

      <div v-if="loading" class="py-10 flex justify-center">
        <span class="text-gray-500 text-sm">Loading…</span>
      </div>

      <ul v-else class="overflow-y-auto space-y-1 flex-1 min-h-0">
        <li>
          <button
            type="button"
            class="w-full text-left px-4 py-3 rounded-xl border transition"
            :class="
              selectedBoardId === null
                ? 'border-black bg-gray-100'
                : 'border-transparent hover:bg-gray-50'
            "
            @click="selectedBoardId = null"
          >
            <span class="font-medium text-black">Saved</span>
            <span class="block text-xs text-gray-500">Not in a board</span>
          </button>
        </li>
        <li v-for="board in boards" :key="board.id">
          <button
            type="button"
            class="w-full text-left px-4 py-3 rounded-xl border transition"
            :class="
              selectedBoardId === board.id
                ? 'border-black bg-gray-100'
                : 'border-transparent hover:bg-gray-50'
            "
            @click="selectedBoardId = board.id"
          >
            <span class="font-medium text-black">{{ board.title }}</span>
          </button>
        </li>
        <li v-if="!boards.length" class="px-4 py-2 text-sm text-gray-400">
          No boards yet — saves go to Saved
        </li>
      </ul>

      <div class="flex justify-end gap-2 mt-4 pt-3 border-t">
        <button type="button" class="px-4 py-2 rounded-full text-sm" @click="close">
          Cancel
        </button>
        <button
          type="button"
          class="px-5 py-2 rounded-full text-sm bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          :disabled="saving"
          @click="confirmSave"
        >
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
      </div>
    </div>
  </div>
</template>
