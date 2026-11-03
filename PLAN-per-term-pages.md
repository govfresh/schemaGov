# Plan: per-term web pages for the schemaGov vocabulary

Status: planned, not started. Written 2026-10-05.

Counts below are as of 2026-10-05. The org refinement (`PLAN-org-refinement.md`) and the later
`fees` profile will add terms. Regenerate the counts before starting. Building this before `fees`
means the new fee terms get pages from the start.

## Problem

`vocabulary/schemagov.ttl` defines 228 `gs:` terms. 28 are code-list sets and already have
pages (for example `/v1/ServiceStatus/`). The other 200 are classes and properties, and none
has a page, so `https://schema.govfresh.com/v1/Project` and `https://schema.govfresh.com/v1/produces`
do not load. This applies to every profile, not only Projects (`gs:Meeting` and
`gs:electionDate` are the same).

## The hard part: case collisions

47 groups of terms differ only by letter case, so their page paths collide on a case-insensitive
file system (macOS, Windows). Examples:

- `Post` (class) and `post` (property)
- `Election` and `election`
- `governmentLevel` (property) and `GovernmentLevel` (code-list set, which already has a page)
- `projectStatus` and `ProjectStatus`

The IRIs are published identifiers, so they cannot be renamed. Deploys run on Linux, which is
case-sensitive, so production would be fine. A local build would silently overwrite one page
with the other, and `check-namespace` would pass or fail depending on which spelling won.

## Proposed approach

For each group of names that collide case-insensitively, render **one combined page** and write
the same content at every spelling. It lists each term in the group (class, property, set), so
a collision cannot change what a page says on any OS. Every IRI still resolves. The existing
code-list set pages use the same combined rendering where a set shares a name with a property.

## Steps

1. **Parse the vocabulary.** New `_data/vocabulary.js` reading `schemagov.ttl` with the `n3`
   package (new dependency). Output per term: label, comment, parent class or property, the types
   it applies to and returns, and the profile section it sits under.
2. **Page template.** One new template with pagination, in the same look as the code-list pages.
   Each page embeds JSON-LD for the term and links to the `.ttl` file, since a static host cannot
   do content negotiation.
3. **Merge the set pages.** Fold `content/term.njk` into the combined rendering where a set shares
   a name with a property.
4. **Site integration.** Add the terms to the vocabulary index page and the search index. The
   sitemap picks up new pages automatically.
5. **Checks.**
   - `tools/check-namespace.js` expects every vocabulary term IRI to resolve.
   - New check: fail if two paths that are equal ignoring case have different content.
   - New audit: every `gs:` term used in the context, schemas and shapes is defined in the `.ttl`.
     This may surface terms that are used but undefined.
6. **Size.** About 200 new pages and one new dependency. The data file and template are small. The
   collision handling and the checks are the real work.

## Decisions (settled 2026-11-03)

- **Collision approach: one combined page, written at every spelling.** It is the only option that
  keeps every IRI resolving on every OS and makes the page content identical whichever spelling
  wins. Leaving collided terms without pages would leave 47 groups of IRIs dead, including
  `Post`, `Election` and `Project`-related terms that publishers are most likely to look up.
- **`n3` dependency: yes, as a dev dependency.** `schemagov.ttl` is simple (no blank nodes or
  collections), but a hand-written reader would be one more thing to maintain and could quietly
  misread a comment or a multi-line string. `n3` is small and widely used, and the repo already
  depends on a real RDF parser (`rdflib`) in its Python checks.
- **Scope: full per-term pages, not the single `/vocabulary/terms/` page.** The anchor page is
  about a tenth of the work, but the term IRIs would still not load, which is the actual problem.

Next step: regenerate the term counts (they changed after the org refinement added four code-list
values), then start at step 1.
