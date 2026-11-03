# Plan: organization profile refinement (before `fees`)

Status: implemented on branch `org-refinement`, not committed. Written 2026-11-03. `npm run check` passes.
The Step 0 design review was folded into this document; the decisions below were confirmed.

Merges two earlier drafts: a general org-foundation plan, and a plan drawn from the County of
Marin implementation. This version is checked against what the repo already has.

## What already exists (the drafts missed this)

Both drafts propose a new `organizationType` property. The repo already has one:

| Draft proposal | Already in the repo |
|---|---|
| `organizationType` controlled vocabulary | `organizationClassification`, code list `profiles/_core/codelists/organization-classification.json` (legislature, executive, department, agency, committee, commission, court, office, enterprise), mapped to Popolo `classification` in `crosswalks/popolo.md` |
| One `GovernmentOrganization` class, no `GovDepartment` etc. | Already the rule |
| `parentOrganization` for hierarchy | In `organization.schema.json`, plus a SHACL shape in `shapes/schemaGov.shapes.ttl` |
| `subOrganization` vs `department` | Both present; descriptions already distinguish constituted bodies from administrative units |
| Jurisdiction is not an organization | Enforced in `tools/validate.py` (typed as both fails Core) |
| `identifier` separate from `@id` | `identifier` is **required**, scheme-qualified (`identifier.schema.json`) |
| Reference, never inline | Enforced by the reference check in `validate.py` |
| `gs:Post`, Popolo/ORG alignment, `Directory` as a `DataFeed` | `profiles/org/` |

So **do not add `organizationType`.** Extend `organizationClassification` if the vocabulary is
short, and leave the property name alone. A second property meaning the same thing would be the
exact duplication both drafts warn against.

## Where the drafts disagree, and the call

1. **`@id` convention.** Draft 1 says `/id/org/...` persistent URIs. Draft 2 says use the
   canonical public page URL and never invent `/id/` URLs. The repo's fixtures and pilots all use
   `/id/organization/<slug>` on the publisher's domain, and the `@id` description says
   "dereferenceable identifier". **Keep `/id/organization/`** as the recommended form. Take from
   Draft 2 the warning that an `@id` must not imply a URL that was never established, and that
   `url` is where the public page goes. Take from Draft 1 that `@id` is the entity, not the page.
   Do not tell publishers to use page URLs as `@id`: pages move, which is the failure Draft 1
   describes. Document the no-canonical-URL case as: mint a URI in a namespace you control, or
   use a `urn:`/`tag:` URI. Do not omit `@id`, because every reference depends on it.
2. **Hierarchy direction.** Draft 1: `parentOrganization` only. Draft 2: also expose children via
   `department`. **Child → parent is canonical** (`parentOrganization`). `subOrganization` and
   `department` stay valid for publishers who emit them, but are derived views. Add a validator
   check that they agree with `parentOrganization` instead of banning them.
3. **`program`.** Leave it out of the classification vocabulary. Programs are services or
   initiatives unless they have their own staff and budget, and `gs:Project` / services already
   cover them. Revisit later.
4. **Marin fixture.** Marin source data is not in the repo. Build the generic fixture now; add a
   Marin pilot only if the source export is supplied (see open questions).
5. **Relationship types** (appoints, oversees, funds). Draft 1: investigate first. Agreed. Do not
   mint `gs:OrganizationRelationship` unless W3C ORG / Popolo genuinely cannot express it.
   W3C ORG has `org:linkedTo`, `org:transitiveSubOrganizationOf`, and reporting-line terms to check
   first.

## Scope

In: organization model clarity, one vocabulary extension if justified, ID guidance, a multi-level
fixture, validation, docs, crosswalk.

No new `gs:` classes or properties are planned here, which keeps `PLAN-per-term-pages.md`
unaffected (one new code-list value only).

Out: fees, and any redesign of services, permits, budgets, procurement or projects. Problems found
elsewhere go in a follow-up list in this file. One exception to note, not fix: `gs:fee`
(`vocabulary/schemagov.ttl`, "Fee charged for a permit") will need reconciling with the fees
profile.

