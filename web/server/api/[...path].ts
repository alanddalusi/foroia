// Solo expone las rutas públicas de lectura; el destino permanece en el servidor.
export default defineEventHandler((event) => {
  if (event.method !== 'GET') {
    throw createError({ statusCode: 405, statusMessage: 'Método no permitido' })
  }
  const path = getRouterParam(event, 'path') || ''
  if (!/^(categories(?:\/[a-z0-9-]+\/topics)?|topics(?:\/[a-z0-9-]+)?|sections|search|articles(?:\/[a-z0-9-]+)?|article-assets\/[a-f0-9]{32}-(480|800|1200)\.(png|webp))$/.test(path)) {
    throw createError({ statusCode: 404, statusMessage: 'Ruta no encontrada' })
  }
  const config = useRuntimeConfig(event)
  return proxyRequest(event, `${config.apiBase}/${path}${getRequestURL(event).search}`)
})
