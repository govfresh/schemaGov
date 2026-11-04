# Plan: organization and budget model update (mission, service area, Fund, Program)

Status: planned, not started. Reviewed against `main` on 2026-11-03.

Goal: let schemaGov describe an organization's mission, a service-area grouping, and the durable
things a budget points at (organization, fund, program), without minting anything the model already
has. Keep it generic. Nothing here is specific to one government.

This revises an earlier draft after checking it against the repo. The first section lists what
changed and why.

## What the review found (changes to the draft)

| Draft said | Repo reality | Change |
|---|---|---|
| Add `mission` to `GovernmentOrganization` | schema.org has no `mission` or `missionStatement`; the context has none | **Keep.** Genuine gap. Mint `gs:mission`. |
| Add classification `service-area` | Codes are camelCase (`specialPurpose`, `exOfficio`, `temporarilyClosed`) | Use **`serviceArea`**. Also confirm it does not collide with schema.org's `serviceArea` property (see step 2). |
| Add `administeredBy` | **`gs:administeredBy` already exists**, scoped to `gs:Election` ("the body running the election") | **Reuse it.** Widen its `domainIncludes` to Fund and Program and generalize the comment. Do not mint a second property. |
| Class named `GovernmentProgram` | gs: classes are unprefixed (`Budget`, `BudgetLine`, `Project`, `Post`). The `Government…` prefix is a schema.org habit (`GovernmentService`, `GovernmentPermit`) | Name it **`gs:Program`**, and **`gs:Fund`**. Avoids reading like a schema.org term. |
| Evaluate whether Program is needed | `gs:Project` exists, but its README defines it as *bounded* work that ends. The service `provider` is an org. `programClassification` is only a code string | **Program is a real gap**: an ongoing activity that outlives any one budget or project. Keep it small. |
| `@type: "Jurisdiction"` in the district example | There is no `Jurisdiction` type. Jurisdictions are `AdministrativeArea`, `Country`, `State` or `City` | Fix the example. |
| Document elected officials, department heads, districts, contact info | All already modelled and exercised: `Post` with `representsJurisdiction`, `EmployeeRole` with `post`, district jurisdictions and `Boundary` in `example-gov`, `address`/`contactPoint`/`location`/`Facility` in `_core` | **Documentation and example work only. No schema change.** |
| Top diagram: Division → Program | Programs are not organizations. The org refinement already left `program` out of `organizationClassification` for this reason | A Program **sits beside** the org tree, linked by `administeredBy`. It is never a child in it. |
| `fundClassification` property | No evidence yet that it is needed | **Defer.** `identifier` plus `name` carry a fund today. |
| Fund and Program placement unspecified | Budget is their only consumer today | Put both in the **`budget` profile** for v1. Revisit if `services` later references Program. |

## Principles (unchanged)

- Search the repo, the context, and schema.org before adding anything. Reuse when the meaning fits.
- Nothing removed or redefined. `fundSource`, `programClassification`, `description` and
  `administrativeClassification` keep their meaning.
- Every new property is optional. Existing valid data stays valid.
- No new classes for department, division, service area, supervisor, director or district.

## Steps

### 1. `mission` on organizations (small)
- `gs:mission`, `schema:domainIncludes schema:GovernmentOrganization`, `rangeIncludes schema:Text`.
  Definition: "The formally stated mission or purpose of the organization." `description` keeps its
  meaning.
- Files: `vocabulary/schemagov.ttl`, `context/v1/context.jsonld`,
  `profiles/_core/schema/organization.schema.json`.

### 2. `serviceArea` classification (small)
- Add `serviceArea` to `profiles/_core/codelists/organization-classification.json` and the schema
  `enum`. Description in plain language: a grouping of related departments under a government.
- It remains a `GovernmentOrganization`; `parentOrganization` handles the tree
  (government → service area → department → division).
