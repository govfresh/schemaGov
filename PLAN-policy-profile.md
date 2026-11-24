# Plan: policy and regulation support (reviewed against `main`, 2026-11-23)

Status: steps 0-5 implemented on branch `policy-profile` (2026-11-23); `npm run check` passes. Steps 6-7: structure-only Marin pilot added 2026-11-24 (`examples/pilot-marin-pmr/`, no regulation text); findings are in its README. Partial ISO dates (`YYYY`, `YYYY-MM`) are now accepted on `legislationDate`, `legislationDateOfApplicability` and `legislationDateVersion`.

Decisions taken: definition link is `subjectOf` (no `gs:definedIn`); `legislationJurisdiction` is required only on top-level works; citations are a mixed `{@id}`/string array with no `Citation` node. No `gs:` terms were added.

Goal: represent government policies, administrative and personnel regulations, procedures and
directives as structured JSON-LD, with the County of Marin Personnel Management Regulations
(PMRs) as the first real test. Nothing in the model is specific to Marin or to HR.

This revises a draft plan after checking it against the repo. The first section lists what
changed and why.

## What the review found (changes to the draft)

| Draft said | Repo reality | Change |
|---|---|---|
| New `provision.schema.json`, `policy.schema.json` | `validate.py` maps **one `@type` to one schema file** (`SCHEMA_FOR`). `Legislation` is already `code/legislation.schema.json`. A second schema for the same type would be ignored or collide, as `services` and `requests` already had to work around | **No parallel Policy/Provision types.** Documents, groups, regulations and provisions are all `Legislation`, tiered by `codificationLevel`. Extend `legislation.schema.json` additively. |
| Policy → `Legislation?`, Provision → `LegislationObject?` | `LegislationObject` is a **file** (a PDF or XML rendering), not a clause. `Legislation` + `hasPart` + `isPartOf` + `position` is already how the `code` profile and `pilot-uk-legislation` (11 parts, 122 sections, 136 entities) model structure | Provision = `Legislation` at a lower `codificationLevel`. `LegislationObject` is used for the **source file** (see tables below). |
| Hierarchy: collection → group → policy → provision | `codificationLevel` already has `code, title, book, part, division, chapter, article, section, subsection, paragraph, schedule, annex`. The `code` README says depth comes from `isPartOf`, not a fixed tier list | Map by role, not by the source's word: collection = `code`, group = `part`, regulation = `chapter`, numbered provision = `section`, then `subsection`, `paragraph`. **Beware: PMR "Section 4" is a group, so it is `part`, not `section`.** The source label stays in `name` / `legislationIdentifier`. |
| Arbitrary nesting | Levels stop at `paragraph`, and `level` is optional | Keep nesting in `isPartOf`. Add `subparagraph` (and `clause`) only if the stress test needs levels the list lacks. Never enforce level ordering. |
| Ordering not mentioned | `hasPart` is an unordered `@set` in the context | Order comes from `position` (already in the schema). Say so in the README. |
| `policyType` code list in `profiles/policy/codelists/policy-type.json` | `legislationType` already exists with `regulation` and `directive`, among others | **No new property and no new code list.** Add `policy` and `procedure` to `code/codelists/legislation-type.json`. Do **not** add `personnelRegulation` or `administrativeRegulation`: that is a subject or issuer, not a type. Use `regulation` plus `about`/`keywords`. |
| Effective date → `legislationDate`? | `legislationDate` is **adoption/signature**. Effective is `legislationDateOfApplicability`. The code profile already separates them | Effective = `legislationDateOfApplicability`. Revision date = `legislationDateVersion`. Adoption = `legislationDate`. Say this in the mapping, because the draft's guess is the common mistake. |
| Revision number, prepared by, approving authority | `schema:version`, `creator` (in the context), `legislationPassedBy` / `legislationResponsible` / `legislationCountersignedBy`, `publisher`, `url`, `encoding` | All exist. **Zero new properties** for provenance. No `gs:` term needed. |
| Definitions: `DefinedTerm.source` pointing at the provision | `source` is **not** a schema.org property and not in the context. `DefinedTerm` has only `termCode`, `inDefinedTermSet`, `name`, `description` | Definition text goes in `description`. Link back with `subjectOf` (a `CreativeWork` about the term), or mint one `gs:definedIn` if `subjectOf` reads wrong in the stress test. Decide before coding. |
| Definitions as addressable entities | `DefinedTerm` is only used inside code-list files today, never as a validated fixture entity. Not in `SCHEMA_FOR` | New `definition.schema.json` for `DefinedTerm` / `DefinedTermSet`, registered in `validate.py`. This is the **one genuinely new schema**. |
| `reference.schema.json` in the policy profile | `_core/reference.schema.json` is `{@id, @type, name}`, `@id` required, `additionalProperties: false`, and `collect_refs` treats such objects as pointers to check | Reuse it for resolved targets. **Do not fork it.** For an unresolved citation, use `schema:citation` as plain text. The context deliberately does not coerce `citation`, so IRI objects and strings can sit side by side. Never put a made-up `@id` on a literal. |
| "Reference" as a first-class entity | The plan also wants the literal citation kept when a target exists | Open decision, see below. Default: `citation` array of either `{@id}` or a string. If a regulation needs both the literal wording and the target, add a small `Citation` node only after a real case demands it. |
| Tables | Neither schema.org `Legislation` nor `code` models tables. The `code` README puts everything inside the text out of scope on purpose and delegates it to Akoma Ntoso | **This is the main architectural tension.** Resolve it by keeping per-provision `text` as plain authoritative text and attaching the **whole source file** as a `LegislationObject` (`text/html`, real `contentUrl`, `legislationLegalValue`). Tables and inline markup live there. Do not model table cells. Revisit only if the stress test shows tables are common and must be queryable. |
| `Legislation` requires `name` | Many provisions have no heading (`(a)`, `(1)`). Requiring `name` would force invented headings, which the plan forbids | Relax to "`name` **or** `legislationIdentifier`" via `anyOf`. Use `legislationIdentifier` for `27.2` or `(a)`. |
| `Legislation` requires `legislationJurisdiction` on every node | Thousands of provisions would repeat it. Inheriting from the parent is inference, which the plan forbids | Keep required on top-level nodes. For nodes with `isPartOf`, make it optional and let consumers walk up. **Needs your call**, see below. |
| `docs/policy-profile-mapping.md`, `docs/policy-profile-findings.md` | **There is no `docs/` directory.** Conventions: `crosswalks/*.md`, `PLAN-*.md` at root, profile README, `SPEC.md` | Mapping table → `crosswalks/policy.md`. Findings → a section in this plan file, then `profiles/policy/README.md` once settled. No new `docs/` tree. |
| `profiles/policy/schema/{policy,provision,reference}.schema.json` | See above. Only definitions are new | `profiles/policy/` holds `README.md`, `schema/definition.schema.json`, and nothing else unless the stress test earns it. No `codelists/` (the type terms go in `code`). |
| "Add tests" | **No test framework exists.** Negative testing is `examples/_invalid/*.jsonld` plus a `FAULTS` map in `tools/check-invalid.py` | Add fault nodes there (list below). Same for SHACL, in `shapes/schemaGov.shapes.ttl`. |
| Validation commands only | A new profile must be registered in several places or it silently isn't checked | Checklist below. |
| Pilot example not specified | Real-publisher examples live in `examples/pilot-*/` with a README, are wired into `validate:pilot`, and generated ones have an adapter in `tools/adapters/` | Add `examples/example-gov/policy.jsonld` (generic, fictional, small) and `examples/pilot-marin-pmr/` (PMR 27 only). The full-manual conversion stays **outside** the repo, as the draft says. |
| Marin text in the repo | The repo is **CC0**. Pilot READMEs state the source licence (e.g. legislation.gov.uk) | **Check the licence and terms of the Marin source before committing any verbatim text.** If unclear, the pilot can carry structure and short excerpts with `url` back to the source. |

