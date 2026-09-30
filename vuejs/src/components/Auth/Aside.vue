<script setup>
import { onMounted, ref, onBeforeUnmount } from 'vue';
import axios from 'axios'
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n'
import { useUnreadMessagesStore } from "@/stores/unreadMessages";
import { authUserStore } from "@/stores/authUserStore";
import { useUnavailableContentStore } from '@/stores/unavailableContent';
import { probeContentPath } from '@/composables/probeContentAvailability';
import { profilePath } from '@/utils/profileLinks';

const unreadMessagesStore = useUnreadMessagesStore();
const userStore = authUserStore();
const unavailableStore = useUnavailableContentStore();
const router = useRouter();
const { t } = useI18n()

import { useUnreadUpdatesStore } from "@/stores/unreadUpdates";

const unreadUpdatesStore = useUnreadUpdatesStore();

const isAdminPath = () => {
  const route = useRoute();
  return route.path.startsWith('/admin');
};

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import "dayjs/locale/en";

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale("en");

const formatTime = (createdAt) => {
  const now = dayjs();
  const createdTime = dayjs.utc(createdAt).local();
  const diffMinutes = now.diff(createdTime, "minute");

  return diffMinutes < 30 ? "just now" : createdTime.fromNow();
};

const isActiveLink = (routePath) => {
  const route = useRoute();
  return route.path === routePath;
};

const emit = defineEmits(['logout'])

const props = defineProps({
  me: Object,
  meImage: String
})

async function logout() {
  try {
    await axios.post('/api/users/logout')
  } catch (error) {
    console.log(error)
  } finally {
    emit('logout')
  }
}

const cntUnreadMessages = ref(null)

const showModal = ref(false)

const JOB_UPDATE_TYPES = new Set([
  'job_application_received',
  'job_application_viewed',
  'job_application_rejected',
  'job_application_passed',
  'work_exp_pending',
  'work_exp_approved',
  'work_exp_rejected',
  'company_suspended',
  'company_unsuspended',
])

function isJobUpdate(type) {
  return JOB_UPDATE_TYPES.has(type)
}

function jobUpdateMeta(update) {
  return update?.metadata || update?.meta || {}
}

function jobUpdateLink(update) {
  const meta = jobUpdateMeta(update)
  const type = String(update.update_type || '')
  if (type.startsWith('job_application')) {
    return meta.job_id ? `/explore?job=${meta.job_id}` : '/explore'
  }
  if (type.startsWith('work_exp')) {
    const we = meta.work_exp_id
    // Owner reviewing someone else's exp → artist profile.
    // Artist receiving approve/reject → own profile (me).
    const uname =
      type === 'work_exp_pending' && meta.artist_username
        ? meta.artist_username
        : props.me?.username
    if (!uname) return '/explore'
    return profilePath(uname, { tab: 'experience', workExpId: we })
  }
  if (type === 'company_suspended' || type === 'company_unsuspended') {
    return props.me?.username ? profilePath(props.me.username, { tab: 'company' }) : '/explore'
  }
  return props.me?.username ? profilePath(props.me.username) : '/explore'
}

function actorProfilePath(update) {
  const u = update?.user?.username
  return u ? `/user/${u}` : '/'
}

function updatePinPath(update) {
  return update?.pin_id != null ? `/pin/${update.pin_id}` : '/'
}

function openModal() {
  showModal.value = true
  loadUpdates().finally(() => {
    unreadUpdatesStore.fetchUnreadUpdates()
  })
}


function closeModal() {
  showModal.value = false
  updates.value = []
  offset.value = 0
  limit.value = 7
  canLoad.value = true
  isPinsLoading.value = false
  unreadUpdatesStore.fetchUnreadUpdates()
}

let updateNavBusy = false

async function onUpdatesPanelClick(event) {
  const anchor = event.target?.closest?.('a[href]')
  if (!anchor || updateNavBusy) return

  const href = anchor.getAttribute('href')
  if (!href || href.startsWith('http') || href.startsWith('mailto:')) return

  event.preventDefault()
  event.stopPropagation()

  updateNavBusy = true
  try {
    closeModal()
    const ok = await probeContentPath(href)
    if (!ok) {
      unavailableStore.show()
      return
    }
    await router.push(href)
  } finally {
    updateNavBusy = false
  }
}

const updates = ref([])
const tempUpdates = ref([])

const offset = ref(0);
const limit = ref(7);

const isPinsLoading = ref(false);

const canLoad = ref(true)

