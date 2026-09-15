// The external standards schemaGov profiles against — kept outside
// _data/ deliberately: Eleventy treats every _data/*.js file's default
// export as global template data, and a file with more than one export
// (the STANDARDS array, the linkifyTerms function) gets exposed as its
// raw module-namespace object instead, not the array itself, breaking
// anything that tries to iterate or paginate over it. _data/standards.js
// imports STANDARDS from here and re-exports a clean, single default.
export const STANDARDS = [
  {
    slug: 'schema-org',
    name: 'schema.org',
    aliases: [],
    org: 'schema.org community (Google, Microsoft, Yahoo, Yandex)',
    url: 'https://schema.org',
    description: 'The general-purpose vocabulary schemaGov is a profile of; every domain projects into it.',
  },
  {
    slug: 'wikidata',
    name: 'Wikidata QID',
    aliases: [],
    org: 'Wikimedia Foundation',
    url: 'https://www.wikidata.org/wiki/Wikidata:Identifiers',
    description: 'A free knowledge base whose stable identifiers (QIDs) let schemaGov records join up with any other dataset that also cites Wikidata.',
  },
  {
    slug: 'akoma-ntoso',
    name: 'Akoma Ntoso',
    aliases: [],
    org: 'OASIS LegalDocML Technical Committee',
    url: 'https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=legaldocml',
    description: 'An XML standard for marking up the structure of legislative and judicial documents so their internal parts - clauses, provisos, amendments - are machine-readable.',
  },
  {
    slug: 'w3c-org',
    name: 'W3C ORG',
    aliases: [],
    org: 'W3C',
    url: 'https://www.w3.org/TR/vocab-org/',
    description: 'A vocabulary for describing organizational structures, changes over time, and the roles people hold within them.',
  },
  {
    slug: 'popolo',
    name: 'Popolo',
    aliases: [],
    org: 'Popolo Project',
    url: 'https://www.popoloproject.com',
    description: 'An open specification for describing people, organizations, and the memberships and roles that connect them in government and legislative data.',
  },
  {
    slug: 'eli',
    name: 'ELI',
    aliases: [],
    org: 'Publications Office of the European Union',
    url: 'https://eur-lex.europa.eu/eli-register/about.html',
    description: 'The European Legislation Identifier, a standard scheme for identifying and citing pieces of national and EU legislation consistently across countries.',
  },
  {
    slug: 'open-civic-data',
    name: 'Open Civic Data',
    aliases: ['OCD'],
    org: 'Open Civic Data community',
    url: 'https://opencivicdata.org/',
    description: 'Conventions, including the OCD Division identifier scheme, for describing political geography and civic entities in a way that works across countries.',
  },
  {
    slug: 'open311-georeport-v2',
    name: 'Open311 GeoReport v2',
    aliases: [],
    org: 'Open311 community',
    url: 'https://wiki.open311.org/GeoReport_v2/',
    description: 'A standard API for submitting and tracking non-emergency service requests, like reporting a pothole, to a local government.',
  },
  {
    slug: 'fiscal-data-package',
    name: 'Fiscal Data Package',
    aliases: [],
    org: 'Frictionless Data (Open Knowledge Foundation)',
    url: 'https://specs.frictionlessdata.io/fiscal-data-package/',
    description: 'A specification for publishing structured, machine-readable government budget and spending data with enough context to compare figures across publishers.',
  },
  {
    slug: 'cofog',
    name: 'COFOG',
    aliases: [],
    org: 'United Nations Statistics Division',
    url: 'https://unstats.un.org/unsd/classifications/Family/Detail/4',
    description: 'The Classification of the Functions of Government, used to categorize spending by purpose - health, education, defence - so it is comparable across countries.',
  },
  {
    slug: 'gfsm-2014',
    name: 'GFSM 2014',
    aliases: [],
    org: 'International Monetary Fund',
    url: 'https://www.imf.org/external/Pubs/FT/GFS/Manual/2014/gfsfinal.pdf',
    description: "The IMF's Government Finance Statistics Manual, which classifies government transactions by economic type - salaries, goods, interest - rather than purpose.",
  },
  {
    slug: 'ocds',
    name: 'Open Contracting Data Standard',
    aliases: ['OCDS'],
    org: 'Open Contracting Partnership',
    url: 'https://standard.open-contracting.org',
    description: 'A standard for publishing data about every stage of a public contracting process, from planning through award to implementation.',
  },
  {
    slug: 'dcat',
    name: 'DCAT / DCAT-AP',
    aliases: [],
    org: 'W3C; DCAT-AP profile maintained by the European Commission',
    url: 'https://www.w3.org/TR/vocab-dcat-3/',
    description: 'A vocabulary for describing datasets and data catalogs so they can be discovered and cross-referenced across different portals.',
  },
  {
    slug: 'cap',
    name: 'Common Alerting Protocol (OASIS)',
    aliases: ['CAP 1.2 (OASIS)'],
    org: 'OASIS Emergency Management Technical Committee',
    url: 'https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html',
    description: 'A standard for structuring public warning messages so they can be exchanged consistently across every kind of alerting system and media.',
  },
  {
    slug: 'blds',
    name: 'BLDS',
    aliases: [],
    org: 'PermitData.org',
    url: 'https://permitdata.org/',
    description: 'A shared data specification for building and land-development permits, so permit data is comparable across the many local systems that issue them.',
  },
  {
    slug: 'nist-sp-1500-100',
    name: 'NIST SP 1500-100',
    aliases: [],
    org: 'National Institute of Standards and Technology',
    url: 'https://www.nist.gov/itl/voting/1500-100',
    description: 'A NIST special publication defining a common data format for election results reporting.',
  },
  {
    slug: 'open-referral-hsds',
    name: 'Open Referral / HSDS',
    aliases: [],
    org: 'Open Referral initiative',
    url: 'https://openreferral.org/',
    description: 'The Human Services Data Specification, an open standard for describing health, human, and social services so referral directories can share listings.',
  },
]

