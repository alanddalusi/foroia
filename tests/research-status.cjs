const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
const sandbox = { exports: {}, Date, Number, Intl }
vm.runInNewContext(ts.transpileModule(fs.readFileSync('utils/research-status.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText, sandbox)
const { researchRunLabel: label, researchRunReason: reason, researchDayNotice: notice } = sandbox.exports
const migrated = { status: 'skipped', reason: 'migrated_local_budget', date: '2026-10-22' }
assert.match(reason({ status: 'skipped', reason: 'insufficient_independent_topic_sources' }), /dos organizaciones independientes/)
assert.equal(label(migrated), 'Historial importado')
assert.match(reason(migrated), /No corresponde a una investigación activa/)
for (const status of ['skipped', 'draft', 'interrupted', 'unknown', 'published']) assert.notEqual(reason({ status, reason: 'unknown' }), 'Ejecución en curso')
assert.equal(reason({ status: 'running', reason: '' }), 'Ejecución en curso')
assert.notEqual(reason({ status: 'running', reason: '', finished_at: '2026-10-23T18:00:00Z' }), 'Ejecución en curso')
assert.match(notice([migrated], new Date('2026-10-23T19:00:00Z'), '22:30'), /prevista/)
assert.match(notice([migrated], new Date('2026-10-23T20:31:00Z'), '22:30'), /30 segundos/)
assert.match(notice([migrated], new Date('2026-10-23T20:36:00Z'), '22:30'), /más de cinco minutos/)
assert.match(notice([migrated], new Date('2026-10-22T20:36:00Z'), '22:30'), /reserva histórica/)
assert.match(notice([], new Date('2026-12-23T21:00:00Z'), '22:30'), /prevista/)
assert.match(notice([{ date: '2026-10-23', status: 'published', reason: 'quality_checks_passed' }], new Date('2026-10-23T21:00:00Z'), '22:30'), /Publicado/)
console.log('Research status: imported history, final states, active work, daily gaps and Madrid summer/winter time passed.')
