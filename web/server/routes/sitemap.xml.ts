import { xmlEscape, inventory } from '../utils/seo'
export default defineEventHandler(async (event) => {
  const data = await inventory(event)
  const paths = ['/sitemap-pages.xml']
  for (const kind of ['articles', 'topics'] as const) {
    for (let page = 1; page <= Math.ceil(data[kind] / 5000); page++) paths.push(`/sitemaps/${kind}/${page}`)
  }
  setHeaders(event, { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'no-store' })
  return `<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${paths.map(p => `<sitemap><loc>${xmlEscape(useRuntimeConfig(event).public.siteUrl + p)}</loc></sitemap>`).join('')}</sitemapindex>`
})
