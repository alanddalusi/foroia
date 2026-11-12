<script setup lang="ts">
import { accountHeaders } from '~/utils/account'
import { researchRunLabel, researchRunReason, researchDayNotice } from '~/utils/research-status'
interface TopicSelection { selected_organizations: string[]; generation_calls_avoided: number; rejected_candidates: number; candidates: { topic_id: string; title: string; organizations: string[]; status: string; reason: string }[]; excluded_documents: { url: string; reason: string }[] }
interface WebDiagnostic { state?: string; reason?: string; accounted_microusd?: number; cost_basis?: string; research_status?: string; search_summary?: string; empty_reason?: string; invalid_candidates?: { index: number; reason: string }[]; provider_discarded?: { title: string; reason: string; urls?: string[] }[] }
interface SourceDiagnostic { url: string; stage: string; code: string; reason: string; http_status?: number | null }
interface EventSearch { method: string; status: string; query?: string; index_url?: string; found_urls?: string[]; matching_links?: number; actual_queries?: string[]; reason?: string; accounted_microusd?: number; queries?: { title: string; official_query: string; independent_query: string }[] }
interface Run { id: number; phase_usage?: { stage: string; accounted_microusd: number; reported_calls: number }[]; date: string; status: string; reason: string; finished_at?: string | null; article_id: number | null; reserved_usd: string; report: { manual_news_retry?: { result?: { status: string; reason: string; new_article_id: number | null } }; web_discovery?: { event_searches?: EventSearch[]; opportunities?: { title: string; reason_for_decision: string; diagnostics?: SourceDiagnostic[]; verified_source_urls?: string[]; urls: string[]; candidate_ids: number[]; reason: string }[] }; web_research?: WebDiagnostic; publications?: { article_id: number; candidate_id: number; url?: string }[]; editorial_version?: number; engine?: string; news_statistics?: { candidate_count?: number; fetch_failures?: number }; candidate_attempts?: { candidate_id: number; engine: string; reason: string; reserved_microusd?: number }[]; selection?: TopicSelection; candidate_count?: number; fetch_failures?: number; fetch_errors?: { url: string; stage: string; code: string; http_status?: number }[]; source_organizations?: string[]; corrections_used?: number; review?: { reasons: string[] } } }
interface Opportunity { primary_keyword: string; semantic_variants: string[]; related_questions: string[]; target_countries: string[]; cannibalization_risk: string; assessed_at: string; unavailable_reason: string; related_content: { url: string; title: string }[] }
interface QueueItem { verification_mode?: string | null }
interface TopicSelection { verification_mode?: string | null }
interface Opportunity { assessment?: { practical_application: string | null; site_coverage: { related_published_articles: number; basis: string }; originality: { status: string; basis: string }; traffic_potential: { status: string; basis: string }; freshness: { status: string }; example_id: string | null; requires_editorial_reframing: boolean } }
interface QueueItem { queue_audit?: { decision: string; merged_into_candidate_id?: number | null } | null }
interface QueueItem { recovery?: { kind: string; recoverable: boolean; reason: string; technical_code: string; corrections_used: number; correction_limit: number; has_saved_draft: boolean; automatic_recoveries: number; next_attempt_at?: string | null; review_reasons: string[] } }
interface Research { editorial_target?: { news: number; practical: number; total: number; active: boolean }; queue_truncated?: boolean }
interface Run { lanes?: { engine: string; slot: number; status: string; reason: string; candidate_id: number | null; article_id: number | null; reported_cost_microusd?: number | null; report: Run['report'] }[] }
interface Research { content_counts?: { published_articles: number; verified_published_articles: number; completed_manual_executions: number; verified_publication_events: number } }
interface QueueItem { id: number; topic: string; engine: string; kind: string; section: string; intent: string; keyword: string; priority: number; state: string; reason: string; attempts: number; article_url: string | null; source_count: number; source_urls?: string[]; demand_source?: string; unreported_usage_calls?: number; opportunity?: Opportunity; reserved_microusd?: number; usage_events?: { input_tokens: number; output_tokens: number; estimated_microusd: number }[] }
interface Health { checked_at: string; alerts: string[]; last_publication_at: string | null; notification_channel: string; seo: { sitemap_urls: number | null; sitemap_files: number | null; sampled_articles: number; published_articles: number; all_articles_checked: boolean; sitemap_scope?: string } }
interface Research { enabled: boolean; configured: boolean; worker_alive: boolean; model: string; at: string; timezone: string; auto_publish: boolean; monthly_usd: string; daily_usd: string; reserved_usd: string; feeds: string[]; runs: Run[]; next_execution?: string; queue?: QueueItem[]; queue_counts?: Record<string, number>; health?: Health; daily_reserved_usd?: string; remaining_reservation_usd?: { monthly: string; daily: string }; reported_usage?: { input_tokens: number; output_tokens: number; estimated_usd: string; billing_verified: boolean; reported_calls?: number; cached_input_tokens?: number } }
useSeoMeta({ title: 'Investigación diaria | ForoIA', robots: 'noindex, nofollow' })
const { data, error, refresh } = useFetch<Research>('/api/editorial/research', { server: false })
const busy = ref(false)
interface Execution { id: number; state: string; reason: string; stage: string; max_usd: string; max_microusd: number; reserved_usd: string; quote_digest: string; expires_at: string; candidate_id: number; stages: { stage: string; state: string; reason?: string }[]; failure?: { code: string; details: unknown[] } }
const executions = computed(() => (data.value as (Research & { executions?: Execution[] }) | null)?.executions || [])
async function prepareExecution() {
  if (busy.value) return
  busy.value = true; message.value = ''
  try {
    await $fetch('/api/editorial/research/executions', { method: 'POST', headers: accountHeaders(), body: { mode: 'auto', request_key: crypto.randomUUID() } })
    await refresh(); message.value = 'Preparación sin llamadas de pago solicitada. Espera el presupuesto antes de confirmar.'
  } catch { message.value = 'No se pudo preparar: comprueba si ya existe una ejecución pendiente.' }
  finally { busy.value = false }
}
async function executionAction(job: Execution, action: 'confirm' | 'cancel') {
  if (busy.value) return
  busy.value = true; message.value = ''
  try {
    await $fetch(`/api/editorial/research/executions/${job.id}/${action}`, { method: 'POST', headers: accountHeaders(), ...(action === 'confirm' ? { body: { quote_digest: job.quote_digest, max_microusd: job.max_microusd } } : {}) })
    await refresh(); message.value = action === 'confirm' ? 'Autorización registrada. El trabajador ejecutará las etapas pendientes.' : 'Solicitud cancelada.'
  } catch { message.value = 'No se pudo completar: comprueba la pausa y la caducidad del presupuesto; actualiza el panel.' }
  finally { busy.value = false }
}
const message = ref('')
const now = ref(new Date())
const dayNotice = computed(() => data.value ? researchDayNotice(data.value.runs, now.value, data.value.at) : '')
const queueStates: Record<string, string> = { queued: 'En cola', preparing: 'Comprobando fuentes', ready: 'Preparado', generating: 'Redactando', published: 'Publicado', rejected: 'Descartado definitivamente', deferred: 'Pospuesto', needs_verification: 'Verificando publicación', correction_pending: 'Pendiente de corrección', budget_pending: 'Pendiente de presupuesto', publication_error: 'Error técnico de publicación', technical_error: 'Error técnico: diagnóstico necesario' }
const queueState = (state: string) => queueStates[state] || state
const editorialChecks = (run: Run) => (run.report as { editorial_style?: { checks?: Record<string, boolean> } }).editorial_style?.checks
const editorialCheckLabels: Record<string,string> = { natural: 'Español natural', non_repetitive: 'Sin redundancias', well_structured: 'Estructura proporcionada', attribution_clear: 'Atribución clara' }
const candidateReason = (reason: string) => reason ? researchRunReason({ status: 'skipped', reason }) : ''
// Resumen legible de la cola: agrupa estados técnicos en cuatro categorías.
type Bucket = 'pending' | 'published' | 'rejected' | 'merged'
const PENDING_STATES = ['queued', 'preparing', 'ready', 'generating', 'deferred', 'needs_verification', 'correction_pending', 'budget_pending', 'publication_error', 'technical_error']
const bucketOf = (c: QueueItem): Bucket => c.state === 'published' ? 'published'
  : PENDING_STATES.includes(c.state) ? 'pending'
  : c.queue_audit?.merged_into_candidate_id || c.reason === 'documentation_topic_merged' ? 'merged' : 'rejected'
