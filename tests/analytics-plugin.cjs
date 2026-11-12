// Run in the web build image (TypeScript is already a dev dependency).
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))

let hook
let calls = []
let fail = false
const context = {
  exports: {},
  defineNitroPlugin: fn => fn({ hooks: { hook: (_, callback) => { hook = callback } } }),
  getRequestURL: event => new URL(event.path, 'https://example.test'),
  getHeader: (event, key) => event.headers[key],
  useRuntimeConfig: () => ({ apiBase: 'http://api:8000', editorialApiToken: 'internal-test-secret' }),
  $fetch: async (...args) => { calls.push(args); if (fail) throw new Error('unavailable') },
  console: { warn: () => {} }
}
vm.runInNewContext(ts.transpileModule(fs.readFileSync('server/plugins/analytics.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS }
}).outputText, context)
const event = (path = '/', headers = {}, status = 200, method = 'GET') => ({
  path, method, headers: { accept: 'text/html', 'user-agent': 'Mozilla/5.0 Chrome/130.0', ...headers },
  node: { res: { statusCode: status } }
})
;(async () => {
  for (const item of [event('/cuenta'), event('/editorial'), event('/sitemap.xml'), event('/blog/actualidad'),
    event('/', {}, 404), event('/', {}, 503), event('/', {}, 200, 'HEAD'),
    event('/', { cookie: 'foroia_session=private' }), event('/', { 'user-agent': 'Googlebot' }),
    event('/', { 'user-agent': 'HeadlessChrome' }), event('/', { accept: 'application/json' })]) {
    await hook(item)
  }
  assert.equal(calls.length, 0)
  await hook(event('/articulos/real-article?email=private@example.test'))
  assert.equal(calls.length, 1)
  assert.equal(calls[0][1].body.path, '/articulos/real-article')
  assert.deepEqual(Object.keys(calls[0][1].body), ['path'])
  assert.deepEqual(Object.keys(calls[0][1].headers), ['x-internal-token'])
  await hook(event('/actualidad'))
  assert.equal(calls.length, 2)
  fail = true
  await hook(event('/')) // collection failure must not throw or retry
  assert.equal(calls.length, 3)
  console.log('Analytics hook: exclusions, data minimization and failure isolation passed.')
})().catch(error => { console.error(error); process.exitCode = 1 })
