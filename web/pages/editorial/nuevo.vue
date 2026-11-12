<script setup lang="ts">
import type { EditorialArticle } from '~/utils/blog'
useSeoMeta({ title: 'Nuevo artículo | Panel editorial', robots: 'noindex, nofollow' })
const onSaved = (a: EditorialArticle) => navigateTo(`/editorial/${a.id}`, { replace: true })
</script>
<template>
  <div>
    <nav class="breadcrumbs" aria-label="Migas de pan"><NuxtLink to="/editorial">Panel editorial</NuxtLink> › Nuevo</nav>
    <h1>Nuevo artículo</h1>
    <EditorialForm @saved="onSaved" />
  </div>
</template>