const bucketLabels: Record<Bucket, string> = { pending: 'Pendientes', published: 'Publicados', rejected: 'Descartados', merged: 'Agrupados' }
const BUCKETS: Bucket[] = ['pending', 'published', 'rejected', 'merged']
const filter = ref<Bucket | 'all'>('pending')
const queueBuckets = computed(() => {
  const result: Record<Bucket, QueueItem[]> = { pending: [], published: [], rejected: [], merged: [] }
  for (const c of data.value?.queue || []) result[bucketOf(c)].push(c)
  return result
})
const visibleQueue = computed(() => filter.value === 'all'
  ? (data.value?.queue || []).filter(c => bucketOf(c) !== 'merged')
  : queueBuckets.value[filter.value])
const laneCount = (bucket: Bucket, engine: string) => queueBuckets.value[bucket].filter(c => c.engine === engine).length
const candidateCost = (c: QueueItem) => (c.usage_events || []).reduce((t, e) => t + e.estimated_microusd, 0) / 1_000_000
const usedPercent = (reserved?: string, limit?: string) => {
  const r = Number(reserved || 0), l = Number(limit || 0)
  return l > 0 ? Math.min(100, Math.round(r / l * 100)) : 0
}
const runTone = (run: Run) => run.status === 'published' ? 'ok' : run.status === 'running' ? 'info' : 'warn'
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    now.value = new Date()
    if (!document.hidden) void refresh()
  }, 30_000)
})
onBeforeUnmount(() => clearInterval(timer))