- **Check the collision.** schema.org has a property named `serviceArea`. The classification
  context is a scoped `@vocab`, and earlier work found that code values matching a context term
  can silently expand into schema.org. Run `npm run audit:jsonld`, and if `serviceArea` expands
  anywhere but `https://schema.govfresh.com/v1/orgclass/serviceArea`, map it explicitly like
  `department` is today.
- The new value gets a term page automatically; keep the description under the readability gate.

### 3. `Fund` class
- `gs:Fund`, `rdfs:subClassOf schema:Intangible` (same as `BudgetLine`). Definition: a financial
  account or grouping a government uses to account for resources that are restricted, designated or
  otherwise managed for particular purposes. Have an accounting reader check the wording.
- Properties, all reused where possible: `name`, `alternateName`, `description`, `url`,
  `identifier` (optional, scheme-qualified; `@id` and `name` are the required fields, since a named
  fund such as a general fund may have no code), and `gs:administeredBy` (the widened existing
  property).
- New `profiles/budget/schema/fund.schema.json`, and `Fund` in the type-to-schema mapping near
  the top of `tools/validate.py`.
- No `fundClassification` in v1.

### 3b. Widen `gs:administeredBy`
Update its `domainIncludes` to `gs:Election, gs:Fund, gs:Program` and its comment to
"The organization that runs or manages this." Existing election data is unaffected. Check the
SHACL and `check:vocabulary` still pass.

### 4. `BudgetLine.fund`
- `gs:fund`, optional, a reference to a `Fund` (`@type: @id`). Add to `budget-line.schema.json`
  and the context.
- `fundSource` stays: text for datasets with no Fund entity. Document the split: **`fund` is a
  reference to a persistent entity; `fundSource` is source-system text.**
- SHACL: `fund` must point at a `gs:Fund` (shape in `shapes/schemaGov.shapes.ttl`).

### 5. `Program` class
- Placed in the `budget` profile for v1. `gs:Program`, `rdfs:subClassOf schema:Intangible`.
  Definition: an ongoing or defined government activity administered by an organization to achieve
  a public purpose, which can span many budgets and fiscal years.
- Properties: `name`, `alternateName`, `description`, `url`, `identifier`, `gs:administeredBy`.
- New `profiles/budget/schema/program.schema.json`. Not a subclass of `gs:Project` (Project is
  bounded) and not a `GovernmentService`.
- No sub-program hierarchy in v1. If a real dataset nests programs, add `schema:isPartOf` then.

### 6. `BudgetLine.program`
- `gs:program`, optional reference to a `Program`. `programClassification` stays as the
  publisher's own program or activity code. SHACL: must point at a `gs:Program`.

### 7. Program vs Service (docs only)
- A **Program** is something government organizes, runs or funds (Adult Mental Health, Road
  Maintenance). A **Service** is something a person can request, apply for or receive (apply for a
  building permit). Organization → Program → Service in concept. No new relationship and no change
  to `service.schema.json`.
- Also explain Program vs `gs:Project` (ongoing vs bounded).
- Write it in `profiles/budget/README.md` and `profiles/services/README.md`.

### 8–11. Document existing patterns (no schema change)
In `profiles/org/README.md`, and `profiles/_core/README.md` where noted:
- **Elected officials:** Person → `OrganizationRole` → `Post` → Organization, with
  `representsJurisdiction` for a geographic seat. Worked example.
- **Appointed leaders:** the same with `EmployeeRole`. Do not use a `director: "Jane Smith"`
  property, since that loses the office and its history.
- **Districts:** an `AdministrativeArea` jurisdiction plus a separate `Boundary`, so the boundary
  can change without changing the jurisdiction's identity. (`_core` README.)
- **Contact and facility:** `address`, `contactPoint`, `location`, `Facility`. (`_core` README.)
- Check the existing README before adding: do not repeat what is already there.

### 12. Budget profile README
Explain the four concepts and the relationships (organization, fund and program are durable;
a BudgetLine belongs to one budget):

```
Budget
  └── BudgetLine
        ├── administrativeClassification → GovernmentOrganization
        ├── program → Program ── administeredBy → GovernmentOrganization
        └── fund → Fund ── administeredBy → GovernmentOrganization
```

