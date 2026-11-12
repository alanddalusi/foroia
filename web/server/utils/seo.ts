import type { H3Event } from 'h3'
export const xmlEscape = (v: string) => v.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;')
export async function inventory(event: H3Event) {
  try { return await $fetch<{ articles: number; topics: number; sections: string[] }>(`${useRuntimeConfig(event).apiBase}/seo/inventory`) }
  catch { throw createError({ statusCode: 503, statusMessage: 'Sitemap temporalmente no disponible' }) }
}
export function urlset(event: H3Event, entries: { path: string; updated_at?: string }[]) {
  setHeaders(event, { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'no-store' })
  const base = useRuntimeConfig(event).public.siteUrl
  return `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries.map(e => `<url><loc>${xmlEscape(base + e.path)}</loc>${e.updated_at ? `<lastmod>${xmlEscape(new Date(e.updated_at).toISOString())}</lastmod>` : ''}</url>`).join('')}</urlset>`
}