async function toggle() {
  if (!data.value || busy.value) return
  busy.value = true; message.value = ''
  try {
    await $fetch('/api/editorial/research', { method: 'PATCH', body: { enabled: !data.value.enabled }, headers: accountHeaders() })
    await refresh(); message.value = data.value?.enabled ? 'Investigación activada.' : 'Investigación pausada. Las llamadas ya enviadas pueden tener coste.'
  } catch { message.value = 'No se pudo cambiar el estado. Inténtalo de nuevo.' }
  finally { busy.value = false }
}
</script>
<template>
  <div>
    <NuxtLink to="/editorial">Volver al panel editorial</NuxtLink>
    <header class="editor-bar"><h1>Investigación diaria</h1><button type="button" class="secondary" @click="refresh()">Actualizar</button></header>
    <p v-if="error" class="notice error" role="alert">No se pudo consultar la investigación. Comprueba tu sesión y vuelve a intentarlo.</p>
    <template v-else-if="data">
      <p v-if="!data.configured" class="notice">Pendiente de configurar la clave del proveedor. No se están generando artículos ni realizando llamadas de pago.</p>
      <p v-if="!data.worker_alive" class="notice error" role="alert">El trabajador no ha enviado señal en los últimos 90 segundos. Comprueba que el servicio esté encendido.</p>

      <section class="rs-status" aria-label="Estado de la investigación">
        <span class="rs-pill" :class="data.enabled ? 'ok' : 'warn'">{{ data.enabled ? 'Activada' : 'Pausada' }}</span>
        <span class="rs-pill" :class="data.worker_alive ? 'ok' : 'bad'">Trabajador {{ data.worker_alive ? 'activo' : 'sin señal' }}</span>
        <span v-if="data.next_execution">Próxima ejecución: <strong>{{ new Date(data.next_execution).toLocaleString('es-ES', { timeZone: 'Europe/Madrid', dateStyle: 'medium', timeStyle: 'short' }) }}</strong> (Madrid)</span>
        <button type="button" class="secondary" :disabled="busy" @click="toggle()">{{ data.enabled ? 'Pausar' : 'Reanudar' }}</button>
      </section>
      <p v-if="message" role="status" class="notice">{{ message }}</p>
      <p v-if="data.enabled && data.configured" class="notice" role="status">{{ dayNotice }}</p>
      <p v-if="data.editorial_target?.active">Objetivo diario: hasta {{ data.editorial_target.total }} publicaciones válidas: {{ data.editorial_target.news }} noticia y {{ data.editorial_target.practical }} artículos prácticos. Cada línea conserva su resultado; no se publican textos para completar una cuota.</p>

      <section aria-labelledby="rs-summary">
        <h2 id="rs-summary" class="rs-h2">Resumen de la cola</h2>
        <div class="rs-kpis">
          <button v-for="b in BUCKETS" :key="b" type="button"
                  class="rs-kpi" :class="[b, { active: filter === b }]" :aria-pressed="filter === b" @click="filter = b">
            <span class="rs-kpi-n">{{ queueBuckets[b].length }}</span>
            <span class="rs-kpi-l">{{ bucketLabels[b] }}</span>
            <span v-if="b !== 'merged'" class="rs-kpi-s">Noticias {{ laneCount(b, 'news') }} · Prácticos {{ laneCount(b, 'evergreen') }}</span>
            <span v-else class="rs-kpi-s">Integrados en otros temas</span>
          </button>
        </div>
        <p v-if="data.content_counts" class="muted">Artículos publicados en la web: <strong>{{ data.content_counts.published_articles }}</strong> ({{ data.content_counts.verified_published_articles }} con verificación del trabajador).</p>
      </section>

      <section aria-labelledby="rs-budget">
        <h2 id="rs-budget" class="rs-h2">Presupuesto</h2>
        <div class="rs-budget">
          <div>
            <div class="rs-bar-label"><span>Hoy</span><span>{{ data.daily_reserved_usd ?? '—' }} / {{ data.daily_usd }} USD</span></div>
            <div class="rs-bar" role="progressbar" :aria-valuenow="usedPercent(data.daily_reserved_usd, data.daily_usd)" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: usedPercent(data.daily_reserved_usd, data.daily_usd) + '%' }" /></div>
            <small class="muted">Disponible: {{ data.remaining_reservation_usd?.daily ?? '—' }} USD</small>
          </div>
          <div>
            <div class="rs-bar-label"><span>Este mes</span><span>{{ data.reserved_usd }} / {{ data.monthly_usd }} USD</span></div>
            <div class="rs-bar" role="progressbar" :aria-valuenow="usedPercent(data.reserved_usd, data.monthly_usd)" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: usedPercent(data.reserved_usd, data.monthly_usd) + '%' }" /></div>
            <small class="muted">Disponible: {{ data.remaining_reservation_usd?.monthly ?? '—' }} USD</small>
          </div>
        </div>
        <p v-if="data.reported_usage?.reported_calls" class="muted">Coste calculado este mes: <strong>{{ data.reported_usage.estimated_usd }} USD</strong> en {{ data.reported_usage.reported_calls }} llamadas ({{ data.model }}). Estimación con tarifas registradas, no la factura.</p>
      </section>

      <details class="rs-help"><summary>Cómo funciona la investigación diaria</summary>
        <p>Cada día a las {{ data.at }} ({{ data.timezone }}) se ejecutan dos líneas independientes: una noticia de IA y un artículo práctico. Si una falla, la otra continúa. {{ data.auto_publish ? 'Se publica automáticamente lo que supera los controles.' : 'Los artículos quedan en revisión.' }} Los descartados no se publican.</p>
        <p>Si detecta errores corregibles, intenta una corrección automática y vuelve a revisar antes de publicar. Cada llamada respeta el mismo presupuesto.</p>
        <p>Las reservas incluyen llamadas pendientes o de coste incierto; las de fechas anteriores cuentan para el mes. La factura se consulta en el proveedor.</p>
        <p v-if="data.reported_usage?.reported_calls">Tokens este mes: {{ data.reported_usage.input_tokens }} de entrada ({{ data.reported_usage.cached_input_tokens }} en caché) y {{ data.reported_usage.output_tokens }} de salida.</p>
        <p>Investigación con OpenAI y búsqueda web: noticias de las últimas 24 horas, ampliables hasta 48; las fuentes se descargan y verifican antes de redactar.</p>
        <p class="muted">El panel se actualiza cada 30 segundos mientras está visible.</p>
      </details>
      <h2>Ejecución manual y recuperación</h2>
      <p>Primero se comprueban las fuentes y el borrador guardado sin llamar al modelo. Después debes autorizar el máximo indicado. Comparte los límites diarios y mensuales, el bloqueo y los controles de calidad de la programación diaria.</p>
      <button type="button" :disabled="busy || executions.some(j => ['preparing','awaiting_approval','queued','running'].includes(j.state))" @click="prepareExecution()">Preparar ejecución sin gasto</button>
      <article v-for="job in executions" :key="job.id" class="research-run">
        <h3>Ejecución {{ job.id }} · {{ job.state }}</h3>
        <p>Etapa: {{ job.stage || 'preparación' }}. Motivo: {{ job.reason || 'sin errores registrados' }}.</p>
        <p>Máximo autorizado: {{ job.max_usd }} USD. Reservado: {{ job.reserved_usd }} USD.</p>
        <ul v-if="job.stages.length"><li v-for="(stage, i) in job.stages" :key="i">{{ stage.stage }}: {{ stage.state }} {{ stage.reason || '' }}</li></ul>
        <pre v-if="job.failure" tabindex="0" aria-label="Detalle del fallo">{{ JSON.stringify(job.failure, null, 2) }}</pre>
        <template v-if="job.state === 'awaiting_approval'">
          <p>Caduca: {{ new Date(job.expires_at).toLocaleString('es-ES', { timeZone: 'Europe/Madrid' }) }}.</p>
          <button type="button" :disabled="busy || !data.enabled" @click="executionAction(job, 'confirm')">Autorizar hasta {{ job.max_usd }} USD y ejecutar</button>
        </template>
        <button v-if="['awaiting_approval','queued'].includes(job.state)" type="button" class="secondary" :disabled="busy" @click="executionAction(job, 'cancel')">Cancelar solicitud</button>
      </article>
      <h2>Supervisión editorial y SEO</h2>
      <template v-if="data.health">
        <p>Última comprobación: {{ new Date(data.health.checked_at).toLocaleString('es-ES', { timeZone: 'Europe/Madrid' }) }}. Última publicación registrada: {{ data.health.last_publication_at ? new Date(data.health.last_publication_at).toLocaleString('es-ES', { timeZone: 'Europe/Madrid' }) : 'sin publicaciones registradas' }}.</p>
        <p v-if="now.getTime() - new Date(data.health.checked_at).getTime() > 900000" class="notice error" role="alert">La comprobación lleva más de quince minutos sin actualizarse. Revisa el servicio de salud.</p>
        <ul v-if="data.health.alerts.length" class="notice"><li v-for="alert in data.health.alerts" :key="alert">{{ candidateReason(alert) }} <code>{{ alert }}</code></li></ul>
        <p v-else>Sin incidencias en la última comprobación. Las verificaciones de artículos son una muestra rotativa.</p>
        <p>URLs contadas en sitemaps: {{ data.health.seo.sitemap_urls ?? 'dato no disponible' }} en {{ data.health.seo.sitemap_files ?? '—' }} archivos comprobados. Artículos revisados en esta muestra: {{ data.health.seo.sampled_articles }} de {{ data.health.seo.published_articles }} publicados. {{ data.health.seo.sitemap_scope === 'first_four_files' ? 'Recuento parcial: primeros cuatro archivos.' : '' }}</p>
        <p class="muted">El sitemap no demuestra indexación en Google. Las incidencias quedan en el panel y en los registros del servidor; no hay avisos externos configurados.</p>
      </template>
      <p v-else class="notice">La supervisión todavía no tiene un informe reciente. Esto no confirma que todo esté correcto.</p>
      <h2 id="rs-queue">Cola editorial</h2>
      <p v-if="data.queue_truncated" class="notice">La lista muestra los primeros 100 candidatos por estado y prioridad; los totales del servidor pueden incluir más registros.</p>
      <p v-if="!data.queue?.length" class="empty">La cola se prepara automáticamente al iniciar la siguiente investigación.</p>
      <div v-else class="rs-tabs" role="group" aria-labelledby="rs-queue">
        <button v-for="b in BUCKETS" :key="b" type="button" :class="{ active: filter === b }" :aria-pressed="filter === b" @click="filter = b">{{ bucketLabels[b] }} ({{ queueBuckets[b].length }})</button>
        <button type="button" :class="{ active: filter === 'all' }" :aria-pressed="filter === 'all'" @click="filter = 'all'">Todos</button>
      </div>
      <p v-if="data.queue?.length && !visibleQueue.length" class="empty">No hay temas en esta categoría.</p>
      <ul v-if="filter === 'merged' && visibleQueue.length" class="rs-merged">
        <li v-for="candidate in visibleQueue" :key="candidate.id">{{ candidate.topic }} <span class="muted">→ integrado en #{{ candidate.queue_audit?.merged_into_candidate_id ?? '—' }}</span></li>
      </ul>
      <template v-else>
      <article v-for="candidate in visibleQueue" :key="candidate.id" class="rs-card" :class="bucketOf(candidate)">
        <header class="rs-card-head">
          <span class="rs-pill" :class="bucketOf(candidate) === 'published' ? 'ok' : bucketOf(candidate) === 'pending' ? 'info' : 'bad'">{{ queueState(candidate.state) }}</span>
          <span class="rs-tag">{{ candidate.engine === 'news' ? 'Noticia' : 'Práctico' }}</span>
          <span class="muted">#{{ candidate.id }} · {{ candidate.source_count }} fuentes · {{ candidate.attempts }} intentos<template v-if="candidate.usage_events?.length"> · {{ candidateCost(candidate).toFixed(4) }} USD</template></span>
        </header>
        <h3>{{ candidate.topic }}</h3>
        <p v-if="candidate.reason && bucketOf(candidate) !== 'published'" class="rs-reason">{{ candidateReason(candidate.reason) }} <code>{{ candidate.reason }}</code></p>
        <div v-if="candidate.recovery && bucketOf(candidate) !== 'published'">
          <p>Diagnóstico: <code>{{ candidate.recovery.technical_code }}</code>. {{ candidate.recovery.recoverable ? 'Recuperación automática disponible.' : candidate.state === 'technical_error' ? 'Recuperación automática detenida para evitar cambios inseguros o cobros inciertos.' : '' }}</p>
          <p>Correcciones: {{ candidate.recovery.corrections_used }} de {{ candidate.recovery.correction_limit }}. {{ candidate.recovery.has_saved_draft ? 'Borrador conservado para reutilizarlo.' : 'Sin borrador reutilizable conservado.' }}</p>
          <p v-if="candidate.recovery.next_attempt_at">Disponible a partir de {{ new Date(candidate.recovery.next_attempt_at).toLocaleString('es-ES', { timeZone: 'Europe/Madrid' }) }}; se procesa en el turno programado según prioridad y presupuesto.</p>
          <ul v-if="candidate.recovery.review_reasons.length"><li v-for="(reason, index) in candidate.recovery.review_reasons" :key="index">{{ reason }}</li></ul>
        </div>
        <NuxtLink v-if="candidate.article_url" :to="candidate.article_url" class="rs-link">Leer publicación →</NuxtLink>
        <details class="rs-more"><summary>Detalles</summary>
        <p v-if="candidate.verification_mode === 'official_announcement'">Anuncio oficial verificado · Las afirmaciones se atribuyen a la organización.</p>
        <p v-else-if="candidate.verification_mode === 'independently_corroborated'">Noticia corroborada por varias organizaciones.</p>
        <p v-if="candidate.state === 'ready' && candidate.attempts === 0" class="muted">Fuentes comprobadas durante la preparación, sin generar texto ni hacer llamadas de pago. Se procesará en una ejecución programada según prioridad y presupuesto.</p>
        <p v-if="candidate.unreported_usage_calls" class="notice">{{ candidate.unreported_usage_calls }} llamadas sin datos de uso válidos. Consumo desconocido; se conservan sus reservas.</p>
        <p>{{ candidate.intent }}</p>
        <p v-if="candidate.usage_events?.length">Coste calculado sobre el uso comunicado de este candidato: {{ candidateCost(candidate).toFixed(6) }} USD. No es facturación confirmada.</p>
        <p v-if="candidate.reserved_microusd">Reservas atribuidas en las últimas catorce ejecuciones: {{ (candidate.reserved_microusd / 1000000).toFixed(6) }} USD.</p>
        <details v-if="candidate.opportunity"><summary>Ficha de oportunidad SEO</summary>
          <p>Consulta objetivo propuesta: {{ candidate.opportunity.primary_keyword }}. Riesgo de solapamiento estimado localmente: {{ candidate.opportunity.cannibalization_risk }}.</p>
          <p v-if="candidate.opportunity.assessment?.practical_application">Necesidad del lector: {{ candidate.opportunity.assessment.practical_application }}</p>
          <p v-if="candidate.opportunity.assessment">{{ candidate.opportunity.assessment.site_coverage.basis }} {{ candidate.opportunity.assessment.traffic_potential.basis }}</p>
          <p v-if="candidate.opportunity.assessment?.example_id">Ejemplo reproducible previsto: {{ candidate.opportunity.assessment.example_id }}. Su comprobación se exige al preparar el artículo.</p>
          <p v-if="candidate.opportunity.semantic_variants.length">Variantes de vocabulario: {{ candidate.opportunity.semantic_variants.join(', ') }}.</p>
          <p v-if="candidate.opportunity.related_questions.length">Preguntas propuestas: {{ candidate.opportunity.related_questions.join(' ') }}.</p>
          <p>Audiencia en español internacional: {{ candidate.opportunity.target_countries.join(', ') }} y otros países hispanohablantes. No se generan copias regionales.</p>
          <p>{{ candidate.opportunity.unavailable_reason }}</p>
          <ul v-if="candidate.opportunity.related_content.length"><li v-for="related in candidate.opportunity.related_content" :key="related.url"><NuxtLink :to="related.url">{{ related.title }}</NuxtLink></li></ul>
        </details>
        <p class="muted">{{ candidate.demand_source === 'search_console_export' ? 'Prioridad apoyada en un informe importado de Search Console.' : candidate.engine === 'news' ? 'Oportunidad detectada en fuentes de noticias.' : 'Hipótesis editorial basada en documentación; sin volumen de búsqueda medido.' }}</p>
        <p v-if="candidate.queue_audit?.merged_into_candidate_id">Material agrupado con el candidato #{{ candidate.queue_audit.merged_into_candidate_id }}; no se ha eliminado la propuesta ni su fuente.</p>
        <details v-if="candidate.source_urls?.length"><summary>Fuentes del candidato</summary><ul><li v-for="url in candidate.source_urls" :key="url"><a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a></li></ul></details>
        </details>
      </article>
      </template>
      <p><NuxtLink to="/editorial/estadisticas">Consultar visitas y publicaciones</NuxtLink></p>
      <h2>Últimos 14 días con ejecuciones</h2>
      <p v-if="!data.runs.length" class="empty">Todavía no hay investigaciones. El trabajador necesita estar encendido a la hora programada.</p>
      <article v-for="run in data.runs" :key="run.id" class="rs-card">
        <header class="rs-card-head">
          <span class="rs-pill" :class="runTone(run)">{{ researchRunLabel(run) }}</span>
          <strong>{{ run.date }}</strong>
          <span class="muted">Reserva {{ run.reserved_usd }} USD<template v-if="run.report.publications?.length"> · {{ run.report.publications.length }} publicación(es)</template></span>
        </header>
        <p>{{ researchRunReason(run) }}</p>
        <section v-if="run.lanes?.length" aria-label="Resultado de cada línea editorial">
          <article v-for="lane in run.lanes" :key="`${lane.engine}-${lane.slot}`">
            <h3>{{ lane.engine === 'news' ? 'Actualidad' : `Práctico ${lane.slot}` }}: {{ researchRunLabel(lane) }}</h3>
            <p>{{ candidateReason(lane.reason) }} <code>{{ lane.reason }}</code><template v-if="lane.article_id"> · Artículo #{{ lane.article_id }}</template></p>
            <p v-if="lane.reported_cost_microusd != null">Coste calculado de redacción y revisión de esta línea: {{ (lane.reported_cost_microusd / 1000000).toFixed(6) }} USD. La investigación compartida se contabiliza aparte; factura no verificada.</p>
            <ul v-if="lane.report.candidate_attempts?.length"><li v-for="(attempt, index) in lane.report.candidate_attempts" :key="index">Candidato #{{ attempt.candidate_id }}: {{ candidateReason(attempt.reason) }} <code>{{ attempt.reason }}</code></li></ul>
          </article>
        </section>
        <NuxtLink v-if="run.article_id" :to="`/editorial/${run.article_id}`" class="rs-link">Abrir artículo →</NuxtLink>
        <details class="rs-more"><summary>Detalles de la ejecución</summary>
        <p v-if="run.report.web_research">Búsqueda web: {{ run.report.web_research.state }} · {{ run.report.web_research.reason || run.report.web_research.cost_basis || 'pendiente' }}. Coste calculado: {{ run.report.web_research.accounted_microusd === undefined ? 'desconocido' : (run.report.web_research.accounted_microusd / 1000000).toFixed(6) + ' USD' }}.</p>
        <p v-if="run.report.web_research?.search_summary">Investigación: {{ run.report.web_research.search_summary }}</p>
        <p v-if="run.report.web_research?.research_status === 'empty' || run.report.web_research?.research_status === 'invalid'" class="notice" role="status">La investigación no encontró candidatas válidas: {{ run.report.web_research.empty_reason || candidateReason(run.report.web_research.reason || '') }}.</p>
        <ul v-if="run.report.web_research?.invalid_candidates?.length"><li v-for="item in run.report.web_research.invalid_candidates" :key="item.index">Propuesta {{ item.index + 1 }}: {{ candidateReason(item.reason) }}</li></ul>
        <details v-if="run.report.web_research?.provider_discarded?.length"><summary>Resultados descartados por la investigación</summary><ul><li v-for="(item, i) in run.report.web_research.provider_discarded" :key="i">{{ item.title }}: {{ item.reason }}</li></ul></details>
        <p v-if="run.report.manual_news_retry?.result">Prueba adicional de noticias: {{ run.report.manual_news_retry.result.reason }}. Nueva publicación: {{ run.report.manual_news_retry.result.new_article_id || 'ninguna' }}.</p>
        <ul v-if="run.phase_usage?.length"><li v-for="phase in run.phase_usage" :key="phase.stage">{{ phase.stage }}: {{ phase.reported_calls }} llamadas, {{ (phase.accounted_microusd / 1000000).toFixed(6) }} USD calculados según uso comunicado; factura no verificada.</li></ul>
        <details v-if="run.report.web_discovery?.event_searches?.length"><summary>Búsquedas alternativas por acontecimiento</summary>
          <article v-for="(search, index) in run.report.web_discovery.event_searches" :key="index">
            <h4>{{ search.method === 'official_index_local_query' ? 'Consulta de índice oficial' : 'Búsqueda web alternativa' }}</h4>
            <p v-if="search.query">Consulta: {{ search.query }}</p>
            <p v-if="search.index_url">Índice: {{ search.index_url }}</p>
            <ul v-if="search.queries?.length"><li v-for="query in search.queries" :key="query.title">{{ query.title }}: {{ query.official_query }} · {{ query.independent_query }}</li></ul>
            <p>Estado: {{ search.status }}<span v-if="search.reason"> · {{ candidateReason(search.reason) }}</span></p>
            <ul v-if="search.found_urls?.length"><li v-for="url in search.found_urls" :key="url">{{ url }}</li></ul>
            <p v-if="search.actual_queries?.length">Consultas comunicadas por la herramienta: {{ search.actual_queries.join(' · ') }}</p>
            <p v-if="search.accounted_microusd != null">Coste calculado según uso comunicado: {{ (search.accounted_microusd / 1000000).toFixed(6) }} USD; factura no verificada.</p>
          </article>
        </details>
        <details v-if="run.report.web_discovery?.opportunities?.length"><summary>Noticias investigadas y decisiones</summary><article v-for="(item, index) in run.report.web_discovery.opportunities" :key="index">
          <h4>{{ item.title }}</h4><p>{{ item.reason }}</p>
          <p>{{ candidateReason(item.reason_for_decision) }} · Candidatos: {{ item.candidate_ids.join(', ') || 'ninguno' }}</p>
          <ul><li v-for="url in item.urls" :key="url">{{ url }}</li></ul>
          <p v-if="item.verified_source_urls?.length">Documentos verificados: {{ item.verified_source_urls.length }}.</p>
          <ul v-if="item.diagnostics?.length"><li v-for="(diagnostic, d) in item.diagnostics" :key="d">
            {{ candidateReason(diagnostic.reason) }} <code>{{ diagnostic.code }}</code>
            <span v-if="diagnostic.http_status"> · HTTP {{ diagnostic.http_status }}</span>
            <span> · {{ diagnostic.stage }} · {{ diagnostic.url }}</span>
          </li></ul>
        </article></details>
        <p v-if="run.report.publications?.length">Publicaciones verificadas en esta ejecución: {{ run.report.publications.length }}. Identificadores de artículos: {{ run.report.publications.map(item => '#' + item.article_id).join(', ') }}. Sus enlaces aparecen en la cola editorial.</p>
        <details v-if="editorialChecks(run)"><summary>Revisión de calidad editorial</summary><ul><li v-for="(passed, key) in editorialChecks(run)" :key="key">{{ editorialCheckLabels[String(key)] || key }}: {{ passed ? 'Correcto' : 'Necesita reescritura' }}.</li></ul></details>
        <p v-if="run.report.news_statistics?.candidate_count !== undefined">Noticias: {{ run.report.news_statistics.candidate_count }} candidatos · {{ run.report.news_statistics.fetch_failures }} consultas fallidas.</p>
        <p v-else-if="!run.report.editorial_version && run.report.candidate_count !== undefined">{{ run.report.candidate_count }} novedades detectadas · {{ run.report.fetch_failures }} consultas fallidas.</p>
        <details v-if="run.report.candidate_attempts?.length"><summary>Ver candidatos evaluados</summary><ul><li v-for="(attempt, index) in run.report.candidate_attempts" :key="index">Candidato {{ attempt.candidate_id }} · {{ attempt.engine === 'news' ? 'Noticias' : 'Evergreen' }} · {{ candidateReason(attempt.reason) }} <code>{{ attempt.reason }}</code> · Reserva adicional: {{ ((attempt.reserved_microusd || 0) / 1000000).toFixed(6) }} USD.</li></ul></details>
        <p v-if="run.report.source_organizations?.length">Organizaciones confirmadas: {{ run.report.source_organizations.join(', ') }}.</p>
        <details v-if="run.report.selection"><summary>Selección de temas y fuentes</summary>
          <p>{{ run.report.selection.rejected_candidates }} candidatos descartados antes de redactar. {{ run.report.selection.generation_calls_avoided }} {{ run.report.selection.generation_calls_avoided === 1 ? 'llamada inicial de redacción evitada' : 'llamadas iniciales de redacción evitadas' }} en esta ejecución.</p>
          <p v-if="run.report.selection.selected_organizations.length">Organizaciones seleccionadas: {{ run.report.selection.selected_organizations.join(', ') }}.</p>
          <p v-if="run.report.selection.verification_mode === 'official_announcement'">Anuncio oficial verificado.</p>
          <p v-else-if="run.report.selection.verification_mode === 'independently_corroborated'">Noticia corroborada por varias organizaciones.</p>
          <ul><li v-for="candidate in run.report.selection.candidates" :key="candidate.topic_id"><strong>{{ candidate.title }}</strong> · {{ candidate.organizations.join(', ') }} · {{ candidate.status === 'selected' ? 'Seleccionado' : candidate.status === 'eligible' ? 'Válido, se priorizó otro tema' : 'Descartado: faltan organizaciones independientes sobre el mismo tema' }}.</li></ul>
          <ul v-if="run.report.selection.excluded_documents.length"><li v-for="document in run.report.selection.excluded_documents" :key="document.url"><code>{{ document.url }}</code> · {{ document.reason === 'unverified_or_inconsistent_organization' ? 'Organización sin verificar o incoherente' : document.reason === 'insufficient_document_content' ? 'Documento sin contenido suficiente' : 'Contenido duplicado o procedencia compartida' }}.</li></ul>
        </details>
        <details v-if="run.report.fetch_errors?.length"><summary>Ver consultas fallidas</summary><ul><li v-for="(failure, i) in run.report.fetch_errors" :key="i"><code>{{ failure.url }}</code> · {{ failure.http_status ? `HTTP ${failure.http_status}` : failure.code }}. {{ failure.http_status === 403 ? 'La fuente denegó el acceso a la descarga.' : 'Consulta no completada.' }}</li></ul></details>
        <p>Reserva: {{ run.reserved_usd }} USD.</p>
        <p v-if="run.report.corrections_used">Correcciones automáticas realizadas: {{ run.report.corrections_used }} de 1.</p>
        <ul v-if="run.report.review?.reasons?.length"><li v-for="(reason, i) in run.report.review.reasons" :key="i">{{ reason }}</li></ul>
        </details>
      </article>
      <h2>Fuentes iniciales</h2>
      <p>Investigación principalmente en inglés, redacción en español. La selección cubre estas fuentes; no mide las tendencias de toda la web.</p>
      <ul><li v-for="feed in data.feeds" :key="feed"><a :href="feed" target="_blank" rel="noopener noreferrer">{{ feed }}</a></li></ul>
    </template>
    <p v-else role="status">Cargando…</p>
  </div>
