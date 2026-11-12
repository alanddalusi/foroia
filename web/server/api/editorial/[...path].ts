import { forwardCommunity } from '../../utils/community'
export default defineEventHandler((event) => {
  const path = getRouterParam(event, 'path') || ''
  if (!/^(?:articles(?:\/[1-9][0-9]{0,9}(?:\/status)?)?|research(?:\/signals|\/executions(?:\/[1-9][0-9]{0,9}\/(?:confirm|cancel))?)?)$/.test(path)) {
    throw createError({ statusCode: 404, statusMessage: 'Ruta no encontrada' })
  }
  if (!['GET', 'POST', 'PATCH'].includes(event.method)) {
    throw createError({ statusCode: 405, statusMessage: 'Metodo no permitido' })
  }
  return forwardCommunity(event, `editorial/${path}`)
})
