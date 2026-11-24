# Plan: statistics profile (reviewed against `main`, 2026-11-24)

Status: **Stage 2 implemented on branch `statistics-profile` (2026-11-24); `npm run check` passes.** Census test re-run on live ACS data (see Outcome).

Goal: let a publisher state a statistical measure, about a defined population or subject, for a geographic area and period, with a value, unit, source dataset and optional uncertainty. Nothing in the model is specific to Marin or to the U.S. Census Bureau.

This revises a draft plan after checking it against the repo. The first section lists what changed and why.

## What the review found (changes to the draft)

| Draft said | Repo reality | Change |
|---|---|---|
| Stage 1 deliverable at `docs/proposals/statistics-profile.md` | **There is no `docs/` directory.** Conventions: `PLAN-*.md` at root, `crosswalks/*.md`, profile README, `SPEC.md` | This file is the Stage 1 deliverable. No `docs/` tree. |
| `profiles/statistics/schema/*.schema.json` **and** `shapes/*.shacl.ttl` per entity | JSON Schema is per `@type` via `SCHEMA_FOR` in `tools/validate.py`. SHACL is **one file**, `shapes/schemaGov.shapes.ttl`, not per profile | Schemas under `profiles/statistics/schema/`. Shapes appended to the existing SHACL file. No `shapes/` dir in the profile. |
| `profiles/statistics/mappings/census.md` | Crosswalks live in `crosswalks/` and are indexed in `crosswalks/README.md` | `crosswalks/census-acs.md`, plus a row in the README table. Keeps Census out of the profile, as the draft wants. |
| `examples/example-gov/statistics/{variables,observations,...}.jsonld` | `example-gov` is **flat**: one file per profile (`budget.jsonld`, `policy.jsonld`) | One file, `examples/example-gov/statistics.jsonld`. A pilot, if wanted, goes in `examples/pilot-*/` with a README and a `validate:pilot` entry. |
| Profile named `statistics`; research Data Commons as a separate idea | ROADMAP tier two already lists an `indicators` profile (SDMX), noting "`Observation` and `StatisticalVariable` exist". **Data Commons' approach is schema.org `StatisticalVariable`** (*verify*) | Keep the name `statistics` (broader than performance indicators). Replace the ROADMAP `indicators` row with it. Treat schema.org as the primary source, not an alternative to Data Commons. |
| Decide between `DefinedTerm`, `PropertyValue` and a new type for variables | schema.org has `StatisticalVariable` (with `measuredProperty`, `populationType`, `constraintProperty`, `statType`) and `Observation` (with `observationAbout`, `observationPeriod`, `variableMeasured`, `marginOfError`) (*verify exact names and status*) | Default to those. `DefinedTerm` is the fallback only if `StatisticalVariable` proves unusable. This probably answers questions 1, 2, 3 and 4 with **zero new types**. |
| "Statistical/community area" may need a new type | `Place` is already in the SHACL shapes (`sh:class schema:Place`) but **has no JSON Schema** (`SCHEMA_FOR` has no `Place`). Jurisdiction `@type` is an enum of `AdministrativeArea, Country, State, City`. So a non-governed area **currently has nowhere valid to live** | Use plain `schema:Place` with a `Place` schema in the statistics profile. Area kind goes in `additionalType` (a code list), not a new type. Mint a `gs:` type only if the stress test shows `Place` cannot be told apart from a jurisdiction. |
| Both area kinds "capable of having boundaries" | `boundary.schema.json` says `boundaryOf` is "the `Jurisdiction`". Boundaries carry `validFrom`/`validUntil` already (the exact reason GEOSPATIAL.md gives, and tract lines are redrawn every decade) | **Small `_core` change**: widen the `boundaryOf` description and shape to `Place`. Additive, no existing data breaks. This answers question 9. |
| GeoSPARQL for `within` / `contains` / `overlaps` | The context already carries `schema:containedInPlace` / `containsPlace`. SHACL line ~37 says `containedInPlace` "must point at another jurisdiction", which a tract inside a county satisfies, but a tract inside a **place** or a community area inside a tract does not. Overlap has no schema.org equivalent. Check `geoOverlaps`, `geoWithin`, `geoContains` in schema.org, which exist on `GeospatialGeometry` and `Place` (*verify*) | Use `containedInPlace`/`containsPlace` for strict containment. Use schema.org `geoOverlaps` for overlap if present on `Place`. **Do not add GeoSPARQL** unless a fixture needs a relation schema.org lacks. Relax the SHACL shape to allow `Place` targets. |
| "Migrate or preserve" `population` | `population` is already `gs:population`, a `QuantitativeValue` with `value`, `observationDate`, `sourceDataset`, defined in the context, vocabulary and `jurisdiction.schema.json`, with a fixture (75000, 2020-04-01) | **Option 3: keep it as a convenience.** Add an optional pointer to the matching `Observation` only if a real case needs it. Do not deprecate. It is already a degenerate observation. |
| Observation period "2025 ACS 5-year" needs correct representation | schema.org `Observation` has `observationPeriod` (a `Duration`/interval) alongside `observationDate`. `Boundary` already uses `validFrom`/`validUntil` | Use `observationPeriod` as an ISO 8601 interval string (`2020/2024`), and keep `observationDate` for point-in-time only. SHACL: exactly one of the two. **Needs a call**, see below. |
| Confidence level, bounds | `marginOfError` is in schema.org. **No confidence level, no bounds** (*verify*) | `marginOfError` reused. Confidence level is the one probable gap. Prefer a nested `QuantitativeValue` or `additionalProperty` over a new term. If neither validates sensibly, mint exactly one `gs:confidenceLevel`. Lower/upper bound: use `QuantitativeValue.minValue` / `maxValue`. |
| Observation references a `Dataset` | `sourceDataset` already exists as `gs:sourceDataset` (an IRI string, used by `Boundary` and `population`). `schema:isBasedOn` is the alternative | **Reuse `sourceDataset`.** One convention across the repo. Publisher, version and release date are read from the `Dataset` (catalog profile), never copied onto the observation. |
| "Add JSON Schema and SHACL" | No test framework. Negative tests are `examples/_invalid/*.jsonld` plus a `FAULTS` map in `tools/check-invalid.py` | Add fault nodes there (list below). |
| Profile must be "registered" | Silent otherwise | Checklist below. |
| Marin acceptance test inside this task | Marin work belongs in `marin-data`; the repo is CC0 | Fictional fixtures only. A Census pilot is optional and **must state the source licence** in its README. U.S. Census data is public domain, but confirm before committing real values. |

