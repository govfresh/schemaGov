import fs from 'node:fs'
import path from 'node:path'
import { IdAttributePlugin } from '@11ty/eleventy'
import pluginSyntaxHighlight from '@11ty/eleventy-plugin-syntaxhighlight'
import pluginNavigation from '@11ty/eleventy-navigation'
import Prism from 'prismjs'
import 'prismjs/components/prism-json.js'
import { linkifyTerms } from './_lib/standards.js'

// The JSON-LD context is the one place that already says, authoritatively,
// whether a term is a real schema.org type/property (mapped to schema:) or
// one gov-schema mints itself (mapped to gs:) — reusing it here means a
// term only ever links to schema.org's own reference page when the
// published data would actually expand there too, never a guess based on
// how the word is capitalized.
const contextTerms = (() => {
  const ctx = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'context/v1/context.jsonld'), 'utf8'))['@context']
  const schemaOrg = new Set()
  for (const [key, val] of Object.entries(ctx)) {
    if (key.startsWith('@')) continue
    const id = typeof val === 'string' ? val : val?.['@id']
    if (id && id.startsWith('schema:')) schemaOrg.add(key)
  }
  return schemaOrg
})()

/** @param {import("@11ty/eleventy").UserConfig} eleventyConfig */
export default async function (eleventyConfig) {
  eleventyConfig.addPlugin(pluginSyntaxHighlight, { preAttributes: { tabindex: 0 } })
  eleventyConfig.addPlugin(pluginNavigation)
  eleventyConfig.addPlugin(IdAttributePlugin)

  // eleventy-plugin-syntaxhighlight only tokenizes {% highlight %} template
  // tags, not content loaded at build time from a variable (examples/
  // index.njk's f.raw, read from disk in _data/examples.js) — this filter
  // calls the same underlying Prism.js the plugin uses, directly, so that
  // content can be tokenized too. Matches the Prism token classes the
  // shared lf-components.css code-block theme is written against.
  eleventyConfig.addFilter('highlight', (content, language) => {
    if (!content) return ''
    const grammar = Prism.languages[language]
    if (!grammar) return content
    return Prism.highlight(content.trim(), grammar, language)
  })

  // --- static assets -------------------------------------------------------
  eleventyConfig.addPassthroughCopy({ './public/': '/' })

  // --- the namespace itself ------------------------------------------------
  // These are not documentation. Every published gov-schema document pins these
  // exact URLs in its @context and $id, and SPEC section 6 makes them immutable.
  // If a path here changes, previously published data stops resolving.
  eleventyConfig.addPassthroughCopy({ './context/v1/': '/v1/' })
  eleventyConfig.addPassthroughCopy({ './profiles/_core/schema/': '/v1/_core/' })
  eleventyConfig.addPassthroughCopy({ './vocabulary/govschema.ttl': '/v1/govschema.ttl' })
  eleventyConfig.addPassthroughCopy({ './profiles/org/schema/': '/v1/org/' })
  eleventyConfig.addPassthroughCopy({ './profiles/_core/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/org/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/code/schema/': '/v1/code/' })
  eleventyConfig.addPassthroughCopy({ './profiles/code/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/meetings/schema/': '/v1/meetings/' })
  eleventyConfig.addPassthroughCopy({ './profiles/meetings/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/requests/schema/': '/v1/requests/' })
  eleventyConfig.addPassthroughCopy({ './profiles/requests/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/budget/schema/': '/v1/budget/' })
  eleventyConfig.addPassthroughCopy({ './profiles/budget/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/procurement/schema/': '/v1/procurement/' })
  eleventyConfig.addPassthroughCopy({ './profiles/procurement/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/catalog/schema/': '/v1/catalog/' })
  eleventyConfig.addPassthroughCopy({ './profiles/catalog/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/alerts/schema/': '/v1/alerts/' })
  eleventyConfig.addPassthroughCopy({ './profiles/alerts/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/permits/schema/': '/v1/permits/' })
  eleventyConfig.addPassthroughCopy({ './profiles/permits/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/elections/schema/': '/v1/elections/' })
  eleventyConfig.addPassthroughCopy({ './profiles/elections/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/services/schema/': '/v1/services/' })
  eleventyConfig.addPassthroughCopy({ './profiles/services/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './examples/': '/examples/' })

  eleventyConfig.addWatchTarget('./profiles/')
  eleventyConfig.addWatchTarget('./context/')
  eleventyConfig.addWatchTarget('./SPEC.md')

  // --- filters -------------------------------------------------------------
  eleventyConfig.addFilter('jsonPretty', (v) => JSON.stringify(v, null, 2))
  eleventyConfig.addFilter('json', (v) => JSON.stringify(v))

  // Shared by `fieldType` and `inlineCode` below, and built once from
  // whichever calls first — `typePages` maps a schema's own local name and
  // its schema.org @type value(s) to the profile section that defines it
  // (for a type NAMED in prose); `refPages` maps a schema FILE's basename
  // to the same, keyed the way a JSON Schema `$ref` actually points
  // (`legislation-object`, not "LegislationObject") so a $ref can be
  // resolved without guessing a title from a kebab-case filename.
  let typePages = null
  let refPages = null
  function ensureTypeLookups(builtProfiles) {
    if (typePages || !builtProfiles) return
    typePages = {}
    refPages = {}
    for (const b of builtProfiles) {
      for (const s of b.schemas) {
        const url = `/profiles/${b.slug}/#${s.slug}`
        // s.title is the schema's own local name (what a description
        // actually says, e.g. "the Jurisdiction this applies to");
        // s.types is the schema.org @type value(s) it's allowed to
        // carry, which for an enum-typed schema (Jurisdiction can be
        // AdministrativeArea/Country/State/City) never includes the
        // local name itself, so both need mapping, not just one.
        for (const t of [s.title, ...s.types]) typePages[t] = url
        refPages[s.file.replace('.schema.json', '')] = { title: s.title, url }
      }
    }
  }

  // Render a JSON Schema "type" cell: enum, $ref, or plain type. A $ref
  // prints as the referenced schema's real name, linked to its profile
  // section, instead of the raw relative file path JSON Schema uses
  // internally (`../_core/reference.schema.json` -> a clickable
  // `Reference`) — the path depth is a repo-layout accident, not
  // information a reader needs. Takes the whole field (not just `f.def`)
  // because an enum backed by a code list (`f.enumLinked`, set in
  // profiles.js right where `f.codelistLink` is) prints as plain `string`
  // instead of every value spelled out — the Field name already links to
  // that same list's own tabulated page, so the full value list stays
  // available, just not duplicated here. An enum with no code list (a
  // schema.org @type choice list, say) is the only place those values are
  // documented, so it keeps every one. Returns HTML; callers must `| safe` it.
  eleventyConfig.addFilter('fieldType', (f, builtProfiles) => {
    if (!f || !f.def) return ''
    const field = f.def
    ensureTypeLookups(builtProfiles)
    const refName = (ref) => {
      const base = ref.replace('.schema.json', '').split('/').pop()
      const page = refPages && refPages[base]
      return page ? `<a href="${page.url}">${page.title}</a>` : base
    }
    if (field.$ref) return refName(field.$ref)
    if (field.const) return `"${field.const}"`
    if (field.enum) return f.enumLinked ? 'string' : field.enum.map((e) => `"${e}"`).join(' | ')
    if (field.type === 'array' && field.items) {
      const inner = field.items.$ref ? refName(field.items.$ref) : field.items.type || 'object'
      return `${inner}[]`
    }
    return field.type || 'object'
  })

  // Pull the schema.org term a description mentions, for the mapping column.
  eleventyConfig.addFilter('schemaOrgTerm', (desc) => {
    if (!desc) return null
    const m = desc.match(/schema:([A-Za-z]+)/)
    return m ? m[1] : null
  })

  eleventyConfig.addFilter('count', (o) => (o ? Object.keys(o).length : 0))

  // External-standard names that a non-technical reader can't be expected
  // to already know get linked to that standard's own /standards/ page —
  // STANDARDS lives in _data/standards.js, shared with docs.js (SPEC.md's
  // rendered HTML runs through the same function, not just .njk-templated
  // text).
  eleventyConfig.addFilter('linkifyTerms', linkifyTerms)

  // Backtick-quoted spans in schema/field description prose ("`schema:
  // VideoObject` or `AudioObject`") render as real <code>, the same way
  // a field's own name already does in the Field column — so a type or
  // property name mentioned in body text reads as code everywhere it
  // appears, not just there. A bare gs:-local type (Jurisdiction,
  // GovernmentOrganization...) links to the profile page section that
  // actually defines it, via the same `typePages` lookup `fieldType`
  // above builds — this is what makes a field's reference to another type
  // clickable, not just its own code-list-backed value.
  eleventyConfig.addFilter('inlineCode', (html, builtProfiles) => {
    if (!html) return ''
    ensureTypeLookups(builtProfiles)
    return html.replace(/`([^`]+)`/g, (match, term) => {
      const isLocal = term.startsWith('gs:')
      const bare = isLocal ? term.slice(3) : term.startsWith('schema:') ? term.slice(7) : term
      if (!isLocal && contextTerms.has(bare)) {
        return `<code><a href="https://schema.org/${bare}">${term}</a></code>`
      }
      if (typePages && typePages[bare]) {
        return `<code><a href="${typePages[bare]}">${term}</a></code>`
      }
      return `<code>${term}</code>`
    })
  })

  // Heading anchors + "On this page" TOC — the Eleventy-native equivalent
  // of govfresh/lukefretwell's anchor_headings.html + toc.html (Liquid,
  // can't run here). Ids are assigned here rather than left to Eleventy's
  // IdAttributePlugin (which only fills in headings that don't already
  // have one) so the anchor link and the TOC entry always agree on the
  // same id. Renders the link icon as an inline fill="currentColor" SVG
  // (same technique as brand-mark.html) rather than a Font Awesome
  // ligature, since gov-schema doesn't load an icon font.
  const slugify = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const LINK_ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512" fill="currentColor"><path d="M579.8 267.7c56.5-56.5 56.5-148 0-204.5c-50-50-128.8-56.5-186.3-15.4l-1.6 1.1c-14.4 10.3-17.7 30.3-7.4 44.6s30.3 17.7 44.6 7.4l1.6-1.1c32.1-22.9 76-19.3 103.8 8.6c31.5 31.5 31.5 82.5 0 114L422.3 334.8c-31.5 31.5-82.5 31.5-114 0c-27.9-27.9-31.5-71.8-8.6-103.8l1.1-1.6c10.3-14.4 6.9-34.4-7.4-44.6s-34.4-6.9-44.6 7.4l-1.1 1.6C206.5 251.2 213 330 263 380c56.5 56.5 148 56.5 204.5 0L579.8 267.7zM60.2 244.3c-56.5 56.5-56.5 148 0 204.5c50 50 128.8 56.5 186.3 15.4l1.6-1.1c14.4-10.3 17.7-30.3 7.4-44.6s-30.3-17.7-44.6-7.4l-1.6 1.1c-32.1 22.9-76 19.3-103.8-8.6C74 372 74 321 105.5 289.5L217.7 177.2c31.5-31.5 82.5-31.5 114 0c27.9 27.9 31.5 71.8 8.6 103.9l-1.1 1.6c-10.3 14.4-6.9 34.4 7.4 44.6s34.4 6.9 44.6-7.4l1.1-1.6C433.5 260.8 427 182 377 132c-56.5-56.5-148-56.5-204.5 0L60.2 244.3z"/></svg>'

  eleventyConfig.addFilter('withToc', (html) => {
    if (!html) return { html: html || '', toc: '' }
    const tocItems = []
    const seen = new Set()
    const processed = html.replace(/<h([23])([^>]*)>([\s\S]*?)<\/h\1>/g, (match, level, attrs, inner) => {
      const title = inner.replace(/<[^>]+>/g, '').trim()
      const existingId = attrs.match(/\sid="([^"]+)"/)
      let id = existingId ? existingId[1] : slugify(title)
      if (!existingId) {
        if (seen.has(id)) {
          let i = 2
          while (seen.has(`${id}-${i}`)) i++
          id = `${id}-${i}`
        }
        seen.add(id)
      }
      tocItems.push({ level: Number(level), id, title })
      const anchor = `<a class="heading-hashtag" href="#${id}"><span style="display:none">${id.replace(/-/g, ' ')} link</span>${LINK_ICON}</a>`
      const idAttr = existingId ? '' : ` id="${id}"`
      // Plain-text title, not the original inner HTML — a heading must
      // never contain a link (lf-ui/README.md's content conventions).
      // markdown-it's linkify:true auto-links bare domain-like text
      // (e.g. "schema.org") anywhere it appears, headings included, so
      // this can't be prevented at the markdown-authoring level; strip it
      // here instead, unconditionally, regardless of where a link in a
      // heading might come from.
      return `<h${level}${attrs}${idAttr}>${title} ${anchor}</h${level}>`
    })
    const toc = tocItems.length
      ? '<nav class="toc" aria-label="On this page"><p class="toc-heading">On this page</p><ul class="toc-list">' +
        tocItems.map((h) => `<li${h.level === 3 ? ' class="toc-h3"' : ''}><a href="#${h.id}" class="toc-link">${h.title}</a></li>`).join('') +
        '</ul></nav>'
      : ''
    return { html: processed, toc }
  })
}

export const config = {
  templateFormats: ['md', 'njk', 'html'],
  markdownTemplateEngine: 'njk',
  htmlTemplateEngine: 'njk',
  dir: {
    input: 'content',
    includes: '../_includes',
    data: '../_data',
    output: '_site',
  },
}
