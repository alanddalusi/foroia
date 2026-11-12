// Count successful HTML document loads only. Never forward visitor identifiers.
export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('afterResponse', async (event) => {
    const path = getRequestURL(event).pathname
    if (event.method !== 'GET' || event.node.res.statusCode !== 200) return
    if (!getHeader(event, 'accept')?.includes('text/html')) return
    if (getHeader(event, 'cookie')?.includes('foroia_session=')) return
    const agent = getHeader(event, 'user-agent') || ''
    if (!agent || /bot|crawler|spider|headless|preview|monitor|curl|wget|python|httpx/i.test(agent)) return
    if (!(path === '/' || /^\/(actualidad|herramientas|programacion|tutoriales)$/.test(path)
      || /^\/articulos\/[a-z0-9-]{1,180}$/.test(path))) return
    const config = useRuntimeConfig(event)
    if (!config.editorialApiToken) return
    try {
      await $fetch(`${config.apiBase}/internal/page-view`, {
        method: 'POST', body: { path }, timeout: 1500, retry: 0,
        headers: { 'x-internal-token': config.editorialApiToken as string }
      })
    } catch {
      // Analytics failure must not break reading or leak request data into logs.
      console.warn('Aggregate page counter unavailable')
    }
  })
})
