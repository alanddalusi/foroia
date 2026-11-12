export default defineEventHandler((event) => {
  const url = getRequestURL(event)
  const match = /^\/blog\/(actualidad|herramientas|programacion|tutoriales)\/?$/.exec(url.pathname)
  if (match) return sendRedirect(event, `/${match[1]}${url.search}`, 301)
})
