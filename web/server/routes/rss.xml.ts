import { xmlEscape } from '../utils/seo'
// RSS 2.0 con los últimos artículos publicados: título, enlace, resumen, sección y fecha.
type Item = { slug: string; title: string; summary: string; section: string; published_at: string | null; updated_at: string }
const SECTION_NAMES: Record<string, string> = { actualidad: 'Actualidad', herramientas: 'Herramientas', programacion: 'Programación', tutoriales: 'Tutoriales' }
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  let items: Item[]
  try { items = (await $fetch<{ items: Item[] }>(`${config.apiBase}/articles`, { query: { limit: 30 } })).items }
  catch { throw createError({ statusCode: 503, statusMessage: 'RSS temporalmente no disponible' }) }
  const site = config.public.siteUrl
  const date = (iso: string | null) => new Date(iso || Date.now()).toUTCString()
  setHeaders(event, { 'Content-Type': 'application/rss+xml; charset=utf-8', 'Cache-Control': 'no-store' })
  const entries = items.map((a) => {
    const url = `${site}/articulos/${a.slug}`
    return `<item><title>${xmlEscape(a.title)}</title><link>${xmlEscape(url)}</link><guid isPermaLink="true">${xmlEscape(url)}</guid>`
      + `<description>${xmlEscape(a.summary)}</description><category>${xmlEscape(SECTION_NAMES[a.section] ?? a.section)}</category>`
      + `<pubDate>${date(a.published_at)}</pubDate></item>`
  }).join('')
  return `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>`
    + `<title>Foro IA al Día</title><link>${xmlEscape(site)}/</link>`
    + `<description>Inteligencia artificial en español: noticias con fuentes, guías, herramientas y programación.</description>`
    + `<language>es</language><atom:link href="${xmlEscape(site)}/rss.xml" rel="self" type="application/rss+xml"/>`
    + (items[0] ? `<lastBuildDate>${date(items[0].updated_at)}</lastBuildDate>` : '')
    + `${entries}</channel></rss>`
})
