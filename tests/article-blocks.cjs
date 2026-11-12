const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
const sandbox = { exports: {} }
vm.runInNewContext(ts.transpileModule(fs.readFileSync('utils/article-blocks.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText, sandbox)
const { articleBlocks: parse, articleSpeech: speech } = sandbox.exports
const body = '## One\n\nText.\n\n```python\n## Not a heading\nprint("literal")\n```\n\n### Two\n\n| Field | Value |\n| --- | ---: |\n| Name | <script>literal</script> |'
const blocks = parse(body)
assert.equal(blocks.filter(b => b.type === 'h2' || b.type === 'h3').length, 2)
assert.equal(blocks[0].id, 'apartado-1')
assert.equal(blocks.find(b => b.type === 'h3').id, 'apartado-2')
assert.equal(blocks.find(b => b.type === 'code').text, '## Not a heading\nprint("literal")')
const table = blocks.find(b => b.type === 'table')
assert.equal(table.rows[0][1], '<script>literal</script>')
assert.equal(table.headers.length, 2)
assert(!speech(body).includes('print('))
assert(!speech(body).includes('<script>'))
assert(speech('## Header\n\n[Guide](/tutoriales) [1, 2]').includes('Guide'))
assert(!speech('## Header\n\n[Guide](/tutoriales) [1, 2]').includes('/tutoriales'))
console.log('Article blocks: stable anchors, code isolation, literal table cells and speech filtering passed.')

// Notas de transparencia (11/11/2026): se separan del cuerpo y la frase antigua se muestra con exactitud.
{
  const body = '## Uno\nTexto del artículo con contenido suficiente. [1]\n\nNo se ha probado la interfaz ni un servicio externo; solo el ejemplo aislado si se proporciona.\n\nRedacción y revisión automatizadas con IA. Sin revisión humana previa.'
  const split = sandbox.exports.splitTransparencyNotes(sandbox.exports.articleBlocks(body))
  assert.equal(split.blocks.length, 2)
  assert.equal(JSON.stringify(split.notes), JSON.stringify(['No se ha probado la interfaz ni ningún servicio externo.', 'Redactado y revisado de forma automatizada con IA a partir de las fuentes citadas, sin revisión humana previa.']))
}
