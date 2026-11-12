<script setup lang="ts">
import type { EditorialArticle } from '~/utils/blog'
const props = defineProps<{ initial?: EditorialArticle }>()
const emit = defineEmits<{ saved: [EditorialArticle] }>()

const empty: EditorialArticle = { slug: '', title: '', summary: '', body: '', section: 'actualidad', author_name: '', sources: [] }
const form = reactive<EditorialArticle>(JSON.parse(JSON.stringify(props.initial ?? empty)))
const preview = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')
const slugTouched = ref(Boolean(props.initial?.slug))
const isPublished = computed(() => form.status === 'published')
const isSlugLocked = computed(() => Boolean(form.published_at))

const slugify = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 180)
watch(() => form.title, (title) => { if (!slugTouched.value && !isPublished.value) form.slug = slugify(title) })

const addSource = () => form.sources.push({ title: '', url: '', language: 'en' })
const removeSource = (i: number) => form.sources.splice(i, 1)

const describe = (e: any) => {
  const detail = e?.data?.detail
  if (Array.isArray(detail)) return detail.map((d: any) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join(' · ')
  return typeof detail === 'string' ? detail : 'No se pudo guardar. Revisa los campos.'
}

async function save () {
  saving.value = true; message.value = ''; error.value = ''
  const payload = { slug: form.slug, title: form.title, summary: form.summary, body: form.body, section: form.section, author_name: form.author_name, sources: form.sources, ...(form.id ? { comments_enabled: form.comments_enabled ?? true } : {}) }
  try {
    const saved = form.id
      ? await $fetch<EditorialArticle>(`/api/editorial/articles/${form.id}`, { method: 'PATCH', body: payload, headers: accountHeaders() })
      : await $fetch<EditorialArticle>('/api/editorial/articles', { method: 'POST', body: payload, headers: accountHeaders() })
    Object.assign(form, saved)
    message.value = 'Cambios guardados.'
    emit('saved', saved)
  } catch (e) { error.value = describe(e) } finally { saving.value = false }
}

async function changeStatus (status: string) {
  if (!form.id) return
  if (status === 'published' && !confirm('¿Publicar este artículo? Será visible para todo el mundo.')) return
  saving.value = true; message.value = ''; error.value = ''
  try {
    const saved = await $fetch<EditorialArticle>(`/api/editorial/articles/${form.id}/status`, { method: 'POST', body: { status }, headers: accountHeaders() })
    Object.assign(form, saved)
    message.value = `Estado actualizado: ${STATUS_LABELS[saved.status ?? 'draft']}.`
  } catch (e) { error.value = describe(e) } finally { saving.value = false }
}

const actions = computed<Array<[string, string]>>(() => ({
  draft: [['review', 'Enviar a revisión'], ['archived', 'Archivar']],
  review: [['published', 'Aprobar y publicar'], ['draft', 'Devolver a borrador'], ['archived', 'Archivar']],
  published: [['archived', 'Retirar (archivar)'], ['draft', 'Despublicar a borrador']],
  archived: [['draft', 'Recuperar como borrador']]
} as Record<string, Array<[string, string]>>)[form.status ?? 'draft'] ?? [])
</script>

<template>
  <div class="editor">
    <div class="editor-bar">
      <span v-if="form.status" class="badge" :data-status="form.status">{{ STATUS_LABELS[form.status] }}</span>
      <button type="button" class="secondary" @click="preview = !preview">{{ preview ? 'Volver a editar' : 'Previsualizar' }}</button>
      <NuxtLink v-if="isPublished" :to="`/articulos/${form.slug}`" target="_blank">Ver publicado ↗</NuxtLink>
    </div>
    <p v-if="message" class="notice" role="status">{{ message }}</p>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>

    <article v-if="preview" class="article preview">
      <p class="eyebrow">{{ sectionName(form.section) }} · Vista previa</p>
      <h1>{{ form.title || 'Sin título' }}</h1>
      <p class="lead">{{ form.summary }}</p>
      <p class="muted">Por {{ form.author_name || '—' }}</p>
      <ArticleBody :body="form.body" />
      <section v-if="form.sources.length" class="sources"><h2>Fuentes originales</h2>
        <ol><li v-for="(s, i) in form.sources" :key="i">{{ s.title }} — <span class="muted">{{ s.url }}</span> ({{ languageName(s.language) }})</li></ol>
      </section>
    </article>

    <form v-else class="form" @submit.prevent="save">
      <label v-if="form.id" class="checkbox-label"><input v-model="form.comments_enabled" type="checkbox">Permitir nuevos comentarios</label>
      <label>Título <input v-model="form.title" required minlength="10" maxlength="180"></label>
      <label>Slug (URL) <input v-model="form.slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxlength="180" :readonly="isSlugLocked" @input="slugTouched = true">
        <small class="muted">/articulos/{{ form.slug || '…' }}<template v-if="isSlugLocked"> · No editable una vez publicado.</template></small></label>
      <div class="row">
        <label>Sección <select v-model="form.section"><option v-for="s in SECTIONS" :key="s.slug" :value="s.slug">{{ s.name }}</option></select></label>
        <label>Autor <input v-model="form.author_name" required minlength="2" maxlength="80"></label>
      </div>
      <label>Resumen / meta descripción <textarea v-model="form.summary" required minlength="50" maxlength="300" rows="3" />
        <small class="muted">{{ form.summary.length }}/300 · mínimo 50</small></label>
      <label>Cuerpo <textarea v-model="form.body" required rows="22" class="mono" />
        <small class="muted">Formato: párrafos separados por línea en blanco, «## » y «### » para títulos, «- » para listas y ``` para código. No se admite HTML. {{ form.body.length }} caracteres (mínimo 300 para publicar).</small></label>
      <fieldset>
        <legend>Fuentes originales</legend>
        <div v-for="(s, i) in form.sources" :key="i" class="row source-row">
          <label>Título <input v-model="s.title" required maxlength="200"></label>
          <label>URL <input v-model="s.url" required type="url" maxlength="2000"></label>
          <label>Idioma <select v-model="s.language"><option value="en">Inglés</option><option value="es">Español</option><option value="fr">Francés</option><option value="de">Alemán</option></select></label>
          <button type="button" class="secondary" :aria-label="`Quitar fuente ${i + 1}`" @click="removeSource(i)">Quitar</button>
        </div>
        <button type="button" class="secondary" @click="addSource">Añadir fuente</button>
      </fieldset>
      <button type="submit" :disabled="saving">{{ form.id ? 'Guardar cambios' : 'Crear borrador' }}</button>
    </form>

    <div v-if="form.id" class="status-actions">
      <h2>Flujo editorial</h2>
      <p class="muted small">Para publicar: guarda, envía a revisión y aprueba. Se exige al menos una fuente.</p>
      <button v-for="[status, label] in actions" :key="status" type="button" :class="status === 'published' ? '' : 'secondary'" :disabled="saving" @click="changeStatus(status)">{{ label }}</button>
    </div>
  </div>
</template>
