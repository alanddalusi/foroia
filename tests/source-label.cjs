const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const ts = require(require.resolve('typescript', { paths: [process.cwd()] }))
const sandbox = { exports: {}, URL }
vm.runInNewContext(ts.transpileModule(fs.readFileSync('utils/source-label.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
}).outputText, sandbox)
const { sourceLabel: label } = sandbox.exports

// Casos reales vistos en producción (12/11/2026): solo cambia lo que se muestra.
assert.equal(label('[1] Pricing', 'https://developers.openai.com/api/docs/pricing.md'), '[1] Documentación de OpenAI: Pricing')
assert.equal(label('[2] > ## AI Agent Context > For the complete', 'https://aistudio.google.com/docs/pricing.md'), '[2] Documentación de Google AI: Pricing')
assert.equal(label('[3] Pricing', 'https://platform.claude.com/docs/en/about-claude/pricing.md'), '[3] Documentación de Anthropic: Pricing')
assert.equal(label('[1] Use Gemini Apps You can use Gemini Apps to supercharge your ideas', 'https://support.google.com/gemini/answer/13275745'), '[1] Ayuda de Google (Gemini): Use Gemini Apps')
assert.equal(label('[2] Upload & analyze files in Gemini Apps You can upload documents', 'https://support.google.com/gemini/answer/14903178'), '[2] Ayuda de Google (Gemini): Upload & analyze files in Gemini Apps')
assert.equal(label('[1] This article is about paid Pro plans for individual consumers. If you', 'https://support.claude.com/en/articles/8325606-what-is-the-pro-plan'), '[1] Centro de ayuda de Claude: What is the pro plan')
assert.equal(label('[1] --- title: Reduce hallucinations url: https://x', 'https://platform.claude.com/docs/en/x/reduce-hallucinations.md'), '[1] Documentación de Anthropic: Reduce hallucinations')
assert.equal(label('[2] Streaming responses with the API', 'https://developers.openai.com/api/docs/guides/streaming-responses.md'), '[2] Streaming responses with the API')
console.log('Source labels: readable names for official docs and help centres passed.')
