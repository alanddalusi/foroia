const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
const sandbox = { exports: {}, URL }
vm.runInNewContext(ts.transpileModule(fs.readFileSync('utils/article-inline.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText, sandbox)
const { articleInline: parse, safeArticleHref: safe } = sandbox.exports
for (const url of ['javascript:alert(1)', 'data:text/html,x', '//evil.test', '/\\evil.test', '/a/../cuenta', 'https://user:pass@example.com', '/a%0aevil']) assert.equal(safe(url), undefined, url)
assert.equal(safe('/articulos/guia-pdf'), '/articulos/guia-pdf')
assert.equal(safe('https://example.com/docs'), 'https://example.com/docs')
assert.equal(parse('[Guía](/articulos/guia-pdf)')[0].href, '/articulos/guia-pdf')
assert.equal(parse('[Mal](javascript:alert)')[0].href, undefined)
assert.equal(parse('`[no](/link)`')[0].style, 'code')
assert.equal(parse('<img src=x onerror=alert(1)>')[0].text, '<img src=x onerror=alert(1)>')
console.log('Article inline: allowlisted destinations, unsafe schemes, code isolation and literal HTML passed.')

// Referencias del servidor (11/11/2026): mismo texto visible, enlazado a las fuentes; enlaces de sección legibles.
{
  const cite = parse('Texto apoyado. [2, 1]').find(p => p.style === 'cite')
  assert.equal(cite.text, '[2, 1]'); assert.equal(cite.href, '#fuentes')
  assert.equal(parse('[Guía](/articulos/guia-pdf)')[0].style, undefined)
  assert.equal(parse('[Más guías de programacion](/programacion)')[0].text, 'Más guías de programación')
}
