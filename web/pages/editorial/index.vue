<script setup lang="ts">
import type { EditorialArticle } from '~/utils/blog'
useSeoMeta({ title: 'Panel editorial | ForoIA', robots: 'noindex, nofollow' })
const status = ref('')
const { data: articles, error, refresh, status: loading } = useFetch<EditorialArticle[]>('/api/editorial/articles', { query: { status: computed(() => status.value || undefined) }, server: false, default: () => [] })
</script>
<template>
  <div>
    <header class="editor-bar"><h1>Panel editorial</h1><NuxtLink to="/editorial/nuevo" class="button">Nuevo artículo</NuxtLink></header>
    <label>Filtrar por estado
      <select v-model="status"><option value="">Todos</option><option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">{{ label }}</option></select>
    </label>
    <p v-if="error" class="notice error" role="alert">No se pudieron cargar los artículos. <button type="button" class="secondary" @click="refresh()">Reintentar</button></p>
    <p v-else-if="loading === 'pending'" class="muted">Cargando…</p>
    <table v-else-if="articles.length" class="table">
      <thead><tr><th scope="col">Título</th><th scope="col">Sección</th><th scope="col">Estado</th><th scope="col">Actualizado</th></tr></thead>
      <tbody>
        <tr v-for="a in articles" :key="a.id">
          <td><NuxtLink :to="`/editorial/${a.id}`">{{ a.title }}</NuxtLink></td>
          <td>{{ sectionName(a.section) }}</td>
          <td><span class="badge" :data-status="a.status">{{ STATUS_LABELS[a.status ?? 'draft'] }}</span></td>
          <td>{{ formatDate(a.updated_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">No hay artículos con este filtro.</p>
  </div>
</template>
