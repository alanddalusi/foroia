<script setup lang="ts">
import type { ArticlePage } from '~/utils/blog'
const config = useRuntimeConfig()
const url = `${config.public.siteUrl}${AUTHOR.path}`
const { data } = await useAsyncData('author-latest', () => $fetch<ArticlePage>('/api/articles', { query: { limit: 12 } }))
const items = computed(() => data.value?.items ?? [])
const description = 'Quién escribe Foro IA al Día, cómo se elaboran los artículos con asistencia de IA y qué controles de calidad y fuentes se aplican.'
useSeoMeta({ title: seoTitle('Redacción y método editorial'), description, ogTitle: 'Redacción de Foro IA al Día', ogDescription: description, ogType: 'profile', ogUrl: url })
useHead({ link: [{ rel: 'canonical', href: url }], script: [{ type: 'application/ld+json', innerHTML: jsonLd({
  '@context': 'https://schema.org', '@type': 'ProfilePage', url, inLanguage: 'es',
  mainEntity: { '@type': 'Organization', name: AUTHOR.name, url, parentOrganization: { '@type': 'Organization', name: 'Foro IA al Día', url: `${config.public.siteUrl}/` },
    knowsAbout: ['Inteligencia artificial', 'Python', 'APIs de modelos de lenguaje', 'OpenAI', 'Gemini', 'Claude'] }
}) }] })
</script>
<template>
  <div class="author-page">
    <nav aria-label="Migas de pan" class="breadcrumbs"><NuxtLink to="/">Inicio</NuxtLink> › Redacción</nav>
    <header><p class="eyebrow">Autoría</p><h1>Redacción de Foro IA al Día</h1>
      <p class="lead">Explicamos en español qué ocurre en inteligencia artificial y cómo usarla en la práctica, con fuentes originales y límites claros.</p></header>
    <section>
      <h2>Cómo trabajamos</h2>
      <p>Los artículos se preparan con asistencia de IA a partir de documentación oficial y comunicados originales. Antes de publicarse pasan controles automáticos: cada afirmación debe apoyarse en una fuente citada, se rechazan cifras sin respaldo y un segundo proceso revisa el texto frente a esas fuentes.</p>
      <p>Los ejemplos de código marcados como reproducibles se ejecutan en un entorno aislado. Cuando algo es una recomendación nuestra y no un hecho documentado, lo indicamos.</p>
      <p>Al final de cada artículo se indica si ha tenido revisión humana. Puedes leer el <NuxtLink to="/informacion/criterio-editorial">criterio editorial completo</NuxtLink> o <NuxtLink to="/informacion/contacto">avisarnos de un error</NuxtLink>.</p>
    </section>
    <section>
      <h2>Temas</h2>
      <ul><li><NuxtLink to="/programacion">Programar con IA en Python</NuxtLink></li><li><NuxtLink to="/herramientas">Herramientas: ChatGPT, Gemini y Claude</NuxtLink></li>
        <li><NuxtLink to="/tutoriales">Tutoriales paso a paso</NuxtLink></li><li><NuxtLink to="/actualidad">Noticias de IA</NuxtLink></li></ul>
    </section>
    <section v-if="items.length" aria-labelledby="ultimos"><h2 id="ultimos">Últimos artículos</h2>
      <div class="cards"><ArticleCard v-for="a in items" :key="a.slug" :article="a" /></div></section>
  </div>
</template>
<style scoped>
.author-page > header, .author-page > section:not(:last-child) { max-width:760px }.author-page section { margin:28px 0;font:16px/1.7 system-ui,sans-serif }
</style>
