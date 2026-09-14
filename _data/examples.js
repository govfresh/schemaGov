import fs from 'node:fs/promises'
import path from 'node:path'
import profilesData from './profiles.js'

const ROOT = path.resolve(import.meta.dirname, '..')
const DIR = path.join(ROOT, 'examples', 'example-city')

/**
 * One real example per schema, pulled from the example-city fixture set and
 * grouped by the profile page section it belongs on — shown inline there
 * instead of on a separate examples page, so a schema's fields and a worked
 * instance of it are never more than a scroll apart.
 */
export default async function () {
  let names = []
  try {
    names = (await fs.readdir(DIR)).filter((n) => n.endsWith('.jsonld'))
  } catch {
    return { bySchema: {} }
  }

  // Maps a rendered @type (e.g. "GovernmentOrganization") back to the
  // schema(s) that declare it. Usually one — but schema.org's own type can
  // be reused deliberately at two different depths (requests/service.schema.json
  // and services/service.schema.json are both `GovernmentService`, one Open311-
  // shaped and one the fuller HSDS-shaped definition), so this is a list, not
  // a single winner — collapsing it to one would silently let the
  // later-processed profile's schema claim every fixture node of that type,
  // starving the other of an example it actually has.
  const { built } = await profilesData()
  const typeCandidates = {}
  for (const b of built) {
    for (const s of b.schemas) {
      for (const t of s.types) {
        ;(typeCandidates[t] ||= []).push({ key: `${b.slug}/${s.slug}`, fields: new Set(s.fields.map((f) => f.name)) })
      }
    }
  }
  // When a @type has more than one candidate schema, the node's own field
  // names decide which one it's actually an instance of — whichever
  // schema's declared fields overlap most with the keys the node actually
  // has.
  const resolveKey = (type, node) => {
    const candidates = type && typeCandidates[type]
    if (!candidates || !candidates.length) return null
    if (candidates.length === 1) return candidates[0].key
    const nodeKeys = Object.keys(node)
    let best = candidates[0]
    let bestScore = -1
    for (const c of candidates) {
      const score = nodeKeys.filter((k) => c.fields.has(k)).length
      if (score > bestScore) {
        best = c
        bestScore = score
      }
    }
    return best.key
  }

  // A reference (the shape reference.schema.json defines) carries only
  // @id and, as optional display hints, @type/name — nothing else. Some
  // of those hints happen to name a real schema type (e.g. a Contest's
  // `election` field links back with {"@id", "@type": "Election", "name"}),
  // and without this check that stub would get picked up as an "example"
  // of Election, crowding out — or racing to be picked before — the real,
  // fully-populated one.
  const isFullEntity = (node) => !Object.keys(node).every((k) => ['@id', '@type', 'name'].includes(k))

  // Keyed "{profileSlug}/{schemaSlug}" -> [{ id, raw }, ...]. Walks into
  // nested arrays/objects too, not just each file's top-level @graph
  // entries — a Contest's `candidacy` array is exactly this shape: full
  // Candidacy objects, each with its own @id, nested one level down
  // because that's how the schema models a candidacy (as part of the
  // contest it belongs to), not because it lacks its own identity.
  // Tender/Award/Contract stay correctly excluded regardless — they're
  // embedded with no @id of their own, a genuine value-object rather than
  // an entity — so those schemas simply get no example, on purpose.
  const bySchema = {}
  const visit = (node) => {
    if (!node || typeof node !== 'object') return
    const type = Array.isArray(node['@type']) ? node['@type'][0] : node['@type']
    const key = resolveKey(type, node)
    if (key && node['@id'] && isFullEntity(node)) {
      ;(bySchema[key] ||= []).push({ id: node['@id'], raw: JSON.stringify(node, null, 2) })
    }
    for (const val of Object.values(node)) {
      if (Array.isArray(val)) val.forEach(visit)
      else visit(val)
    }
  }
  for (const n of names) {
    const doc = JSON.parse(await fs.readFile(path.join(DIR, n), 'utf8'))
    const nodes = doc['@graph'] || [doc]
    nodes.forEach(visit)
  }

  return { bySchema }
}
