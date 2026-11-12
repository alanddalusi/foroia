<script setup lang="ts">
import type { ArticlePage } from '~/utils/blog'
const route = useRoute(); const config = useRuntimeConfig()
const slug = String(route.params.seccion)
const section = SECTIONS.find(s => s.slug === slug)
if (!section) throw createError({ statusCode: 404, statusMessage: 'Sección no encontrada', fatal: true })
const rawPage = route.query.pagina
const page = rawPage === undefined ? 1 : Number(rawPage)
if (!Number.isInteger(page) || page < 1 || page > 1000 || (rawPage !== undefined && page === 1)) {
  throw createError({ statusCode: 404, statusMessage: 'Página no encontrada', fatal: true })
}
const { data, error } = await useAsyncData(`section-${slug}-${page}`, () => $fetch<ArticlePage>('/api/articles', { query: { section: slug, page, limit: 12 } }))
if (error.value) throw createError({ statusCode: 503, statusMessage: 'Sección temporalmente no disponible' })
const items = computed(() => data.value?.items ?? [])
if (page > 1 && !items.value.length) throw createError({ statusCode: 404, statusMessage: 'Página no encontrada', fatal: true })
const { data: sections } = await useAsyncData('sections', () => $fetch<{ slug: string, name: string, description: string }[]>('/api/sections'), { default: () => [] })
const description = sections.value.find(s => s.slug === slug)?.description ?? `Artículos de ${section.name} sobre inteligencia artificial.`
const intro = SECTION_INTROS[slug]
const base = `${config.public.siteUrl}/${slug}`
const canonical = page === 1 ? base : `${base}?pagina=${page}`
const metaDescription = seoDescription(page === 1 && intro ? intro.paragraphs[0]! : description)
useSeoMeta({ title: page === 1 && intro ? seoTitle(intro.title) : `${section.name}${page > 1 ? ` (página ${page})` : ''} | Foro IA al Día`, description: `${metaDescription}${page > 1 ? ` Página ${page}.` : ''}`, ogTitle: intro?.title ?? section.name, ogDescription: metaDescription, ogType: 'website', ogUrl: canonical, ogImage: `${config.public.siteUrl}/images/${slug}.png`,
  robots: items.value.length ? undefined : 'noindex, follow' })
useHead({ link: [{ rel: 'canonical', href: canonical }], script: [{ type: 'application/ld+json', innerHTML: jsonLd({
  '@context': 'https://schema.org', '@type': 'CollectionPage', name: intro?.title ?? section.name, url: canonical, inLanguage: 'es',
  isPartOf: { '@id': `${config.public.siteUrl}/#website` },
  breadcrumb: { '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${config.public.siteUrl}/` },
    { '@type': 'ListItem', position: 2, name: section.name, item: base }] }
}) }] })
const pageLink = (p: number) => p === 1 ? `/${slug}` : `/${slug}?pagina=${p}`
</script>
<template>
  <div>
    <nav aria-label="Migas de pan" class="breadcrumbs"><NuxtLink to="/">Inicio</NuxtLink> › {{ section!.name }}</nav>
    <header class="section-header"><h1>{{ page === 1 && intro ? intro.title : section!.name }}</h1><p class="lead">{{ description }}</p></header>
    <section v-if="page === 1 && intro" class="section-intro" aria-label="Sobre esta sección">
      <p v-for="(p, i) in intro.paragraphs" :key="i">{{ p }}</p>
      <template v-if="intro.start.length"><h2>Por dónde empezar</h2>
        <ul><li v-for="l in intro.start" :key="l.href"><NuxtLink :to="l.href">{{ l.label }}</NuxtLink></li></ul></template>
    </section>
    <div v-if="items.length" class="section-articles"><ArticleCard v-for="a in items" :key="a.slug" :article="a" heading-level="h2" /></div>
    <p v-else class="empty">Todavía no hay artículos publicados en esta sección.</p>
    <nav v-if="page > 1 || data?.has_next" class="pagination" aria-label="Paginación">
      <NuxtLink v-if="page > 1" :to="pageLink(page - 1)" rel="prev">← Más recientes</NuxtLink>
      <span>Página {{ page }}</span>
      <NuxtLink v-if="data?.has_next" :to="pageLink(page + 1)" rel="next">Anteriores →</NuxtLink>
    </nav>
  </div>
</template>
<style scoped>
.section-intro { max-width:760px;margin:0 0 32px;font:16px/1.7 system-ui,sans-serif }.section-intro h2 { font:600 16px/1.4 system-ui,sans-serif;margin:18px 0 8px }.section-intro ul { padding-left:20px;margin:0 }
</style>
