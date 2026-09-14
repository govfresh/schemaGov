import fs from 'node:fs/promises'
import path from 'node:path'
import MarkdownIt from 'markdown-it'

const ROOT = path.resolve(import.meta.dirname, '..')
// linkify:false — with it on, markdown-it auto-links bare domain-like text
// (e.g. "schema.org") anywhere it appears, always externally to the literal
// domain. Every standard already gets a real internal /standards/ page, so
// an auto-generated external link is never what we want here; explicit
// [text](url) markdown links are how every intentional link in these docs
// is written.
const md = new MarkdownIt({ html: true, linkify: false })

// markdown-it's default table renderer emits a bare <table> with no class
// at all, so a markdown table in SPEC.md would never pick up the shared
// .table styling (lf-components.css) that every hand-authored <table> in
// the njk templates already uses — wrap it the same way those are.
md.renderer.rules.table_open = () => '<div class="table-responsive"><table class="table align-middle">\n'
md.renderer.rules.table_close = () => '</table></div>\n'

/**
 * Root-level .md files are rendered here rather than duplicated into a
 * template, so a published page and the repository file it documents can
 * never disagree. Every page built this way is a single source file in,
 * one page out — no hand-typed <section>/<div> structure to keep in sync.
 */
async function renderDoc(file) {
  let text
  try {
    text = await fs.readFile(path.join(ROOT, file), 'utf8')
  } catch {
    return ''
  }
  // Drop the leading H1; the page template supplies its own.
  const body = text.replace(/^#\s+.+\n/, '')
  return md.render(body)
}

export default async function () {
  return {
    spec: await renderDoc('SPEC.md'),
    about: await renderDoc('ABOUT.md'),
  }
}