async function loadUpdates() {
  if (isPinsLoading.value) {
    return;
  }

  if (!canLoad.value) {
    return
  }

  isPinsLoading.value = true;
  try {
    const response = await axios.get(`/api/updates/`, { params: { offset: offset.value, limit: limit.value } })
    const data = response.data

    for (let i = 0; i < data.length; i++) {

      if (!data[i].is_read) {
        try {
          await axios.put(`/api/updates/read/${data[i].id}`)
          unreadUpdatesStore.decrement()
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "recommendations") {
        const response = await axios.get(`/api/recommendations/${data[i].id}`, {
          params: { offset: 0, limit: 1 },
          withCredentials: true,
        });

        const pin_id = response.data[0].id
        try {
          const pinResponse = await axios.get(`/api/pins/upload/${pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }

      if (data[i].update_type == "follow") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "like_pin") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }

      if (data[i].update_type == "save_pin") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }

      if (data[i].update_type == "comment_pin") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].comment_id}`, { withCredentials: true })
          data[i].comment = response.data

          if (data[i].comment.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].comment.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].commentFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].commentIsIamge = true;
              } else {
                data[i].commentIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "like_comment") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].comment_id}`, { withCredentials: true })
          data[i].comment = response.data

          if (data[i].comment.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].comment.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].commentFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].commentIsIamge = true;
              } else {
                data[i].commentIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "reply_comment") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].comment_id}`, { withCredentials: true })
          data[i].comment = response.data

          if (data[i].comment.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].comment.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].commentFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].commentIsIamge = true;
              } else {
                data[i].commentIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].reply_id}`, { withCredentials: true })
          data[i].reply = response.data

          if (data[i].reply.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].reply.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].replyFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].replyIsIamge = true;
              } else {
                data[i].replyIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "like_reply") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].comment_id}`, { withCredentials: true })
          data[i].comment = response.data

          if (data[i].comment.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].comment.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].commentFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].commentIsIamge = true;
              } else {
                data[i].commentIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const response = await axios.get(`/api/comments/get-by-id/${data[i].reply_id}`, { withCredentials: true })
          data[i].reply = response.data

          if (data[i].reply.image) {
            try {
              const response = await axios.get(`/api/comments/upload/${data[i].reply.id}`, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(response.data);
              const contentType = response.headers['content-type'];
              data[i].replyFile = blobUrl;
              if (contentType.startsWith('image/')) {
                data[i].replyIsIamge = true;
              } else {
                data[i].replyIsIamge = false;
              }
            } catch (error) {
              console.error(error);
            }
          }
        } catch (error) {
          console.error(error)
        }
      }

      if (data[i].update_type == "pin_created_for_followers") {
        try {
          const response = await axios.get(`/api/users/user_id/${data[i].user_id}`);
          data[i].user = response.data;

          try {
            const userResponse = await axios.get(`/api/users/upload/${data[i].user.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(userResponse.data);
            data[i].image = blobUrl;

          } catch (error) {
            console.error(error);
          }
        } catch (error) {
          console.error(error)
        }

        try {
          const pinResponse = await axios.get(`/api/pins/upload/${data[i].pin_id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(pinResponse.data);
          const contentType = pinResponse.headers['content-type'];
          if (contentType.startsWith('image/')) {
            data[i].file = blobUrl;
            data[i].isImage = true;
          } else {
            data[i].file = blobUrl;
            data[i].isImage = false;
          }
        } catch (error) {
          console.error(error);
        }
      }
      tempUpdates.value.push(data[i])
    }
  } catch (error) {
    console.error(error)
  }

  offset.value += limit.value;

  updates.value.push(...tempUpdates.value)

  if (tempUpdates.value.length < limit.value) {
    canLoad.value = false
  }

  tempUpdates.value = []

  isPinsLoading.value = false;

  if (limit.value == 7) {
    limit.value = 5
  }
}

const handleScroll = (event) => {
  const container = event.target;
  if (container.scrollTop + container.clientHeight >= container.scrollHeight - 10) {
    loadUpdates();
  }
};

let eventSource = null;

function connectSSE() {
  eventSource = new EventSource(`/api/sse/updates/stream/${props.me.id}`);

  eventSource.onmessage = (event) => {
    const rawData = JSON.parse(event.data);
    const new_update = JSON.parse(rawData.message);
    addNewUpdate(new_update)
  };

  eventSource.onerror = () => {
    console.warn("Updates SSE disconnected. Reconnecting...")
    eventSource.close();
    setTimeout(() => {
      connectSSE();
    }, 5000);
  };
}

