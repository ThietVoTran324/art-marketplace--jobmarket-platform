<script setup>
import { onMounted, ref, onBeforeUnmount, nextTick, watch } from 'vue';
import axios from 'axios';
import PinsByBoard from '@/components/Auth/PinsByBoard.vue';
import SavedPins from '@/components/Auth/SavedPins.vue';

import { useSelectedBoard } from "@/stores/userSelectedBoard";
import { bus, PIN_SAVED } from '@/events/bus';

const userSelectedBoardStore = useSelectedBoard();

const props = defineProps({
  user_id: Number,
  auth_user_id: Number,
  initialBoardId: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['board-change'])

const loading = ref(true)

const boards = ref([])

const canEdit = ref(false)

const selectedBoardId = ref(null)
const selectedBoardname = ref(null)

const pinsSectionWrapper = ref(null)
const boardPinsKey = ref(0)
const savedListKey = ref(0)

async function loadBoardCovers(boardList) {
  for (let i = 0; i < boardList.length; i++) {
    try {
      const response = await axios.get(`/api/boards/${boardList[i].id}`, {
        params: { offset: 0, limit: 1 },
        withCredentials: true,
      });
      boardList[i].pins = response.data
      for (let j = 0; j < boardList[i].pins.length; j++) {
        try {
          const pinResponse = await axios.get(`/api/pins/upload/${boardList[i].pins[j].id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            boardList[i].pins[j].file = blobUrl;
            boardList[i].pins[j].isImage = true;
          } else {
            boardList[i].pins[j].file = blobUrl;
            boardList[i].pins[j].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }
    } catch (error) {
      console.error(error)
    }
  }
}

async function reloadBoards() {
  try {
    const response = await axios.get(`/api/boards/user/${props.user_id}`, { withCredentials: true });
    const next = response.data || []
    await loadBoardCovers(next)
    boards.value = next
  } catch (error) {
    console.error(error)
  }
}

async function onPinSaved(payload) {
  if (props.auth_user_id && props.user_id !== props.auth_user_id) return;
  await reloadBoards()
  if (payload?.boardId != null) {
    if (selectedBoardId.value === payload.boardId) {
      boardPinsKey.value += 1
    }
  } else {
    savedListKey.value += 1
  }
}

async function openBoardFromId(boardId) {
  if (boardId == null || boardId === '') {
    selectedBoardId.value = null
    selectedBoardname.value = null
    return
  }
  const id = Number(boardId)
  const board = boards.value.find((b) => Number(b.id) === id)
  if (!board) {
    selectedBoardId.value = null
    selectedBoardname.value = null
    return
  }
  await laodPinsByBoard(board.id, board.title, { emitChange: false })
}

onMounted(async () => {
  canEdit.value = props.user_id === props.auth_user_id
  loading.value = true
  await reloadBoards()
  await openBoardFromId(props.initialBoardId)
  loading.value = false
  bus.on(PIN_SAVED, onPinSaved)
})

watch(
  () => props.initialBoardId,
  async (id) => {
    if (loading.value) return
    const current = selectedBoardId.value == null ? null : String(selectedBoardId.value)
    const next = id == null || id === '' ? null : String(id)
    if (current === next) return
    await openBoardFromId(id)
  }
)

onBeforeUnmount(() => {
  bus.off(PIN_SAVED, onPinSaved)
})

const showAddBoard = ref(false);

const boardName = ref('');

const closeModal = () => {
  showAddBoard.value = false;
  boardName.value = '';
};

const createBoard = async () => {
  if (!boardName.value.trim()) return;
  try {
    const response = await axios.post(`/api/boards/`, {
      title: boardName.value.trim()
    }, {
      withCredentials: true
    });
    const new_board = response.data
    boards.value.push(new_board)
  } catch (error) {
    console.error(error)
  }
  closeModal();
};

const deleteBoard = async (boardId) => {
  try {
    const response = await axios.delete(`/api/boards/${boardId}`, { withCredentials: true });
    boards.value = boards.value.filter(board => board.id !== boardId);
  } catch (error) {
    console.error('Error deleting board:', error);
  }
  if (userSelectedBoardStore.selectedBoard && userSelectedBoardStore.selectedBoard.id === boardId) {
    userSelectedBoardStore.setBoard(null)
  }
  if (selectedBoardId.value === boardId) {
    selectedBoardId.value = null
    selectedBoardname.value = null
    emit('board-change', null)
    await nextTick()
  }
};

async function laodPinsByBoard(boardId, boardName, { emitChange = true } = {}) {
  selectedBoardId.value = null
  selectedBoardname.value = null
  await nextTick()

  selectedBoardId.value = boardId
  selectedBoardname.value = boardName
  if (emitChange) emit('board-change', boardId)
  await nextTick()
}

async function closeBoard() {
  selectedBoardId.value = null
  selectedBoardname.value = null
  emit('board-change', null)
  await nextTick()
}

</script>

<template>
  <div class="mt-10 ml-20">
    <div v-if="loading" class="flex items-center justify-center h-full p-2">
      <span class="text-center loader2"></span>
    </div>
    <div v-else class="">
      <!-- Drill-in: board as a nested Saved view -->
      <template v-if="selectedBoardId">
        <div class="flex items-center gap-3 mx-2 mb-4">
          <button
            type="button"
            class="flex items-center justify-center w-10 h-10 rounded-full hover:bg-gray-100 transition"
            aria-label="Back to Saved"
            @click="closeBoard"
          >
            <i class="pi pi-arrow-left text-xl"></i>
          </button>
          <h2 class="text-xl font-bold truncate">{{ selectedBoardname }}</h2>
        </div>
        <div ref="pinsSectionWrapper">
          <PinsByBoard
            :key="`${selectedBoardId}-${boardPinsKey}`"
            :user_id="user_id"
            :auth_user_id="auth_user_id"
            :boardId="selectedBoardId"
            :canEdit="canEdit"
            :boardName="selectedBoardname"
          />
        </div>
      </template>

      <!-- Root Saved list: boards first, then loose pins -->
      <template v-else>
        <div
          v-if="canEdit"
          class="fixed bottom-6 transform items-center justify-center left-1/2 z-20 ml-7 text-4xl"
        >
          <button
            type="button"
            class="bg-white/80 font-medium rounded-full px-4 py-2 flex justify-center items-center transition-transform duration-300 hover:bg-gray-200 hover:opacity-100 hover:scale-105"
            @click="showAddBoard = true"
          >
            +
          </button>
        </div>
        <div class="grid grid-cols-5 gap-2 mx-2">
          <div
            v-for="board in boards"
            :key="`board-${board.id}`"
            class="rounded-2xl transition transform cursor-pointer hover:scale-105 overflow-hidden w-full h-48 relative"
            @click="laodPinsByBoard(board.id, board.title)"
          >
            <template v-if="board.pins && board.pins.length">
              <div class="w-full h-full">
                <img
                  v-if="board.pins[0].isImage"
                  :src="board.pins[0].file"
                  alt=""
                  class="object-cover w-full h-full"
                />
                <video
                  v-else
                  :src="board.pins[0].file"
                  class="object-cover w-full h-full"
                  autoplay
                  loop
                  muted
                />
              </div>
              <div
                class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3 pointer-events-none"
              >
                <h3 class="text-white text-sm font-semibold truncate">{{ board.title }}</h3>
              </div>
            </template>
            <template v-else>
              <div class="flex items-end w-full h-full bg-gray-200 p-3">
                <h3 class="text-gray-800 text-sm font-semibold truncate">{{ board.title }}</h3>
              </div>
            </template>
            <div v-if="canEdit" class="absolute top-2 right-2">
              <button
                type="button"
                class="px-3 py-1.5 bg-black/60 text-white text-xs rounded-full hover:bg-black transition"
                @click.stop="deleteBoard(board.id)"
              >
                Delete
              </button>
            </div>
          </div>
        </div>

        <SavedPins
          :key="savedListKey"
          :user_id="user_id"
          :auth_user_id="auth_user_id"
          :embedded="true"
          :hide-empty="boards.length > 0"
        />
      </template>
    </div>

    <div
      v-if="showAddBoard"
      class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-40 backdrop-blur-sm"
      @click.self="closeModal"
    >
      <div class="bg-white p-6 rounded-2xl shadow-lg w-96 max-w-full z-50 ml-20">
        <h2 class="text-xl font-bold mb-4 text-gray-800">Create Board</h2>
        <input
          v-model="boardName"
          type="text"
          placeholder="Board name"
          class="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-gray-700"
        />
        <div class="flex justify-end gap-3 mt-5">
          <button
            type="button"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-full hover:bg-gray-300 transition"
            @click="closeModal"
          >
            Cancel
          </button>
          <button
            type="button"
            class="px-5 py-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition"
            @click="createBoard"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.loader2 {
  width: 48px;
  height: 48px;
  background: #FFF;
  border-radius: 50%;
  display: inline-block;
  position: relative;
  box-sizing: border-box;
  animation: rotation 1s linear infinite;
}

.loader2::after {
  content: '';
  box-sizing: border-box;
  position: absolute;
  left: 6px;
  top: 10px;
  width: 12px;
  height: 12px;
  color: #FF3D00;
  background: currentColor;
  border-radius: 50%;
  box-shadow: 25px 2px, 10px 22px;
}

@keyframes rotation {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}
</style>