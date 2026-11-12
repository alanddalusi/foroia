import { normalizePrefetchHead } from '../utils/prefetch'

// Nitro's public hook; no vendor edits, dependency upgrades or prefetch removal.
export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('render:html', (html) => {
    html.head = html.head.map(normalizePrefetchHead)
  })
})