## Answers to the ten questions

| # | Question | Recommendation | Term origin |
|---|---|---|---|
| 1 | Use schema.org `Observation`? | Yes, directly | schema.org |
| 2 | Variables as `DefinedTerm`, external, or new? | schema.org `StatisticalVariable` | schema.org |
| 3 | Dimensions standard? | `StatisticalVariable` constraints (`populationType`, `constraintProperty`) as in Data Commons. Not SDMX or Data Cube dimensions | schema.org |
| 4 | Margin of error, confidence? | `marginOfError` (schema.org); confidence level is the one likely gap | schema.org, maybe 1 new |
| 5 | New area type? | No: `Place` plus `additionalType` | schema.org |
| 6 | GeoSPARQL? | No, unless a fixture proves a need | n/a |
| 7 | Observation periods? | `observationPeriod` (interval) vs `observationDate` (instant) | schema.org |
| 8 | Keep `population`? | Yes | existing schemaGov |
| 9 | `_core` changes? | Widen `boundaryOf` to `Place`; relax the `containedInPlace` shape | existing schemaGov |
| 10 | No new vocabulary at all? | Probably zero or one term (`confidenceLevel`) | pending verification |

## Standards disposition

| Standard | Use |
|---|---|
| schema.org `Observation`, `StatisticalVariable`, `StatisticalPopulation`, `QuantitativeValue`, `Place` | The model |
| `Dataset` / DCAT (existing catalog profile) | Provenance target, unchanged |
| PROV-O | Not adopted. `sourceDataset` is sufficient provenance for v1 |
| SDMX | Crosswalk only (`crosswalks/sdmx.md`), as a source system. Subsumes the ROADMAP `indicators` note |
| W3C RDF Data Cube | Crosswalk reference only. Superseded in practice by SDMX and schema.org here |
| GeoSPARQL | Not adopted (see question 6) |
| `StatisticalPopulation` | Only if `StatisticalVariable.populationType` cannot express a subset. Check before adding it |

