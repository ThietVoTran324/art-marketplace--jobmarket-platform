<script setup>
import { onMounted, ref, onActivated, onDeactivated, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import ClipLoader from 'vue-spinner/src/ClipLoader.vue';
import CreatedPins from '@/components/Auth/CreatedPins.vue';
import LikedPins from '@/components/Auth/LikedPins.vue';
import Boards from '@/components/Auth/Boards.vue';
import FollowersSection from '@/components/Auth/FollowersSection.vue';
import FollowingSection from '@/components/Auth/FollowingSection.vue';
import WorkExperienceTab from '@/components/Auth/JobMarket/WorkExperienceTab.vue';
import CredentialsTab from '@/components/Auth/JobMarket/CredentialsTab.vue';
import CvTab from '@/components/Auth/JobMarket/CvTab.vue';
import CompanyProfileTab from '@/components/Auth/JobMarket/CompanyProfileTab.vue';
import HiringJobsTab from '@/components/Auth/JobMarket/HiringJobsTab.vue';
import ManageJobsTab from '@/components/Auth/JobMarket/ManageJobsTab.vue';
import EmployeesTab from '@/components/Auth/JobMarket/EmployeesTab.vue';
import { authUserStore } from '@/stores/authUserStore';
import { useUnavailableContentStore } from '@/stores/unavailableContent';

const userStore = authUserStore();
const unavailableStore = useUnavailableContentStore();

import { useToast } from "vue-toastification";
const toast = useToast();

import { useUnreadMessagesStore } from "@/stores/unreadMessages";

const unreadMessagesStore = useUnreadMessagesStore();

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();

import SearchBar from '@/components/Auth/SearchBar.vue';
import { PROFILE_TABS } from '@/utils/profileLinks';

const isLoading = ref(true);

const activeTab = ref('created');

const updateInformation = ref(false)

const showHeader = ref(false)
const observerTargetHeader = ref(null)
let observerHeader = null

observerHeader = new IntersectionObserver(
  ([entry]) => {
    showHeader.value = !entry.isIntersecting
  },
  {
    threshold: 1,
    rootMargin: '-20px 0px 0px 0px',
  }
)

watch(observerTargetHeader, (newVal) => {
  if (observerTargetHeader.value) {
    observerHeader.observe(observerTargetHeader.value)
  }
})

const showHeaderButtons = ref(false)
const observerTargetHeaderButtons = ref(null)
let observerHeaderButtons = null

observerHeaderButtons = new IntersectionObserver(
  ([entry]) => {
    showHeaderButtons.value = !entry.isIntersecting
  },
  {
    threshold: 0.05,
    rootMargin: '30px 0px 0px 0px',
  }
)

watch(observerTargetHeaderButtons, (newVal) => {
  if (observerTargetHeaderButtons.value) {
    observerHeaderButtons.observe(observerTargetHeaderButtons.value)
  }
})

onActivated(() => {
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = `(${totalUnread}) Pinterest`;
  } else {
    document.title = 'Pinterest';
  }
});

const color = ref('red');
const size = ref('100px');

const route = useRoute();
const router = useRouter();

const loadingUser = ref(true);

const username = route.params.username;
const user = ref(null);
const userImage = ref(null);

const userBanner = ref(null)

const auth_user_id = ref(null);

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

const canEditProfile = ref(false)
const showEditModal = ref(false)

const editUsername = ref('')
const editEmail = ref('')
const editDescription = ref('')
const editInstagram = ref('')
const editTiktok = ref('')
const editTelegram = ref('')
const editPinterest = ref('')

const imageFile = ref(null)
const imagePreview = ref(null)

const bannerImageFile = ref(null)
const bannerImagePreview = ref(null)

const cntUserFollowers = ref(null)
const cntUserFollowing = ref(null)
const checkUserFollow = ref(null)
const checkUserChat = ref(null)

const showFollowers = ref(false)
const showFollowing = ref(false)

const userAlreadyExistsError = ref(false)

