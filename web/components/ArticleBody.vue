<script setup lang="ts">
import { articleBlocks, splitTransparencyNotes } from '~/utils/article-blocks'
const props = defineProps<{ body: string }>()
// El cuerpo guardado no cambia: solo se presentan aparte las notas finales de elaboración.
const parts = computed(() => splitTransparencyNotes(articleBlocks(props.body)))
const blocks = computed(() => parts.value.blocks)
</script>
<template>
  <div class="prose">
    <template v-for="(b, n) in blocks" :key="n">
      <h2 v-if="b.type === 'h2'" :id="b.id"><ArticleInline :text="b.text || ''" /></h2>
      <h3 v-else-if="b.type === 'h3'" :id="b.id"><ArticleInline :text="b.text || ''" /></h3>
      <ul v-else-if="b.type === 'ul'"><li v-for="(item, k) in b.items" :key="k"><ArticleInline :text="item" /></li></ul>
      <ArticleCode v-else-if="b.type === 'code'" :code="b.text || ''" :language="b.lang" />
      <div v-else-if="b.type === 'table'" class="article-table" role="region" aria-label="Tabla del artículo; desplazamiento horizontal disponible" tabindex="0">
        <table><caption>Comparación: {{ b.headers?.join(' · ') }}</caption><thead><tr><th v-for="(cell, i) in b.headers" :key="i" scope="col"><ArticleInline :text="cell" /></th></tr></thead>
          <tbody><tr v-for="(row, i) in b.rows" :key="i"><td v-for="(cell, j) in row" :key="j"><ArticleInline :text="cell" /></td></tr></tbody></table>
      </div>
      <p v-else><ArticleInline :text="b.text || ''" /></p>
    </template>
    <!-- Decisión del propietario (12/11/2026): las notas finales de elaboración no se muestran en el
         artículo; el método sigue explicado en /autor/redaccion y /informacion/criterio-editorial.
         El cuerpo guardado no cambia. -->
    <p class="report-error"><NuxtLink to="/informacion/contacto">¿Has visto un error? Avísanos</NuxtLink></p>
  </div>
</template>
<style scoped>
h2,h3 { scroll-margin-top:24px }
.article-table { max-width:100%;overflow:auto;margin:24px 0;font:15px/1.6 system-ui,sans-serif }
table { border-collapse:collapse;width:100%;min-width:360px }caption { text-align:left;color:var(--muted);font-size:13px;padding-bottom:12px }
th,td { text-align:left;vertical-align:top;padding:13px;border-bottom:1px solid var(--rule) }th { background:var(--soft) }
.report-error { margin:28px 0 0;font:13px/1.6 system-ui,sans-serif;color:var(--muted) }
</style>
