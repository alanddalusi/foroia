<script setup lang="ts">
import type { ArticleSummary } from '~/utils/blog'
const props = withDefaults(defineProps<{ article: ArticleSummary; featured?: boolean; headingLevel?: 'h2' | 'h3' | 'div'; sizes?: string }>(), { headingLevel: 'h3' })
// El navegador elige 480/800/1200 según el ancho real de la tarjeta (no se descarga más de lo necesario).
const srcset = computed(() => Object.entries(props.article.media?.cover?.variants ?? {})
  .filter(([w]) => /^[0-9]{3,4}$/.test(w)).map(([w, src]) => `${src} ${w}w`).join(', ') || undefined)
const imageSizes = computed(() => props.sizes || (props.featured
  ? '(max-width: 680px) calc(100vw - 40px), (max-width: 900px) calc(100vw - 300px), 742px'
  : '(max-width: 680px) calc(100vw - 40px), 360px'))
</script>
<template>
  <article class="article-card" :class="{ 'article-card--lead': featured }">
    <div v-if="article.media?.cover" class="card-image"><img :src="article.media.cover.variants['480'] || article.media.cover.src" :srcset="srcset" :sizes="srcset ? imageSizes : undefined" :alt="article.media.cover.alt || article.title" width="480" height="252" :loading="featured ? 'eager' : 'lazy'" decoding="async"></div>
    <p class="eyebrow">{{ sectionName(article.section) }}</p>
    <component :is="headingLevel" class="article-card-title"><NuxtLink :to="`/articulos/${article.slug}`">{{ article.title }}</NuxtLink></component>
    <p>{{ article.summary }}</p>
    <p class="muted small">{{ articleAuthor(article.author_name) }} · <time :datetime="htmlDateTime(article.published_at)">{{ formatDate(article.published_at) }}</time></p>
  </article>
</template>
<style scoped>.card-image { display:block;margin-bottom:18px }.card-image img { display:block;width:100%;height:auto;aspect-ratio:1200/630;border:1px solid var(--rule);border-radius:3px }</style>
