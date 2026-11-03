#!/usr/bin/env node
/**
 * Every URL the profile bakes into published documents must resolve in the built
 * site. SPEC section 6 makes these immutable: if one stops resolving, data that
 * other people already published silently breaks. Run after every build.
 */
import fs from 'node:fs'
import path from 'node:path'
import { Parser } from 'n3'

const ROOT = path.resolve(import.meta.dirname, '..')
const SITE = process.env.SITE_DIR || path.join(ROOT, '_site')
const BASE = JSON.parse(fs.readFileSync(path.join(ROOT, '_lib/site.json'), 'utf8')).url

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
const exDir = path.join(ROOT, 'examples/example-gov')
for (const f of fs.readdirSync(exDir).filter((f) => f.endsWith('.jsonld'))) {
  const ctx = JSON.parse(fs.readFileSync(path.join(exDir, f), 'utf8'))['@context']
  if (typeof ctx === 'string') expected.add(ctx)
}

expected.add(`${BASE}/v1/schemagov.ttl`)

// Every class, property and code-list set the vocabulary defines. These IRIs are what
// published documents expand to, so each must load.
const NS = `${BASE}/v1/`
for (const q of new Parser({ baseIRI: NS }).parse(fs.readFileSync(path.join(ROOT, 'vocabulary/schemagov.ttl'), 'utf8'))) {
  const s = q.subject.value
  if (s.startsWith(NS) && s !== NS) expected.add(s)
}

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

// Names that differ only by letter case would overwrite each other on a case-insensitive
// file system, so they are rendered as one page written at every spelling. Where a
// case-sensitive build keeps both, they must be byte-identical: a page may not say one
// thing at /v1/Post/ and another at /v1/post/.
const byLower = new Map()
const v1 = path.join(SITE, 'v1')
for (const name of fs.readdirSync(v1)) {
  const index = path.join(v1, name, 'index.html')
  if (!fs.existsSync(index)) continue
  const key = name.toLowerCase()
  if (!byLower.has(key)) byLower.set(key, [])
  byLower.get(key).push(name)
}
let collisions = 0
for (const names of byLower.values()) {
  if (names.length < 2) continue
  collisions++
  const [first, ...rest] = names
  const ref = fs.readFileSync(path.join(v1, first, 'index.html'))
  for (const other of rest) {
    if (!ref.equals(fs.readFileSync(path.join(v1, other, 'index.html')))) {
      console.log(`  FAIL  /v1/${first}/ and /v1/${other}/ differ but are the same path ignoring case`)
      failed++
    }
  }
}
console.log(`case-collision pages: ${collisions} group(s) present as separate files, all identical`)

console.log(
  `\nnamespace: ${sorted.length} URL(s) checked, ${failed} unresolved`,
)
process.exit(failed ? 1 : 0)
