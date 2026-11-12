<script setup lang="ts">
const route = useRoute(); const config = useRuntimeConfig(); const slug = String(route.params.slug)
const { data: categories } = await useAsyncData('categories', () => $fetch<any[]>('/api/categories'))
const category = computed(() => categories.value?.find(c => c.slug === slug))
if (!category.value) throw createError({ statusCode: 404, statusMessage: 'Categoría no encontrada' })
const page = Number(route.query.pagina ?? 1)
if (!Number.isInteger(page) || page < 1 || page > 1000 || route.query.pagina === '1') throw createError({ statusCode: 404 })
const pageLink = (p: number) => `/categoria/${slug}${p === 1 ? '' : `?pagina=${p}`}`
const { data: topics, error } = await useAsyncData(`category-${slug}-${page}`, () => $fetch<any[]>(`/api/categories/${encodeURIComponent(slug)}/topics`, { query: { limit: 21, offset: (page - 1) * 20 } }), { default: () => [] })
if (error.value) throw createError({ statusCode: 503, statusMessage: 'Categoría temporalmente no disponible' })
if (page > 1 && !topics.value.length) throw createError({ statusCode: 404 })
useSeoMeta({ title: () => `${category.value.name}${page > 1 ? ` (página ${page})` : ''} | Foro IA al Día`, description: () => `${category.value.description}${page > 1 ? ` Página ${page}.` : ''}`,
  robots: () => topics.value?.length ? undefined : 'noindex, follow' })
useHead({ link: [{ rel: 'canonical', href: `${config.public.siteUrl}${pageLink(page)}` }] })
</script>
<template><section><p class="eyebrow">Categoría</p><h1>{{ category.name }}</h1><p>{{ category.description }}</p><div class="topics"><NuxtLink v-for="topic in topics.slice(0, 20)" :key="topic.slug" class="topic" :to="`/tema/${topic.slug}`">{{ topic.title }} <span>→</span></NuxtLink></div><p v-if="!topics?.length" class="empty">Todavía no hay debates publicados.</p><nav v-if="page > 1 || topics.length > 20" class="pagination" aria-label="Paginación"><NuxtLink v-if="page > 1" :to="pageLink(page - 1)" rel="prev">Anterior</NuxtLink><span>Página {{ page }}</span><NuxtLink v-if="topics.length > 20" :to="pageLink(page + 1)" rel="next">Siguiente</NuxtLink></nav></section></template>