onMounted(async () => {
  let unreadMessagesCount = unreadMessagesStore.count;
  let unreadUpdatesCount = unreadUpdatesStore.count;
  let totalUnread = unreadMessagesCount + unreadUpdatesCount;

  if (totalUnread > 0) {
    document.title = `(${totalUnread}) Pinterest`;
  } else {
    document.title = 'Pinterest';
  }

  try {
    const meRes = await axios.get('/api/users/me', { withCredentials: true })
    auth_user_id.value = meRes.data.id
  } catch (error) {
    console.error(error)
  }

  try {
    const response = await axios.get(`/api/users/user_username/${username}`);
    user.value = response.data;
    canEditProfile.value = auth_user_id.value === user.value.id;

    try {
      const userResponse = await axios.get(`/api/users/upload/${user.value.id}`, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(userResponse.data);
      userImage.value = blobUrl;

    } catch (error) {
      console.error(error);
    }
  } catch (error) {
    unavailableStore.show();
    router.back();
  }

  try {
    if (user.value.banner_image) {
      try {
        const userResponse = await axios.get(
          `/api/users/banner/upload/${user.value.id}`,
          {
            responseType: 'blob', // Treat the response as a binary file
            withCredentials: true, // Include credentials such as cookies or client certificates
          }
        );
        const blobUrl = URL.createObjectURL(userResponse.data);
        userBanner.value = blobUrl;

      } catch (error) {
        console.error(error);
      }
    }
  } catch (error) {
    console.log(error);
  }

  try {
    const response = await axios.get(`/api/subscription/followers/cnt/${user.value.id}`, { withCredentials: true });
    cntUserFollowers.value = response.data;

  } catch (error) {
    console.error(error);
  }

  try {
    const response = await axios.get(`/api/subscription/following/cnt/${user.value.id}`, { withCredentials: true });
    cntUserFollowing.value = response.data;
  } catch (error) {
    console.error(error);
  }

  try {
    const response = await axios.get(`/api/subscription/check_user_follow/${user.value.id}`, { withCredentials: true });
    checkUserFollow.value = response.data;

  } catch (error) {
    console.error(error);
  }

  try {
    const response = await axios.get(`/api/messages/check_chat/${user.value.id}`, { withCredentials: true });
    checkUserChat.value = response.data;

  } catch (error) {
    console.error(error);
  }

  loadingUser.value = false;
  isLoading.value = false;

  await applyRouteQuery();
});

watch(
  () => [route.query.tab, route.query.workExpId, route.query.boardId],
  async () => {
    if (loadingUser.value || !user.value) return;
    await applyRouteQuery();
  }
);

const formatLink = (url) => {
  return url.replace(/^https?:\/\//, '');
};

const showCreated = ref(false);
const showSaved = ref(false);
const showLiked = ref(false)
const showBoards = ref(false)
const showExperience = ref(false)
const showCredentials = ref(false)
const showCv = ref(false)
const showCompany = ref(false)
const showHiringJobs = ref(false)
const showManageJobs = ref(false)
const showEmployees = ref(false)
const highlightWorkExpId = ref(null)
const initialBoardId = ref(null)
const showEditModalBanner = ref(false)
let syncingFromRoute = false

const isOrgProfile = () => user.value?.account_kind === 'organization'

function clearJmTabs() {
  showExperience.value = false
  showCredentials.value = false
  showCv.value = false
  showCompany.value = false
  showHiringJobs.value = false
  showManageJobs.value = false
  showEmployees.value = false
}

function syncProfileQuery(tab, extra = {}) {
  if (syncingFromRoute) return
  const next = {}
  if (tab && PROFILE_TABS.includes(tab)) next.tab = tab
  if (extra.workExpId != null && extra.workExpId !== '') {
    next.workExpId = String(extra.workExpId)
  }
  if (extra.boardId != null && extra.boardId !== '') {
    next.boardId = String(extra.boardId)
  }
  const cur = route.query
  const same =
    String(cur.tab || '') === String(next.tab || '') &&
    String(cur.workExpId || '') === String(next.workExpId || '') &&
    String(cur.boardId || '') === String(next.boardId || '')
  if (same) return
  router.replace({ params: route.params, query: next })
}

function resolveDefaultTab() {
  if (user.value?.account_kind === 'organization' && user.value?.company_id) return 'company'
  return 'created'
}

function guardTab(tab) {
  const org = isOrgProfile()
  const hasCompany = !!user.value?.company_id
  const isOwner = auth_user_id.value === user.value?.id

  if (org && ['experience', 'credentials', 'cv'].includes(tab)) return resolveDefaultTab()
  if (!org && ['company', 'hiring', 'manage-jobs', 'employees'].includes(tab)) return resolveDefaultTab()
  if (['company', 'hiring', 'employees'].includes(tab) && !hasCompany) return resolveDefaultTab()
  if (tab === 'manage-jobs' && (!hasCompany || !isOwner)) return resolveDefaultTab()
  if (tab === 'cv' && !isOwner) return resolveDefaultTab()
  if (!PROFILE_TABS.includes(tab)) return resolveDefaultTab()
  return tab
}

async function selectTab(tab, { sync = true, workExpId, boardId } = {}) {
  const nextTab = guardTab(tab)
  activeTab.value = nextTab

  if (nextTab === 'experience') {
    highlightWorkExpId.value = workExpId != null ? workExpId : highlightWorkExpId.value
  } else if (sync) {
    highlightWorkExpId.value = null
  }

  if (nextTab === 'saved') {
    if (boardId != null) initialBoardId.value = boardId
  } else if (sync) {
    initialBoardId.value = null
  }

  showCreated.value = false
  showSaved.value = false
  showLiked.value = false
  showBoards.value = false
  clearJmTabs()

  switch (nextTab) {
    case 'created':
      showCreated.value = true
      break
    case 'saved':
      showSaved.value = true
      break
    case 'liked':
      showLiked.value = true
      break
    case 'experience':
      showExperience.value = true
      break
    case 'credentials':
      showCredentials.value = true
      break
    case 'cv':
      showCv.value = true
      break
    case 'company':
      showCompany.value = true
      break
    case 'hiring':
      showHiringJobs.value = true
      break
    case 'manage-jobs':
      showManageJobs.value = true
      break
    case 'employees':
      showEmployees.value = true
      break
    default:
      showCreated.value = true
      activeTab.value = 'created'
  }

  if (sync) {
    syncProfileQuery(activeTab.value, {
      workExpId: activeTab.value === 'experience' ? highlightWorkExpId.value : undefined,
      boardId: activeTab.value === 'saved' ? initialBoardId.value : undefined,
    })
  }
}

async function applyRouteQuery() {
  if (!user.value) return
  syncingFromRoute = true
  try {
    const qTab = String(route.query.tab || '')
    const qWorkExp = route.query.workExpId || null
    const qBoard = route.query.boardId || null
    highlightWorkExpId.value = qWorkExp
    initialBoardId.value = qBoard
    const tab = qTab ? guardTab(qTab) : resolveDefaultTab()
    await selectTab(tab, { sync: false, workExpId: qWorkExp, boardId: qBoard })
  } finally {
    syncingFromRoute = false
  }
}

function onSavedBoardChange(boardId) {
  initialBoardId.value = boardId
  syncProfileQuery('saved', { boardId })
}

async function createdPins() { await selectTab('created') }
async function savedPins() { await selectTab('saved') }
async function likedPins() { await selectTab('liked') }
async function experienceTab() { await selectTab('experience') }
async function credentialsTab() { await selectTab('credentials') }
async function cvTab() { await selectTab('cv') }
async function companyTab() { await selectTab('company') }
async function hiringJobsTab() { await selectTab('hiring') }
async function manageJobsTab() { await selectTab('manage-jobs') }
async function employeesTab() { await selectTab('employees') }

// Function to go back to the previous page in history
const goBack = () => {
  router.back();
};

const userHasTestAcc = ref(false)

async function editProfile() {

  let newUsername = null
  let email = null
  let description = null
  let instagram = null
  let tiktok = null
  let telegram = null
  let pinterest = null

  let atLeastOneField = false

  if (editUsername.value.trim()) {
    newUsername = editUsername.value.trim()
    atLeastOneField = true
  }
  if (editEmail.value.trim()) {
    email = editEmail.value.trim()
    atLeastOneField = true
  }
  if (editDescription.value.trim()) {
    description = editDescription.value.trim()
    atLeastOneField = true
  }
  if (editInstagram.value.trim()) {
    instagram = editInstagram.value.trim()
    atLeastOneField = true
  }
  if (editTiktok.value.trim()) {
    tiktok = editTiktok.value.trim()
    atLeastOneField = true
  }
  if (editTelegram.value.trim()) {
    telegram = editTelegram.value.trim()
    atLeastOneField = true
  }
  if (editPinterest.value.trim()) {
    pinterest = editPinterest.value.trim()
    atLeastOneField = true
  }

  if (atLeastOneField == true) {
    updateInformation.value = true
    try {
      const response = await axios.patch('/api/users/information',
        {
          username: newUsername,
          email: email,
          description: description,
          instagram: instagram,
          tiktok: tiktok,
          telegram: telegram,
          pinterest: pinterest
        },  // Data to be sent in the request body
        {
          withCredentials: true  // Include credentials like cookies or authorization headers
        }
      );
      user.value = response.data

      showEditModal.value = false

      updateInformation.value = false

    } catch (error) {
      if (error.response.status === 409) {
        updateInformation.value = false
        userAlreadyExistsError.value = true
      }
      if (error.response.status === 403) {
        updateInformation.value = false
        userHasTestAcc.value = true
      }
    }
  }
}

const showModal = ref(false)

const showEditModalImage = ref(false)

const updateProfileImage = ref(false)

const errorUpdateProfileImage = ref(false)

async function editProfileImage() {
  if (imageFile.value) {
    updateProfileImage.value = true
    try {
      const formData = new FormData();
      formData.append('file', imageFile.value);

      const response = await axios.post(
        `/api/users/upload/${auth_user_id.value}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          withCredentials: true, // Include credentials like cookies or authorization headers
        }
      );

      imageFile.value = null
      imagePreview.value = null

      try {
        const userResponse = await axios.get(`/api/users/upload/${user.value.id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(userResponse.data);
        userImage.value = blobUrl;
      } catch (error) {
        console.error(error);
      }

      showEditModalImage.value = false
      updateProfileImage.value = false

    } catch (error) {
      if (error.response.status === 415) {
        imageFile.value = null
        imagePreview.value = null
        updateProfileImage.value = false
        errorUpdateProfileImage.value = true
      }
    }
  }
}

const updateProfileBanner = ref(false)

const errorUpdateBannerImage = ref(false)

async function editBannerImage() {
  if (bannerImageFile.value) {
    updateProfileBanner.value = true
    try {
      const formData = new FormData();
      formData.append('file', bannerImageFile.value);

      const response = await axios.post(
        `/api/users/banner/upload/${auth_user_id.value}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          withCredentials: true, // Include credentials like cookies or authorization headers
        }
      );

      bannerImageFile.value = null
      bannerImagePreview.value = null

      try {
        const userResponse = await axios.get(
          `/api/users/banner/upload/${auth_user_id.value}`,
          {
            responseType: 'blob', // Treat the response as a binary file
            withCredentials: true, // Include credentials such as cookies or client certificates
          }
        );
        const blobUrl = URL.createObjectURL(userResponse.data);
        userBanner.value = blobUrl;
      } catch (error) {
        console.error(error);
      }

      showEditModalBanner.value = false
      updateProfileBanner.value = false

    } catch (error) {
      if (error.response.status === 415) {
        bannerImageFile.value = null
        bannerImagePreview.value = null
        updateProfileBanner.value = false
        errorUpdateBannerImage.value = true
      }
    }
  }
}

function handleImageUpload(event) {
  const file = event.target.files[0];

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp'];

  if (file) {

    if (!allowedTypes.includes(file.type)) {
      toast.warning('Please select a valid image file (.jpg, .jpeg, .gif, .webp, .png, .bmp).', { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
      return;
    }

    imageFile.value = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.value = e.target.result; // Update the preview data
    };
    reader.readAsDataURL(file);
  }
}

function handleBannerUpload(event) {
  const file = event.target.files[0];

  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/png', 'image/bmp'];

  if (file) {

    if (!allowedTypes.includes(file.type)) {
      toast.warning('Please select a valid image file (.jpg, .jpeg, .gif, .webp, .png, .bmp).', { position: "top-center", bodyClassName: ["cursor-pointer", "text-black", "font-bold"] });
      return;
    }

    const minWidth = 200;
    const minHeight = 300;

    const img = new Image();
    img.onload = () => {
      if (img.width < minWidth || img.height < minHeight) {
        toast.warning(`Image must be at least ${minWidth}x${minHeight}.`, {
          position: "top-center",
          bodyClassName: ["cursor-pointer", "text-black", "font-bold"]
        });
        return;
      }

      bannerImageFile.value = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        bannerImagePreview.value = e.target.result; // Update the preview data
      };
      reader.readAsDataURL(file);

    };
    img.src = URL.createObjectURL(file);
  }
}

const showEditButtons = ref(false)

async function follow() {
  try {
    const response = await axios.post(`/api/subscription/${user.value.id}`, { withCredentials: true })
  } catch (error) {
    console.log(error)
  }
  checkUserFollow.value = true
  cntUserFollowers.value += 1
}

async function unfollow() {
  try {
    const response = await axios.delete(`/api/subscription/${user.value.id}`, { withCredentials: true })
  } catch (error) {
    console.log(error)
  }
  checkUserFollow.value = false
  cntUserFollowers.value -= 1
}

const openingChat = ref(false)

/** Open Messages tab on the DM with this profile user (create chat if needed). */
async function openChatWithUser() {
  if (!user.value?.id || openingChat.value) return
  openingChat.value = true
  const wasExisting = !!checkUserChat.value
  try {
    const response = await axios.get(`/api/messages/get_chat/${user.value.id}`, {
      withCredentials: true,
    })
    const chatId = response.data
    checkUserChat.value = true
    if (wasExisting) {
      await router.push(`/messages?chat_id=${chatId}`)
    } else {
      await router.push(`/messages?chat_id=${chatId}&new_chat=true`)
    }
  } catch (error) {
    console.error(error)
    toast.error(error?.response?.data?.detail || 'Cannot open chat')
  } finally {
    openingChat.value = false
  }
}
</script>

<template>
  <transition name="fade" appear>
    <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-6"
      @click.self="showEditModal = false">
      
      <div class="ml-20 bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 relative">

        
        <ClipLoader v-if="updateInformation" color="#E60023" :size="size"
          class="flex flex-col items-center justify-center text-center min-h-[200px]" />

        
        <div v-if="!updateInformation" class="flex flex-col items-stretch gap-6">
          
          <h2 class="text-2xl font-semibold text-gray-900 text-center">
            Edit Profile
          </h2>

          <div class="space-y-6">
            <!-- Username Input -->
            <div>
              <label for="usernameEditUsername" class="block text-gray-700 text-lg mb-2">Username</label>
              <input v-model="editUsername" type="text" name="username" id="usernameEditUsername" autocomplete="off"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>

            <div>
              <label for="emailEditUser" class="block text-gray-700 text-lg mb-2">Email</label>
              <input v-model="editEmail" type="email" name="email" id="emailEditUser" autocomplete="email"
                placeholder="Email (needed to upload a CV)"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>

            <!-- Description Input -->
            <div>
              <label for="descriptionEditUser" class="block text-gray-700 text-lg mb-2">Description</label>
              <textarea v-model="editDescription" name="description" id="descriptionEditUser" rows="4"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300 resize-none"></textarea>
            </div>
          </div>

          
          <div class="flex flex-col gap-4">
            <div class="flex items-center space-x-3">
              <i class="pi pi-instagram text-3xl text-gray-700"></i>
              <input v-model="editInstagram" type="url" name="href-instagram" id="instagram" autocomplete="off"
                placeholder="Instagram URL"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>
            <div class="flex items-center space-x-3">
              <i class="pi pi-tiktok text-3xl text-gray-700"></i>
              <input v-model="editTiktok" type="url" name="href-tiktok" id="tiktok" autocomplete="off"
                placeholder="Tiktok URL"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>
            <div class="flex items-center space-x-3">
              <i class="pi pi-telegram text-3xl text-gray-700"></i>
              <input v-model="editTelegram" type="url" name="href-telegram" id="telegram" autocomplete="off"
                placeholder="Telegram URL"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>
            <div class="flex items-center space-x-3">
              <i class="pi pi-pinterest text-3xl text-gray-700"></i>
              <input v-model="editPinterest" type="url" name="href-pinterest" id="pinterest" autocomplete="off"
                placeholder="Pinterest URL"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-600 transition duration-300" />
            </div>
          </div>

          
          <div class="flex justify-center items-center gap-4 mt-6">
            <button @click="showEditModal = false"
              class="w-28 py-2 border border-gray-300 rounded-full text-gray-700 font-semibold hover:bg-gray-100 transition duration-300">
              Cancel
            </button>
            <button @click="editProfile"
              class="w-28 py-2 rounded-full bg-red-600 text-white font-semibold hover:bg-red-700 transition duration-300">
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>

  <transition name="fade" appear>
    <div v-if="showEditModalImage"
      class="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-6"
      @click.self="showEditModalImage = false">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-8 relative ml-20">
        
        <ClipLoader v-if="updateProfileImage" color="#E60023" :size="size"
          class="flex flex-col items-center justify-center text-center min-h-[150px]" />

        
        <div v-else class="flex flex-col items-center justify-center gap-5">
          <div class="flex flex-col items-center w-full">
            <label for="imageProfile" class="block mb-2 text-sm font-medium text-gray-700">
              Your Profile Image (.jpg, .jpeg, .gif, .webp, .png, .bmp)
            </label>
            <input type="file" id="imageProfile" name="image" accept=".jpg,.jpeg,.gif,.webp,.png,.bmp"
              @change="handleImageUpload"
              class="block w-full text-sm text-gray-900 border border-gray-300 rounded-3xl cursor-pointer bg-gray-50 focus:outline-none focus:ring-1 focus:ring-red-500 focus:border-red-500 transition duration-300" />
            <img v-if="imagePreview" :src="imagePreview" alt="Image Preview"
              class="mt-4 rounded-full w-32 h-32 object-cover border-4 border-gray-300"
              style="box-shadow: 0 0 15px rgba(255, 255, 255, 0.8), 0 0 30px rgba(255, 255, 255, 0.6);" />
          </div>
          <div class="flex space-x-4 mt-4">
            <button @click="showEditModalImage = false"
              class="w-28 py-2 border border-gray-300 rounded-full text-gray-700 font-medium hover:bg-gray-100 transition duration-300">
              Cancel
            </button>
            <button @click="editProfileImage"
              class="w-28 py-2 rounded-full bg-red-600 text-white font-medium hover:bg-red-700 transition duration-300">
              Update
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>

  <transition name="fade" appear>
    <div v-if="showEditModalBanner"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="showEditModalBanner = false">

      

      
      <div class="bg-white rounded-xl shadow-lg p-6 max-w-lg w-full ml-20">

        <ClipLoader v-if="updateProfileBanner" color="#E60023" :size="size"
          class="flex flex-col items-center justify-center text-center min-h-[300px]" />

        <div v-else>
          <h2 class="text-center text-2xl font-bold text-gray-800 mb-4">Update Banner</h2>

          
          <div class="mb-6">
            <label for="imageBanner" class="block mb-2 text-sm font-semibold text-gray-700">
              Select Banner Image (.jpg, .jpeg, .gif, .webp, .png, .bmp)
            </label>
            <input type="file" id="imageBanner" name="image" accept=".jpg,.jpeg,.gif,.webp,.png,.bmp"
              @change="handleBannerUpload"
              class="block w-full text-sm text-gray-900 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none focus:ring focus:ring-red-500" />
            <img v-if="bannerImagePreview" :src="bannerImagePreview" class="mt-4 rounded-xl w-full object-cover"
              style="max-height: 300px;" alt="Image Preview" />
          </div>

          
          <div class="flex justify-end space-x-4">
            <button @click="showEditModalBanner = false"
              class="px-4 py-2 bg-gray-100 text-gray-800 rounded-md hover:bg-gray-200 transition-colors">
              Cancel
            </button>
            <button @click="editBannerImage"
              class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors">
              Update
            </button>
          </div>
        </div>

      </div>
    </div>
  </transition>

  <div v-if="userAlreadyExistsError"
    class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full ml-20">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black"> User with that username already exists </h3>
          <button @click="userAlreadyExistsError = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            Ok, understand
          </button>
        </div>
      </div>
    </div>
  </div>

  
  <div v-if="userHasTestAcc"
    class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full ml-20">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black"> U cannot change username of test profile </h3>
          <button @click="userHasTestAcc = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            Ok, understand
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="errorUpdateProfileImage"
    class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full ml-20">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black"> Invalid file type. Allowed types: .jpg, .jpeg, .gif, .webp,
            .png, .bmp </h3>
          <button @click="errorUpdateProfileImage = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            Ok, understand
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="errorUpdateBannerImage"
    class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[60]">
    <div class="relative p-4 w-full max-w-md max-h-full ml-20">
      <div class="relative bg-white rounded-3xl shadow">
        <div class="p-5 text-center">
          <svg class="mx-auto mb-4 text-gray-400 w-12 h-12" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 20 20">
            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M10 11V6m0 8h.01M19 10a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <h3 class="mb-5 text-lg font-normal text-black"> Invalid file type. Allowed types: .jpg, .jpeg, .gif, .webp,
            .png, .bmp </h3>
          <button @click="errorUpdateBannerImage = false" type="button"
            class="text-white bg-red-600 hover:bg-red-800  font-medium rounded-3xl text-sm inline-flex items-center px-5 py-2.5 text-center">
            Ok, understand
          </button>
        </div>
      </div>
    </div>
  </div>

  <transition name="fade" appear>
    <div v-if="showFollowers" class="fixed inset-0 bg-black bg-opacity-75 z-50 p-6">
      <div class="ml-20 flex justify-center items-center min-h-screen" @click.self="showFollowers = false">
        <FollowersSection :user_id="user.id" :cntUserFollowers="cntUserFollowers" />
        <i @click="showFollowers = false"
          class="absolute right-20 top-20 pi pi-times text-white text-4xl cursor-pointer transition-transform duration-200 transform hover:scale-150"
          style="text-shadow: 0 0 20px rgba(255, 255, 255, 0.9), 0 0 40px rgba(255, 255, 255, 0.8), 0 0 80px rgba(255, 255, 255, 0.7);"></i>
      </div>
    </div>
  </transition>

  <transition name="fade" appear>
    <div v-if="showFollowing" class="fixed inset-0 bg-black bg-opacity-75 z-50 p-6">
      <div class="ml-20 flex justify-center items-center min-h-screen" @click.self="showFollowing = false">
        <FollowingSection :user_id="user.id" :cntUserFollowing="cntUserFollowing" />
        <i @click="showFollowing = false"
          class="absolute right-20 top-20 pi pi-times text-white text-4xl cursor-pointer transition-transform duration-200 transform hover:scale-150"
          style="text-shadow: 0 0 20px rgba(255, 255, 255, 0.9), 0 0 40px rgba(255, 255, 255, 0.8), 0 0 80px rgba(255, 255, 255, 0.7);"></i>
      </div>
    </div>
  </transition>

  <SearchBar />

  <div class="flex items-center justify-center mt-20 ml-20">
    <ClipLoader v-if="isLoading" :color="color" :size="size" class="" />
    <div v-else>
      <button @click="goBack" class="absolute top-4 left-20 text-gray-500 ml-20 mt-20 hover:-translate-x-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div v-if="!userBanner" class="flex flex-col items-center">
        <div class="relative">
          <i v-if="user && user.verified" class="absolute top-0 left-28 pi pi-verified text-2xl"></i>
          <img v-if="userImage" :src="userImage" alt="Profile Picture"
            class="rounded-full w-32 h-32 object-cover border-4 border-white" />
        </div>
        <p v-if="user" class="mt-4 text-3xl font-extrabold">{{ user.username }}</p>
        <div>
          <p v-if="user && user.description"
            class="description-box destext-center text-center mt-4 text-md mx-auto w-[500px]">
            {{ user.description }}
          </p>
          <span v-if="user && user.description && user.description.length > 200"
            class="text-black cursor-pointer justify-center flex font-extrabold" @click="showModal = true">
            More
          </span>

          <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-40 "
            @click.self="showModal = false">
            <div class="bg-white p-6 rounded-2xl w-[550px] relative h-[700px] ml-20">

              <button @click="showModal = false"
                class="absolute top-10 right-10 text-gray-500 hover:text-black">✕</button>

              <h2 class="text-4xl font-bold mb-4 mt-10 px-4 py-7">About user {{ user.username }}</h2>

              <div class="overflow-y-auto max-h-[400px] mt-10">

                <div class="space-y-6 text-md ml-4 mb-6">
                  <a v-if="user && user.instagram" :href="user.instagram" class="block w-full" target="_blank"
                    rel="noopener noreferrer">
                    <i class="pi pi-instagram mr-5"></i> {{ formatLink(user.instagram) }}
                  </a>
                  <a v-if="user && user.telegram" :href="user.telegram" class="block w-full" target="_blank"
                    rel="noopener noreferrer">
                    <i class="pi pi-telegram mr-5"></i> {{ formatLink(user.telegram) }}
                  </a>
                  <a v-if="user && user.tiktok" :href="user.tiktok" class="block w-full" target="_blank"
                    rel="noopener noreferrer">
                    <i class="pi pi-tiktok mr-5"></i> {{ formatLink(user.tiktok) }}
                  </a>
                  <a v-if="user && user.pinterest" :href="user.pinterest" class="block w-full" target="_blank"
                    rel="noopener noreferrer">
                    <i class="pi pi-pinterest mr-5"></i> {{ formatLink(user.pinterest) }}
                  </a>
                </div>

                <div class="space-y-6">
                  <a v-show="cntUserFollowers > 0" @click="showFollowers = true"
                    class=" text-black block w-full cursor-pointer hover:underline font-extrabold px-4">
                    <i class="pi pi-user-plus mr-5"></i> {{ cntUserFollowers }} follower
                  </a>

                  <a v-show="cntUserFollowing > 0" @click="showFollowing = true"
                    class=" text-black block w-full cursor-pointer hover:underline font-extrabold px-4">
                    <i class="pi pi-users mr-5"></i> {{ cntUserFollowing }} following
                  </a>
                </div>

                <p class="text-gray-800 whitespace-pre-line px-4 py-7 ">{{ user.description }}</p>

              </div>

              <!-- Follow Button -->
              <div class="absolute bottom-6 right-6">
                <button v-if="!canEditProfile && !checkUserFollow" @click="follow"
                  class="px-6 py-3 bg-red-500 text-white  rounded-2xl transition hover:bg-red-700 ">
                  Follow
                </button>
                <button v-if="!canEditProfile && checkUserFollow" @click="unfollow" :class="[
                  'px-6 py-3 rounded-2xl transition',
                  checkUserFollow ? 'bg-black text-white hover:bg-gray-900' : 'bg-red-500 text-white hover:bg-red-700'
                ]">
                  Unfollow
                </button>
              </div>

              <div class="absolute bottom-6 left-6">
                <button
                  v-if="!canEditProfile"
                  type="button"
                  :disabled="openingChat"
                  class="px-6 py-3 bg-gray-300 hover:bg-gray-400 text-black rounded-2xl transition disabled:opacity-50"
                  @click="openChatWithUser"
                >
                  {{ openingChat ? 'Opening…' : 'Send Message' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="flex flex-row gap-2 text-md text-black max-w-[500px] mt-2">
          <a v-if="user && user.instagram" :href="user.instagram" class="truncate inline-block max-w-[100px]"
            target="_blank" rel="noopener noreferrer">
            <i class="pi pi-instagram"></i> {{ formatLink(user.instagram) }}
          </a>
          <a v-if="user && user.telegram" :href="user.telegram" class="truncate inline-block max-w-[100px]"
            target="_blank" rel="noopener noreferrer">
            <i class="pi pi-telegram"></i> {{ formatLink(user.telegram) }}
          </a>
          <a v-if="user && user.tiktok" :href="user.tiktok" class="truncate inline-block max-w-[100px]" target="_blank"
            rel="noopener noreferrer">
            <i class="pi pi-tiktok"></i> {{ formatLink(user.tiktok) }}
          </a>
          <a v-if="user && user.pinterest" :href="user.pinterest" class="truncate inline-block max-w-[100px]"
            target="_blank" rel="noopener noreferrer">
            <i class="pi pi-pinterest"></i> {{ formatLink(user.pinterest) }}
          </a>
        </div>
        <div class="flex gap-4 mt-4">
          <a v-show="cntUserFollowers > 0" @click="showFollowers = true"
            class=" text-black cursor-pointer hover:underline font-extrabold">
            {{ cntUserFollowers }} follower
          </a>
          <a v-show="cntUserFollowing > 0" @click="showFollowing = true"
            class=" text-black cursor-pointer hover:underline font-extrabold">
            {{ cntUserFollowing }} following
          </a>
        </div>
        <div v-if="!canEditProfile" class="flex flex-row gap-4 mt-4">
          <button
            type="button"
            :disabled="openingChat"
            class="px-6 py-3 bg-gray-300 hover:bg-gray-400 text-black rounded-2xl transition disabled:opacity-50"
            @click="openChatWithUser"
          >
            {{ openingChat ? 'Opening…' : 'Send Message' }}
          </button>
          <button v-if="!canEditProfile && !checkUserFollow" @click="follow"
            class="px-6 py-3 bg-red-500 text-white  rounded-2xl transition hover:bg-red-700 ">
            Follow
          </button>
          <button v-if="!canEditProfile && checkUserFollow" @click="unfollow" :class="[
            'px-6 py-3 rounded-2xl transition',
            checkUserFollow ? 'bg-black text-white hover:bg-gray-900' : 'bg-red-500 text-white hover:bg-red-700'
          ]">
            Unfollow
          </button>
        </div>
        <div class="flex flex-col items-center">
          
          <button v-if="canEditProfile" @click="showEditButtons = !showEditButtons"
            class="px-5 py-2 bg-red-600 text-white font-medium rounded-full transition duration-300 hover:bg-red-700 focus:outline-none">
            Edit Profile
          </button>

          
          <div v-if="showEditButtons" class="mt-4 flex space-x-3">
            <button v-if="canEditProfile" @click="showEditModal = true"
              class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
              Information
            </button>
            <button v-if="canEditProfile" @click="showEditModalImage = true"
              class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
              Profile Image
            </button>
            <button v-if="canEditProfile" @click="showEditModalBanner = true"
              class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
              Banner
            </button>
          </div>
        </div>
      </div>
      <div v-if="userBanner" class="">
        
        <div class="grid grid-cols-2 gap-6 px-4 py-6">

          <div v-if="showHeader"
            class="fixed left-20 right-0 top-14 w-full z-20 bg-white bg-opacity-20 backdrop-blur-sm">
            <div class="ml-[140px] flex items-center gap-4">
              
              <img :src="userImage" alt="User Avatar" class="w-12 h-12 rounded-full object-cover" />

              <!-- Username -->
              <span class="text-2xl font-semibold text-black">
                {{ user.username }}
              </span>

              <div v-if="showHeaderButtons" class="ml-[195px] space-x-4">
                <button @click="createdPins(); activeTab = 'created'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-xl"
                  :class="{ 'active scale-105': activeTab === 'created' }">
                  Created
                </button>

                <button @click="savedPins(); activeTab = 'saved'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'saved' }">
                  Saved
                </button>

                <button @click="likedPins(); activeTab = 'liked'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'liked' }">
                  Liked
                </button>

                <button
                  v-if="user?.account_kind === 'organization' && user?.company_id"
                  @click="companyTab(); activeTab = 'company'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'company' }">
                  Company
                </button>

                <button
                  v-if="user?.account_kind === 'organization' && user?.company_id"
                  @click="hiringJobsTab(); activeTab = 'hiring'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'hiring' }">
                  Đang tuyển
                </button>

                <button
                  v-if="user?.account_kind === 'organization' && user?.company_id && auth_user_id === user.id"
                  @click="manageJobsTab(); activeTab = 'manage-jobs'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'manage-jobs' }">
                  Manage jobs
                </button>

                <button
                  v-if="user?.account_kind === 'organization' && user?.company_id"
                  @click="employeesTab(); activeTab = 'employees'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'employees' }">
                  Employees
                </button>

                <button
                  v-if="user?.account_kind !== 'organization'"
                  @click="experienceTab(); activeTab = 'experience'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'experience' }">
                  Experience
                </button>

                <button
                  v-if="user?.account_kind !== 'organization'"
                  @click="credentialsTab(); activeTab = 'credentials'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'credentials' }">
                  Credentials
                </button>

                <button
                  v-if="auth_user_id === user.id && user?.account_kind !== 'organization'"
                  @click="cvTab(); activeTab = 'cv'"
                  class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border  rounded-t-2xl"
                  :class="{ 'active scale-105': activeTab === 'cv' }">
                  CV
                </button>
              </div>
            </div>
          </div>

          
          <div ref="observerTargetHeader" class="ml-10">
            
            <div class="relative flex items-center">
              <i v-if="user && user.verified" class="absolute top-0 left-28 pi pi-verified text-2xl text-black"></i>
              <img v-if="userImage" :src="userImage" alt="Profile Picture"
                class="rounded-full w-32 h-32 object-cover" />
              <p v-if="user" class="ml-4 text-3xl font-extrabold text-gray-800">{{ user.username }}</p>
            </div>

            <div class="flex gap-4 mt-4 justify-left">
              <a v-show="cntUserFollowers > 0" @click="showFollowers = true"
                class="cursor-pointer hover:underline font-extrabold text-black">
                {{ cntUserFollowers }} follower
              </a>
              <a v-show="cntUserFollowing > 0" @click="showFollowing = true"
                class="cursor-pointer hover:underline font-extrabold text-black">
                {{ cntUserFollowing }} following
              </a>
            </div>

            

            
            <div class="mt-4">
              <p v-if="user && user.description" class="description-box destext-center mt-4 text-md w-[500px]">
                {{ user.description }}
              </p>
              <span v-if="user && user.description && user.description.length > 200"
                class="text-black cursor-pointer flex justify-left font-extrabold mt-2" @click="showModal = true">
                More
              </span>
            </div>

            
            <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-40"
              @click.self="showModal = false">
              <div class="bg-white p-6 rounded-2xl w-[550px] relative h-[700px]">
                <button @click="showModal = false" class="absolute top-4 right-4 text-gray-500 hover:text-black">
                  ✕
                </button>
                <h2 class="text-4xl font-bold mb-4 mt-10 text-center">
                  About user {{ user.username }}
                </h2>
                <div class="overflow-y-auto max-h-[400px] px-4 mt-10">
                  <div class="space-y-6 text-md mb-6">
                    <a v-if="user && user.instagram" :href="user.instagram" class="block" target="_blank"
                      rel="noopener noreferrer">
                      <i class="pi pi-instagram mr-3"></i> {{ formatLink(user.instagram) }}
                    </a>
                    <a v-if="user && user.telegram" :href="user.telegram" class="block" target="_blank"
                      rel="noopener noreferrer">
                      <i class="pi pi-telegram mr-3"></i> {{ formatLink(user.telegram) }}
                    </a>
                    <a v-if="user && user.tiktok" :href="user.tiktok" class="block" target="_blank"
                      rel="noopener noreferrer">
                      <i class="pi pi-tiktok mr-3"></i> {{ formatLink(user.tiktok) }}
                    </a>
                    <a v-if="user && user.pinterest" :href="user.pinterest" class="block" target="_blank"
                      rel="noopener noreferrer">
                      <i class="pi pi-pinterest mr-3"></i> {{ formatLink(user.pinterest) }}
                    </a>
                  </div>
                  <div class="space-y-6">
                    <a v-show="cntUserFollowers > 0" @click="showFollowers = true"
                      class="block cursor-pointer hover:underline font-extrabold">
                      <i class="pi pi-user-plus mr-3"></i> {{ cntUserFollowers }} follower
                    </a>
                    <a v-show="cntUserFollowing > 0" @click="showFollowing = true"
                      class="block cursor-pointer hover:underline font-extrabold">
                      <i class="pi pi-users mr-3"></i> {{ cntUserFollowing }} following
                    </a>
                  </div>
                  <p class="text-gray-800 whitespace-pre-line py-7">
                    {{ user.description }}
                  </p>
                </div>
                
                <div class="absolute bottom-6 right-6 flex flex-col space-y-3">
                  <button v-if="!canEditProfile && !checkUserFollow" @click="follow"
                    class="px-6 py-3 bg-red-500 text-white rounded-2xl transition hover:bg-red-700">
                    Follow
                  </button>
                  <button v-if="!canEditProfile && checkUserFollow" @click="unfollow"
                    :class="['px-6 py-3 rounded-2xl transition', checkUserFollow ? 'bg-black text-white hover:bg-gray-900' : 'bg-red-500 text-white hover:bg-red-700']">
                    Unfollow
                  </button>
                </div>
                <div class="absolute bottom-6 left-6 flex flex-col space-y-3">
                  <button
                    v-if="!canEditProfile"
                    type="button"
                    :disabled="openingChat"
                    class="px-6 py-3 bg-neutral-200 hover:bg-neutral-300 text-black rounded-2xl transition disabled:opacity-50"
                    @click="openChatWithUser"
                  >
                    {{ openingChat ? 'Opening…' : 'Send Message' }}
                  </button>
                </div>
              </div>
            </div>

            
            <div class="flex flex-row gap-2 text-md text-black max-w-[500px] mt-2 justify-left">
              <a v-if="user && user.instagram" :href="user.instagram" class="truncate inline-block max-w-[100px]"
                target="_blank" rel="noopener noreferrer">
                <i class="pi pi-instagram"></i> {{ formatLink(user.instagram) }}
              </a>
              <a v-if="user && user.telegram" :href="user.telegram" class="truncate inline-block max-w-[100px]"
                target="_blank" rel="noopener noreferrer">
                <i class="pi pi-telegram"></i> {{ formatLink(user.telegram) }}
              </a>
              <a v-if="user && user.tiktok" :href="user.tiktok" class="truncate inline-block max-w-[100px]"
                target="_blank" rel="noopener noreferrer">
                <i class="pi pi-tiktok"></i> {{ formatLink(user.tiktok) }}
              </a>
              <a v-if="user && user.pinterest" :href="user.pinterest" class="truncate inline-block max-w-[100px]"
                target="_blank" rel="noopener noreferrer">
                <i class="pi pi-pinterest"></i> {{ formatLink(user.pinterest) }}
              </a>
            </div>

            
            <div class="flex flex-row gap-4 mt-4 justify-left">
              <button v-if="!canEditProfile && !checkUserFollow" @click="follow"
                class="px-6 py-3 bg-red-500 text-white rounded-2xl transition hover:bg-red-700">
                Follow
              </button>
              <button v-if="!canEditProfile && checkUserFollow" @click="unfollow"
                :class="['px-6 py-3 rounded-2xl transition', checkUserFollow ? 'bg-black text-white hover:bg-gray-900' : 'bg-red-500 text-white hover:bg-red-700']">
                Unfollow
              </button>
              <button
                v-if="!canEditProfile"
                type="button"
                :disabled="openingChat"
                class="px-6 py-3 bg-neutral-200 hover:bg-neutral-300 text-black rounded-2xl transition disabled:opacity-50"
                @click="openChatWithUser"
              >
                {{ openingChat ? 'Opening…' : 'Send Message' }}
              </button>
            </div>

            
            <div class="flex flex-col items-start justify-start mt-6">
              <button v-if="canEditProfile" @click="showEditButtons = !showEditButtons"
                class="px-5 py-2 bg-red-600 text-white font-medium rounded-full transition duration-300 hover:bg-red-700 focus:outline-none">
                Edit Profile
              </button>
              <div v-if="showEditButtons" class="mt-4 flex space-x-3">
                <button v-if="canEditProfile" @click="showEditModal = true"
                  class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
                  Information
                </button>
                <button v-if="canEditProfile" @click="showEditModalImage = true"
                  class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
                  Profile Image
                </button>
                <button v-if="canEditProfile" @click="showEditModalBanner = true"
                  class="px-5 py-2 bg-gray-100 text-gray-800 font-medium rounded-full transition duration-300 hover:bg-gray-200 focus:outline-none">
                  Banner
                </button>
              </div>
            </div>
          </div>

          
          <div ref="observerTargetHeaderButtons" class="flex items-center justify-center">
            <img v-if="userBanner" :src="userBanner" alt="Banner"
              class="rounded-2xl h-[400px] w-[600px] object-cover" />
          </div>
        </div>
      </div>
      <div  class="flex items-center mt-6 justify-center space-x-4 flex-wrap">
        <button @click="createdPins(); activeTab = 'created'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'created' }">
          Created
        </button>

        <button @click="savedPins(); activeTab = 'saved'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'saved' }">
          Saved
        </button>

        <button @click="likedPins(); activeTab = 'liked'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'liked' }">
          Liked
        </button>

        <button
          v-if="user?.account_kind === 'organization' && user?.company_id"
          @click="companyTab(); activeTab = 'company'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'company' }">
          Company
        </button>

        <button
          v-if="user?.account_kind === 'organization' && user?.company_id"
          @click="hiringJobsTab(); activeTab = 'hiring'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'hiring' }">
          Đang tuyển
        </button>

        <button
          v-if="user?.account_kind === 'organization' && user?.company_id && auth_user_id === user.id"
          @click="manageJobsTab(); activeTab = 'manage-jobs'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'manage-jobs' }">
          Manage jobs
        </button>

        <button
          v-if="user?.account_kind === 'organization' && user?.company_id"
          @click="employeesTab(); activeTab = 'employees'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'employees' }">
          Employees
        </button>

        <button
          v-if="user?.account_kind !== 'organization'"
          @click="experienceTab(); activeTab = 'experience'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'experience' }">
          Experience
        </button>

        <button
          v-if="user?.account_kind !== 'organization'"
          @click="credentialsTab(); activeTab = 'credentials'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'credentials' }">
          Credentials
        </button>

        <button
          v-if="auth_user_id === user.id && user?.account_kind !== 'organization'"
          @click="cvTab(); activeTab = 'cv'"
          class="relative px-6 py-2 text-black transition hover:border-red-600 animated-border hover:bg-gray-100 rounded-t-2xl"
          :class="{ 'active scale-105': activeTab === 'cv' }">
          CV
        </button>
      </div>
    </div>
  </div>
  <div class="min-h-[500px]">
    <CreatedPins v-if="showCreated" :user_id="user.id" :auth_user_id="auth_user_id" />
    <Boards
      v-if="showSaved"
      :user_id="user.id"
      :auth_user_id="auth_user_id"
      :initial-board-id="initialBoardId"
      @board-change="onSavedBoardChange"
    />
    <LikedPins v-if="showLiked" :user_id="user.id" />
    <CompanyProfileTab
      v-if="showCompany && user?.company_id"
      :company-id="user.company_id"
      :is-owner="auth_user_id === user.id"
    />
    <HiringJobsTab
      v-if="showHiringJobs && user?.company_id"
      :company-id="user.company_id"
    />
    <ManageJobsTab
      v-if="showManageJobs && user?.company_id"
      :company-id="user.company_id"
      :is-owner="auth_user_id === user.id"
    />
    <EmployeesTab
      v-if="showEmployees && user?.company_id"
      :company-id="user.company_id"
      :is-owner="auth_user_id === user.id"
    />
    <WorkExperienceTab
      v-if="showExperience"
      :user-id="user.id"
      :is-owner="auth_user_id === user.id"
      :highlight-id="highlightWorkExpId"
    />
    <CredentialsTab
      v-if="showCredentials"
      :user-id="user.id"
      :is-owner="auth_user_id === user.id"
    />
    <CvTab v-if="showCv" :is-owner="auth_user_id === user.id" />
  </div>
</template>

<style scoped>
.animated-border {
  position: relative;
  transition: color 0.3s ease-in-out, transform 0.2s ease-out;
}

.animated-border::after {
  content: "";
  position: absolute;
  bottom: -4px;
  left: 50%;
  width: 0;
  height: 2px;
  background-color: red;
  transition: width 0.3s ease-out, transform 0.3s ease-out;
  transform: translateX(-50%);
}

.active::after {
  width: 100%;
  left: 50%;
  transform: translateX(-50%);
}

.animated-border:hover {
  color: red;
  transform: scale(1.05);
}

.animated-border:hover::after {
  width: 100%;
  left: 50%;
  transform: translateX(-50%);
}

/* Define transition animations */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  /* Internet Explorer 10+ */
  scrollbar-width: none;
  /* Firefox */
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
  /* Chrome, Safari, Opera */
}

.fade-in-animation {
  opacity: 0;
  transform: scale(0.95);
  animation: fadeIn 0.3s ease-in-out forwards;
}

@keyframes fadeIn {
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.loader {
  width: 48px;
  height: 48px;
  display: inline-block;
  position: relative;
  border-width: 3px 2px 3px 2px;
  border-style: solid dotted solid dotted;
  border-color: #c50000 rgba(10, 255, 39, 0.3) #1c589e rgba(255, 101, 101, 0.836);
  border-radius: 50%;
  box-sizing: border-box;
  animation: 1s rotate linear infinite;
}

.loader:before,
.loader:after {
  content: '';
  top: 0;
  left: 0;
  position: absolute;
  border: 10px solid transparent;
  border-bottom-color: #a309d27a;
  transform: translate(-10px, 19px) rotate(-35deg);
}

.loader:after {
  border-color: #de3500 #670e6d00 #7b090900 #0000;
  transform: translate(32px, 3px) rotate(-35deg);
}

@keyframes rotate {
  100% {
    transform: rotate(360deg)
  }
}

.description-box {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
}
</style>