## What already covers each concept

| Concept | Existing schemaGov / schema.org | Gap | Recommendation |
|---|---|---|---|
| Policy collection / manual | `Legislation`, `codificationLevel: code`, `legislationType` | Code list lacks `policy`, `manual` | Reuse; add `policy`, `procedure` types |
| Group | `Legislation`, `codificationLevel: part` (or `division`) | None | Reuse |
| Regulation / policy | `Legislation`, `codificationLevel: chapter`, `legislationType: regulation` or `policy` | Type terms | Reuse |
| Provision, nested | `Legislation` + `isPartOf`/`hasPart`/`position`, levels `section`→`paragraph` | `name` required; level list may stop short | Relax `name`; add levels only if needed |
| Provision text | `schema:text` on `CreativeWork`. `@vocab` is schema.org, so it already expands | Not listed in the context or schema | Add `text` to `legislation.schema.json`. No `gs:` term |
| Heading / number | `name` / `legislationIdentifier` | None | Reuse |
| Identifier | `identifier` (`_core/identifier`), `legislationIdentifier` | None | Reuse |
| Jurisdiction | `legislationJurisdiction` → core jurisdiction | Required on every node | Make optional below top level |
| Issuing organization | `publisher`; `legislationPassedBy`; `legislationResponsible` | None | Reuse |
| Prepared by | `creator` | None | Reuse |
| Approving authority | `legislationPassedBy`, `legislationCountersignedBy` | None | Reuse |
| Source | `url`; `encoding` → `LegislationObject` | None | Reuse. Source HTML/PDF is a `LegislationObject` |
| Effective date | `legislationDateOfApplicability` | None | Reuse. **Not** `legislationDate` |
| Adoption date | `legislationDate` | None | Reuse |
| Revision date | `legislationDateVersion` | None | Reuse |
| Revision number | `schema:version` | Not in schema file | Add `version` to `legislation.schema.json` |
| In force | `legislationLegalForce` | None | Reuse; never a status string |
| Supersedes / amends | `legislationAmends`, `legislationConsolidates`, … | None | Reuse |
| Definition | `DefinedTerm`, `DefinedTermSet`, `termCode`, `inDefinedTermSet` | No schema file, no link to source provision | New `definition.schema.json`; `subjectOf` or one `gs:definedIn` |
| Internal reference | `citation` → `{@id}` of another `Legislation` | None | Reuse `citation` |
| External reference, resolvable | `citation` → `{@id}` | None | Reuse |
| External reference, unresolved | `citation` as text | None | Reuse; no invented IRI |
| Form | `citation` → a `CreativeWork`/`DigitalDocument` with a real URL, else text | Unclear | Decide in the stress test |
| Table | none | **Real gap** | Defer. Keep in the source `LegislationObject` |
| Applicability / purpose | `description`, or a part at a defined level | Unclear | Preserve as text provisions. Do not extract |
| Obligations, deadlines, eligibility | none | Out of scope | Deferred |

