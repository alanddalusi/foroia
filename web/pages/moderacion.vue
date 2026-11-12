<script setup lang="ts">
useSeoMeta({ title: 'Moderación | ForoIA', robots: 'noindex, nofollow' })
const comments = ref<any[]>([]), next = ref<string | null>(null), error = ref(''), message = ref('')
async function load(cursor?: string) {
  try {
    const page = await $fetch<any>('/api/community/moderation/comments', { query: cursor ? { cursor } : undefined })
    comments.value = cursor ? [...comments.value, ...page.items] : page.items; next.value = page.next_cursor
  } catch (e) { error.value = accountError(e) }
}
onMounted(() => load())
async function decide(comment: any, status: string) {
  error.value = ''; message.value = ''
  try {
    await $fetch(`/api/community/moderation/comments/${comment.id}`, { method: 'POST', body: { status, version: comment.version }, headers: accountHeaders() })
    message.value = 'Decisión guardada.'; await load()
  } catch (e) { error.value = accountError(e); await load() }
}
</script>
<template><div><h1>Moderación de comentarios</h1><p v-if="error" role="alert" class="notice error">{{ error }}</p><p v-if="message" role="status" class="notice">{{ message }}</p><p v-if="!comments.length">No hay comentarios pendientes.</p>
  <article v-for="comment in comments" :key="comment.id" class="comment"><p>{{ comment.author_name }} · <NuxtLink :to="`/articulos/${comment.article_slug}`">Ver artículo</NuxtLink></p><p class="comment-text">{{ comment.body }}</p><div class="editor-bar"><button @click="decide(comment, 'approved')">Aprobar</button><button class="secondary" @click="decide(comment, 'rejected')">Rechazar</button><button class="secondary" @click="decide(comment, 'removed')">Retirar</button></div></article>
  <button v-if="next" class="secondary" @click="load(next!)">Más pendientes</button>
</div></template>
