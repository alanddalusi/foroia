<script setup lang="ts">
const route = useRoute(); const config = useRuntimeConfig()
const slug = String(route.params.slug)
const { data: topic, error } = await useAsyncData(`topic-${slug}`, () => $fetch<any>(`/api/topics/${encodeURIComponent(slug)}`))
if (error.value || !topic.value) throw createError({ statusCode: error.value && error.value.statusCode !== 404 ? 503 : 404, statusMessage: 'Debate no encontrado' })
const url = `${config.public.siteUrl}/tema/${slug}`
useSeoMeta({ title: () => `${topic.value.title} | Foro IA al Día`, description: () => topic.value.body.slice(0, 155), ogTitle: () => topic.value.title, ogDescription: () => topic.value.body.slice(0, 155), ogType: 'article' })
useHead({ link: [{ rel: 'canonical', href: url }], script: [{ type: 'application/ld+json', innerHTML: jsonLd({ '@context': 'https://schema.org', '@type': 'DiscussionForumPosting', headline: topic.value.title, text: topic.value.body, datePublished: topic.value.created_at, author: { '@type': 'Person', name: topic.value.author_name }, url }) }] })
</script>
<template><article class="article"><p class="eyebrow">Debate</p><h1>{{ topic.title }}</h1><p class="muted">Publicado por {{ topic.author_name }} · <time :datetime="htmlDateTime(topic.created_at)">{{ formatDate(topic.created_at) }}</time></p><p class="body">{{ topic.body }}</p><NuxtLink to="/foro">← Volver al foro</NuxtLink></article></template>