## Profile boundary

Confirm `profiles/policy/` with these terms:

- A **thin profile on top of `code`**. Depends on `_core` and `code`. It does not redefine `Legislation`.
- Policies are not laws, so labelling a procedure as `Legislation` will bother some readers. The README must say plainly that schema.org's `Legislation` is the closest typed work, that the profile uses `legislationType` to distinguish policy from statute, and that this matches how the `code` profile already treats ordinances and resolutions.
- The `code` README says clause-level structure is out of scope. State the boundary in the policy README: **addressable numbered units are in scope; inline markup (internal anchors, amendment instructions, table cells) is not.**
- Alternative if you disagree: put everything in `code` and skip a new profile. I recommend against it, because `code` is about law and the policy profile adds definitions and citation conventions that a municipal code user does not need.

## Principles

- Search the repo, the context and schema.org before adding anything. Reuse when the meaning fits.
- Every change to `legislation.schema.json` is **additive and optional**, except relaxing two `required` rules. Existing valid data stays valid.
- Preserve authoritative text. No summaries, no derived fields (`deadlineDays`, `employeeMust`, `eligible`).
- Do not infer dates, authorities, citations or jurisdictions that the source omits.
- Separate source-data problems from schema problems in the findings.
- Minimum new vocabulary: probably zero `gs:` terms, at most one (`gs:definedIn`). If so, `npm run check:vocabulary` and the term-page generator pick it up automatically, and the description must pass `npm run check:readability`.

## Steps

### 0. Settle three decisions (before any code)
1. Definition → provision link: `subjectOf` or `gs:definedIn`.
2. `legislationJurisdiction`: required everywhere, or only on nodes with no `isPartOf`.
3. Citation shape: `citation` as mixed `{@id}`/string, or a `Citation` node.

### 1. Mapping
Write `crosswalks/policy.md` from the table above, in the style of `crosswalks/akoma-ntoso.md`. Add a "where publishers get this wrong" note: effective date vs adoption date, and "Section" as a group vs a provision.

### 2. Extend `code` (additive)
- `legislation.schema.json`: add `text`, `version`, `creator`, `publisher`, `citation` (array of reference or string); relax `required` to `name` **or** `legislationIdentifier`, and jurisdiction per decision 2.
- `legislation-type.json`: add `policy`, `procedure`. Check `npm run audit:jsonld` that the new codes do not expand into schema.org (the same collision risk the org work found).
- `codification-level.json` and the schema `enum`: add levels only if step 6 shows a need.
- `shapes/schemaGov.shapes.ttl`: `citation` targets must be `Legislation` or text; `hasPart`/`isPartOf` must agree (as the org shape already does for `parentOrganization`).

