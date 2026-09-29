<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { authUserStore } from '@/stores/authUserStore'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const authStore = authUserStore()

const loading = ref(true)
const error = ref(null)
const preview = ref(null)
const confirming = ref(false)
const cancelling = ref(false)
const mocking = ref(false)
const pinBlobUrl = ref(null)
const pollTimer = ref(null)
let loadSeq = 0

const pinId = computed(() => {
  const fromRoute = Number(route.params.pinId)
  if (Number.isFinite(fromRoute) && fromRoute > 0) return fromRoute
  const fromQuery = Number(route.query.pin)
  if (Number.isFinite(fromQuery) && fromQuery > 0) return fromQuery
  return preview.value?.pin?.pin_id || null
})
const orderIdParam = computed(() => {
  const n = Number(route.params.orderId)
  return Number.isFinite(n) && n > 0 ? n : null
})

const phase = computed(() => preview.value?.phase || 'draft')
const instr = computed(() => preview.value?.payment_instructions || null)
const expiresLabel = computed(() => {
  const iso = preview.value?.expires_at
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString()
})

function formatListingPrice(row) {
  if (!row) return ''
  return `${row.currency} ${(row.price_minor / 100).toFixed(2)}`
}

function formatVnd(n) {
  if (n == null) return '—'
  return `${Number(n).toLocaleString('vi-VN')} đ`
}

async function copyText(text, label) {
  if (text == null || text === '') return
  try {
    await navigator.clipboard.writeText(String(text))
    toast.success(`Đã copy ${label}`)
  } catch {
    toast.error('Không copy được')
  }
}

async function loadPinImage(id) {
  if (pinBlobUrl.value) {
    URL.revokeObjectURL(pinBlobUrl.value)
    pinBlobUrl.value = null
  }
  if (!id) return
  try {
    const r = await axios.get(`/api/pins/upload/${id}`, { responseType: 'blob' })
    pinBlobUrl.value = URL.createObjectURL(r.data)
  } catch {
    pinBlobUrl.value = null
  }
}

function stopPoll() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

function startPoll() {
  stopPoll()
  if (phase.value !== 'pending' || !preview.value?.order_id) return
  pollTimer.value = setInterval(async () => {
    const id = preview.value?.order_id
    const pin = preview.value?.pin?.pin_id || pinId.value
    if (!id) return
    try {
      const r = await axios.get(`/api/marketplace/me/orders/${id}/checkout`)
      preview.value = r.data
      if (r.data.phase === 'owned') {
        stopPoll()
        toast.success('Thanh toán thành công — license đã mở')
      }
    } catch (e) {
      const status = e.response?.status
      const detail = e.response?.data?.detail
      // Cancelled / expired — leave pay UI, go back to draft for this pin.
      if (status === 409 || status === 404) {
        stopPoll()
        if (pin) {
          try {
            const r = await axios.get(`/api/marketplace/pins/${pin}/checkout`)
            preview.value = r.data
            if (route.name === 'checkout-order') {
              await router.replace({
                name: 'checkout-pin',
                params: { pinId: String(pin) },
              })
            }
          } catch {
            error.value = typeof detail === 'string' ? detail : 'Đơn đã hủy hoặc hết hạn'
            preview.value = null
          }
        }
      }
    }
  }, 5000)
}

