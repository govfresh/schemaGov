import fs from 'node:fs/promises'
import path from 'node:path'
import { STANDARDS } from '../_lib/standards.js'
import profilesData from './profiles.js'

const navData = JSON.parse(await fs.readFile(path.join(import.meta.dirname, 'nav.json'), 'utf8'))

/**
 * One entry per searchable page: {id, title, url, body}. `body` is what
 * Lunr actually matches against beyond the title, so it has to carry real
 * field/term text, not just each page's short frontmatter description — a
 * search for `electoralSystem` (a field name) or `fptp` (a term code) needs
 * to find the Elections profile and the ElectoralSystem code list, and
 * neither word will ever appear in those pages' own one-line descriptions.
 * Built from the same `_data` every page itself is generated from, not
 * scraped HTML, so the index can never say more than the page actually
 * does.
 */
export default async function () {
  const { built } = await profilesData()
  const entries = []

  for (const b of built) {
    const body = [b.description]
    for (const s of b.schemas) {
      body.push(s.title, s.description)
      for (const f of s.fields) body.push(f.name, f.description)
    }
    entries.push({ title: b.name, url: `/profiles/${b.slug}/`, body: body.join(' ') })

    for (const c of b.codelists) {
      const termBody = [c.description]
      for (const t of c.terms) termBody.push(t.code, t.name, t.description)
      entries.push({ title: c.name, url: `/v1/${c.termSegment}/`, body: termBody.join(' ') })
    }
  }

  for (const std of STANDARDS) {
    entries.push({ title: std.name, url: `/standards/${std.slug}/`, body: std.description })
  }

  // The handful of static index/nav pages — matched by title, mostly; a
  // short body is enough since there's no deeper structured content behind
  // any of these the way there is for a profile or codelist.
  for (const item of navData.docs) {
    entries.push({ title: item.title, url: item.url, body: item.title })
  }
  // nav.icons entries are icon-only (see nav.njk's ICON_PRESETS for the
  // same title fallback) and mostly external (GitHub) — only an internal
  // one, like the search page itself, is worth a search-index entry.
  const ICON_LABELS = { github: 'GitHub', search: 'Search' }
  for (const item of navData.icons || []) {
    if (/^https?:\/\//.test(item.url)) continue
    const title = item.label || ICON_LABELS[item.type] || item.type
    entries.push({ title, url: item.url, body: title })
  }
  entries.push({ title: 'Home', url: '/', body: 'schemaGov a shared vocabulary for government operations' })
  entries.push({ title: 'Site index', url: '/site-index/', body: 'every page on the site' })

  return entries.map((e, id) => ({ id, ...e }))
}