const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// Flattened (name, alias) -> standard lookup, longest term first so e.g.
// "DCAT / DCAT-AP" matches before a bare "DCAT" mention would (there is no
// bare "DCAT" alias today, but the ordering rule stays in place for
// whichever standard is added next).
const TERMS = STANDARDS.flatMap((std) => [std.name, ...std.aliases].map((term) => [term, std.slug])).sort(
  (a, b) => b[0].length - a[0].length,
)

/**
 * Wraps the first mention of any standard's name or alias in plain text
 * with a link to that standard's own schemaGov page. Escapes the input
 * first — callers pass raw text, not markup, same contract as before.
 */
export function linkifyTerms(text) {
  if (!text) return ''
  let out = escapeHtml(text)
  for (const [term, slug] of TERMS) {
    // Lookarounds, not \b — \b is a word/non-word transition, which fails
    // to match at all when a term starts or ends on a non-word character
    // (e.g. "Common Alerting Protocol (OASIS)" — \b(OASIS)\b never
    // matches, since ")" is non-word and there's nothing word-ish right
    // after it). These check "not adjacent to a word character" directly,
    // which is what "don't match inside a larger word" actually means.
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(?<![a-zA-Z0-9])${escaped}(?![a-zA-Z0-9])`)
    // Only match outside links already generated by an earlier (longer,
    // more specific) term — otherwise a shorter term that's a substring of
    // one already linked (e.g. "DCAT" inside a "DCAT / DCAT-AP" link's own
    // visible text) gets wrapped a second time, nesting <a> inside <a>.
    out = out
      .split(/(<a\b[^>]*>.*?<\/a>)/)
      .map((part) => (part.startsWith('<a') ? part : part.replace(re, `<a href="/standards/${slug}/">${term}</a>`)))
      .join('')
  }
  return out
}
