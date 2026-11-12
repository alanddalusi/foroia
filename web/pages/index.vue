<script setup lang="ts">
import type { ArticlePage } from '~/utils/blog'
import { jsonLd } from '~/utils/blog'
const config = useRuntimeConfig()
const siteUrl = `${config.public.siteUrl}/`
const shareText = 'Foro IA al Día: inteligencia artificial en español, explicada con calma'
const [{ data: latest, error: latestError }, { data: guides }, { data: sections }, { data: categories }] = await Promise.all([
  useAsyncData('home-latest', () => $fetch<ArticlePage>('/api/articles', { query: { limit: 12 } })),
  useAsyncData('home-guides', () => $fetch<ArticlePage>('/api/articles', { query: { limit: 15, section: 'tutoriales' } })),
  useAsyncData('sections', () => $fetch<{ slug: string, name: string, description: string }[]>('/api/sections'), { default: () => [] }),
  useAsyncData('categories', () => $fetch<any[]>('/api/categories'), { default: () => [] })
])
if (latestError.value) throw createError({ statusCode: 503, statusMessage: 'Blog temporalmente no disponible' })
const latestItems = computed(() => latest.value?.items ?? [])
// Sin duplicados: una guía ya mostrada en «recientes» no se repite (texto y encabezado duplicados).
const guideItems = computed(() => {
  const shown = new Set(latestItems.value.map(a => a.slug))
  return (guides.value?.items ?? []).filter(a => !shown.has(a.slug)).slice(0, 3)
})
useSeoMeta({ title: 'Foro IA al Día | Inteligencia artificial en español', description: 'Foro y blog de inteligencia artificial en español: noticias contrastadas con sus fuentes, guías sobre cómo usar ChatGPT, Gemini y Claude, y programación con IA.', ogTitle: 'Foro IA al Día — Inteligencia artificial en español', ogDescription: 'Noticias de IA con fuentes originales, guías sobre cómo usar ChatGPT, Gemini y Claude, programación con IA en Python y un foro para conversar en español.', ogType: 'website', ogUrl: `${config.public.siteUrl}/` })
useHead({
  link: [{ rel: 'canonical', href: `${config.public.siteUrl}/` }],
  script: [{ key: 'home-website', type: 'application/ld+json', innerHTML: jsonLd([{
    '@context': 'https://schema.org', '@type': 'WebSite',
    '@id': `${config.public.siteUrl}/#website`,
    name: 'Foro IA al Día', alternateName: 'foroiaaldia.com',
    url: `${config.public.siteUrl}/`, inLanguage: 'es',
    publisher: { '@id': `${config.public.siteUrl}/#organization` }
  }, {
    '@context': 'https://schema.org', '@type': 'Organization',
    '@id': `${config.public.siteUrl}/#organization`,
    name: 'Foro IA al Día', url: `${config.public.siteUrl}/`,
    logo: `${config.public.siteUrl}/apple-touch-icon.png`
  }]) }]
})
</script>
<template>
  <div>
    <header class="home-intro">
      <div><p class="eyebrow">Actualidad y aprendizaje</p><h1>Inteligencia artificial en español,<br>explicada con calma.</h1></div>
      <p>Qué está cambiando en la <strong>inteligencia artificial</strong>, cómo usar herramientas como ChatGPT, Gemini o Claude y cómo programar con IA en Python. Todo explicado en español, con fuentes originales y espacio para conversar.</p>
      <p>La inteligencia artificial cambia cada semana. Aquí está explicada con calma y paso a paso: qué se ha anunciado, qué está confirmado y cómo aplicarlo en tu trabajo o en tu código.</p>
    </header>
    <div class="frontpage">
      <section aria-labelledby="recientes" class="latest-section">
        <div class="section-heading"><h2 id="recientes">Artículos recientes sobre inteligencia artificial</h2><span class="section-caption">Lo último del blog</span></div>
        <template v-if="latestItems.length">
          <ArticleCard v-if="latestItems[0]" :article="latestItems[0]" featured />
          <div v-if="latestItems.length > 1" class="article-list"><ArticleCard v-for="a in latestItems.slice(1)" :key="a.slug" :article="a" /></div>
        </template>
        <div v-else class="publication-empty"><p class="eyebrow">Estamos empezando</p><h3>Las primeras lecturas<br>están en preparación.</h3><p>Los artículos aparecerán aquí cuando estén revisados. Mientras tanto, puedes recorrer los temas que vamos a tratar.</p><a href="#secciones">Explorar las secciones</a></div>
      </section>
      <aside class="reading-desk" aria-label="Para seguir aprendiendo">
        <section v-if="guideItems.length" aria-labelledby="guias"><div class="section-heading"><h2 id="guias">Guías prácticas</h2></div><div class="guide-list"><ArticleCard v-for="a in guideItems" :key="a.slug" :article="a" heading-level="div" sizes="(max-width: 680px) calc(100vw - 40px), (max-width: 900px) 235px, 290px" /></div></section>
        <section class="editorial-note" aria-labelledby="nota-lectura"><p class="eyebrow">Una invitación</p><h2 id="nota-lectura">Lee. Prueba.<br>Cuéntalo.</h2><p>Empieza por una pregunta. Consulta las fuentes. Y, cuando pruebes algo, comparte qué te ha servido y qué no.</p><p class="small">Nos apoyamos en la documentación oficial de <a href="https://developers.openai.com/" rel="noopener" target="_blank">OpenAI</a>, <a href="https://ai.google.dev/" rel="noopener" target="_blank">Google Gemini</a> y <a href="https://platform.claude.com/docs/" rel="noopener" target="_blank">Anthropic</a>.</p><NuxtLink to="/tutoriales">Ir a los tutoriales</NuxtLink></section>
      </aside>
    </div>
    <section id="secciones" aria-labelledby="secciones-titulo">
      <div class="section-heading"><h2 id="secciones-titulo">Un tema para cada curiosidad</h2><span class="section-caption">Las secciones</span></div>
      <div class="section-directory"><NuxtLink v-for="(s, index) in sections" :key="s.slug" :to="`/${s.slug}`" class="directory-entry"><span class="directory-number" aria-hidden="true">0{{ index + 1 }}</span><div><strong class="entry-title">{{ s.name }}</strong><p>{{ s.description }}</p></div></NuxtLink></div>
    </section>
    <section id="foro" aria-labelledby="foro-titulo" class="forum-section">
      <div class="section-heading"><h2 id="foro-titulo">Foro de la comunidad</h2><span class="section-caption">La conversación sigue aquí</span></div>
      <p class="forum-intro">Explora las categorías de la comunidad y los debates publicados, o <NuxtLink to="/foro">entra en todas las conversaciones</NuxtLink>.</p>
      <div class="forum-links"><NuxtLink v-for="category in categories" :key="category.slug" :to="`/categoria/${category.slug}`" class="forum-link"><strong class="entry-title">{{ category.name }}</strong><p>{{ category.description }}</p></NuxtLink></div>
      <p v-if="!categories?.length" class="empty">Estamos preparando las primeras categorías.</p>
    </section>
    <nav class="home-share" aria-label="Compartir Foro IA al Día"><span>¿Te resulta útil? Compártelo:</span>
      <a :href="`https://x.com/intent/post?url=${encodeURIComponent(siteUrl)}&text=${encodeURIComponent(shareText)}`" rel="noopener nofollow" target="_blank">X</a>
      <a :href="`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(siteUrl)}`" rel="noopener nofollow" target="_blank">LinkedIn</a>
      <a :href="`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(siteUrl)}`" rel="noopener nofollow" target="_blank">Facebook</a>
      <a :href="`https://api.whatsapp.com/send?text=${encodeURIComponent(shareText + ' ' + siteUrl)}`" rel="noopener nofollow" target="_blank">WhatsApp</a>
      <a :href="`https://t.me/share/url?url=${encodeURIComponent(siteUrl)}&text=${encodeURIComponent(shareText)}`" rel="noopener nofollow" target="_blank">Telegram</a>
    </nav>
  </div>
</template>
<style scoped>
.home-share { display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;margin:40px 0 8px;padding-top:20px;border-top:1px solid var(--rule);font:14px/1.5 system-ui,sans-serif }.home-share span { color:var(--muted) }
</style>
