import { inventory, urlset } from '../utils/seo'
export default defineEventHandler(async (event) => {
  const data = await inventory(event)
  let categories: { slug: string; published_topics: number }[]
  try { categories = await $fetch<{ slug: string; published_topics: number }[]>(`${useRuntimeConfig(event).apiBase}/categories`) }
  catch { throw createError({ statusCode: 503, statusMessage: 'Sitemap temporalmente no disponible' }) }
  const paths = ['/', '/autor/redaccion', ...['contacto', 'criterio-editorial', 'normas', 'cookies'].map(s => `/informacion/${s}`),
    ...data.sections.map(s => `/${encodeURIComponent(s)}`),
    ...categories.filter(c => c.published_topics > 0).map(c => `/categoria/${encodeURIComponent(c.slug)}`)]
  if (data.topics > 0) paths.push('/foro')
  return urlset(event, paths.map(path => ({ path })))
})