async function addNewUpdate(update) {
  if (showModal.value === false) {
    unreadUpdatesStore.increment()
  } else {

    try {
      await axios.put(`/api/updates/read/${update.id}`)
    } catch (error) {
      console.error(error)
    }

    if (update.update_type == "recommendations") {
      const response = await axios.get(`/api/recommendations/${update.id}`, {
        params: { offset: 0, limit: 1 },
        withCredentials: true,
      });

      const pin_id = response.data[0].id
      try {
        const pinResponse = await axios.get(`/api/pins/upload/${pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "follow") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;

        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error)
      }
    }

    if (update.update_type == "like_pin") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "save_pin") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "comment_pin") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.comment_id}`, { withCredentials: true });
        update.comment = response.data;

        if (update.comment.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.comment.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.commentFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.commentIsIamge = true;
            } else {
              update.commentIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "like_comment") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.comment_id}`, { withCredentials: true });
        update.comment = response.data;

        if (update.comment.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.comment.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.commentFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.commentIsIamge = true;
            } else {
              update.commentIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "reply_comment") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.comment_id}`, { withCredentials: true });
        update.comment = response.data;

        if (update.comment.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.comment.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.commentFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.commentIsIamge = true;
            } else {
              update.commentIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.reply_id}`, { withCredentials: true });
        update.reply = response.data;

        if (update.reply.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.reply.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.replyFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.replyIsIamge = true;
            } else {
              update.replyIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "like_reply") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;
        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.comment_id}`, { withCredentials: true });
        update.comment = response.data;

        if (update.comment.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.comment.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.commentFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.commentIsIamge = true;
            } else {
              update.commentIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }

      try {
        const response = await axios.get(`/api/comments/get-by-id/${update.reply_id}`, { withCredentials: true });
        update.reply = response.data;

        if (update.reply.image) {
          try {
            const response = await axios.get(`/api/comments/upload/${update.reply.id}`, { responseType: 'blob' });
            const blobUrl = URL.createObjectURL(response.data);
            const contentType = response.headers['content-type'];
            update.replyFile = blobUrl;
            if (contentType.startsWith('image/')) {
              update.replyIsIamge = true;
            } else {
              update.replyIsIamge = false;
            }
          } catch (error) {
            console.error(error);
          }
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (update.update_type == "pin_created_for_followers") {
      try {
        const response = await axios.get(`/api/users/user_id/${update.user_id}`);
        update.user = response.data;

        try {
          const userResponse = await axios.get(`/api/users/upload/${update.user.id}`, { responseType: 'blob' });
          const blobUrl = URL.createObjectURL(userResponse.data);
          update.image = blobUrl;

        } catch (error) {
          console.error(error);
        }
      } catch (error) {
        console.error(error)
      }

      try {
        const pinResponse = await axios.get(`/api/pins/upload/${update.pin_id}`, { responseType: 'blob' });
        const blobUrl = URL.createObjectURL(pinResponse.data);
        const contentType = pinResponse.headers['content-type'];
        if (contentType.startsWith('image/')) {
          update.file = blobUrl;
          update.isImage = true;
        } else {
          update.file = blobUrl;
          update.isImage = false;
        }
      } catch (error) {
        console.error(error);
      }
    }

    updates.value.unshift(update);
  }
}

onMounted(async () => {
  connectSSE()
})

onBeforeUnmount(() => {
  if (eventSource) {
    eventSource.close();
  }
})
</script>

<template>
  <nav
    class="fixed top-0 left-0 h-full w-20 flex flex-col justify-between items-center z-30 border-r border-gray-300 py-4 ">
    <!-- Icons -->
    <div class="flex flex-col items-center text-xl space-y-6">
      <RouterLink to="/"
        :class="[isActiveLink('/') ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']">
        <i :class="['pi', 'pi-home', ]"></i>
      </RouterLink>
      <RouterLink :to="`/user/${me.username}`"
        :class="[isActiveLink(`/user/${me.username}`) ? '' : 'transition-transform duration-100 transform hover:scale-125 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']">
        <img :src="meImage" alt="me profile"
          :class="[isActiveLink(`/user/${me.username}`) ? 'border-black' : 'border-gray-400', 'w-10', 'h-10', 'object-cover', 'rounded-full', 'border-2']" />
      </RouterLink>
      <RouterLink
        v-if="userStore.canCreatePin"
        to="/create-pin"
        :class="[isActiveLink('/create-pin') ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']">
        <i :class="['pi', 'pi-plus-circle']"></i>
      </RouterLink>
      <RouterLink to="/explore"
        :class="[isActiveLink('/explore') ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']"
        :title="t('nav.exploreJobs')">
        <i class="pi pi-briefcase"></i>
      </RouterLink>
      <div @click="openModal" class="relative"
        :class="[showModal ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']"
        :title="t('nav.updates')">
        <i class="pi pi-bell"></i>
        <div v-if="unreadUpdatesStore.count > 0"
          class="absolute top-0 right-0 py-0.5 px-2 bg-red-600 rounded-full flex align-center items-center">
          <span class="text-xs text-white"> {{ unreadUpdatesStore.count }}</span>
        </div>
      </div>
      <RouterLink to="/messages" class="relative"
        :class="[isActiveLink('/messages') ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']"
        :title="t('nav.messages')">
        <i class="pi pi-envelope"></i>
        <div v-if="unreadMessagesStore.count"
          class="absolute top-0 right-0 py-0.5 px-2 bg-red-600 rounded-full flex align-center items-center">
          <span class="text-xs text-white"> {{ unreadMessagesStore.count }}</span>
        </div>
      </RouterLink>
      <RouterLink to="/settings"
        :class="[isActiveLink('/settings') ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']"
        :title="t('nav.settings')">
        <i class="pi pi-cog"></i>
      </RouterLink>
      <RouterLink
        v-if="userStore.hasRole('admin')"
        to="/admin"
        :class="[isAdminPath() ? 'bg-gray-200' : 'transition-transform duration-100 transform hover:scale-150 cursor-pointer', 'rounded-lg', 'px-4', 'py-3', 'flex', 'items-center']"
        :title="t('nav.admin')">
        <i class="pi pi-shield"></i>
      </RouterLink>
      <div @click="logout"
        class="cursor-pointer rounded-md transition-transform duration-100 transform hover:scale-150 p-5 text-xl flex items-center">
        <i class="pi pi-sign-out"></i>
      </div>
    </div>
  </nav>

  <Transition name="fade">
    <div v-if="showModal" class="fixed top-4 left-24 bottom-4 w-1/4 bg-white shadow-2xl z-[60] rounded-3xl">
      
      <div class="flex justify-between items-center p-4">
        <h2 class="text-xl font-bold text-black">{{ t('nav.updates') }}</h2>
        <button @click="closeModal"
          class="text-black text-4xl transition duration-300 transform hover:scale-125 hover:bg-gray-200 rounded-full px-2 items-center justify-center flex">
          ×
        </button>
      </div>

      
      <div
        class="space-y-4 overflow-y-auto h-[600px]"
        @scroll="handleScroll"
        @click.capture="onUpdatesPanelClick"
      >
        <div class="pl-4 space-y-2" v-auto-animate>
          <div v-for="update in updates" :key="update.id">
            <RouterLink @click="closeModal" v-if="update.update_type == 'recommendations'"
              :to="`/recommendations/${update.id}`" :class="[
                'rounded-lg flex items-center space-x-4 w-full h-24 relative hover:bg-purple-300 transition',
                !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
              ]">
              
              <div class="w-20 h-24 flex-shrink-0">
                <template v-if="update.isImage">
                  <img :src="update.file" alt="Update Image" class="w-full h-full object-cover rounded-lg" />
                </template>
                <template v-else>
                  <video :src="update.file" autoplay muted loop class="w-full h-full object-cover rounded-lg"></video>
                </template>
              </div>

              
              <p class="text-black text-md font-medium flex items-center justify-center">
                {{ update.content }}
              </p>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold">
                ● New
              </span>
            </RouterLink>

            <RouterLink @click="closeModal" v-if="update.update_type == 'follow'" :to="`/user/${update.user.username}`"
              :class="[
                'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
                !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
              ]">
              
              <div class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center">
                <img :src="update.image" alt="Update Image" class="w-20 h-20 object-cover rounded-full" />
              </div>

              
              <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                <span class="text-black text-md font-bold truncate">
                  {{ update.user.username }}
                </span>
                <span class="text-black text-md font-medium">started following you</span>
              </div>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold">
                ● New
              </span>
            </RouterLink>

            <div v-if="update.update_type == 'like_pin'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-md font-medium">
                    ❤️ liked your pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Liked Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'save_pin'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-md font-medium">
                    💾 saved your pin to {{ update.content }}
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Saved Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'comment_pin'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-md font-medium flex flex-wrap gap-0.5">
                    💬 commented on
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.comment.content">{{
                      update.comment.content
                      }}</span>
                    <div v-if="update.commentFile" class="">
                      <img v-if="update.commentIsIamge" :src="update.commentFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.commentFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    on your pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'like_comment'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[190px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-sm font-medium flex flex-wrap gap-0.5">
                    ❤️liked your 💬comment
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.comment.content">{{
                      update.comment.content
                      }}</span>
                    <div v-if="update.commentFile" class="">
                      <img v-if="update.commentIsIamge" :src="update.commentFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.commentFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    on pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'reply_comment'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-sm font-medium flex flex-wrap gap-0.5">
                    💬 reply on
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.comment.content">{{
                      update.comment.content
                      }}</span>
                    <div v-if="update.commentFile" class="">
                      <img v-if="update.commentIsIamge" :src="update.commentFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.commentFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    with
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.reply.content">{{
                      update.reply.content
                      }}</span>
                    <div v-if="update.replyFile" class="">
                      <img v-if="update.replyIsIamge" :src="update.replyFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.replyFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    on pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'like_reply'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mr-2 w-16 h-16 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-16 h-16 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[220px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-sm font-medium flex flex-wrap gap-0.5">
                    ❤️liked your reply
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.reply.content">{{
                      update.reply.content
                      }}</span>
                    <div v-if="update.replyFile" class="">
                      <img v-if="update.replyIsIamge" :src="update.replyFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.replyFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    on comment
                    <span class="text-gray-700 italic truncate max-w-[50px]" v-if="update.comment.content">{{
                      update.comment.content
                      }}</span>
                    <div v-if="update.commentFile" class="">
                      <img v-if="update.commentIsIamge" :src="update.commentFile" alt="Comment media"
                        class="w-7 h-7 object-cover rounded-lg" />
                      <video v-else :src="update.commentFile" autoplay loop muted
                        class="w-7 h-7 object-cover rounded-lg"></video>
                    </div>
                    on pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <div v-if="update.update_type == 'pin_created_for_followers'" :class="[
              'rounded-lg flex items-center w-full h-24 relative hover:bg-purple-300 transition',
              !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
            ]">
              
              <RouterLink @click="closeModal" :to="actorProfilePath(update)"
                class="mx-2 w-20 h-24 flex-shrink-0 flex justify-center items-center relative z-10">
                <img :src="update.image" alt="User Avatar" class="w-20 h-20 object-cover rounded-full" />
              </RouterLink>

              <RouterLink @click="closeModal" :to="updatePinPath(update)"
                class="flex items-center flex-1 min-w-0 h-full pr-4 relative z-10">
                <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[180px]">
                  <span class="text-black text-md font-bold truncate">
                    {{ update.user.username }}
                  </span>
                  <span class="text-black text-md font-medium">
                    whom you follow, published a new pin
                  </span>
                </div>
                <div class="ml-auto flex-shrink-0">
                  <img v-if="update.isImage" :src="update.file" alt="Pin" class="w-10 h-10 object-cover rounded" />
                  <video v-else :src="update.file" autoplay loop muted class="w-10 h-10 object-cover rounded"></video>
                </div>
              </RouterLink>

              
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs pointer-events-none">
                {{ formatTime(update.created_at) }}
              </span>

              
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold pointer-events-none">
                ● New
              </span>
            </div>

            <RouterLink
              v-else-if="isJobUpdate(update.update_type)"
              @click="closeModal"
              :to="jobUpdateLink(update)"
              :class="[
                'rounded-lg flex items-center w-full min-h-24 relative hover:bg-purple-300 transition px-3',
                !update.is_read ? 'border-l-4 border-blue-500 bg-blue-50' : ''
              ]"
            >
              <div class="mx-2 w-14 h-14 flex-shrink-0 flex justify-center items-center rounded-full bg-gray-100">
                <i class="pi pi-briefcase text-gray-700" />
              </div>
              <div class="flex flex-col justify-center overflow-hidden mr-auto max-w-[220px] py-3">
                <span class="text-black text-md font-bold break-words">
                  {{ update.content || update.update_type }}
                </span>
                <span class="text-gray-500 text-xs mt-1">{{ update.update_type }}</span>
              </div>
              <span class="absolute top-2 right-2 font-medium text-gray-600 text-xs">
                {{ formatTime(update.created_at) }}
              </span>
              <span v-if="!update.is_read" class="absolute bottom-2 right-2 text-xs text-blue-600 font-semibold">
                ● New
              </span>
            </RouterLink>

          </div>

          <div v-if="isPinsLoading" class="flex item-center justify-center">
            <span class="loader2"></span>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style>

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

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