## Step 0: short design review (before any file changes)

One page, appended to this file, covering: current model, gaps, the existing-standard answer for
each gap, proposed extensions, files touched, backward-compatibility impact, and an
implement/don't-implement call per item. Use the Concept / Existing option / Sufficient? /
Proposal / Compatibility / Example template for anything new. Stop for approval here.

## Candidate changes (each subject to the Step 0 review)

### A. Extend `organizationClassification` (likely, small)
Gaps against both drafts: `board`, `division`, `bureau`, `authority`, `district`. Mapping notes:
a board of supervisors is already `legislature`; a county's government root is `executive` or
needs `government`. Review each against Popolo and W3C ORG before adding. Adding values to the
code list and the schema `enum` is backward compatible. Document that hierarchy depth never
implies classification, and that the value is not inferred from the name.

### B. Hierarchy rules (docs + validator)
- Convention: `parentOrganization` defines hierarchy; classification and names do not.
- Validator: `parentOrganization` target exists, is a `GovernmentOrganization`, no cycles, and any
  `subOrganization`/`department` listing agrees with it. Check which of these `validate.py` and
  the shapes already do before adding.
- SHACL: only if a rule is not already covered at `shapes/schemaGov.shapes.ttl` ~line 64 and ~405.

### C. ID and identifier guidance (docs only)
- Requirements: stable, unique, persistent, dereferenceable where practical, independent of page
  navigation and of display names.
- `@id` identifies the entity, `url` the public page, `identifier` the source-system codes.
- Identifiers are unique only within their scheme. The same code can appear under several branches
  of a source system; qualify with `propertyID`.
- Public structure vs. ERP / budget / HR structure: publish the public chart in
  `parentOrganization`. Keep source-system structure in `identifier` for now. Document the gap
  rather than adding `administrativeParent`.

### D. Jurisdiction vs. organization (docs + example)
Example County (`AdministrativeArea`) separate from County of Example
(`GovernmentOrganization`) linked by `areaServed`. Add the diagram to the org README. Employees,
departments, budgets, services, contracts and fees attach to the organization.

### E. Non-hierarchical relationships (investigation only)
Write up what Popolo, W3C ORG and schema.org cover. Implement nothing unless there is a real gap.

### F. Do not model services, permits, programs or fees as org units
One short README section. This is the rule the fees profile depends on.

## Files likely to change

- `profiles/_core/codelists/organization-classification.json`
- `profiles/_core/schema/organization.schema.json` (enum, descriptions)
- `profiles/org/README.md` (new "Organization structure" section)
- `profiles/_core/README.md`
- `crosswalks/popolo.md`, `profiles/org/crosswalk.md` (classification, parent, relationships, and
  where schemaGov adds semantics beyond schema.org)
- `tools/validate.py`, and `shapes/schemaGov.shapes.ttl` only if needed
- `examples/example-city/` renamed to `examples/example-gov/`, then `organizations.jsonld` extended
  to a three-level structure (see Fixtures)
- `examples/_invalid/` (new failing cases)
- `vocabulary/schemagov.ttl` only if a term is added
- `ROADMAP.md` or a changelog entry, per repo convention

## Fixtures

**Step 1: rename `examples/example-city` to `examples/example-gov`**, in its own commit before any
model changes. The fixture will grow beyond cities (county, state), so the name should not say
city. It is mechanical but wide: about 590 occurrences in 25 files, including every fixture file,
`package.json` (`validate`, `validate:shacl`), `_data/examples.js`, `.github/workflows/deploy.yml`,
`tools/*`, `SPEC.md`, `README.md`, `LICENSING.md`, `GEOSPATIAL.md`, `shapes/README.md`,
`profiles/_core/README.md`, `profiles/projects/README.md`, `examples/_legacy/`. Decide the `@id`
domain at the same time (`example-city.gov` to `example.gov`). Changing `@id`s is safe here because
nothing outside the repo references them, but do it in the same commit so history stays readable.
The entities inside (Example City, Mayor, and so on) keep their content for now. Only the
directory, domain and slugs change. Confirm `npm run check` is green before and after. Also check
the built site for a published `/examples/example-city/` path that needs a redirect.

