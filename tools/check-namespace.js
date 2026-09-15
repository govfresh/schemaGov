#!/usr/bin/env node
/**
 * Every URL the profile bakes into published documents must resolve in the built
 * site. SPEC section 6 makes these immutable: if one stops resolving, data that
 * other people already published silently breaks. Run after every build.
 */
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const SITE = path.join(ROOT, '_site')
const BASE = JSON.parse(fs.readFileSync(path.join(ROOT, '_data/site.json'), 'utf8')).url

const expected = new Set()

// Every profile's JSON Schema $id values and code list term IRIs
const profilesDir = path.join(ROOT, 'profiles')
for (const profile of fs.readdirSync(profilesDir)) {
  for (const [sub, key] of [['schema', '$id'], ['codelists', '@id']]) {
    const dir = path.join(profilesDir, profile, sub)
    if (!fs.existsSync(dir)) continue
    for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.json'))) {
      const doc = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'))
      const id = doc[key]
      if (id) expected.add(id)

      // Every individual term too. Published documents expand code-list values into
      // these IRIs, so one that does not resolve is a document pointing at nothing.
      for (const term of doc.hasDefinedTerm || []) {
        const tid = term['@id']
        if (tid && tid.startsWith('gs:')) expected.add(`${BASE}/v1/${tid.slice(3)}`)
      }
    }
  }
}

// Every @context actually used by the examples
const exDir = path.join(ROOT, 'examples/example-city')
for (const f of fs.readdirSync(exDir).filter((f) => f.endsWith('.jsonld'))) {
  const ctx = JSON.parse(fs.readFileSync(path.join(exDir, f), 'utf8'))['@context']
  if (typeof ctx === 'string') expected.add(ctx)
}

expected.add(`${BASE}/v1/schemagov.ttl`)

let failed = 0
const sorted = [...expected].sort()
for (const url of sorted) {
  if (!url.startsWith(BASE)) {
    console.log(`  SKIP  ${url} (external)`)
    continue
  }
  const rel = url.slice(BASE.length)
  const asFile = path.join(SITE, rel)
  const asDir = path.join(SITE, rel, 'index.html')
  if (fs.existsSync(asFile) && fs.statSync(asFile).isFile()) {
    console.log(`  OK    ${url}`)
  } else if (fs.existsSync(asDir)) {
    console.log(`  OK    ${url}/`)
  } else {
    console.log(`  FAIL  ${url}\n          expected ${path.relative(ROOT, asFile)}`)
    failed++
  }
}

console.log(
  `\nnamespace: ${sorted.length} URL(s) checked, ${failed} unresolved`,
)
process.exit(failed ? 1 : 0)
