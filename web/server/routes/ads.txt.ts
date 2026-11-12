// No invented publisher IDs and no advertising scripts.
export default defineEventHandler((event) => {
  const id = useRuntimeConfig(event).adsPublisherId
  if (!/^pub-[0-9]{16}$/.test(id)) throw createError({ statusCode: 404 })
  setHeaders(event, { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' })
  return `google.com, ${id}, DIRECT, f08c47fec0942fa0\n`
})
