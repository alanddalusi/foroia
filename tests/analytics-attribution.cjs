const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
const sandbox = { exports: {}, URL, Set, Object }
vm.runInNewContext(ts.transpileModule(fs.readFileSync('utils/analytics.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS }
}).outputText, sandbox)
const { analyticsEntry: entry, analyticsLocation: location, publicAnalyticsPage: publicPage } = sandbox.exports
const base = 'https://foroiaaldia.com/tutoriales'
assert.equal(entry('https://www.google.com/search?q=private#private', base).page_referrer, 'https://www.google.com/')
assert.equal(entry('', base).page_referrer, '')
assert.equal(entry('javascript:alert(1)', base).page_referrer, '')
assert.equal(entry('https://person:secret@example.com/private', base).page_referrer, '')
assert.equal(entry('https://foroiaaldia.com/cuenta#private', base).page_referrer, '')
const good = entry('', base + '?utm_source=newsletter&utm_medium=email&utm_campaign=editorial-90dias')
assert.equal(good.campaign_source, 'newsletter')
assert.equal(good.campaign_name, 'editorial-90dias')
const bad = entry('', base + '?utm_source=person@example.com&utm_medium=email&utm_campaign=private')
assert.deepEqual(Object.keys(bad), ['page_referrer'])
assert.equal(location(base + '?email=private&pagina=2#secret'), base + '?pagina=2')
assert.equal(location(base + '?pagina=bad&token=private'), base)
assert.equal(publicPage('/editorial/estadisticas'), false)
assert.equal(publicPage('/cuenta'), false)
assert.equal(publicPage('/tutoriales'), true)
console.log('Attribution: external source, direct entry, campaign allowlists, URL minimization and private-route exclusions passed.')
