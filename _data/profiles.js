import fs from 'node:fs/promises'
import path from 'node:path'
import { STANDARDS } from '../_lib/standards.js'

const ROOT = path.resolve(import.meta.dirname, '..')

/** Profiles with schemas on disk are "implemented"; the rest are read as planned stubs. */
// "Source standard" always leads with schema.org — every profile is a
// schema.org projection first, with these domain standards as the
// non-schema.org model being crosswalked (SPEC.md's own "5. Domain
// profiles" table lists these the same way, sourced from the same facts).
const IMPLEMENTED = [
  { dir: '_core', slug: 'core', name: 'Core', source: 'schema.org, Popolo, W3C ORG', description: 'The basic building blocks every other profile depends on: jurisdictions, organizations, people, and the roles people hold.' },
  { dir: 'org', slug: 'org', name: 'Organization structure', source: 'schema.org, Popolo, W3C ORG', description: "How a government's departments and offices are described, including who runs them and how they're organized." },
  { dir: 'code', slug: 'code', name: 'Legislation and codes', source: 'schema.org, Akoma Ntoso, ELI', description: 'How laws, ordinances, and municipal codes are described so their text, status, and history can be tracked.' },
  { dir: 'meetings', slug: 'meetings', name: 'Meetings and votes', source: 'schema.org, Popolo, Open Civic Data', description: 'How public meetings, agendas, and votes are recorded so residents can see what was decided and how each member voted.' },
  { dir: 'requests', slug: 'requests', name: 'Service requests', source: 'schema.org, Open311 GeoReport v2', description: 'How resident requests, like reporting a pothole, are tracked from submission to resolution.' },
  { dir: 'budget', slug: 'budget', name: 'Budgets and spending', source: 'schema.org, Fiscal Data Package, COFOG, GFSM 2014', description: 'How government budgets and spending are described so figures can be compared across agencies and years.' },
  { dir: 'procurement', slug: 'procurement', name: 'Procurement and contracts', source: 'schema.org, Open Contracting Data Standard', description: 'How government contracts and bidding processes are described, from the request for bids to the signed contract.' },
  { dir: 'catalog', slug: 'catalog', name: 'Discovery and data catalogue', source: 'schema.org, DCAT / DCAT-AP', description: "How a government lists its published datasets so people and search engines can find them." },
  { dir: 'alerts', slug: 'alerts', name: 'Public warnings and notices', source: 'schema.org, Common Alerting Protocol (OASIS)', description: 'How public alerts and emergency warnings are described so they can be shared consistently across systems.' },
  { dir: 'permits', slug: 'permits', name: 'Permits and licences', source: 'schema.org, BLDS, national equivalents', description: 'How building and other permits are described, from application through approval or denial.' },
  { dir: 'elections', slug: 'elections', name: 'Elections and results', source: 'schema.org, NIST SP 1500-100, VIP', description: 'How elections, candidates, and results are described so outcomes can be reported consistently.' },
  { dir: 'services', slug: 'services', name: 'Service catalogue', source: 'schema.org, Open Referral / HSDS', description: 'How the services a government offers are described so residents can find and understand them.' },
]
const PLANNED = []

async function readJson(p) {
  return JSON.parse(await fs.readFile(p, 'utf8'))
}

async function readDirJson(dir) {
  let names
  try {
    names = await fs.readdir(dir)
  } catch {
    return []
  }
  const out = []
  for (const n of names.filter((n) => n.endsWith('.json')).sort()) {
    out.push({ file: n, ...(await readJson(path.join(dir, n))) })
  }
  return out
}

function toSchema(s) {
  const required = new Set(s.required || [])
  const fields = Object.entries(s.properties || {})
    .filter(([name]) => name !== '@context')
    .map(([name, def]) => ({
      name,
      required: required.has(name),
      def,
      description: def.description || '',
    }))
  // The @type value(s) this schema declares — a single const for a
  // one-type schema, or the enum list for one that covers several
  // related types (e.g. facility.schema.json's Place subtypes). Lets
  // examples.js link an entity's rendered @type back to the schema that
  // defines it.
  const typeDef = s.properties?.['@type'] || {}
  const types = typeDef.const ? [typeDef.const] : typeDef.enum || []
  // The specific standard(s) this schema's shape follows, e.g. `post.schema.json`
  // leans on Popolo's person/membership/role split while `directory.schema.json`
  // follows W3C ORG's organizational-change model - both narrower than the
  // profile's own aggregate `source` line. Authored per schema (like `source`
  // is authored per profile) because it isn't reliably derivable from the
  // schema's own text - most schemas that do follow a specific standard never
  // name it in their description.
  const standards = (s.standards || []).map((slug) => {
    const std = STANDARDS.find((x) => x.slug === slug)
    if (!std) throw new Error(`Unknown standard slug "${slug}" in ${s.file}`)
    return { slug, name: std.name }
  })
  return {
    file: s.file,
    slug: s.file.replace('.schema.json', ''),
    title: s.title,
    description: s.description,
    id: s.$id,
    types,
    standards,
    fields,
    requiredCount: required.size,
    fieldCount: fields.length,
  }
}

