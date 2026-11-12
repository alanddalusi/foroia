import type { H3Event } from 'h3'
import { Buffer } from 'node:buffer'
import { isIP } from 'node:net'

export async function forwardCommunity(event: H3Event, path: string) {
  const config = useRuntimeConfig(event)
  const forwarded = getHeader(event, 'x-foroia-client-ip') || ''
  const clientIp = config.trustedProxyHeaders && isIP(forwarded)
    ? forwarded : getRequestIP(event, { xForwardedFor: false }) || 'unknown'
  let body: unknown
  if (!['GET', 'HEAD'].includes(event.method)) {
    const chunks: Buffer[] = []
    let size = 0
    for await (const chunk of event.node.req) {
      const data = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
      size += data.length
      if (size > 300_000) throw createError({ statusCode: 413, statusMessage: 'Contenido demasiado grande' })
      chunks.push(data)
    }
    try { body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}') }
    catch { throw createError({ statusCode: 400, statusMessage: 'JSON no válido' }) }
  }
  const response = await $fetch.raw(`${config.apiBase}/${path}`, {
    method: event.method as 'GET' | 'POST' | 'PATCH' | 'DELETE',
    query: getQuery(event), body: body as any,
    headers: {
      cookie: getHeader(event, 'cookie') || '', origin: getHeader(event, 'origin') || '',
      'content-type': getHeader(event, 'content-type') || '', 'x-csrf-token': getHeader(event, 'x-csrf-token') || '',
      'x-internal-token': config.editorialApiToken as string,
      'x-client-ip': clientIp
    }, ignoreResponseError: true
  })
  for (const cookie of response.headers.getSetCookie()) appendResponseHeader(event, 'set-cookie', cookie)
  setHeader(event, 'cache-control', 'no-store'); setHeader(event, 'x-robots-tag', 'noindex, nofollow')
  if (response.headers.has('retry-after')) setHeader(event, 'retry-after', Number(response.headers.get('retry-after')))
  setResponseStatus(event, response.status)
  return response._data
}
