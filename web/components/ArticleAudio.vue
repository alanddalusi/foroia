<script setup lang="ts">
import { articleSpeech } from '~/utils/article-blocks'
const props = defineProps<{ title: string; body: string }>()
const available = ref(false), playing = ref(false), paused = ref(false), message = ref('')
let voice: SpeechSynthesisVoice | undefined, chunks: string[] = [], index = 0, utterance: SpeechSynthesisUtterance | null = null
function refresh() { voice = window.speechSynthesis.getVoices().find(v => v.localService && /^es(?:-|$)/i.test(v.lang)); available.value = !!voice }
function stop() { playing.value = false; paused.value = false; chunks = []; window.speechSynthesis.cancel(); utterance = null }
function next() {
  if (!playing.value || index >= chunks.length) { playing.value = false; return }
  utterance = new SpeechSynthesisUtterance(chunks[index++]!); utterance.voice = voice || null; utterance.lang = voice?.lang || 'es-ES'
  utterance.onend = next; utterance.onerror = () => { playing.value = false; message.value = 'La lectura se ha detenido.' }
  window.speechSynthesis.speak(utterance)
}
function toggle() {
  if (playing.value) { paused.value = !paused.value; paused.value ? window.speechSynthesis.pause() : window.speechSynthesis.resume(); return }
  refresh(); if (!voice) return
  chunks = (props.title + '. ' + articleSpeech(props.body)).match(/[^.!?]{1,220}(?:[.!?]|\s|$)/g) || []; index = 0; playing.value = true; next()
}
onMounted(() => { if ('speechSynthesis' in window) { refresh(); window.speechSynthesis.addEventListener('voiceschanged', refresh) } })
onBeforeUnmount(() => { if ('speechSynthesis' in window) { window.speechSynthesis.removeEventListener('voiceschanged', refresh); if (playing.value) stop() } })
</script>
<template>
  <!-- Sin voz en español disponible no se muestra nada (antes aparecía un aviso en pleno artículo). -->
  <div v-if="available || playing" class="article-audio">
    <button type="button" :disabled="!available" :aria-pressed="playing" @click="toggle">{{ playing ? paused ? 'Continuar lectura' : 'Pausar lectura' : 'Escuchar artículo' }}</button>
    <button v-if="playing" type="button" @click="stop">Detener</button>
    <p class="small muted">Voz local de tu dispositivo. No se lee el código.</p>
    <span role="status" class="sr-only">{{ message }}</span>
  </div>
</template>
<style scoped>
.article-audio { margin:20px 0 }.article-audio button { padding:10px 14px;margin:0 8px 8px 0;min-height:44px;background:var(--paper);color:var(--ink);border:1px solid var(--rule);border-radius:4px;font-size:14px }.article-audio p { margin:0;font-size:12px }button:disabled { opacity:.65;cursor:default }
</style>
