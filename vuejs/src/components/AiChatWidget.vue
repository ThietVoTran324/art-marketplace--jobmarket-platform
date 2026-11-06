<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { authUserStore } from '@/stores/authUserStore'
import { useAuthModal } from '@/composables/useAuthModal'

const { locale } = useI18n()
const router = useRouter()
const userStore = authUserStore()
const { openAuthModal } = useAuthModal()

const open = ref(false)
const loading = ref(false)
const sending = ref(false)
const clearing = ref(false)
const draft = ref('')
const messages = ref([])
const error = ref(null)
const panelEl = ref(null)
let tempIdSeq = 0

const isAuthed = computed(() => userStore.isAuthenticated)
const isVi = computed(() => !!locale.value?.startsWith('vi'))

const title = computed(() => (isVi.value ? 'Trợ lý AI' : 'AI assistant'))
const placeholder = computed(() =>
  isVi.value ? 'Hỏi về pin, art, job, đơn hàng…' : 'Ask about pins, art, jobs, orders…'
)
const loginHint = computed(() =>
  isVi.value ? 'Đăng nhập để chat với trợ lý.' : 'Log in to chat with the assistant.'
)

function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`
  const entry = document.cookie.split('; ').find((item) => item.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null
}

async function csrfHeader() {
  let csrfToken = readCookie('csrf_token')
  if (!csrfToken) {
    const response = await axios.get('/api/users/csrf', { withCredentials: true })
    csrfToken = response.data.csrf_token
  }
  return { 'X-CSRF-Token': csrfToken }
}

async function scrollBottom() {
  await nextTick()
  if (panelEl.value) {
    panelEl.value.scrollTop = panelEl.value.scrollHeight
  }
}

function citesOf(m) {
  const raw = m?.meta?.cites
  return Array.isArray(raw) ? raw : []
}

/** Real in-app / absolute href only — FAQ cites often have no page. */
function navigableHref(raw) {
  if (raw == null) return null
  const href = String(raw).trim()
  if (!href || href === '#' || href === 'null' || href === 'undefined') return null
  // Corpus filesystem paths must never become routes
  if (href.startsWith('app/') || /\.md(?:$|[?#])/i.test(href)) return null
  return href
}

function citeHref(c) {
  return navigableHref(c?.url) || navigableHref(c?.path)
}

function citeLabel(c) {
  return String(c?.title || c?.source_ref || c?.type || '').trim()
}

/** FAQ / non-route cite → send follow-up in chat (no /null navigation). */
async function onCiteClick(evt, c) {
  const href = citeHref(c)
  if (href) {
    onInternalNav(evt, href, c.type === 'job' || c.open_in_new_tab)
    return
  }
  evt.preventDefault()
  const label = citeLabel(c)
  if (!label || sending.value) return
  draft.value = label
  await send()
}

async function onSuggestClick(label) {
  const text = String(label || '').trim()
  if (!text || sending.value) return
  draft.value = text
  await send()
}

/** Split assistant text into text / markdown-link / suggest segments. */
function contentSegments(text) {
  const src = text || ''
  // Absolute http(s) OR any (...) target so [choice](null) stays clickable as suggest
  const re = /\[([^\]]+)\]\(([^)\s]+)\)/g
  const parts = []
  let last = 0
  let match
  while ((match = re.exec(src)) !== null) {
    if (match.index > last) {
      parts.push({ type: 'text', value: src.slice(last, match.index) })
    }
    const href = navigableHref(match[2])
    if (href) {
      parts.push({
        type: 'link',
        label: match[1],
        href,
        isJob: /\/jobs\/\d+/i.test(href),
        isPin: /\/pin\/\d+/i.test(href),
        isUser: /\/user\//i.test(href),
      })
    } else {
      parts.push({ type: 'suggest', label: match[1] })
    }
    last = match.index + match[0].length
  }
  if (last < src.length) {
    parts.push({ type: 'text', value: src.slice(last) })
  }
  return parts.length ? parts : [{ type: 'text', value: src }]
}

function onInternalNav(evt, href, openBlank) {
  const safe = navigableHref(href)
  if (!safe) {
    evt.preventDefault()
    return
  }
  if (openBlank || evt.metaKey || evt.ctrlKey) {
    return
  }
  try {
    const u = new URL(safe, window.location.origin)
    if (u.origin === window.location.origin) {
      evt.preventDefault()
      // Guard bogus model/tool urls like /null
      if (!u.pathname || u.pathname === '/null' || u.pathname === '/undefined') {
        return
      }
      router.push(u.pathname + u.search + u.hash)
    }
  } catch {
    /* external — let browser handle */
  }
}

async function loadHistory() {
  if (!isAuthed.value) {
    messages.value = []
    return
  }
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get('/api/ai/chat/messages', {
      params: { limit: 80 },
      withCredentials: true,
    })
    messages.value = data.messages || []
    await scrollBottom()
  } catch (e) {
    const detail = e?.response?.data?.detail
    if (detail === 'ai_chat_disabled') {
      error.value = isVi.value
        ? 'Chat AI đang tắt trên server.'
        : 'AI chat is disabled on the server.'
    } else if (e?.response?.status === 401) {
      messages.value = []
    } else {
      error.value = detail || e.message || 'Failed to load chat'
    }
  } finally {
    loading.value = false
  }
}

async function toggle() {
  if (!open.value) {
    open.value = true
    if (!isAuthed.value) {
      openAuthModal('login')
      return
    }
    await loadHistory()
  } else {
    open.value = false
  }
}

function replaceOptimistic(optimisticId, userMessage) {
  const idx = messages.value.findIndex((m) => m.id === optimisticId)
  if (idx !== -1) {
    if (userMessage) messages.value.splice(idx, 1, userMessage)
    else messages.value.splice(idx, 1)
  } else if (userMessage) {
    messages.value.push(userMessage)
  }
}

async function sendJson(content, optimisticId) {
  const { data } = await axios.post(
    '/api/ai/chat/messages',
    { content },
    { withCredentials: true }
  )
  replaceOptimistic(optimisticId, data.user_message)
  if (data.assistant_message) messages.value.push(data.assistant_message)
  await scrollBottom()
}

async function sendStream(content, optimisticId) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    ...(await csrfHeader()),
  }
  const res = await fetch('/api/ai/chat/messages/stream', {
    method: 'POST',
    credentials: 'include',
    headers,
    body: JSON.stringify({ content }),
  })
  if (res.status === 503) {
    const body = await res.json().catch(() => ({}))
    const err = Object.assign(new Error(body.detail || 'stream_unavailable'), {
      response: { status: 503, data: body },
      allowJsonFallback: body.detail === 'ai_chat_sse_disabled' || true,
    })
    throw err
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw Object.assign(new Error(body.detail || res.statusText), {
      response: { status: res.status, data: body },
      allowJsonFallback: false,
    })
  }

  const streamBotId = `tmp-bot-${++tempIdSeq}`
  messages.value.push({
    id: streamBotId,
    role: 'assistant',
    content: '',
    meta: { streaming: true },
    created_at: null,
  })
  await scrollBottom()

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let gotDone = false
  let streamError = false

  const applyEvent = async (eventName, rawData) => {
    let data = {}
    try {
      data = JSON.parse(rawData)
    } catch {
      return
    }
    if (eventName === 'token' && data.text) {
      const bot = messages.value.find((m) => m.id === streamBotId)
      if (bot) bot.content = (bot.content || '') + data.text
      await scrollBottom()
    } else if (eventName === 'done') {
      gotDone = true
      replaceOptimistic(optimisticId, data.user_message)
      const idx = messages.value.findIndex((m) => m.id === streamBotId)
      if (idx !== -1) {
        if (data.assistant_message) messages.value.splice(idx, 1, data.assistant_message)
        else messages.value.splice(idx, 1)
      } else if (data.assistant_message) {
        messages.value.push(data.assistant_message)
      }
      await scrollBottom()
    } else if (eventName === 'error') {
      streamError = true
      messages.value = messages.value.filter(
        (m) => m.id !== streamBotId && m.id !== optimisticId
      )
      const err = data.error || 'stream_error'
      if (err === 'quota_exceeded') {
        error.value = isVi.value ? 'Hết lượt chat hôm nay.' : 'Daily chat quota reached.'
      } else {
        error.value = data.detail || err
      }
      draft.value = content
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const block of chunks) {
      const lines = block.split('\n')
      let eventName = 'message'
      const dataLines = []
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (dataLines.length) await applyEvent(eventName, dataLines.join('\n'))
    }
  }

  if (!gotDone && !streamError) {
    // Body opened — user msg may already be persisted; reload history instead of double POST
    messages.value = messages.value.filter((m) => m.id !== streamBotId)
    await loadHistory()
  }
}

async function send() {
  if (!isAuthed.value) {
    openAuthModal('login')
    return
  }
  const content = draft.value.trim()
  if (!content || sending.value) return

  sending.value = true
  error.value = null
  draft.value = ''

  const optimisticId = `tmp-user-${++tempIdSeq}`
  messages.value.push({
    id: optimisticId,
    role: 'user',
    content,
    meta: { optimistic: true },
    created_at: null,
  })
  await scrollBottom()

  try {
    try {
      await sendStream(content, optimisticId)
    } catch (streamErr) {
      const detail = streamErr?.response?.data?.detail
      if (streamErr?.allowJsonFallback || detail === 'ai_chat_sse_disabled') {
        await sendJson(content, optimisticId)
      } else {
        throw streamErr
      }
    }
  } catch (e) {
    messages.value = messages.value.filter((m) => m.id !== optimisticId)
    const detail = e?.response?.data?.detail
    if (detail === 'quota_exceeded') {
      error.value = isVi.value ? 'Hết lượt chat hôm nay.' : 'Daily chat quota reached.'
    } else {
      error.value = detail || e.message || 'Send failed'
    }
    draft.value = content
  } finally {
    sending.value = false
  }
}

async function clearChat() {
  if (!isAuthed.value || clearing.value || sending.value) return
  const ok = window.confirm(
    isVi.value
      ? 'Xóa toàn bộ hội thoại AI? Không hoàn tác được.'
      : 'Clear the entire AI conversation? This cannot be undone.'
  )
  if (!ok) return
  clearing.value = true
  error.value = null
  try {
    await axios.delete('/api/ai/chat/conversation', { withCredentials: true })
    messages.value = []
  } catch (e) {
    error.value = e?.response?.data?.detail || e.message || 'Clear failed'
  } finally {
    clearing.value = false
  }
}

watch(isAuthed, (v) => {
  if (v && open.value) loadHistory()
  if (!v) messages.value = []
})
</script>

<template>
  <div class="ai-chat-root">
    <button
      type="button"
      class="ai-chat-fab"
      :aria-label="title"
      :title="title"
      @click="toggle"
    >
      <span v-if="!open">AI</span>
      <span v-else>×</span>
    </button>

    <div v-if="open" class="ai-chat-panel" role="dialog" :aria-label="title">
      <header class="ai-chat-head">
        <strong>{{ title }}</strong>
        <div class="ai-chat-head-actions">
          <button
            v-if="isAuthed"
            type="button"
            class="ai-chat-clear"
            :disabled="clearing || sending"
            @click="clearChat"
          >
            {{ isVi ? 'Xóa' : 'Clear' }}
          </button>
          <button type="button" class="ai-chat-close" @click="open = false">×</button>
        </div>
      </header>

      <div v-if="!isAuthed" class="ai-chat-guest">
        <p>{{ loginHint }}</p>
        <button type="button" class="ai-chat-login" @click="openAuthModal('login')">
          {{ isVi ? 'Đăng nhập' : 'Log in' }}
        </button>
      </div>

      <template v-else>
        <div ref="panelEl" class="ai-chat-body">
          <p v-if="loading" class="ai-chat-muted">…</p>
          <p v-else-if="!messages.length && !sending" class="ai-chat-muted">
            {{
              isVi
                ? 'Hỏi về pin đang bán, art, việc làm hoặc đơn hàng của bạn.'
                : 'Ask about listed pins, art, jobs, or your orders.'
            }}
          </p>
          <div
            v-for="m in messages"
            :key="m.id"
            class="ai-chat-bubble"
            :class="m.role === 'user' ? 'is-user' : 'is-bot'"
          >
            <template v-if="m.role === 'user'">{{ m.content }}</template>
            <template v-else>
              <div
                v-if="m.meta?.streaming && !m.content"
                class="ai-chat-bubble-inner is-typing"
                aria-live="polite"
              >
                <span class="ai-chat-dots" aria-hidden="true"><i /><i /><i /></span>
              </div>
              <div v-else class="ai-chat-rich">
                <template v-for="(seg, i) in contentSegments(m.content)" :key="i">
                  <span v-if="seg.type === 'text'">{{ seg.value }}</span>
                  <button
                    v-else-if="seg.type === 'suggest'"
                    type="button"
                    class="ai-chat-md-suggest"
                    :disabled="sending"
                    @click="onSuggestClick(seg.label)"
                  >{{ seg.label }}</button>
                  <a
                    v-else
                    :href="seg.href"
                    class="ai-chat-md-link"
                    :target="seg.isJob ? '_blank' : undefined"
                    :rel="seg.isJob ? 'noopener noreferrer' : undefined"
                    @click="onInternalNav($event, seg.href, seg.isJob)"
                  >{{ seg.label }}</a>
                </template>
              </div>
              <div v-if="citesOf(m).length" class="ai-chat-cites">
                <component
                  :is="citeHref(c) ? 'a' : 'button'"
                  v-for="(c, ci) in citesOf(m)"
                  :key="`${c.type}-${c.id}-${ci}`"
                  class="ai-chat-cite"
                  :class="{ 'is-suggest': !citeHref(c) }"
                  :type="citeHref(c) ? undefined : 'button'"
                  :disabled="citeHref(c) ? undefined : sending"
                  :href="citeHref(c) || undefined"
                  :target="
                    citeHref(c) && (c.type === 'job' || c.open_in_new_tab)
                      ? '_blank'
                      : undefined
                  "
                  :rel="
                    citeHref(c) && (c.type === 'job' || c.open_in_new_tab)
                      ? 'noopener noreferrer'
                      : undefined
                  "
                  @click="onCiteClick($event, c)"
                >
                  <img
                    v-if="c.thumb_url"
                    :src="c.thumb_url"
                    alt=""
                    class="ai-chat-thumb"
                    loading="lazy"
                  />
                  <span class="ai-chat-cite-title">{{ citeLabel(c) }}</span>
                </component>
              </div>
            </template>
          </div>
          <div
            v-if="sending && !messages.some((m) => m.meta?.streaming)"
            class="ai-chat-bubble is-bot is-typing"
            aria-live="polite"
          >
            <span class="ai-chat-dots" aria-hidden="true">
              <i /><i /><i />
            </span>
            <span class="ai-chat-sr">
              {{ isVi ? 'Đang trả lời…' : 'Thinking…' }}
            </span>
          </div>
        </div>
        <p v-if="error" class="ai-chat-error">{{ error }}</p>
        <form class="ai-chat-form" @submit.prevent="send">
          <input
            v-model="draft"
            type="text"
            :placeholder="placeholder"
            :disabled="sending"
            maxlength="2000"
            autocomplete="off"
          />
          <button type="submit" :disabled="sending || !draft.trim()">
            {{ sending ? '…' : isVi ? 'Gửi' : 'Send' }}
          </button>
        </form>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ai-chat-root {
  position: fixed;
  right: 1.25rem;
  bottom: 1.25rem;
  z-index: 80;
  font-family: system-ui, sans-serif;
}
.ai-chat-fab {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 999px;
  border: none;
  background: #1a1a1a;
  color: #f5f5f5;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
.ai-chat-panel {
  position: absolute;
  right: 0;
  bottom: 3.75rem;
  width: min(22rem, calc(100vw - 2rem));
  height: min(28rem, 70vh);
  display: flex;
  flex-direction: column;
  background: #faf9f7;
  color: #1a1a1a;
  border: 1px solid #ddd6ce;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
}
.ai-chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 0.85rem;
  background: #efeae3;
  border-bottom: 1px solid #ddd6ce;
  gap: 0.5rem;
}
.ai-chat-head-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.ai-chat-clear {
  border: 1px solid #ccc4ba;
  background: #fff;
  border-radius: 6px;
  padding: 0.2rem 0.45rem;
  font-size: 0.75rem;
  cursor: pointer;
  color: #5a534c;
}
.ai-chat-clear:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ai-chat-close {
  border: none;
  background: transparent;
  font-size: 1.25rem;
  cursor: pointer;
  line-height: 1;
}
.ai-chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.ai-chat-bubble {
  max-width: 90%;
  padding: 0.55rem 0.7rem;
  border-radius: 10px;
  font-size: 0.875rem;
  line-height: 1.4;
  word-break: break-word;
}
.ai-chat-bubble.is-user {
  align-self: flex-end;
  background: #1a1a1a;
  color: #f5f5f5;
  white-space: pre-wrap;
}
.ai-chat-bubble.is-bot {
  align-self: flex-start;
  background: #fff;
  border: 1px solid #e5e0d8;
}
.ai-chat-rich {
  white-space: pre-wrap;
}
.ai-chat-md-link {
  color: #0b57d0;
  text-decoration: underline;
  word-break: break-all;
}
.ai-chat-cites {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.45rem;
}
.ai-chat-cite {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  text-decoration: none;
  color: inherit;
  border: 1px solid #ebe4db;
  border-radius: 8px;
  padding: 0.3rem 0.4rem;
  background: #f7f4ef;
}
.ai-chat-cite:hover {
  border-color: #cfc6ba;
}
.ai-chat-cite.is-suggest {
  cursor: pointer;
  font: inherit;
  text-align: left;
  appearance: none;
}
.ai-chat-cite.is-suggest:hover:not(:disabled) {
  border-color: #cfc6ba;
  background: #f0ebe3;
}
.ai-chat-cite.is-suggest:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ai-chat-md-suggest {
  display: inline;
  margin: 0;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  color: #1a5f4a;
  text-decoration: underline;
  cursor: pointer;
}
.ai-chat-md-suggest:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ai-chat-thumb {
  width: 2.25rem;
  height: 2.25rem;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  background: #ddd;
}
.ai-chat-cite-title {
  font-size: 0.78rem;
  line-height: 1.25;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.ai-chat-bubble.is-typing {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 2.1rem;
  padding-block: 0.7rem;
}
.ai-chat-dots {
  display: inline-flex;
  align-items: flex-end;
  gap: 0.28rem;
  height: 1rem;
}
.ai-chat-dots i {
  display: block;
  width: 0.35rem;
  height: 0.35rem;
  border-radius: 50%;
  background: #6b6560;
  animation: ai-bounce 1s ease-in-out infinite;
}
.ai-chat-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.ai-chat-dots i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes ai-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.45;
  }
  30% {
    transform: translateY(-0.35rem);
    opacity: 1;
  }
}
.ai-chat-sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.ai-chat-form {
  display: flex;
  gap: 0.4rem;
  padding: 0.55rem;
  border-top: 1px solid #ddd6ce;
  background: #fff;
}
.ai-chat-form input {
  flex: 1;
  border: 1px solid #ccc4ba;
  border-radius: 8px;
  padding: 0.45rem 0.55rem;
  font-size: 0.875rem;
}
.ai-chat-form button {
  border: none;
  border-radius: 8px;
  padding: 0.45rem 0.7rem;
  background: #1a1a1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.8rem;
}
.ai-chat-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ai-chat-muted {
  color: #7a736a;
  font-size: 0.85rem;
}
.ai-chat-error {
  color: #a33;
  font-size: 0.8rem;
  padding: 0 0.75rem 0.25rem;
}
.ai-chat-guest {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-start;
}
.ai-chat-login {
  border: none;
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  background: #1a1a1a;
  color: #fff;
  cursor: pointer;
}
</style>
