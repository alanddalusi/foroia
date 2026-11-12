const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
function load(path) {
  const sandbox = { exports: {}, Date, Number }
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText, sandbox)
  return sandbox.exports
}
const { htmlDateTime, articleAuthor } = load('utils/blog.ts')
assert.equal(articleAuthor('Redacción de Foro IA al Día · con asistencia de IA'), 'Redacción de Foro IA al Día')
assert.equal(articleAuthor('Redacción automatizada · IA'), 'Redacción de Foro IA al Día')
assert.equal(articleAuthor('Ana García'), 'Ana García')
assert.equal(htmlDateTime('2026-10-23T16:45:47.539481Z'), '2026-10-23T16:45:47.539Z')
assert.equal(htmlDateTime('2026-10-23T18:45:47.539481+02:00'), '2026-10-23T16:45:47.539Z')
assert.equal(htmlDateTime(null), undefined)
assert.equal(htmlDateTime('invalid'), undefined)
const { normalizePrefetchHead: normalize } = load('server/utils/prefetch.ts')
assert.equal(normalize('<link rel="prefetch" as="style" href="/x.css">'), '<link rel="prefetch" href="/x.css">')
assert.equal(normalize("<link as='script' rel='prefetch' href='/x.js'>"), "<link rel='prefetch' href='/x.js'>")
for (const input of ['<link rel="modulepreload" as="script" href="/x.js">', '<link rel="preload" as="style" href="/x.css">', '<link rel="stylesheet" href="/x.css">', '<link data-rel="prefetch" as="style" href="/x.css">']) assert.equal(normalize(input), input)
assert.equal(normalize('<link rel="prefetch" data-as="script" as="script" crossorigin href="/x.js">'), '<link rel="prefetch" data-as="script" crossorigin href="/x.js">')
console.log('SEO presentation: datetime normalization and scoped prefetch hints passed.')

// SEO 04/11/2026: título <=60 con marca solo si cabe; descripción <=155 cortada por palabra.
{
  const { seoTitle, seoDescription, SECTION_INTROS } = load('utils/blog.ts')
  assert.equal(seoTitle('Validar un JSON generado por IA en Python'), 'Validar un JSON generado por IA en Python | Foro IA al Día')
  const long = 'Cómo separar instrucciones, contexto y datos: pautas oficiales de OpenAI'
  assert.equal(seoTitle(long), long)
  const d = seoDescription('palabra '.repeat(40))
  assert.ok(d.length <= 155 && d.endsWith('…') && !d.includes('palab…'))
  assert.equal(seoDescription('Corta.'), 'Corta.')
  for (const s of ["actualidad", "herramientas", "programacion", "tutoriales"]) { const n = SECTION_INTROS[s].paragraphs.join(" ").split(" ").length; assert.ok(n > 40, s + " " + n) }
}
