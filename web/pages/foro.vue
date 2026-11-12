<script setup lang="ts">
const config = useRuntimeConfig()
const { data: categories, error } = await useAsyncData('categories', () => $fetch<{ slug: string; name: string; description: string; published_topics: number }[]>('/api/categories'))
if (error.value) throw createError({ statusCode: 503, statusMessage: 'Foro temporalmente no disponible' })
const hasTopics = computed(() => categories.value?.some(c => c.published_topics > 0))
useSeoMeta({ title: 'Foro de inteligencia artificial | Foro IA al Día', description: 'Categorías y debates publicados de la comunidad sobre inteligencia artificial, herramientas y programación.', robots: () => hasTopics.value ? undefined : 'noindex, follow' })
useHead({ link: [{ rel: 'canonical', href: `${config.public.siteUrl}/foro` }] })
</script>
<template>
  <section><nav class="breadcrumbs" aria-label="Migas de pan"><NuxtLink to="/">Inicio</NuxtLink> › Foro</nav><h1>Foro de inteligencia artificial</h1><p>Lee las conversaciones publicadas de la comunidad. El foro está disponible para lectura; todavía no se pueden crear temas desde la web.</p><div class="forum-links"><NuxtLink v-for="c in categories" :key="c.slug" :to="`/categoria/${c.slug}`" class="forum-link"><h2>{{ c.name }}</h2><p>{{ c.description }}</p><p>{{ c.published_topics }} temas publicados</p></NuxtLink></div><p v-if="!hasTopics" class="empty">Todavía no hay debates publicados. Puedes empezar por los <NuxtLink to="/tutoriales">tutoriales del blog</NuxtLink>.</p></section>
</template>