### 13–14. Context, vocabulary, schemas, validation
New terms: `mission`, `Fund`, `fund`, `Program`, `program`. `administeredBy` already exists.
- `vocabulary/schemagov.ttl`: declare every new term. `npm run check:vocabulary` fails if a used
  term is undefined, and the per-term pages build from this file.
- `context/v1/context.jsonld`: add the terms; run `npm run check:context` and
  `npm run audit:jsonld`.
- JSON Schema, SHACL shapes, and `tools/validate.py` mappings as above.
- Tests: add to `examples/_invalid/` and `tools/check-invalid.py`: `fund` pointing at an
  organization, `program` pointing at a fund, and a Fund with no name. Add a valid case
  with both `fundSource` text and a `fund` reference on the same line.

### 15. Generic examples (in `examples/example-gov`)
Extend the existing fixture, not a new directory:
- Org: Example City Government → a service area → a department → a division, with `mission`.
- Governance: confirm the existing elected Post and district example; add a department head
  (`EmployeeRole` + `Post`) if none exists.
- Budget: a Fund, a Program administered by a department, and a BudgetLine referencing both.
  Keep the existing lines using only `fundSource` so both forms stay valid.

### 16. Docs
Org, Budget, Services, Core READMEs as listed above. Crosswalks: add rows for `mission` (no
schema.org equivalent), Fund and Program (no equivalent; related to Fiscal Data Package
fund/function dimensions) in `crosswalks/fiscal-data-package.md`. ROADMAP entry per repo
convention. Add a short implementation note (what changed, why, reused, new, compatibility,
open questions); the ROADMAP entry can serve as it.

### 17–19. IDs and scope
Follow the existing convention (`https://<domain>/id/<type>/<slug>`); do not prescribe URI
structure in the spec. Do not add classes for Department, Division, ServiceArea, Supervisor,
Director or SupervisorialDistrict.

## Compatibility
- New optional properties and one new classification value. Nothing removed or retyped.
- `gs:administeredBy` only gains types it applies to.
- Published `context.jsonld` changes on merge, so any converter that uses the new terms needs the
  deployed context. Wait for the deploy before pointing external data at them.

## Acceptance
- `npm run check` passes, including `check:vocabulary`, `audit:jsonld`, `validate:invalid`, pilots.
- Every existing example validates unchanged.
- `mission` accepts a string; `serviceArea` is a valid classification and expands into the
  schemaGov namespace.
- Fund and Program are identifiable entities, referenced from BudgetLine, with `fundSource` and
  `programClassification` still valid.
- New terms have working term pages (`check-namespace`).
- Program vs Service vs Project is documented. Officials, department heads and districts are
  documented with examples.
- No Marin-specific terms.

## Order of work
1. `mission`, `serviceArea`, and docs-only items (smallest; ships value alone).
2. `administeredBy` widening, `Fund`, `BudgetLine.fund`.
3. `Program`, `BudgetLine.program`, Program vs Service docs.
Each can be its own PR.

## Decisions on the open questions

1. **Fund type code list: not in v1.** A fund's `name` and `identifier` carry it today, and no
   dataset has asked for a type yet. Public-sector accounting fund types (general, special revenue,
   capital projects, debt service, enterprise, internal service, fiduciary) are well defined, so
   the code list is easy to add later, as an optional `fundType`. Revisit when real budget data
   needs to compare funds across governments.
2. **Program stays in `budget` for v1.** Budget is its only consumer. Moving it to `_core` later
   is a path change only, because the IRI is `gs:Program` either way, so nothing published
   breaks.
3. **No program nesting in v1.** Add `schema:isPartOf` between programs only when a real dataset
   needs it. Adding an optional property later is backward compatible.
4. **Marin converter list: update after the deploy.** Once `serviceArea` and `mission` are
   live on schema.govfresh.com, add `serviceArea` to the allowed classifications and `mission` to
   the field mapping in the converter prompt. Do not use them earlier: documents that use terms
   the published context does not yet define will not expand correctly.
