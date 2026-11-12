// Sesiones y roles validados en servidor antes de servir el panel.
export default defineEventHandler(async (event) => {
  const path = event.path.split('?')[0] || '/'
  const editorial = /^\/(editorial|api\/editorial)(\/|$)/.test(path)
  const moderation = path === '/moderacion'
  if (!editorial && !moderation) return
  setHeaders(event, { 'X-Robots-Tag': 'noindex, nofollow', 'Cache-Control': 'no-store', 'Referrer-Policy': 'same-origin' })
  const config = useRuntimeConfig(event)
  const response = await $fetch.raw<{ role: string, verified: boolean }>(`${config.apiBase}/auth/me`, {
    headers: { cookie: getHeader(event, 'cookie') || '' }, ignoreResponseError: true
  })
  if (response.status === 401) {
    if (!path.startsWith('/api/')) return sendRedirect(event, '/cuenta', 302)
    throw createError({ statusCode: 401, statusMessage: 'Inicia sesion' })
  }
  const roles = moderation ? ['moderator', 'admin'] : ['editor', 'admin']
  if (response.status !== 200 || !response._data?.verified || !roles.includes(response._data.role)) {
    throw createError({ statusCode: 403, statusMessage: 'Permisos insuficientes' })
  }
})
