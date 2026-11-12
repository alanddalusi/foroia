<script setup lang="ts">
const props = defineProps<{ code: string; language?: string }>()
const status = ref('')
async function copy() {
  try { await navigator.clipboard.writeText(props.code); status.value = 'Código copiado' }
  catch { status.value = 'Selecciona el código para copiarlo' }
}
</script>
<template>
  <div class="article-code">
    <div class="code-toolbar"><span>{{ language || 'Código' }}</span><button type="button" @click="copy">Copiar código</button></div>
    <pre tabindex="0" role="region" :aria-label="`Código ${language || ''}; desplazamiento horizontal disponible`"><code>{{ code }}</code></pre>
    <span class="sr-only" role="status">{{ status }}</span>
  </div>
</template>
<style scoped>
.article-code { margin: 1.6em 0; max-width: 100%; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; font-family: var(--sans) }
.code-toolbar { display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 14px;background:var(--soft);font:13px ui-monospace,monospace;border-bottom:1px solid var(--rule) }
.code-toolbar button { font:inherit;padding:6px 10px;min-height:36px;background:var(--paper);color:var(--ink);border:1px solid var(--rule);border-radius:3px }
.article-code pre { margin:0;border:0;background:#f1f2ed;padding:20px;font-size:14px;line-height:1.75;overflow:auto;max-width:100% }
</style>
