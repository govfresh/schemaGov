# `statistics` profile — Statistical observations

**Status:** implemented · **Depends on:** `_core`, `catalog` · **Source standard:** [schema.org](https://schema.org/Observation) `Observation` and `StatisticalVariable` (the Data Commons pattern) · **Crosswalks:** [SDMX](../../crosswalks/sdmx.md), [U.S. Census ACS](../../crosswalks/census-acs.md)

A statistic is a measured value about a place or population, for a period, from a source. The
profile publishes that as one `Observation` that points at three things kept elsewhere: the
variable it measures, the area it describes, and the dataset it came from. It mints no new
type and no per-indicator property. The domain (population, income, housing, language) lives
in `StatisticalVariable` records, never in the schema.

```
Observation ─ variableMeasured ─▶ StatisticalVariable   what was measured, source-independent
            ─ observationAbout ─▶ Jurisdiction | Place   where or who
            ─ sourceDataset    ─▶ Dataset (catalog)      provenance, publisher, release
```

## What it reuses

| Need | Term | Origin |
|---|---|---|
| One statistical value | `Observation` | schema.org |
| What is measured | `StatisticalVariable` | schema.org |
| Subject of the value | `observationAbout` | schema.org |
| The value, its unit | `value`, `unitText`, `unitCode` | schema.org (`Observation` is a `QuantitativeValue`) |
| Point in time / calendar period | `observationDate` (`2024`, `2024-06-30`) | schema.org |
| Span of an estimate | `observationPeriod` (ISO 8601 interval, `2020/2024`) | schema.org |
| Margin of error | `marginOfError` (a `QuantitativeValue`) | schema.org |
| Confidence level | `additionalProperty` on the margin, `propertyID: confidenceLevel`, 0 to 1 | schema.org |
| Interval bounds | `minValue`, `maxValue` | schema.org |
| Source | `sourceDataset` | existing schemaGov |
| Area with no governing authority | `Place` + `areaType` | schema.org + existing pattern |
| Containment, overlap | `containedInPlace`, `containsPlace`, `geoOverlaps` | schema.org |
| Area extent over time | `Boundary` (`boundaryOf` now accepts a `Place`) | existing schemaGov |

The one new term is `gs:areaType` with its code list `StatisticalAreaType`. It follows the
pattern `gs:governmentLevel` already sets, and keeps a statistical area from being mistaken
for a jurisdiction. Nothing else was minted.

## Rules

- **Variables are source-independent.** `median-household-income` is the identifier, never a
  source's cell code. A source's code goes in [a crosswalk](../../crosswalks/census-acs.md), or in
  the variable's `identifier` with its scheme named. Several sources can map to one variable.
- **Subsets are variables, not properties.** "Population age 65+" is a variable whose
  `additionalProperty` holds `{propertyID: age, minValue: 65, unitText: year}`. There is no
  `population65Plus`. schemaGov defines no dimension vocabulary; reuse the same `propertyID`
  (`age`, `gender`) for the same dimension. schema.org's own pattern puts dimension values on
  the variable as direct properties, but it has no property for most dimensions, so
  `additionalProperty` avoids minting one.
- **Time is one of two fields.** `observationDate` for a point or a single year,
  `observationPeriod` for a span, never both. A five-year estimate is the interval
  `2020/2024`, not a reading on its last day.
- **Uncertainty is optional.** A source that publishes none yields a valid observation.
  When there is a margin, it is a non-negative `QuantitativeValue` in the observation's unit,
  and a `confidenceLevel` must be between 0 and 1 (`0.9` is 90%).
- **Provenance is a reference.** `sourceDataset` names the `Dataset`. Publisher, release and
  version come from the dataset, so nothing is repeated per observation.
- **Governed and non-governed areas.** A `Jurisdiction` has an organization and a
  `governmentLevel`. A statistical or community area is a plain `Place` with an `areaType`, and
  may not carry `jurisdictionOf`. Both take `Boundary` records and observations. `containedInPlace`
  is strict containment; use `geoOverlaps` for partial overlap.
- **`population` on a jurisdiction stays.** It is a convenience for the commonest number. It is
  already a small observation, and every existing document stays valid. Publish the full
  `Observation` when you need a subset, an estimate, a period or a series.

## Example

See `examples/example-gov/statistics.jsonld`: a population series, a 65+ subset with margin
of error and bounds, median income, and a housing-cost-burden rate for a statistical area
that a community area overlaps.

## What it cannot represent

- **Suppressed or top-coded values.** A suppressed value is omitted, so the reason is lost.
  Annotation and quality flags have no home.
- **A universe with no schema.org class.** `Household` does not exist, so such variables omit
  `populationType` and state the universe in `description`.
- **Weights, sample size and survey design.** Not modelled. Link to the source methodology
  from the `Dataset`.
- **Derived-from relationships** beyond `measurementDenominator`.
- **Observations about things that are not areas** are allowed by `observationAbout`, but the
  fixtures and checks cover places and jurisdictions only.