### 3. Add `profiles/policy/`
- `README.md`: the boundary decision, hierarchy mapping table, why `Legislation` is reused, what is deferred.
- `schema/definition.schema.json` for `DefinedTerm` and `DefinedTermSet`. Register both types in `SCHEMA_FOR` and `policy` in `PROFILE_DIRS` in `tools/validate.py`.
- Registration checklist, or the profile silently isn't checked or shown: `tools/validate.py`, `_data/profiles.js` (`IMPLEMENTED`), the `SPEC.md` profile table and layout lines, the root `README.md` table and layout, `package.json` (`validate:pilot`), `.github/workflows/deploy.yml` if it lists profiles.

### 4. Examples
- `examples/example-gov/policy.jsonld`: fictional, small: manual → group → regulation → provisions with a nested paragraph, one definition, one internal and one external citation, organization and jurisdiction by reference. It must reuse the existing example-gov organization and jurisdiction `@id`s.
- `examples/pilot-marin-pmr/`: PMR 27 only, with a README that states the source and licence. Subject to the licence check.

### 5. Validation and fault tests
Add to `examples/_invalid/` and the `FAULTS` map in `tools/check-invalid.py`:
- provision with neither `name` nor `legislationIdentifier`
- `isPartOf` pointing at a non-`Legislation` entity
- `isPartOf` cycle
- parent lists a child that names a different parent
- `legislationType` outside the code list (e.g. `personnelRegulation`)
- `citation` pointing at an entity that does not exist
- malformed effective or revision date
- effective date before adoption date, if both present
- `legislationPassedBy` pointing at a jurisdiction
- definition with no `inDefinedTermSet`, or pointing at a non-set
- definition not linked to a provision (only if decision 1 makes this required)

Then run, and all must pass: `npm run check` (build, namespace, vocabulary, context, audit, validate, SHACL, invalid, pilots). Existing profiles and pilots must still pass untouched.

### 6. Stress test (outside the repo)
Convert the full Marin PMRs with a throwaway script kept in the scratchpad or a separate directory. Do not add it to `tools/adapters/` unless you decide to keep it.

Check: all four groups, every PMR, all numbered provisions, nesting depth (record the maximum), definitions, tables, forms, internal and external citations, purpose/applicability, approval metadata. Run the repo validators over the output. Record counts: entities, max depth, unresolved citations, provisions without a heading.

Source problems (malformed HTML, inconsistent numbering, missing dates) go in the findings as **source issues**. A schema change is justified only when well-formed source data cannot be represented.

### 7. Findings
Record in the profile README (or `PLAN-policy-profile.md` while in progress):
- **Existing coverage**: the table above, with what turned out to be wrong.
- **New concepts**: expected to be `definition.schema.json`, two type terms, additive fields, possibly one `gs:` term.
- **Source issues**: from step 6.
- **Deferred semantics**: obligations, permissions, prohibitions, deadlines, eligibility, workflows, responsible actors, table cell structure, inline cross-reference anchors, amendment history between revisions.
- **Future uses**: policy search, APIs, retrieval for AI assistants (each provision has a stable `@id`, a parent chain and authoritative text), comparison and change tracking across `legislationDateVersion`, links from regulations to the laws they implement via `citation`.

## Acceptance criteria

1. Policies, regulations and procedures are representable with the existing `code` model plus the small additions above.
2. No Marin-specific or HR-specific vocabulary anywhere in the schema, code lists or vocabulary.
3. Nested provisions of arbitrary depth, ordered by `position`, with hierarchy held in `isPartOf`/`hasPart`, not in IDs.
4. Internal and external references work. An unresolved citation keeps its literal text and has no invented IRI.
5. A definition is an addressable entity that links back to its source provision.
6. Jurisdiction and organization use the existing core entities, by reference.
7. Adoption, effective and revision dates, revision number, creator and approving authority are representable with existing properties.
8. A representative Marin PMR validates (`validate.py` and `shacl.py`), and the fictional example does too.
9. The full Marin manual converts without losing hierarchy or authoritative text. Anything that does not fit is documented, not silently invented.
10. `npm run check` passes, including every existing example and pilot.
11. New `gs:` terms, if any, are defined in `vocabulary/schemagov.ttl` and get term pages.

## Constraints (unchanged from the draft)

Do not summarize or rewrite policy text. Do not infer missing dates, authorities, citations or relationships. Do not add properties just to make the Marin conversion easier. Do not model legal interpretation. Reference rather than duplicate. Keep the first version small.
