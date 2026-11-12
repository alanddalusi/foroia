<script setup lang="ts">
import type { EditorialArticle } from '~/utils/blog'
useSeoMeta({ title: 'Editar artículo | Panel editorial', robots: 'noindex, nofollow' })
const route = useRoute()
const id = String(route.params.id)
if (!/^\d{1,9}$/.test(id)) throw createError({ statusCode: 404, statusMessage: 'Artículo no encontrado', fatal: true })
const { data: article, error, status } = useFetch<EditorialArticle>(`/api/editorial/articles/${id}`, { server: false })
</script>
<template>
  <div>
    <nav class="breadcrumbs" aria-label="Migas de pan"><NuxtLink to="/editorial">Panel editorial</NuxtLink> › Editar</nav>
    <p v-if="status === 'pending'" class="muted">Cargando…</p>
    <p v-else-if="error" class="notice error" role="alert">No se encontró el artículo.</p>
    <template v-else-if="article">
      <h1>{{ article.title }}</h1>
      <EditorialForm :key="article.id" :initial="article" />
    </template>
  </div>
</template>
