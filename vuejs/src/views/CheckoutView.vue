<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import axios from 'axios'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'
import { authUserStore } from '@/stores/authUserStore'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const authStore = authUserStore()
const { t } = useI18n()

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
const phaseLabel = computed(() => {
  if (phase.value === 'draft') return t('checkout.statusDraft')
  if (phase.value === 'pending') return t('checkout.statusPending')
  return t('checkout.statusOwned')
})

function formatListingPrice(row) {
  if (!row) return ''
  return `${row.currency} ${(row.price_minor / 100).toFixed(2)}`
}

function formatVnd(n) {
  if (n == null) return '—'
  return `${Number(n).toLocaleString('vi-VN')} đ`
}

async function copyText(text, labelKey) {
  if (text == null || text === '') return
  try {
    await navigator.clipboard.writeText(String(text))
    toast.success(t('checkout.copied', { label: t(labelKey) }))
  } catch {
    toast.error(t('checkout.copyFailed'))
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
        toast.success(t('checkout.paySuccess'))
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
            error.value = typeof detail === 'string' ? detail : t('checkout.orderGone')
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
      ? t('checkout.adminCannotBuy')
      : t('checkout.orgCannotBuy')
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
          ? t('checkout.loadFailed')
          : t('checkout.loadFailed')
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
    // Stay on /checkout/pin/:id — avoid remount race that leaves UI stuck on preparing.
    toast.success(t('checkout.transferShown'))
    startPoll()
  } catch (e) {
    console.error(e)
    const detail = e.response?.data?.detail
    if (detail === 'email_not_verified') {
      toast.error(t('checkout.emailRequired'))
    } else {
      toast.error(typeof detail === 'string' ? detail : t('checkout.createFailed'))
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
      toast.success(t('checkout.cancelled'))
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
    toast.error(typeof detail === 'string' ? detail : t('checkout.cancelFailed'))
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
    toast.success(t('checkout.paySuccess'))
    await load()
  } catch (e) {
    console.error(e)
    toast.error(t('checkout.createFailed'))
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
    error.value = t('checkout.loginRequired')
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
      <div class="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-3 pr-28">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-stone-500">{{ t('checkout.eyebrow') }}</p>
          <h1 class="text-xl font-semibold tracking-tight">{{ t('checkout.title') }}</h1>
        </div>
        <RouterLink
          v-if="pinId"
          :to="{ name: 'pin', params: { id: String(pinId) } }"
          class="text-sm underline text-stone-600"
        >
          {{ t('checkout.backToPin') }}
        </RouterLink>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 py-8">
      <div v-if="loading" class="text-stone-500">{{ t('checkout.loading') }}</div>
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
            <span v-else class="text-stone-500 text-sm">{{ t('checkout.imageFailed') }}</span>
          </div>
          <div>
            <h2
              class="text-2xl font-semibold"
              :style="preview.pin?.rgb ? { color: preview.pin.rgb } : {}"
            >
              {{ preview.pin?.title || `Pin #${preview.pin?.pin_id}` }}
            </h2>
            <p class="mt-1 text-stone-600 text-sm">
              {{ t('checkout.licensePersonal', { price: formatListingPrice(preview.listing) }) }}
            </p>
            <p class="mt-3 text-sm text-stone-500">
              {{ t('checkout.payToPlatform') }}
            </p>
          </div>
        </section>

        <section
          class="rounded-3xl bg-white ring-1 ring-stone-900/5 shadow-sm p-6 space-y-5"
        >
          <div class="flex items-baseline justify-between gap-3">
            <h3 class="text-lg font-semibold">{{ t('checkout.order') }}</h3>
            <span
              class="text-xs px-2 py-1 rounded-full"
              :class="{
                'bg-amber-100 text-amber-900': phase === 'draft',
                'bg-sky-100 text-sky-900': phase === 'pending',
                'bg-emerald-100 text-emerald-900': phase === 'owned',
              }"
            >
              {{ phaseLabel }}
            </span>
          </div>

          <div class="space-y-1 text-sm">
            <div class="flex justify-between">
              <span class="text-stone-500">{{ t('checkout.listingPrice') }}</span>
              <strong>{{ formatListingPrice(preview.listing) }}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-stone-500">{{ t('checkout.transferAmount') }}</span>
              <strong>{{ formatVnd(preview.charge_amount_vnd) }}</strong>
            </div>
            <div v-if="expiresLabel && phase === 'pending'" class="flex justify-between text-amber-800">
              <span>{{ t('checkout.expires') }}</span>
              <span>{{ expiresLabel }}</span>
            </div>
          </div>

          <template v-if="phase === 'draft'">
            <p class="text-sm text-stone-600">
              {{ t('checkout.confirmHint') }}
            </p>
            <div class="flex flex-col gap-2">
              <button
                type="button"
                class="w-full rounded-2xl bg-stone-900 text-white py-3 text-sm font-medium hover:bg-black disabled:opacity-50"
                :disabled="confirming"
                @click="confirmPay"
              >
                {{ confirming ? t('checkout.preparing') : t('checkout.pay') }}
              </button>
              <button
                type="button"
                class="w-full rounded-2xl border border-stone-300 py-3 text-sm hover:bg-stone-50 disabled:opacity-50"
                :disabled="cancelling || confirming"
                @click="cancelFlow"
              >
                {{ t('checkout.cancel') }}
              </button>
            </div>
          </template>

          <template v-else-if="phase === 'pending' && instr">
            <div class="space-y-3 text-sm border-t border-stone-100 pt-4">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-stone-500">{{ t('checkout.amount') }}</span>
                <strong>{{ formatVnd(instr.charge_amount_vnd) }}</strong>
                <button type="button" class="underline text-xs" @click="copyText(instr.charge_amount_vnd, 'checkout.labelAmount')">
                  {{ t('common.copy') }}
                </button>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-stone-500">{{ t('checkout.transferContent') }}</span>
                <code class="px-2 py-0.5 bg-stone-50 rounded border font-mono text-xs">
                  {{ instr.transfer_content || instr.payment_code }}
                </code>
                <button
                  type="button"
                  class="underline text-xs"
                  @click="copyText(instr.transfer_content || instr.payment_code, 'checkout.labelMemo')"
                >
                  {{ t('common.copy') }}
                </button>
              </div>
              <div v-if="instr.account_number" class="text-stone-700 leading-relaxed">
                {{ t('checkout.bank', { name: instr.bank_name || '—' }) }}<br />
                {{ t('checkout.accountNumber') }}
                <strong>{{ instr.account_number }}</strong>
                <button
                  type="button"
                  class="underline text-xs ml-2"
                  @click="copyText(instr.account_number, 'checkout.labelAccount')"
                >
                  {{ t('common.copy') }}
                </button>
                <br />
                {{ t('checkout.accountName', { name: instr.account_name || '—' }) }}
              </div>
              <p v-else class="text-red-700 text-xs">
                {{ t('checkout.platformAccountMissing') }}
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
                  {{ t('checkout.openQrFull') }}
                </a>
              </div>
              <p class="text-xs text-stone-500">
                {{ t('checkout.pollHint') }}
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
                {{ mocking ? t('checkout.processing') : t('checkout.simulatePayment') }}
              </button>
              <button
                type="button"
                class="w-full rounded-2xl border border-stone-300 py-3 text-sm hover:bg-stone-50 disabled:opacity-50"
                :disabled="cancelling"
                @click="cancelFlow"
              >
                {{ cancelling ? t('checkout.cancelling') : t('checkout.cancelOrder') }}
              </button>
            </div>
          </template>

          <template v-else-if="phase === 'pending' && !instr">
            <p class="text-sm text-stone-600">{{ t('checkout.loadingInstructions') }}</p>
            <button
              type="button"
              class="w-full rounded-2xl border border-stone-300 py-3 text-sm"
              @click="load"
            >
              {{ t('common.retry') }}
            </button>
          </template>

          <template v-else-if="phase === 'owned'">
            <p class="text-sm text-emerald-800">
              {{ t('checkout.ownedHint') }}
            </p>
            <RouterLink
              v-if="pinId"
              :to="{ name: 'pin', params: { id: String(pinId) } }"
              class="block text-center w-full rounded-2xl bg-emerald-700 text-white py-3 text-sm font-medium"
            >
              {{ t('checkout.backToPin') }}
            </RouterLink>
          </template>
        </section>
      </div>
    </main>
  </div>
</template>
