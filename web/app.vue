<script setup lang="ts">
const { user, refreshAccount } = useAccount()
// Query changes need fresh page data; an in-page anchor must keep media/audio mounted.
const pageKey = (route: { fullPath: string }) => route.fullPath.split('#')[0] || '/'
onMounted(refreshAccount)
const config = useRuntimeConfig()
useSeoMeta({ ogSiteName: 'Foro IA al Día', ogLocale: 'es_ES', ogImage: `${config.public.siteUrl}/images/actualidad.png`, twitterCard: 'summary_large_image' })
if (/^[a-zA-Z0-9_-]{10,200}$/.test(config.public.googleSiteVerification)) {
  useHead({ meta: [{ name: 'google-site-verification', content: config.public.googleSiteVerification }] })
}
</script>
<template>
  <div>
    <a class="skip" href="#contenido">Saltar al contenido</a>
    <header class="site-header">
      <div class="masthead">
        <div class="masthead-top"><span>Blog y comunidad · En español</span><span class="masthead-actions"><NuxtLink to="/buscar">Buscar</NuxtLink><NuxtLink to="/cuenta">{{ user ? 'Mi cuenta' : 'Iniciar sesión' }}</NuxtLink></span></div>
        <div class="masthead-title">
          <NuxtLink to="/" class="brand">Foro IA<span aria-hidden="true">.</span><span class="brand-edition">al Día</span></NuxtLink>
          <p>Inteligencia artificial,<br>aprendizaje y conversación.</p>
        </div>
      <nav aria-label="Principal">
        <ul class="nav-links">
          <li><NuxtLink to="/">Portada</NuxtLink></li>
          <li v-for="s in SECTIONS" :key="s.slug"><NuxtLink :to="`/${s.slug}`">{{ s.name }}</NuxtLink></li>
          <li><a href="/foro">Foro</a></li>
        </ul>
      </nav>
      </div>
    </header>
    <main id="contenido" tabindex="-1"><NuxtPage :page-key="pageKey" /></main>
    <footer class="site-footer"><div class="footer-inner">
      <div><p class="footer-brand">Foro IA al Día.</p><p>Un lugar para entender la IA<br>y compartir lo aprendido.</p></div>
      <nav aria-label="Al pie de página"><NuxtLink to="/tutoriales">Guías y tutoriales</NuxtLink><NuxtLink to="/foro">La comunidad</NuxtLink><NuxtLink to="/cuenta">Tu cuenta</NuxtLink><a href="/rss.xml">Suscríbete por RSS</a></nav>
      <nav aria-label="Información de la publicación"><NuxtLink to="/informacion/contacto">Contacto</NuxtLink><NuxtLink to="/informacion/criterio-editorial">Criterio editorial</NuxtLink><NuxtLink to="/informacion/normas">Normas</NuxtLink><NuxtLink to="/informacion/aviso-legal">Aviso legal</NuxtLink><NuxtLink to="/informacion/privacidad">Privacidad</NuxtLink><NuxtLink to="/informacion/cookies">Cookies</NuxtLink></nav>
      <p class="footer-note">Inteligencia artificial en español.<br>Fuentes abiertas y lectura crítica.</p>
    </div></footer>
    <AnalyticsConsent />
  </div>
</template>
