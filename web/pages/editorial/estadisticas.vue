<script setup lang="ts">
interface Metrics {
  days: number; timezone: string; first_recorded_day: string | null
  views: number; previous_views: number; states: Record<string, number>
  series: { day: string; views: number; published: number }[]
  top_articles: { path: string; title: string; views: number }[]
}
useSeoMeta({ title: 'Seguimiento de la web | Foro IA al Día', robots: 'noindex, nofollow' })
const days = ref(30)
const { data, error, status, refresh } = useFetch<Metrics>('/api/editorial/analytics', {
  server: false, query: { days }
})
const maximum = computed(() => Math.max(1, ...data.value?.series.map(d => d.views) || []))
</script>
<template>
  <div>
    <NuxtLink to="/editorial">Volver al panel editorial</NuxtLink>
    <header class="editor-bar"><h1>Seguimiento de la web</h1><button type="button" class="secondary" @click="refresh()">Actualizar</button></header>
    <label>Periodo <select v-model="days"><option :value="7">7 días</option><option :value="30">30 días</option><option :value="90">90 días</option></select></label>
    <p class="muted">Cargas HTML de portada, secciones y artículos. Sin cookies de analítica ni identificadores de visitantes. Las recargas cuentan; la navegación interna sin recarga no cuenta. Se excluyen sesiones iniciadas y bots reconocibles, aunque el filtro no detecta todos. No son personas únicas.</p>
    <p v-if="error" role="alert" class="notice error">No se pudieron cargar las estadísticas. <button @click="refresh()">Reintentar</button></p>
    <p v-else-if="status === 'pending'" role="status">Cargando estadísticas…</p>
    <template v-else-if="data">
      <p v-if="!data.first_recorded_day" class="notice">Todavía no hay cargas registradas. No se han importado visitas anteriores.</p>
      <p v-else>Primer día con datos: {{ data.first_recorded_day }}. Días según {{ data.timezone }}.</p>
      <dl class="metrics">
        <div><dt>Cargas en el periodo</dt><dd>{{ data.views }}</dd></div>
        <div><dt>Periodo anterior de igual duración</dt><dd>{{ data.previous_views }}</dd></div>
        <div><dt>Publicados actualmente</dt><dd>{{ data.states.published || 0 }}</dd></div>
        <div><dt>Borradores / en revisión</dt><dd>{{ data.states.draft || 0 }} / {{ data.states.review || 0 }}</dd></div>
        <div><dt>Archivados</dt><dd>{{ data.states.archived || 0 }}</dd></div>
      </dl>
      <h2>Evolución diaria</h2>
      <div class="daily-chart" aria-hidden="true"><div v-for="day in data.series" :key="day.day" :title="`${day.day}: ${day.views}`" :style="{ height: `${Math.max(1, day.views / maximum * 100)}%` }" /></div>
      <details><summary>Ver datos diarios en tabla</summary><div class="metrics-table"><table class="table"><thead><tr><th scope="col">Día</th><th scope="col">Cargas</th><th scope="col">Publicaciones</th></tr></thead><tbody><tr v-for="day in data.series" :key="day.day"><th scope="row">{{ day.day }}</th><td>{{ day.views }}</td><td>{{ day.published }}</td></tr></tbody></table></div></details>
      <p class="muted">Publicaciones: primera fecha de publicación de cada artículo, aunque se archive después. No mide impresiones en Google ni ingresos.</p>
      <h2>Artículos publicados más leídos</h2>
      <ol v-if="data.top_articles.length"><li v-for="a in data.top_articles" :key="a.path"><NuxtLink :to="a.path">{{ a.title }}</NuxtLink> — {{ a.views }} cargas</li></ol>
      <p v-else>Aún no hay cargas de artículos publicados en este periodo.</p>
      <h2>Métricas aún no disponibles</h2>
      <p>Usuarios únicos, sesiones, países, tráfico orgánico y páginas de entrada: dato no disponible. El contador local mide cargas HTML y no identifica personas.</p>
      <p>Impresiones, clics, CTR y posición media de Search Console: dato no disponible en este panel. La verificación del dominio y el envío del sitemap no conectan automáticamente esos informes.</p>
      <p>GA4 requiere configurar su propiedad, revisar privacidad y consentimiento y autorizar su activación. No se han activado tecnologías de seguimiento ni publicidad para completar estas métricas.</p>
    </template>
  </div>
</template>
<style scoped>
.metrics { display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin:2rem 0 }
.metrics div { border-top:2px solid currentColor;padding-top:.7rem }
.metrics dd { font-size:2rem;margin:.3rem 0;font-variant-numeric:tabular-nums }
.daily-chart { display:flex;align-items:flex-end;gap:3px;height:150px;border-bottom:1px solid currentColor;margin:1rem 0 }
.daily-chart div { flex:1;background:#8b302a;min-width:0 }
.metrics-table { overflow-x:auto }
</style>
