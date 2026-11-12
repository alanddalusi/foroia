import process from 'node:process'
export default defineNuxtConfig({
  compatibilityDate: '2025-07-01',
  css: ['~/assets/css/main.css'],
  // CSS crítico (global + componentes, ~pocos KB) en línea en el HTML de SSR: evita la hoja que bloquea el renderizado.
  features: { inlineStyles: true },
  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE || 'http://localhost:8000',
    // Privados (solo servidor). Se sobrescriben con NUXT_EDITORIAL_API_TOKEN, NUXT_EDITORIAL_USER y NUXT_EDITORIAL_PASSWORD.
    editorialApiToken: '',
    editorialUser: '',
    editorialPassword: '',
    legacyEditorialEnabled: false,
    // Solo activar cuando Nuxt sea privado y Caddy sobrescriba la cabecera.
    trustedProxyHeaders: false,
    adsPublisherId: '',
    public: {
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3000',
      registrationEnabled: true,
      accountEmailEnabled: true,
      legalName: '', legalAddress: '', legalTaxId: '',
       googleSiteVerification: '', ga4Id: '', analyticsEnabled: false
    }
  },
  app: { head: {
    htmlAttrs: { lang: 'es' },
    // Discover exige permitir vistas previas grandes (portadas de 1200 px). Las páginas con
    // useSeoMeta({ robots: 'noindex…' }) sustituyen esta etiqueta: misma clave «robots».
    meta: [{ name: 'theme-color', content: '#f8f7f3' }, { name: 'robots', content: 'max-image-preview:large, max-snippet:-1, max-video-preview:-1' }],
    link: [
      { rel: 'icon', href: '/favicon.ico', sizes: '16x16 32x32 48x48' },
      { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg', sizes: 'any' },
      { rel: 'apple-touch-icon', href: '/apple-touch-icon.png', sizes: '180x180' },
      { rel: 'alternate', type: 'application/rss+xml', title: 'Foro IA al Día', href: '/rss.xml' }
    ]
  } },
  routeRules: {
    '/': { headers: { 'cache-control': 'no-store' } },
    '/categoria/**': { headers: { 'cache-control': 'no-store' } },
    '/tema/**': { headers: { 'cache-control': 'no-store' } },
    '/foro': { headers: { 'cache-control': 'no-store' } },
    '/actualidad': { headers: { 'cache-control': 'no-store' } },
    '/herramientas': { headers: { 'cache-control': 'no-store' } },
    '/programacion': { headers: { 'cache-control': 'no-store' } },
    '/tutoriales': { headers: { 'cache-control': 'no-store' } },
    '/images/**': { headers: { 'cache-control': 'public, max-age=86400' } },
    '/articulos/**': { headers: { 'cache-control': 'no-store' } },
    '/blog/**': { headers: { 'cache-control': 'no-store' } },
    '/sitemap.xml': { headers: { 'cache-control': 'no-store' } },
    '/rss.xml': { headers: { 'cache-control': 'no-store' } },
    // Búsqueda interna: útil para leer, nunca indexable.
    '/buscar': { headers: { 'cache-control': 'no-store', 'x-robots-tag': 'noindex, follow' } },
    '/api/**': { headers: { 'cache-control': 'no-store' } },
    '/cuenta': { ssr: false, headers: { 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } },
    '/moderacion': { ssr: false, headers: { 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } },
    // Panel privado: sin SSR ni caché compartida; datos cargados en el navegador tras la autenticación.
    '/editorial/**': { ssr: false, headers: { 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } },
    '/editorial': { ssr: false, headers: { 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } }
  }
})