function toCodelist(c) {
  const rawTermIds = Object.fromEntries(
    (c.hasDefinedTerm || [])
      .filter((t) => (t['@id'] || '').startsWith('gs:'))
      .map((t) => [t.termCode, t['@id'].slice(3)]),
  )
  return {
    file: c.file,
    slug: c.file.replace('.json', ''),
    name: c.name,
    description: c.description,
    id: c['@id'],
    termSegment: (c['@id'] || '').split('/').pop(),
    // Each term's own dereferenceable page (term-value.njk), so a code-list
    // table can link straight to it instead of only listing the code as
    // plain text.
    terms: (c.hasDefinedTerm || []).map((t) => ({
      code: t.termCode,
      name: t.name,
      description: t.description,
      path: rawTermIds[t.termCode] || null,
    })),
  }
}

/**
 * Documentation is generated from the schemas themselves, so a field can never be
 * documented here and absent there. Adding a property to a schema is the only way
 * to add it to these pages.
 */
export default async function () {
  const built = []
  for (const p of IMPLEMENTED) {
    const base = path.join(ROOT, 'profiles', p.dir)
    const schemas = (await readDirJson(path.join(base, 'schema'))).map(toSchema)
    const codelists = (await readDirJson(path.join(base, 'codelists'))).map(toCodelist)

    built.push({
      ...p,
      urlBase: p.dir === '_core' ? '/v1/_core/' : `/v1/${p.dir}/`,
      schemas,
      codelists,
    })
  }

  // A field whose values come from a code list gets linked straight to
  // that list's page — most descriptions already say so explicitly
  // ("termCode from the X code list"), which is a more reliable signal
  // than guessing from the field's own name (requestStatus draws from
  // ServiceRequestStatus, not "RequestStatus"). Indexed across every
  // profile's code lists, not just the field's own profile — _core's
  // ConformanceLevel, for instance, is referenced from directory.schema.json
  // in the org profile, not only from _core itself.
  const bySegment = Object.fromEntries(built.flatMap((b) => b.codelists).map((c) => [c.termSegment, c]))
  for (const b of built) {
    for (const s of b.schemas) {
      for (const f of s.fields) {
        const m = f.description.match(/`?([A-Z][A-Za-z]*)`?\s+code list/)
        const list = (m && bySegment[m[1]]) || bySegment[f.name[0].toUpperCase() + f.name.slice(1)]
        if (list) {
          f.codelistLink = `/v1/${list.termSegment}/`
          // The Type column would otherwise spell out every enum value
          // pipe-separated (electoralSystem alone has 10) - pure
          // duplication once the Field name links to this same list's own,
          // properly tabulated page. Flag it so fieldType can print a
          // plain `string` instead; a non-codelist enum (an @type choice
          // list, never linked anywhere else) is untouched and keeps every
          // value, since there it's the only place they're documented.
          if (f.def.enum) f.enumLinked = true
          // Reverse pointer, so the codelist's own page can link back to
          // where it's actually used - same object reference as in `built`
          // and the flat `codelists` view below, so one write reaches both.
          if (!list.usedBy) list.usedBy = []
          if (!list.usedBy.some((u) => u.schemaSlug === s.slug)) {
            list.usedBy.push({ profileSlug: b.slug, profileName: b.name, schemaSlug: s.slug, schemaTitle: s.title })
          }
        }
      }
    }
  }

  const planned = []
  for (const d of PLANNED) {
    try {
      const txt = await fs.readFile(path.join(ROOT, 'profiles', d, 'README.md'), 'utf8')
      planned.push({
        slug: d,
        title: txt.match(/^# `[^`]+` profile — (.+)$/m)?.[1] || d,
        source: txt.match(/\*\*Source standard:\*\* (.+)$/m)?.[1] || '',
        depends: txt.match(/\*\*Depends on:\*\* (.+)$/m)?.[1] || '',
      })
    } catch {}
  }

  // Every individual term, so each code-list value gets a dereferenceable page.
  // Published documents expand values into these IRIs, so a 404 here means a document
  // points at nothing.
  const terms = []
  for (const b of built) {
    for (const c of b.codelists) {
      for (const t of c.terms) {
        if (!t.path) continue
        terms.push({
          path: t.path,                    // e.g. "level/municipal"
          code: t.code,
          name: t.name,
          description: t.description,
          setName: c.name,
          setSegment: c.termSegment,
          setUrl: c.id,
          profile: b.slug,
          file: c.file,
        })
      }
    }
  }

  // Flat views, so existing templates keep working.
  const schemas = built.flatMap((b) => b.schemas.map((s) => ({ ...s, profile: b.slug })))
  const codelists = built.flatMap((b) => b.codelists.map((c) => ({ ...c, profile: b.slug })))

  return { built, planned, schemas, codelists, terms }
}
