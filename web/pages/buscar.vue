<script setup lang="ts">
import type { ArticlePage } from '~/utils/blog'
// Búsqueda interna: útil para el lector, nunca indexable (AGENTS.md).
const route = useRoute()
const q = computed(() => String(route.query.q ?? '').replace(/\s+/g, ' ').trim().slice(0, 80))
const page = computed(() => {
  const n = Number(route.query.pagina ?? 1)
  return Number.isInteger(n) && n >= 1 && n <= 20 ? n : 1
})
const { data, error } = await useAsyncData(() => `search-${q.value}-${page.value}`,
  () => q.value.length >= 2 ? $fetch<ArticlePage>('/api/search', { query: { q: q.value, page: page.value } }) : Promise.resolve(null),
  { watch: [q, page] })
const items = computed(() => data.value?.items ?? [])
useSeoMeta({ title: () => q.value ? `Buscar «${q.value}» | Foro IA al Día` : 'Buscar | Foro IA al Día', description: 'Busca artículos, guías y noticias de inteligencia artificial en Foro IA al Día.', robots: 'noindex, follow' })
const pageLink = (p: number) => ({ path: '/buscar', query: { q: q.value, ...(p > 1 ? { pagina: String(p) } : {}) } })
</script>
<template>
  <div class="search-page">
    <nav aria-label="Migas de pan" class="breadcrumbs"><NuxtLink to="/">Inicio</NuxtLink> › Buscar</nav>
    <header class="section-header"><h1>Buscar en Foro IA al Día</h1></header>
    <form action="/buscar" method="get" role="search" class="search-form">
      <label for="buscar-q" class="sr-only">Qué quieres aprender</label>
      <input id="buscar-q" type="search" name="q" :value="q" minlength="2" maxlength="80" placeholder="Por ejemplo: embeddings, ChatGPT, error 429" required>
      <button type="submit">Buscar</button>
    </form>
    <p v-if="error" class="empty">La búsqueda no está disponible en este momento. Prueba de nuevo en unos minutos.</p>
    <template v-else-if="q.length >= 2">
      <p class="muted" aria-live="polite">{{ items.length ? `Resultados para «${q}»` : `No hemos encontrado artículos para «${q}».` }}</p>
      <div v-if="items.length" class="section-articles"><ArticleCard v-for="a in items" :key="a.slug" :article="a" heading-level="h2" /></div>
      <p v-else>Prueba con otra palabra o explora las secciones: <template v-for="(s, i) in SECTIONS" :key="s.slug"><NuxtLink :to="`/${s.slug}`">{{ s.name }}</NuxtLink>{{ i < SECTIONS.length - 1 ? ', ' : '.' }}</template></p>
      <nav v-if="page > 1 || data?.has_next" class="pagination" aria-label="Paginación">
        <NuxtLink v-if="page > 1" :to="pageLink(page - 1)" rel="prev">← Anteriores</NuxtLink>
        <span>Página {{ page }}</span>
        <NuxtLink v-if="data?.has_next" :to="pageLink(page + 1)" rel="next">Siguientes →</NuxtLink>
      </nav>
    </template>
  </div>
</template>
<style scoped>
.search-form { display:flex;gap:8px;max-width:620px;margin:0 0 28px }
.search-form input { flex:1;min-width:0;font:16px/1.4 system-ui,sans-serif;padding:10px 12px;border:1px solid var(--rule);border-radius:3px;background:var(--paper);color:var(--ink) }
.search-form button { font:600 15px/1 system-ui,sans-serif;padding:0 18px }
</style>