</template>
<style scoped>
.rs-h2 { margin-bottom: 10px; }
.rs-status { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; padding: 14px 16px; margin: 16px 0; background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; }
.rs-status button { margin-left: auto; }
.rs-pill { display: inline-block; padding: 3px 10px; border-radius: 999px; font: 600 12px/1.5 var(--sans); background: var(--soft); color: var(--ink); white-space: nowrap; }
.rs-pill.ok { background: #e2f0e4; color: #1f5f2c; }
.rs-pill.info { background: #e3ecf7; color: #1e4a7a; }
.rs-pill.warn { background: #f7eccf; color: #7a5a0e; }
.rs-pill.bad { background: #f6e0dc; color: #8a2a1c; }
.rs-tag { font: 600 11px/1.5 var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
.rs-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 12px; }
.rs-kpi { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 14px 16px; text-align: left; background: var(--surface); color: var(--ink); border: 1px solid var(--rule); border-left-width: 5px; border-radius: 8px; cursor: pointer; }
.rs-kpi.pending { border-left-color: #3b6ea8; }
.rs-kpi.published { border-left-color: #2f7d3e; }
.rs-kpi.rejected { border-left-color: #b0402d; }
.rs-kpi.merged { border-left-color: #8d8a80; }
.rs-kpi.active { box-shadow: 0 0 0 2px var(--ink); }
.rs-kpi-n { font: 700 30px/1.1 var(--serif); }
.rs-kpi-l { font-weight: 600; }
.rs-kpi-s { font-size: 12px; color: var(--muted); }
.rs-budget { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; }
.rs-bar-label { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 4px; }
.rs-bar { height: 10px; background: var(--soft); border-radius: 999px; overflow: hidden; }
.rs-bar span { display: block; height: 100%; background: var(--accent); border-radius: 999px; }
.rs-help { margin: 18px 0; padding: 10px 14px; border: 1px dashed var(--rule); border-radius: 8px; }
.rs-help summary, .rs-more summary { cursor: pointer; font-weight: 600; }
.rs-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 14px; }
.rs-tabs button { padding: 6px 12px; border-radius: 999px; background: var(--surface); color: var(--ink); border: 1px solid var(--rule); font-size: 13px; }
.rs-tabs button.active { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.rs-card { padding: 14px 16px; margin: 0 0 10px; background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; }
.rs-card h3 { margin: 6px 0; font-size: 20px; }
.rs-card p { margin: 6px 0; }
.rs-card-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 13px; }
.rs-reason { font-size: 14px; color: var(--muted); }
.rs-reason code { font-size: 12px; }
.rs-link { font-weight: 600; }
.rs-more { margin-top: 8px; font-size: 14px; }
.rs-merged { columns: 2 300px; font-size: 14px; }
.rs-merged li { break-inside: avoid; margin-bottom: 4px; }
</style>
