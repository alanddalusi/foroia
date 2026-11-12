<script setup lang="ts">
import { analyticsEntry, analyticsLocation, publicAnalyticsPage } from '~/utils/analytics'
import { injectHead } from '#imports'
// Basic mode: Google receives no request before explicit opt-in.
const config = useRuntimeConfig().public
const route = useRoute()
const head = injectHead()
const id = String(config.ga4Id)
const enabled = Boolean(String(config.analyticsEnabled) === 'true' && /^G-[A-Z0-9]{6,20}$/.test(id) && config.legalName && config.legalAddress && config.legalTaxId)
const choice = ref(''); const open = ref(false)
const key = 'foroia-analytics-consent-v1'
let loaded = false
let entry: Record<string, string> = { page_referrer: '' }
let lastLocation = ''
const publicPage = () => publicAnalyticsPage(route.path)
function stored() {
  try {
    const value = JSON.parse(localStorage.getItem(key) || 'null')
    return value && typeof value.at === 'number' && Date.now() >= value.at && Date.now() - value.at < 180 * 86400000 && ['accepted', 'rejected'].includes(value.choice) ? value.choice : ''
  } catch { return '' }
}
function track() {
  if (!enabled || choice.value !== 'accepted' || !publicPage()) return
  const pageLocation = analyticsLocation(location.href)
  if (lastLocation === pageLocation) return
  const w = window as any
  w[`ga-disable-${id}`] = false
  w.dataLayer = w.dataLayer || []
  w.gtag = w.gtag || function () { w.dataLayer.push(arguments) }
  if (!loaded) {
    w.gtag('consent', 'default', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' })
    w.gtag('js', new Date())
    w.gtag('config', id, { send_page_view: false, cookie_expires: 15552000, cookie_update: false, allow_google_signals: false, allow_ad_personalization_signals: false, page_location: pageLocation, ...entry })
    const script = document.createElement('script')
    script.src = `https://www.googletagmanager.com/gtag/js?id=${id}`; script.async = true
    document.head.appendChild(script); loaded = true
  }
  w.gtag('event', 'page_view', { page_location: pageLocation, page_title: document.title, page_referrer: lastLocation || entry.page_referrer })
  lastLocation = pageLocation
}
function decide(value: string) {
  choice.value = value; open.value = false
  try { localStorage.setItem(key, JSON.stringify({ choice: value, at: Date.now() })) } catch { /* consent is session-only when storage is unavailable */ }
  if (value === 'accepted') track()
  else if (loaded) {
    ;(window as any)[`ga-disable-${id}`] = true
    for (const cookie of document.cookie.split(';')) {
      const name = cookie.split('=')[0]?.trim() || ''
      if (!/^_ga(?:_|$)/.test(name)) continue
      document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax; Secure`
      document.cookie = `${name}=; Max-Age=0; Path=/; Domain=${location.hostname}; SameSite=Lax; Secure`
    }
    location.reload()
  }
}
onMounted(() => {
  if (!enabled) return
  // Memory only until opt-in; no session/local storage for acquisition data.
  entry = analyticsEntry(document.referrer, location.href)
  choice.value = stored(); open.value = !choice.value; track()
})
// Head rendering is asynchronous; measure after the new title is committed.
const removeHeadHook = head.hooks?.hook('dom:rendered', () => {
  if (import.meta.client) track()
})
onBeforeUnmount(() => removeHeadHook?.())
watch(() => route.fullPath, async () => {
  if (!import.meta.client || !enabled) return
  ;(window as any)[`ga-disable-${id}`] = !publicPage() || choice.value !== 'accepted'
}, { flush: 'post' })
</script>
<template>
  <ClientOnly v-if="enabled">
    <section v-if="open" class="consent-panel" aria-labelledby="consent-title">
      <h2 id="consent-title">Analítica opcional</h2><p>Si aceptas, Google Analytics medirá el uso de las páginas públicas. Puedes leer sin aceptar y cambiar tu decisión aquí. <NuxtLink to="/informacion/cookies">Más información</NuxtLink>.</p>
      <div class="editor-bar"><button type="button" class="secondary" @click="decide('rejected')">Rechazar analítica</button><button type="button" class="secondary" @click="decide('accepted')">Aceptar analítica</button></div>
    </section>
    <button v-else type="button" class="secondary consent-settings" @click="open = true">Preferencias de analítica</button>
  </ClientOnly>
</template>
<style scoped>
.consent-panel { position:fixed;bottom:0;left:0;right:0;background:var(--paper);border-top:2px solid var(--ink);padding:20px;z-index:20;max-height:70vh;overflow:auto;box-shadow:0 -4px 24px #0002 }
.consent-panel h2 { font-size:24px }.consent-panel p { max-width:80ch }.consent-settings { margin:12px 20px }
</style>
