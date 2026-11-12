<script setup lang="ts">
import type { ArticleDetail } from '~/utils/blog'
import { articleBlocks } from '~/utils/article-blocks'
import { sourceLabel } from '~/utils/source-label'
const route = useRoute(); const config = useRuntimeConfig()
const slug = String(route.params.slug)
const { data: article, error } = await useAsyncData(`article-${slug}`, () => $fetch<ArticleDetail>(`/api/articles/${encodeURIComponent(slug)}`))
if (error.value || !article.value) throw createError({ statusCode: error.value && error.value.statusCode !== 404 ? 503 : 404, statusMessage: 'Artículo no encontrado', fatal: true })
const a = article.value
const authorName = articleAuthor(a.author_name)
const cover = a.media?.cover
const image = `${config.public.siteUrl}${cover?.src || `/images/${a.section}.png`}`
const headings = articleBlocks(a.body).filter(b => b.type === 'h2')
const readingMinutes = Math.max(1, Math.ceil(a.body.split(/\s+/).length / 220))
const url = `${config.public.siteUrl}/articulos/${a.slug}`
const sectionUrl = `${config.public.siteUrl}/${a.section}`
const updated = a.updated_at && a.published_at && new Date(a.updated_at).getTime() - new Date(a.published_at).getTime() > 86_400_000
const isTeam = authorName === AUTHOR.name
const description = seoDescription(a.summary)
const authorLd = isTeam
  ? { '@type': 'Organization', name: authorName, url: `${config.public.siteUrl}${AUTHOR.path}` }
  : { '@type': 'Person', name: authorName }
