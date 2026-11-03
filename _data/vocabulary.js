import fs from 'node:fs/promises'
import path from 'node:path'
import { Parser } from 'n3'
import profilesData from './profiles.js'

const ROOT = path.resolve(import.meta.dirname, '..')
const NS = 'https://schema.govfresh.com/v1/'

const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
const KINDS = {
  'http://www.w3.org/2000/01/rdf-schema#Class': 'class',
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#Property': 'property',
  'https://schema.org/DefinedTermSet': 'set',
}
const PREDICATES = {
  'http://www.w3.org/2000/01/rdf-schema#label': 'label',
  'http://www.w3.org/2000/01/rdf-schema#comment': 'comment',
  'http://www.w3.org/2000/01/rdf-schema#subClassOf': 'subClassOf',
  'http://www.w3.org/2000/01/rdf-schema#subPropertyOf': 'subPropertyOf',
  'http://www.w3.org/2002/07/owl#inverseOf': 'inverseOf',
  'https://schema.org/domainIncludes': 'domainIncludes',
  'https://schema.org/rangeIncludes': 'rangeIncludes',
  'https://schema.org/name': 'label',
}
/** Escapes the characters that matter in HTML text. Apostrophes are left alone. */
const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

const KIND_ORDER = { set: 0, class: 1, property: 2 }
const KIND_LABEL = { set: 'Code list', class: 'Class', property: 'Property' }

/** `https://schema.org/Place` -> a link target and a short display name. */
function describeIri(iri) {
  if (iri.startsWith(NS)) {
    const local = iri.slice(NS.length)
    return { iri, text: `gs:${local}`, href: `/v1/${local}/`, local: true }
  }
  if (iri.startsWith('https://schema.org/')) {
    return { iri, text: `schema:${iri.slice('https://schema.org/'.length)}`, href: iri, local: false }
  }
  return { iri, text: iri, href: iri, local: false }
}

/**
 * The section comment a term sits under (`####  org profile  ####`) is lost by an RDF
 * parser, so read it from the source: the nearest header above the line where the term
 * is first declared.
 */
function sectionsByTerm(source) {
  const out = {}
  let section = null
  for (const line of source.split('\n')) {
    const header = line.match(/^#{5,}\s+(.+?)\s+#{5,}\s*$/)
    if (header) {
      section = header[1]
      continue
    }
    const decl = line.match(/^gs:([A-Za-z0-9_-]+)\s/)
    if (decl && !(decl[1] in out)) out[decl[1]] = section
  }
  return out
}

const JSONLD_TYPE = { set: 'schema:DefinedTermSet', class: 'rdfs:Class', property: 'rdf:Property' }

/** The group as JSON-LD, embedded in the page so a machine reading the HTML gets the definition. */
function jsonLdFor(members) {
  const ref = (list) => list.map((r) => ({ '@id': r.iri }))
  const graph = members.map((m) => {
    const o = { '@id': m.iri, '@type': JSONLD_TYPE[m.kind], 'rdfs:label': m.label }
    if (m.comment) o['rdfs:comment'] = m.comment
    if (m.subClassOf.length) o['rdfs:subClassOf'] = ref(m.subClassOf)
    if (m.subPropertyOf.length) o['rdfs:subPropertyOf'] = ref(m.subPropertyOf)
    if (m.inverseOf.length) o['owl:inverseOf'] = ref(m.inverseOf)
    if (m.domainIncludes.length) o['schema:domainIncludes'] = ref(m.domainIncludes)
    if (m.rangeIncludes.length) o['schema:rangeIncludes'] = ref(m.rangeIncludes)
    return o
  })
  const doc = {
    '@context': {
      rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
      rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      owl: 'http://www.w3.org/2002/07/owl#',
      schema: 'https://schema.org/',
    },
    '@graph': graph,
  }
  // "<" cannot appear inside a script element, whatever the text contains.
  return JSON.stringify(doc, null, 2).replace(/</g, '\\u003c')
}

/**
 * Every class, property and code-list set in vocabulary/schemagov.ttl, grouped so that
 * names which differ only by letter case share one page.
 *
 * The IRIs are published identifiers and cannot be renamed, but `Post` and `post` would
 * overwrite each other on a case-insensitive file system. So a group is rendered once and
 * written at every spelling: `pages` has one entry per spelling, and each carries the
 * whole group. What a page says never depends on which spelling was built last.
 */
export default async function () {
  const source = await fs.readFile(path.join(ROOT, 'vocabulary', 'schemagov.ttl'), 'utf8')
  const sections = sectionsByTerm(source)
  const { built } = await profilesData()
  const profileSlugs = new Set(built.map((b) => b.slug))

  const nodes = new Map()
  const node = (iri) => {
    if (!nodes.has(iri)) nodes.set(iri, { iri, kinds: new Set() })
    return nodes.get(iri)
  }

  const quads = new Parser({ baseIRI: NS }).parse(source)
  for (const q of quads) {
    if (!q.subject.value.startsWith(NS) || q.subject.value === NS) continue
    const n = node(q.subject.value)
    if (q.predicate.value === RDF_TYPE) {
      const kind = KINDS[q.object.value]
      if (kind) n.kinds.add(kind)
      continue
    }
    const key = PREDICATES[q.predicate.value]
    if (!key) continue
    if (key === 'label' || key === 'comment') {
      n[key] = n[key] || q.object.value
    } else {
      ;(n[key] ||= []).push(describeIri(q.object.value))
    }
  }

  const codelistBySegment = {}
  for (const b of built) for (const c of b.codelists) codelistBySegment[c.termSegment] = { ...c, profile: b.slug }

  // One entry per (term, kind): a name can be both a class and a code-list set.
  const terms = []
  for (const n of nodes.values()) {
    const local = n.iri.slice(NS.length)
    for (const kind of n.kinds) {
      const section = sections[local] || null
      const profileMatch = section && section.match(/^(.+) profile$/)
      const profile = profileMatch && profileSlugs.has(profileMatch[1]) ? profileMatch[1] : null
      terms.push({
        iri: n.iri,
        local,
        kind,
        kindLabel: KIND_LABEL[kind],
        label: n.label || local,
        comment: n.comment || '',
        commentHtml: escapeHtml(n.comment || ''),
        subClassOf: n.subClassOf || [],
        subPropertyOf: n.subPropertyOf || [],
        inverseOf: n.inverseOf || [],
        domainIncludes: n.domainIncludes || [],
        rangeIncludes: n.rangeIncludes || [],
        section,
        profile: profile || (kind === 'set' ? codelistBySegment[local]?.profile || null : null),
        codelist: kind === 'set' ? codelistBySegment[local] || null : null,
      })
    }
  }

  const groups = new Map()
  for (const t of terms) {
    const key = t.local.toLowerCase()
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(t)
  }

  const pages = []
  const groupList = []
  for (const [key, members] of groups) {
    members.sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || a.local.localeCompare(b.local))
    const spellings = [...new Set(members.map((m) => m.local))].sort()
    const group = {
      key,
      members,
      spellings,
      canonical: spellings[0],
      title: spellings.length > 1 ? spellings.join(' / ') : spellings[0],
      description: members[0].comment,
      collision: spellings.length > 1,
    }
    group.jsonld = jsonLdFor(members)
    groupList.push(group)
    for (const spelling of spellings) pages.push({ spelling, group })
  }
  groupList.sort((a, b) => a.key.localeCompare(b.key))

  return { terms, groups: groupList, pages, count: terms.length }
}
