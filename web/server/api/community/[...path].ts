import { forwardCommunity } from '../../utils/community'

export default defineEventHandler((event) => {
  const path = getRouterParam(event, 'path') || ''
  const rules: [RegExp, string[]][] = [
    [/^auth\/(login|register|logout|verify|forgot|reset|resend)$/, ['POST']],
    [/^auth\/(me|comments)$/, ['GET']],
    [/^articles\/[a-z0-9-]+\/comments$/, ['GET', 'POST']],
    [/^comments\/[1-9][0-9]{0,9}$/, ['PATCH', 'DELETE']],
    [/^moderation\/comments$/, ['GET']],
    [/^moderation\/comments\/[1-9][0-9]{0,9}$/, ['POST']]
  ]
  const rule = rules.find(([pattern]) => pattern.test(path))
  if (!rule) throw createError({ statusCode: 404, statusMessage: 'Ruta no encontrada' })
  if (!rule[1].includes(event.method)) throw createError({ statusCode: 405, statusMessage: 'Método no permitido' })
  return forwardCommunity(event, path)
})