**Step 2: extend `example-gov`** rather than create a new directory, to match the repo's
one-file-per-profile layout:

```
Example City (jurisdiction)        areaServed
  └─ Example City Government       government
       ├─ City Council             legislature
       ├─ Community Development    department
       │    ├─ Planning            division
       │    └─ Environmental Health division
       └─ Public Works             department
```

A county or state variant can be added later as a second jurisdiction/government in the same
directory, which is why the name is neutral.

Every link is an `@id` reference. No inlined organizations. Check the existing org file (10 org
`@id`s today) before restructuring, and keep existing `@id` slugs stable apart from the rename.

Invalid fixtures: unknown classification value; `parentOrganization` pointing at a jurisdiction;
parent cycle; `department` listing disagreeing with `parentOrganization`.

## Acceptance criteria

- `GovernmentOrganization` is still the one organization class; jurisdictions stay separate.
- No `organizationType` property exists; classification covers it.
- Hierarchy is documented and validated through `parentOrganization`.
- ID, `url` and `identifier` purposes are documented, including the no-canonical-URL case.
- A three-level local-government fixture validates; new invalid fixtures fail for the right reason.
- Crosswalks updated, with schemaGov-added semantics called out.
- Existing pilots validate unchanged. `npm run check` passes.
- No fees schema introduced.

## Then: fees

Depends on stable organization IDs and the `Fee → Organization / Service / Permit / Legislation`
references. Plan separately: `FeeSchedule`, `Fee`, `FeeAmount`, and what happens to `gs:fee` on
permits.

## Decisions (confirmed)

1. **Marin pilot: skip for now.** No Marin data is in the repo, and a pilot needs an adapter plus
   committed source data. The Marin lessons are already built into this plan (mixed unit kinds,
   duplicate source IDs, external agency domains, public vs. admin structure). Cover them with
   synthetic fixtures. Revisit as `pilot-marin-organizations` once the export is available.
   Note that the duplicate-identifier case still needs an invalid or tricky fixture without Marin.
2. **Add `government` to the classification list.** The root body of a government is neither an
   `executive` nor a `legislature`: a county or city contains both. The existing fixture labels the
   root `executive`, which is a mislabel, since the council sits beneath it. `government` means
   the whole-of-government body at the top of a tree, with no `parentOrganization`. Backward
   compatible (new value only). Existing pilot roots keep their current values; the `example-gov`
   root changes to `government`. State in the docs that a state or national government is also
   `government` at its own level, with `governmentLevel` distinguishing them.
3. **Keep `subOrganization` and `department`; do not deprecate.** schema.org defines them as
   inverses of `parentOrganization`, so removing them would diverge from schema.org. The existing
   fixture uses them with a real distinction (`subOrganization` for a constituted body like the
   council, `department` for an administrative unit like public works), and deprecating would
   break it. The risk is drift, so handle it with the validator: `parentOrganization` is
   canonical, and a listed child whose own `parentOrganization` disagrees fails.

## What was built

- Branch `org-refinement` from `main`. `examples/example-city` renamed to `examples/example-gov`
  (domain `example.gov`); city entity slugs unchanged. No redirect: the folder is only a
  passthrough copy of fixture files, not linked from the site or the sitemap.
- Classification adds `government`, `division`, `bureau`, `authority` only. `board` and
  `district` were dropped (covered by `legislature` / `commission` and `governmentLevel`).
- `tools/validate.py` org hierarchy checks; `examples/_invalid/organizations.jsonld` (5 faults);
  `tools/check-invalid.py` updated.
- Docs: `profiles/org/README.md`, `profiles/org/crosswalk.md`, `crosswalks/popolo.md`,
  `ROADMAP.md` entry (the repo's changelog).
- Not done: Marin pilot, `gs:OrganizationRelationship`, administrative-parent property.
