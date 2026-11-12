<script setup lang="ts">
import { INFORMATION } from '~/utils/information'
const slug = String(useRoute().params.slug)
const info = Object.prototype.hasOwnProperty.call(INFORMATION, slug) ? INFORMATION[slug] : undefined
if (!info) throw createError({ statusCode: 404, statusMessage: 'Página no encontrada' })
const config = useRuntimeConfig().public
const needsOwner = ['aviso-legal', 'privacidad'].includes(slug)
const ownerReady = Boolean(config.legalName && config.legalAddress && config.legalTaxId)
const analyticsReady = String(config.analyticsEnabled) === 'true' && /^G-[A-Z0-9]{6,20}$/.test(config.ga4Id) && ownerReady
useSeoMeta({ title: `${info.title} | Foro IA al Día`, description: info.description,
  ogTitle: `${info.title} | Foro IA al Día`, ogDescription: info.description, ogType: 'website', ogUrl: `${config.siteUrl}/informacion/${slug}`,
  robots: needsOwner && !ownerReady ? 'noindex, follow' : undefined })
useHead({ link: [{ rel: 'canonical', href: `${config.siteUrl}/informacion/${slug}` }] })
</script>
<template>
  <article class="article information-page">
    <p class="eyebrow">Foro IA al Día</p><h1>{{ info.title }}</h1>
    <p class="muted">Actualizado el 23 de octubre de 2026</p>
    <div v-if="needsOwner" class="notice">
      <template v-if="ownerReady"><p><strong>Titular:</strong> {{ config.legalName }}</p><p><strong>Dirección:</strong> {{ config.legalAddress }}</p><p><strong>Identificación fiscal:</strong> {{ config.legalTaxId }}</p></template>
      <p v-else>La identificación del titular está pendiente de confirmar. Esta página está en preparación y no debe considerarse una política final aprobada.</p>
    </div>
    <p>Contacto: <a href="mailto:admin@foroiaaldia.com">admin@foroiaaldia.com</a>.</p>
    <div class="prose"><section v-for="block in info.blocks" :key="block.heading"><h2>{{ block.heading }}</h2><p v-for="text in block.text" :key="text">{{ text }}</p></section></div>
    <p v-if="slug === 'privacidad'"><a href="https://www.aepd.es/derechos-y-deberes/ejerce-tus-derechos" rel="noopener noreferrer">Información de la AEPD sobre derechos</a>.</p>
    <section v-if="['cookies', 'privacidad'].includes(slug)"><h2>Analítica opcional</h2><p v-if="analyticsReady">Google Analytics está disponible únicamente si aceptas la analítica. Envía datos de navegación de páginas públicas a Google; no incluimos datos de formularios ni identificadores de cuenta. Para atribuir el origen se usa únicamente el origen externo (sin ruta ni consulta), campañas de una lista cerrada y paginación numérica; se eliminan los demás parámetros y fragmentos de URL. Puedes rechazarla o retirar tu consentimiento en «Preferencias de analítica». La elección se conserva en este navegador durante un máximo de 180 días. Google puede establecer cookies _ga para distinguir navegadores, con duración controlada por la configuración del servicio; el responsable debe documentar también su configuración de conservación y transferencias antes de activarlo.</p><p v-else>Google Analytics está desactivado. No se carga su código ni se envían eventos a Google.</p></section>
  </article>
</template>
