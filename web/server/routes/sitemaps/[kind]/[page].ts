import { inventory, urlset } from '../../../utils/seo'
export default defineEventHandler(async (event) => {
  const kind = getRouterParam(event, 'kind') as 'articles' | 'topics'
  const rawPage = getRouterParam(event, 'page') || ''
  if (!['articles', 'topics'].includes(kind) || !/^[1-9][0-9]{0,3}$/.test(rawPage)) throw createError({ statusCode: 404 })
  const page = Number(rawPage)
  const data = await inventory(event)
  if (page > Math.ceil(data[kind] / 5000)) throw createError({ statusCode: 404 })
  let entries: { slug: string; updated_at: string }[]
  try { entries = await $fetch<{ slug: string; updated_at: string }[]>(`${useRuntimeConfig(event).apiBase}/seo/entries`, { query: { kind, page } }) }
  catch { throw createError({ statusCode: 503, statusMessage: 'Sitemap temporalmente no disponible' }) }
  return urlset(event, entries.map(e => ({ path: `/${kind === 'articles' ? 'articulos' : 'tema'}/${encodeURIComponent(e.slug)}`, updated_at: e.updated_at })))
})
