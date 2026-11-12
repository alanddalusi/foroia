<script setup lang="ts">
useSeoMeta({ title: 'Tu cuenta | ForoIA', robots: 'noindex, nofollow' })
const { user, refreshAccount } = useAccount()
const publicConfig = useRuntimeConfig().public
const availableActions = computed(() => ['login',
  ...(publicConfig.registrationEnabled && publicConfig.accountEmailEnabled ? ['register'] : []),
  ...(publicConfig.accountEmailEnabled ? ['forgot', 'resend'] : [])])
const mode = ref('login'), email = ref(''), password = ref(''), name = ref(''), message = ref(''), error = ref(''), busy = ref(false), token = ref('')
const comments = ref<any[]>([]), next = ref<string | null>(null)
const labels: Record<string, string> = { login: 'Iniciar sesión', register: 'Crear cuenta', forgot: 'Recuperar contraseña', resend: 'Reenviar verificación', verify: 'Verificar correo', reset: 'Guardar nueva contraseña' }
function readToken() {
  const fragment = new URLSearchParams(location.hash.slice(1))
  for (const action of ['verify', 'reset']) if (fragment.has(action)) { mode.value = action; token.value = fragment.get(action)!; history.replaceState(null, '', location.pathname) }
}
onMounted(async () => {
  readToken()
  window.addEventListener('hashchange', readToken)
  await refreshAccount()
  if (user.value) await loadComments()
})
onUnmounted(() => window.removeEventListener('hashchange', readToken))
async function loadComments(cursor?: string) {
  try {
    const page = await $fetch<any>('/api/community/auth/comments', { query: cursor ? { cursor } : undefined })
    comments.value = cursor ? [...comments.value, ...page.items] : page.items; next.value = page.next_cursor
  } catch (e) { error.value = accountError(e) }
}
async function submit() {
  busy.value = true; message.value = ''; error.value = ''
  const action = mode.value
  const body = action === 'register' ? { email: email.value, password: password.value, display_name: name.value }
    : action === 'login' ? { email: email.value, password: password.value }
    : action === 'verify' ? { token: token.value }
    : action === 'reset' ? { token: token.value, password: password.value } : { email: email.value }
  try {
    const result = await $fetch<any>(`/api/community/auth/${action}`, { method: 'POST', body })
    message.value = result.message || 'Sesión iniciada.'; password.value = ''
    await refreshAccount()
    if (user.value) await loadComments()
    if (['verify', 'reset'].includes(action)) { token.value = ''; mode.value = 'login' }
  } catch (e) { error.value = accountError(e) } finally { busy.value = false }
}
async function logout() {
  try {
    await $fetch('/api/community/auth/logout', { method: 'POST', body: {}, headers: accountHeaders() })
    user.value = null; comments.value = []; message.value = 'Sesión cerrada.'
  } catch (e) { error.value = accountError(e) }
}
async function changeComment(comment: any, remove = false) {
  const body = remove ? undefined : prompt('Edita tu comentario; volverá a moderación.', comment.body)
  if (!remove && body === null) return
  try {
    await $fetch(`/api/community/comments/${comment.id}`, { method: remove ? 'DELETE' : 'PATCH', headers: accountHeaders(), body: remove ? {} : { body } })
    await loadComments(); message.value = remove ? 'Comentario retirado.' : 'Cambios enviados a moderación.'
  } catch (e) { error.value = accountError(e) }
}
</script>
<template>
  <div class="account-page"><h1>Tu cuenta</h1>
    <p v-if="message" class="notice" role="status">{{ message }}</p><p v-if="error" class="notice error" role="alert">{{ error }}</p>
    <template v-if="user && !['verify','reset'].includes(mode)">
      <p>Hola, {{ user.display_name }}. Rol: {{ user.role }}.</p><p v-if="!user.verified">Verifica tu correo antes de comentar.</p>
      <div class="editor-bar">
        <NuxtLink v-if="user.verified && ['editor','admin'].includes(user.role)" to="/editorial">Panel editorial</NuxtLink>
        <NuxtLink v-if="user.verified && ['moderator','admin'].includes(user.role)" to="/moderacion">Moderar comentarios</NuxtLink>
        <button type="button" class="secondary" @click="logout">Cerrar sesión</button>
      </div>
      <h2>Mis comentarios</h2><p v-if="!comments.length">Todavía no has enviado comentarios.</p>
      <article v-for="comment in comments" :key="comment.id" class="comment">
        <NuxtLink :to="`/articulos/${comment.article_slug}`">Ver artículo</NuxtLink><p class="comment-text">{{ comment.body }}</p><p>Estado: {{ comment.status }}</p>
        <div v-if="comment.status !== 'removed'" class="editor-bar"><button class="secondary" @click="changeComment(comment)">Editar</button><button class="secondary" @click="changeComment(comment, true)">Retirar</button></div>
      </article>
      <button v-if="next" class="secondary" @click="loadComments(next!)">Más comentarios</button>
    </template>
    <form v-else class="form account-form" @submit.prevent="submit">
      <p v-if="!publicConfig.registrationEnabled" class="notice">Las nuevas cuentas están temporalmente cerradas. Puedes leer el blog sin registrarte.</p>
      <p v-if="!publicConfig.accountEmailEnabled" class="muted">La recuperación por correo aún no está disponible. Contacto: <a href="mailto:admin@foroiaaldia.com">admin@foroiaaldia.com</a>.</p>
      <label v-if="!token">Acción<select v-model="mode"><option v-for="key in availableActions" :key="key" :value="key">{{ labels[key] }}</option></select></label>
      <label v-if="!['verify','reset'].includes(mode)">Correo electrónico<input v-model="email" type="email" autocomplete="email" required maxlength="254"></label>
      <label v-if="mode === 'register'">Nombre público<input v-model="name" required minlength="2" maxlength="80" autocomplete="nickname"></label>
      <label v-if="['login','register','reset'].includes(mode)">Contraseña<input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required minlength="12" maxlength="128"></label>
      <p v-if="mode === 'register'" class="muted">Usa una contraseña única de al menos 12 caracteres. Te enviaremos un enlace para verificar tu correo.</p>
      <button :disabled="busy">{{ labels[mode] }}</button>
    </form>
  </div>
</template>
