<script setup lang="ts">
import { articleInline } from '../utils/article-inline'
defineProps<{ text: string }>()
</script>
<template>
  <template v-for="(part, i) in articleInline(text)" :key="i">
    <sup v-if="part.style === 'cite'" class="cite"><a :href="part.href" title="Ver las fuentes originales">{{ part.text }}</a></sup>
    <a v-else-if="part.href" :href="part.href">{{ part.text }}</a>
    <code v-else-if="part.style === 'code'">{{ part.text }}</code>
    <strong v-else-if="part.style === 'strong'">{{ part.text }}</strong>
    <template v-else>{{ part.text }}</template>
  </template>
</template>