async function load() {
  if (confirming.value) return
  if (!authStore.canBuyLicense) {
    loading.value = false
    error.value = authStore.isAdmin
      ? 'Admin accounts cannot buy licenses'
      : 'Organization accounts cannot buy licenses'
    preview.value = null
    return
  }
  const seq = ++loadSeq
  loading.value = true
  error.value = null
  stopPoll()
  try {
    let r
    if (orderIdParam.value) {
      r = await axios.get(`/api/marketplace/me/orders/${orderIdParam.value}/checkout`)
    } else if (pinId.value) {
      r = await axios.get(`/api/marketplace/pins/${pinId.value}/checkout`)
    } else {
      throw new Error('missing_pin')
    }
    if (seq !== loadSeq) return
    preview.value = r.data
    await loadPinImage(r.data.pin?.pin_id)
    if (r.data.phase === 'pending') startPoll()
  } catch (e) {
    if (seq !== loadSeq) return
    console.error(e)
    const status = e.response?.status
    const detail = e.response?.data?.detail
    // Resume-by-order failed (cancelled) → fall back to pin draft silently.
    if (orderIdParam.value && (status === 409 || status === 404)) {
      const pin = Number(route.query.pin) || preview.value?.pin?.pin_id
      if (pin) {
        await router.replace({ name: 'checkout-pin', params: { pinId: String(pin) } })
        return
      }
    }
    error.value =
      typeof detail === 'string'
        ? detail
        : e.message === 'missing_pin'
          ? 'Thiếu pin'
          : 'Không tải được trang thanh toán'
    preview.value = null
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function confirmPay() {
  if (!pinId.value || confirming.value || cancelling.value) return
  confirming.value = true
  stopPoll()
  try {
    const r = await axios.post(`/api/marketplace/pins/${pinId.value}/orders`)
    preview.value = {
      ...preview.value,
      phase: 'pending',
      order_id: r.data.order?.id,
      order: r.data.order,
      charge_amount_vnd: r.data.order?.charge_amount_vnd,
      payment_instructions: r.data.payment_instructions,
      expires_at: r.data.order?.expires_at,
      sepay_mock_enabled: preview.value?.sepay_mock_enabled,
    }
    // Stay on /checkout/pin/:id — avoid remount race that leaves UI stuck on "Đang chuẩn bị".
    toast.success('Chuyển khoản theo hướng dẫn bên dưới')
    startPoll()
  } catch (e) {
    console.error(e)
    const detail = e.response?.data?.detail
    if (detail === 'email_not_verified') {
      toast.error('Cần xác minh email trước khi mua. Vào Settings → Email.')
    } else {
      toast.error(typeof detail === 'string' ? detail : 'Không tạo được đơn')
    }
  } finally {
    confirming.value = false
  }
}

async function cancelFlow() {
  if (cancelling.value) return
  cancelling.value = true
  stopPoll()
  try {
    if (phase.value === 'pending' && preview.value?.order_id) {
      await axios.post(
        `/api/marketplace/me/orders/${preview.value.order_id}/cancel`
      )
      toast.success('Đã hủy đơn thanh toán')
    }
    const backPin = preview.value?.pin?.pin_id || pinId.value
    if (window.opener) {
      window.close()
    } else if (backPin) {
      await router.push({ name: 'pin', params: { id: String(backPin) } })
    } else {
      await router.push({ name: 'home' })
    }
  } catch (e) {
    console.error(e)
    const detail = e.response?.data?.detail
    toast.error(typeof detail === 'string' ? detail : 'Không hủy được')
  } finally {
    cancelling.value = false
  }
}

async function mockPay() {
  if (!preview.value?.order_id || mocking.value) return
  mocking.value = true
  try {
    await axios.post(
      `/api/marketplace/dev/mock-sepay-paid/${preview.value.order_id}`
    )
    toast.success('Payment recorded')
    await load()
  } catch (e) {
    console.error(e)
    toast.error('Could not record payment')
  } finally {
    mocking.value = false
  }
}

watch(
  () => [route.params.pinId, route.params.orderId],
  () => {
    if (!confirming.value) load()
  }
)

onMounted(() => {
  if (!authStore.authUserId) {
    error.value = 'Cần đăng nhập'
    loading.value = false
    return
  }
  load()
})

onBeforeUnmount(() => {
  stopPoll()
  confirming.value = false
  loadSeq += 1
  if (pinBlobUrl.value) URL.revokeObjectURL(pinBlobUrl.value)
})
</script>

<template>
  <div class="min-h-screen bg-[#f6f3ee] text-stone-900">
    <header class="border-b border-stone-200/80 bg-[#f6f3ee]/90 backdrop-blur sticky top-0 z-10">
      <div class="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-stone-500">Checkout</p>
          <h1 class="text-xl font-semibold tracking-tight">Thanh toán license</h1>
        </div>
        <RouterLink
          v-if="pinId"
          :to="{ name: 'pin', params: { id: String(pinId) } }"
          class="text-sm underline text-stone-600"
        >
          Về pin
        </RouterLink>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 py-8">
      <div v-if="loading" class="text-stone-500">Đang tải…</div>
      <div v-else-if="error" class="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
        {{ error }}
      </div>

      <div
        v-else-if="preview"
        class="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] items-start"
      >
        <section class="space-y-4">
          <div
            class="overflow-hidden rounded-3xl bg-stone-200 shadow-sm ring-1 ring-stone-900/5 min-h-[280px] flex items-center justify-center"
            :style="preview.pin?.rgb ? { backgroundColor: preview.pin.rgb } : {}"
          >
            <img
              v-if="pinBlobUrl"
              :src="pinBlobUrl"
              :alt="preview.pin?.title || 'Pin'"
              class="max-h-[520px] w-full object-contain bg-black/5"
            />
            <span v-else class="text-stone-500 text-sm">Không tải được ảnh</span>
          </div>
          <div>
            <h2
              class="text-2xl font-semibold"
              :style="preview.pin?.rgb ? { color: preview.pin.rgb } : {}"
            >
              {{ preview.pin?.title || `Pin #${preview.pin?.pin_id}` }}
            </h2>
            <p class="mt-1 text-stone-600 text-sm">
              License personal use · {{ formatListingPrice(preview.listing) }}
            </p>
            <p class="mt-3 text-sm text-stone-500">
              Thanh toán vào tài khoản chủ nền tảng (SePay). Tiền không chuyển thẳng cho seller.
            </p>
          </div>
        </section>

        <section
          class="rounded-3xl bg-white ring-1 ring-stone-900/5 shadow-sm p-6 space-y-5"
        >
          <div class="flex items-baseline justify-between gap-3">
            <h3 class="text-lg font-semibold">Đơn hàng</h3>
            <span
              class="text-xs px-2 py-1 rounded-full"
              :class="{
                'bg-amber-100 text-amber-900': phase === 'draft',
                'bg-sky-100 text-sky-900': phase === 'pending',
                'bg-emerald-100 text-emerald-900': phase === 'owned',
              }"
            >
              {{
                phase === 'draft'
                  ? 'Chờ thanh toán'
                  : phase === 'pending'
                    ? 'Chờ chuyển khoản'
                    : 'Đã sở hữu'
              }}
            </span>
          </div>

          <div class="space-y-1 text-sm">
            <div class="flex justify-between">
              <span class="text-stone-500">Giá listing</span>
              <strong>{{ formatListingPrice(preview.listing) }}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-stone-500">Số tiền CK (VND)</span>
              <strong>{{ formatVnd(preview.charge_amount_vnd) }}</strong>
            </div>
            <div v-if="expiresLabel && phase === 'pending'" class="flex justify-between text-amber-800">
              <span>Hết hạn</span>
              <span>{{ expiresLabel }}</span>
            </div>
          </div>

          <template v-if="phase === 'draft'">
            <p class="text-sm text-stone-600">
              Xác nhận để hiện thông tin chuyển khoản và mã QR.
            </p>
            <div class="flex flex-col gap-2">
              <button
                type="button"
                class="w-full rounded-2xl bg-stone-900 text-white py-3 text-sm font-medium hover:bg-black disabled:opacity-50"
                :disabled="confirming"
                @click="confirmPay"
              >
                {{ confirming ? 'Đang chuẩn bị…' : 'Thanh toán' }}
              </button>
              <button
                type="button"
                class="w-full rounded-2xl border border-stone-300 py-3 text-sm hover:bg-stone-50 disabled:opacity-50"
                :disabled="cancelling || confirming"
                @click="cancelFlow"
              >
                Hủy
              </button>
            </div>
          </template>

          <template v-else-if="phase === 'pending' && instr">
            <div class="space-y-3 text-sm border-t border-stone-100 pt-4">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-stone-500">Số tiền:</span>
                <strong>{{ formatVnd(instr.charge_amount_vnd) }}</strong>
                <button type="button" class="underline text-xs" @click="copyText(instr.charge_amount_vnd, 'số tiền')">
                  Copy
                </button>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-stone-500">Nội dung CK:</span>
                <code class="px-2 py-0.5 bg-stone-50 rounded border font-mono text-xs">
                  {{ instr.transfer_content || instr.payment_code }}
                </code>
                <button
                  type="button"
                  class="underline text-xs"
                  @click="copyText(instr.transfer_content || instr.payment_code, 'nội dung')"
                >
                  Copy
                </button>
              </div>
              <div v-if="instr.account_number" class="text-stone-700 leading-relaxed">
                Ngân hàng: {{ instr.bank_name || '—' }}<br />
                STK:
                <strong>{{ instr.account_number }}</strong>
                <button
                  type="button"
                  class="underline text-xs ml-2"
                  @click="copyText(instr.account_number, 'STK')"
                >
                  Copy
                </button>
                <br />
                Chủ TK: {{ instr.account_name || '—' }}
              </div>
              <p v-else class="text-red-700 text-xs">
                Platform chưa cấu hình STK nhận tiền.
              </p>
              <div v-if="instr.vietqr_image_url" class="flex flex-col sm:flex-row gap-3 items-start pt-1">
                <img
                  :src="instr.vietqr_image_url"
                  alt="VietQR"
                  class="w-44 h-44 object-contain bg-white border rounded-xl"
                />
                <a
                  :href="instr.vietqr_image_url"
                  target="_blank"
                  rel="noopener"
                  class="text-xs underline"
                >
                  Mở QR full size
                </a>
              </div>
              <p class="text-xs text-stone-500">
                Trang tự kiểm tra thanh toán mỗi 5 giây. Hãy giữ đúng nội dung chuyển khoản như hướng dẫn.
              </p>
            </div>
            <div class="flex flex-col gap-2 pt-1">
              <button
                v-if="preview.sepay_mock_enabled"
                type="button"
                class="w-full rounded-2xl border border-dashed border-stone-400 py-3 text-sm disabled:opacity-50"
                :disabled="mocking"
                @click="mockPay"
              >
                {{ mocking ? 'Processing…' : 'Simulate payment' }}
              </button>
              <button
                type="button"
                class="w-full rounded-2xl border border-stone-300 py-3 text-sm hover:bg-stone-50 disabled:opacity-50"
                :disabled="cancelling"
                @click="cancelFlow"
              >
                {{ cancelling ? 'Đang hủy…' : 'Hủy đơn' }}
              </button>
            </div>
          </template>

          <template v-else-if="phase === 'pending' && !instr">
            <p class="text-sm text-stone-600">Đang tải hướng dẫn thanh toán…</p>
            <button
              type="button"
              class="w-full rounded-2xl border border-stone-300 py-3 text-sm"
              @click="load"
            >
              Thử lại
            </button>
          </template>

          <template v-else-if="phase === 'owned'">
            <p class="text-sm text-emerald-800">
              Bạn đã có license. Quay lại pin để Download original.
            </p>
            <RouterLink
              v-if="pinId"
              :to="{ name: 'pin', params: { id: String(pinId) } }"
              class="block text-center w-full rounded-2xl bg-emerald-700 text-white py-3 text-sm font-medium"
            >
              Về pin
            </RouterLink>
          </template>
        </section>
      </div>
    </main>
  </div>
</template>
