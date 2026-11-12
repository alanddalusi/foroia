<script setup lang="ts">
const props = defineProps<{ slug: string; enabled: boolean }>()
const { user } = useAccount()
const registrationEnabled = useRuntimeConfig().public.registrationEnabled
const { data: page } = await useAsyncData(`comments-${props.slug}`, () => $fetch<any>(`/api/community/articles/${props.slug}/comments`), { default: () => ({ items: [], next_cursor: null }) })
const extra = ref<any[]>([]), cursor = ref<string | null | undefined>(undefined), body = ref(''), message = ref(''), error = ref(''), busy = ref(false)
const next = computed(() => cursor.value === undefined ? page.value.next_cursor : cursor.value)
async function more() {
  if (!next.value) return
  try {
    const result = await $fetch<any>(`/api/community/articles/${props.slug}/comments`, { query: { cursor: next.value } })
    extra.value.push(...result.items); cursor.value = result.next_cursor
  } catch (e) { error.value = accountError(e) }
}
async function submit() {
  busy.value = true; error.value = ''; message.value = ''
  try {
    await $fetch(`/api/community/articles/${props.slug}/comments`, { method: 'POST', body: { body: body.value }, headers: accountHeaders() })
    body.value = ''; message.value = 'Comentario recibido. Se mostrará cuando lo apruebe moderación.'
  } catch (e) { error.value = accountError(e) } finally { busy.value = false }
}
</script>
<template>
  <section aria-labelledby="comentarios" class="article-comments"><h2 id="comentarios">Comentarios</h2>
    <p v-if="!page.items.length" class="muted">Todavía no hay comentarios aprobados.</p>
    <article v-for="comment in [...page.items, ...extra]" :key="comment.id" class="comment"><p><strong>{{ comment.author_name }}</strong> · <time :datetime="htmlDateTime(comment.created_at)">{{ formatDate(comment.created_at) }}</time></p><p class="comment-text">{{ comment.body }}</p></article>
    <button v-if="next" class="secondary" @click="more">Más comentarios</button>
    <p v-if="!enabled">Los comentarios están cerrados.</p>
    <p v-else-if="!user && !registrationEnabled">Puedes leer sin cuenta. Las nuevas altas están temporalmente cerradas.</p>
    <p v-else-if="!user"><NuxtLink to="/cuenta">Inicia sesión o crea una cuenta</NuxtLink> para comentar.</p>
    <p v-else-if="!user.verified">Verifica tu correo antes de comentar.</p>
    <form v-else class="form" @submit.prevent="submit"><label>Tu comentario<textarea v-model="body" required maxlength="5000" rows="5" /></label><p class="muted">Se publicará después de su aprobación. Puedes editarlo o retirarlo desde tu cuenta.</p><button :disabled="busy">Enviar comentario</button></form>
    <p v-if="message" role="status" class="notice">{{ message }}</p><p v-if="error" role="alert" class="notice error">{{ error }}</p>
  </section>
</template>