useSeoMeta({ title: seoTitle(a.title), description, ogTitle: a.title, ogDescription: description, ogType: 'article', ogUrl: url, articlePublishedTime: a.published_at ?? undefined, articleModifiedTime: a.updated_at, ogImage: image, ogImageWidth: 1200, ogImageHeight: 630, ogImageAlt: cover?.alt || `Ilustración de ${sectionName(a.section)}`, twitterCard: 'summary_large_image', twitterImage: image, twitterTitle: a.title, twitterDescription: description })
useHead({
  link: [{ rel: 'canonical', href: url }],
  script: [{ type: 'application/ld+json', innerHTML: jsonLd([
    // NewsArticle solo en Actualidad; el resto son artículos de blog/guías.
    { '@context': 'https://schema.org', '@type': a.section === 'actualidad' ? 'NewsArticle' : ['Article', 'BlogPosting'], headline: a.title, description: a.summary, datePublished: a.published_at, dateModified: a.updated_at, author: authorLd, publisher: { '@type': 'Organization', name: 'Foro IA al Día', url: `${config.public.siteUrl}/`, logo: { '@type': 'ImageObject', url: `${config.public.siteUrl}/apple-touch-icon.png` } }, image: [image], mainEntityOfPage: url, inLanguage: 'es', citation: a.sources.map(s => s.url) },
    { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${config.public.siteUrl}/` },
      { '@type': 'ListItem', position: 2, name: sectionName(a.section), item: sectionUrl },
      { '@type': 'ListItem', position: 3, name: a.title, item: url }] }
  ]) }]
})
</script>
<template>
  <div>
    <nav aria-label="Migas de pan" class="breadcrumbs reading-breadcrumbs"><NuxtLink to="/">Inicio</NuxtLink> › <NuxtLink :to="`/${a.section}`">{{ sectionName(a.section) }}</NuxtLink></nav>
    <article class="article article--visual">
      <header class="article-header">
        <p class="eyebrow">{{ sectionName(a.section) }}</p>
        <h1>{{ a.title }}</h1>
        <p class="lead">{{ a.summary }}</p>
        <p class="muted article-byline">Por <NuxtLink v-if="isTeam" :to="AUTHOR.path" rel="author">{{ authorName }}</NuxtLink><template v-else>{{ authorName }}</template> · Publicado el <time :datetime="htmlDateTime(a.published_at)">{{ formatDate(a.published_at) }}</time>
          <template v-if="updated"> · Actualizado el <time :datetime="htmlDateTime(a.updated_at)">{{ formatDate(a.updated_at) }}</time></template>
        </p>
        <p class="reading-time muted">{{ readingMinutes }} min de lectura · {{ a.sources.length }} {{ a.sources.length === 1 ? 'fuente' : 'fuentes' }}</p>
      </header>
      <figure class="article-cover">
        <picture v-if="cover"><source type="image/webp" :srcset="Object.entries(cover.variants).map(([w, src]) => `${src} ${w}w`).join(', ')" sizes="(max-width: 760px) 100vw, 1100px"><img :src="cover.src" :alt="cover.alt" width="1200" height="630" loading="eager" fetchpriority="high" decoding="async"></picture>
        <img v-else :src="`/images/${a.section}.svg`" alt="" width="1200" height="630" loading="eager" decoding="async">
        <figcaption>{{ cover ? `${cover.caption} ${cover.credit}.` : `Ilustración editorial de la sección ${sectionName(a.section)}.` }}</figcaption>
      </figure>
      <div class="article-content-grid">
      <div class="article-reading">
      <ArticleAudio :title="a.title" :body="a.body" />
      <ArticleVisuals v-if="a.media" :media="a.media" />
      <ArticleBody :body="a.body" />
      <nav v-if="a.related.length && !/## Para seguir aprendiendo/.test(a.body)" class="keep-learning" aria-labelledby="seguir-aprendiendo">
        <h2 id="seguir-aprendiendo">Para seguir aprendiendo</h2>
        <ul><li v-for="r in a.related" :key="r.slug"><NuxtLink :to="`/articulos/${r.slug}`">{{ r.title }}</NuxtLink></li>
          <li><NuxtLink :to="`/${a.section}`">Más artículos de {{ sectionName(a.section) }}</NuxtLink></li></ul>
      </nav>
      <nav class="share-links" aria-label="Compartir este artículo"><span>Compartir:</span>
        <a :href="`https://x.com/intent/post?url=${encodeURIComponent(url)}&text=${encodeURIComponent(a.title)}`" rel="noopener nofollow" target="_blank">X</a>
        <a :href="`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`" rel="noopener nofollow" target="_blank">LinkedIn</a>
        <a :href="`https://api.whatsapp.com/send?text=${encodeURIComponent(a.title + ' ' + url)}`" rel="noopener nofollow" target="_blank">WhatsApp</a>
        <a :href="`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(a.title)}`" rel="noopener nofollow" target="_blank">Telegram</a>
      </nav>
      <section v-if="a.sources.length" class="sources" aria-labelledby="fuentes">
        <h2 id="fuentes">Fuentes originales</h2>
        <ol><li v-for="s in a.sources" :key="s.url"><a :href="s.url" rel="noopener noreferrer" target="_blank">{{ sourceLabel(s.title, s.url) }}</a> <span class="muted small">({{ languageName(s.language) }})</span></li></ol>
      </section>
      </div>
      <aside v-if="headings.length" class="article-index" aria-label="Índice del artículo"><nav aria-labelledby="indice-articulo"><h2 id="indice-articulo">En esta lectura</h2><ol><li v-for="heading in headings" :key="heading.id"><a :href="`#${heading.id}`">{{ heading.text }}</a></li></ol><a href="#fuentes" class="small">Consultar las fuentes →</a></nav></aside>
      </div>
    </article>
    <ArticleComments :slug="a.slug" :enabled="a.comments_enabled" />
    <section v-if="a.related.length" aria-labelledby="relacionados">
      <h2 id="relacionados">Artículos relacionados</h2>
      <div class="cards"><ArticleCard v-for="r in a.related" :key="r.slug" :article="r" /></div>
    </section>
    <aside class="come-back" aria-labelledby="sigue-al-dia">
      <h2 id="sigue-al-dia">Sigue aprendiendo con Foro IA al Día</h2>
      <p>Publicamos guías y noticias de inteligencia artificial explicadas en español, siempre con sus fuentes.</p>
      <p class="come-back-links"><NuxtLink :to="`/${a.section}`">Más artículos de {{ sectionName(a.section) }}</NuxtLink><NuxtLink v-if="a.section !== 'tutoriales'" to="/tutoriales">Guías paso a paso</NuxtLink><NuxtLink to="/buscar">Buscar un tema</NuxtLink><a href="/rss.xml">Suscríbete por RSS</a></p>
    </aside>
  </div>
</template>
<style scoped>
.come-back { margin:48px 0 8px;padding:24px 0 0;border-top:2px solid var(--ink);font:15px/1.6 system-ui,sans-serif }.come-back h2 { font-size:24px;margin:0 0 8px }.come-back p { color:var(--muted);margin:0 0 12px }.come-back-links { display:flex;flex-wrap:wrap;gap:8px 22px }
.share-links { display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;margin:24px 0;font:14px/1.5 system-ui,sans-serif }.share-links span { color:var(--muted) }
.keep-learning { margin:36px 0;padding:20px 22px;border-left:3px solid var(--ink);background:var(--soft) }.keep-learning h2 { font:600 17px/1.4 system-ui,sans-serif;margin:0 0 10px }.keep-learning ul { margin:0;padding-left:20px;font:15px/1.7 system-ui,sans-serif }
.article--visual { max-width:1100px }.article-header { max-width:860px;margin:0 auto 30px;padding:14px 0 28px;border-bottom:0 }.article-header h1 { font-size:clamp(34px,4.2vw,56px);line-height:1.1;letter-spacing:-.035em }.article-header .lead { max-width:64ch;font-size:clamp(19px,2vw,23px);line-height:1.6 }.reading-time { font-size:12px;letter-spacing:.02em;margin:12px 0 0 }.article-cover { margin:0 0 36px }.article-cover img { border:1px solid var(--rule);border-radius:4px }.article-cover figcaption { max-width:85ch;font-size:11px;line-height:1.6;padding-top:4px }
.article-content-grid { display:grid;grid-template-columns:minmax(0,740px) minmax(170px,1fr);gap:64px }.article-reading { min-width:0 }.article-index nav { position:sticky;top:24px;border-top:2px solid var(--ink);padding-top:18px }.article-index h2 { font:600 14px/1.4 system-ui,sans-serif;margin:0 0 15px }.article-index ol { padding-left:18px;font:13px/1.65 system-ui,sans-serif }.article-index li { margin-bottom:13px }.article-index a { text-decoration:none }.article-index a:hover { text-decoration:underline }
@media(max-width:850px) { .article-content-grid { display:flex;flex-direction:column;gap:0 }.article-index { order:-1;border-bottom:1px solid var(--rule);padding-bottom:16px }.article-index nav { position:static;border-top:0 }.article-index ol { display:flex;flex-wrap:wrap;gap:8px 22px;padding-left:18px;margin-bottom:8px }.article-index li { flex:1 1 200px;margin:0 }.article-cover { margin-bottom:22px }.article-header { padding-top:8px } }
</style>