## Proposed shape of the model

```jsonc
// Observation
{
  "@id": "https://example.gov/id/observation/example-city/population-65-plus/2020-2024",
  "@type": "Observation",
  "observationAbout": {"@id": "https://example.gov/id/jurisdiction/example-city"},
  "variableMeasured": {"@id": "https://example.gov/id/statistical-variable/population-65-plus"},
  "value": 12345,
  "unitText": "persons",
  "observationPeriod": "2020/2024",
  "marginOfError": {"@type": "QuantitativeValue", "value": 650},
  "sourceDataset": "https://example.gov/id/dataset/example-survey-2024"
}
```

Variables carry the dimensions (age 65+, sex), so the observation never does and there is no `population65Plus` property anywhere. Source mappings (Census `B19013_001E`, Statistics Canada IDs) live in `crosswalks/`, and in the variable only as a scheme-qualified `identifier` (the existing `_core/identifier`) if a publisher wants them.

Area:

```jsonc
{"@id": ".../area/tract-a", "@type": "Place", "additionalType": "statisticalArea",
 "containedInPlace": {"@id": ".../jurisdiction/example-county"}}
```

## Implementation steps (after approval)

1. Confirm the *verify* items against schema.org. Write them into a "Verified terms" table here. Stop and report if `StatisticalVariable` or `observationPeriod` is not usable.
2. `profiles/statistics/`: `README.md`, `schema/observation.schema.json`, `schema/statistical-variable.schema.json`, `schema/place.schema.json`, `codelists/area-type.json`.
3. `_core`: widen `boundaryOf` and relax the `containedInPlace` shape. Run all existing profiles untouched.
4. Context: add only terms the context lacks (`Observation`, `StatisticalVariable`, `observationAbout`, etc.). Namespace and vocabulary checks must pass.
5. Register: `tools/validate.py` (`SCHEMA_FOR`, `PROFILE_DIRS`), `_data/profiles.js` (`IMPLEMENTED`), `SPEC.md` profile table and layout, root `README.md`, `package.json` (`validate:pilot` if a pilot), `.github/workflows/deploy.yml` if it lists profiles, ROADMAP `indicators` row.
6. `examples/example-gov/statistics.jsonld`: fictional, small. Reuse existing jurisdiction, dataset and organization `@id`s. Cover: population, median household income, 65+ subset, a non-governed area with housing cost burden, an estimate with margin of error, a three-period time series.
7. `crosswalks/census-acs.md` with about 10 variables across county, place and tract (the draft's list), plus `crosswalks/sdmx.md`. No full variable catalog.
8. Fault tests in `examples/_invalid/` and `tools/check-invalid.py`:
   - observation with no `variableMeasured`
   - observation with neither value nor a valid period
   - both `observationDate` and `observationPeriod`
   - period end before start, or malformed interval
   - negative `marginOfError`, or confidence level outside 0 to 1
   - `sourceDataset` pointing at a non-dataset
   - `Place` carrying governance properties (`jurisdictionOf`)
   - `boundaryOf` pointing at an organization
   - optional uncertainty absent must **still pass**
9. Run `npm run check` (build, namespace, vocabulary, context, audit, validate, SHACL, invalid, pilots). All existing profiles and pilots must pass untouched.
10. Document what the model cannot represent (suppressed or top-coded values, annotation flags, weighting, small-area derived estimates) in the profile README.

## Decisions taken (2026-11-24)

1. **Period encoding:** ISO 8601 interval string in `observationPeriod` (`"2020/2024"`); `observationDate` for point-in-time only. SHACL requires exactly one.
2. **Confidence level:** carried as `additionalProperty` on the `marginOfError` value. No `gs:` term unless that fails validation in the fixtures.
3. **Roadmap:** `indicators` folds into `statistics`. Replace the ROADMAP row.
4. **Pilot:** none for now. Fictional fixtures plus `crosswalks/census-acs.md` only, so no licence question and no adapter. Revisit after the crosswalk test.

## What is not changing

- `population` on `Jurisdiction` stays as written.
- No Census, Marin, ACS table codes or supervisorial districts in schemaGov vocabulary, context or schemas.
- No `marin-census` work.

## Outcome (2026-11-24)

**Verified against the current schema.org release.** `Observation` (a subtype of `QuantitativeValue`), `StatisticalVariable`, `observationAbout`, `observationPeriod` (Text), `observationDate`, `variableMeasured`, `marginOfError`, `measurementDenominator`, `populationType`, `statType`, `geoOverlaps`, `geoWithin`, `geoContains`, `minValue`, `maxValue`, `additionalProperty` all exist. **Names in the draft that do not exist:** `observedNode`, `measuredValue`. **No** confidence level, confidence interval, `Household` class or `median` property.

**Deviations from the plan above**
- **One new `gs:` property and one code list**, not zero: `gs:areaType` and `StatisticalAreaType`. It copies `gs:governmentLevel`'s pattern (subproperty of `additionalType`) and avoids re-pointing `additionalType` for every profile.
- **Dimensions** (age 65+, gender) are `additionalProperty` `PropertyValue`s on the variable, not direct properties, because schema.org has no property for most dimensions. This departs from schema.org's own description of `StatisticalVariable`.
- **`sourceDataset` is required** on an observation (rule 4: provenance travels with the value).
- **The `containedInPlace` shape on `Jurisdiction` was not touched.** Only the new statistical-area shape accepts a `Place` target, and it is selected by `gs:areaType`, so nested `Place` nodes elsewhere (permit locations) are unaffected.
- **`_core` change** is only `boundaryOf`/`boundary` accepting a `Place` (vocabulary text and SHACL). No schema file changed.
- Month and day ranges are checked in the date patterns; interval order is checked in `tools/validate.py` and SHACL.
- Added an `sdmx` entry to `_lib/standards.js`, and two passthrough lines in `eleventy.config.js`.

**Delivered:** `profiles/statistics/` (README, three schemas, `area-type` code list); `examples/example-gov/statistics.jsonld` (3 datasets' worth of cases: series, subset, estimate with bounds, statistical area plus overlapping community area); `examples/_invalid/statistics.jsonld` with 17 faults and 5 clean nodes; `crosswalks/census-acs.md`, `crosswalks/sdmx.md`; registration in `validate.py`, `profiles.js`, SPEC, README, ROADMAP (`indicators` row removed).

**Census test.** All ten mapped ACS variable IDs and labels were checked against the live 2023 5-year variable list. A throwaway converter (outside the repo) then pulled real ACS 2019-2023 values at county, place and tract: 30 observations, all passing JSON Schema and SHACL. One real case exercised the optional-uncertainty rule: the county total population has no computable margin. Findings are in `crosswalks/census-acs.md`.

**Still unmodelled:** suppression reasons, quality flags, weights and sample size, a `Household` universe.

**Not done:** the Marin acceptance test (belongs in `marin-data`); a pilot (decision 4); suppressed values were not seen in the three test areas.
