export default defineEventHandler((event) => {
  setHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  const site = useRuntimeConfig().public.siteUrl
  return `User-agent: *\nAllow: /\nSitemap: ${site}/sitemap.xml\n`
})
