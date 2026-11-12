// No anunciar el framework en las cabeceras (X-Powered-By: Nuxt).
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('beforeResponse', (event) => {
    event.node.res.removeHeader('x-powered-by')
  })
  nitroApp.hooks.hook('render:response', (response) => {
    if (response.headers) {
      delete response.headers['x-powered-by']
      delete response.headers['X-Powered-By']
    }
  })
})
