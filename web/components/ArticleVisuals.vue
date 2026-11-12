<script setup lang="ts">
import type { ArticleMedia } from '~/utils/blog'
defineProps<{ media: ArticleMedia }>()
const loaded = ref<Record<string, boolean>>({})
const number = (value: number) => value.toLocaleString('es-ES', { maximumFractionDigits: 3 })
function bar(value: number, points: { value: number }[]) { return `${Math.max(0, Math.min(100, value / (Math.max(...points.map(p => p.value)) || 1) * 100))}%` }
</script>
<template>
  <div class="article-visuals">
    <figure v-for="(chart, i) in media.charts || []" :key="i" class="data-figure" :aria-labelledby="`chart-title-${i}`">
      <figcaption :id="`chart-title-${i}`"><strong>{{ chart.title }}</strong><span>{{ chart.unit }} · escala desde cero</span></figcaption>
      <div aria-hidden="true" class="chart-bars"><div v-for="p in chart.points" :key="p.label" class="chart-row"><span>{{ p.label }}</span><div class="chart-track"><div :style="{ width: bar(p.value, chart.points) }" /></div><strong>{{ number(p.value) }}</strong></div></div>
      <table class="chart-data"><caption>Datos del gráfico, en {{ chart.unit }}</caption><thead><tr><th scope="col">Periodo</th><th scope="col">Valor</th></tr></thead><tbody><tr v-for="p in chart.points" :key="p.label"><th scope="row">{{ p.label }}</th><td>{{ number(p.value) }}</td></tr></tbody></table>
      <p class="small">Fuente: <a :href="chart.source_url" rel="noopener noreferrer" target="_blank">documento consultado</a>.</p>
      <details><summary>Cómo leer estos datos</summary><p>Los valores conservan la unidad de la fuente enlazada. Consulta el documento original para conocer su contexto; el gráfico no es una previsión.</p></details>
    </figure>
    <figure v-for="video in media.videos || []" :key="video.id" class="video-figure">
      <div class="video-frame">
        <iframe v-if="loaded[video.id]" :src="`https://www.youtube-nocookie.com/embed/${video.id}?autoplay=0`" :title="video.title" width="960" height="540" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" sandbox="allow-scripts allow-same-origin allow-presentation" allow="fullscreen; picture-in-picture" allowfullscreen />
        <div v-else class="video-placeholder"><p>{{ video.title }}</p><button type="button" @click="loaded[video.id] = true">Cargar vídeo de YouTube</button><p class="small">Solo al pulsar se contactará con YouTube. No se reproducirá automáticamente.</p></div>
      </div>
      <figcaption>Vídeo incrustado en la <a :href="video.source_url" rel="noopener noreferrer" target="_blank">fuente oficial consultada</a>. No se ha descargado ni redistribuido.</figcaption>
    </figure>
  </div>
</template>
<style scoped>
.data-figure,.video-figure { margin:32px 0;border:1px solid var(--rule);padding:24px;background:var(--soft);border-radius:6px }
.data-figure figcaption strong { display:block;font-size:20px }.data-figure figcaption span { display:block;font-size:13px;color:var(--muted);margin-top:6px }
.chart-bars { margin:25px 0 }.chart-row { display:grid;grid-template-columns:44px 1fr 52px;align-items:center;gap:12px;margin:15px 0;font-size:14px }.chart-track { height:24px;border-left:1px solid var(--ink) }.chart-track div { height:100%;background:#285d55 }.chart-data { width:100%;border-collapse:collapse;font-size:14px }.chart-data caption { text-align:left;font-size:12px;padding:12px 0 }.chart-data th,.chart-data td { text-align:left;border-bottom:1px solid var(--rule);padding:8px }
details { font-size:13px }summary { cursor:pointer;min-height:40px;padding-top:12px }blockquote { margin:10px 0;overflow-wrap:anywhere;font-size:13px }
.video-frame { aspect-ratio:16/9 }.video-frame iframe { width:100%;height:100%;border:0 }.video-placeholder { height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:12px;background:#e6e9e0 }.video-placeholder button { min-height:44px;padding:12px;background:var(--ink);color:var(--paper);border:0 }.video-placeholder p { margin:8px 0;max-width:48ch }.video-figure figcaption { font-size:12px;line-height:1.6;margin-top:12px }
@media(max-width:600px) { .data-figure,.video-figure { padding:16px }.video-placeholder .small { font-size:11px } }
</style>
