# U.S. Census ACS → schemaGov statistics

The American Community Survey (ACS) is the **test implementation** for the `statistics`
profile. It is one source among many: nothing about it is in the schemaGov vocabulary, and the
table cell codes below are mappings, never identifiers. A schemaGov variable maps to a source
variable, not the other way round, so Statistics Canada or Eurostat can map to the same variables.

Source: ACS 5-year estimates, 2019-2023 (`api.census.gov/data/2023/acs/acs5`). Every variable ID
and label below was checked against that release's published variable list.

## Variables

| schemaGov variable | Universe | ACS cells (estimate; `M` suffix is the margin) | Derivation |
|---|---|---|---|
| `population-total` | people | `B01003_001E` | direct |
| `median-age` | people | `B01002_001E` | direct, years |
| `population-under-18` | people | `B09001_001E` | direct |
| `population-65-plus` | people | `B01001_020E`–`025E` (male 65+) and `044E`–`049E` (female 65+) | sum of 12 cells |
| `median-household-income` | households | `B19013_001E` | direct, inflation-adjusted dollars of the release year |
| `poverty-rate` | people with poverty status determined | `S1701_C03_001E` | direct percent (subject table) |
| `median-gross-rent` | renter-occupied units | `B25064_001E` | direct |
| `rent-burden-rate` | renter households | `B25070_007E`–`010E` over `B25070_001E` | share of rent at 30% or more of income |
| `disability-rate` | civilian noninstitutionalized people | `S1810_C03_001E` | direct percent (subject table) |
| `households-without-internet-rate` | households | `B28002_013E` over `B28002_001E` | share with no internet access |

Shares and percentages are published as `unitText: percent`. The margin of a sum is the
square root of the sum of squared margins; the margin of a share uses the Census proportion
formula. Both are the source's rules, applied by the publisher, not by schemaGov.

## Representation

| ACS | schemaGov |
|---|---|
| Estimate | `value` |
| Margin of error | `marginOfError.value` |
| 90% confidence (ACS standard) | `confidenceLevel` `0.9` on the margin |
| `2019-2023` 5-year | `observationPeriod` `2019/2023` |
| Release | a `Dataset`; the observation's `sourceDataset` |
| County, place, tract GEOID | the area's `identifier`; county and place are `Jurisdiction`s, a tract is a `Place` with `areaType: statistical-area` |
| Margin sentinel `-555555555` (not computable) | `marginOfError` omitted; the observation is still valid |
| Other negative sentinels, null | the observation is omitted |
| Tract, place, county nesting | `containedInPlace`; a place and a tract may overlap, so use `geoOverlaps` |

## Test result

A throwaway converter (kept outside the repo) pulled the ten variables from the live ACS
2019-2023 API at three geography levels, a county, a place and a tract (all in one U.S. state,
chosen arbitrarily). That gave 30 observations. All passed JSON Schema and SHACL.

What the real data showed:

- The county's **total population has no margin of error**: the Census controls that estimate,
  so the margin is the sentinel `-555555555`. The observation is valid without one, which is the
  case the profile requires.
- Margins for the 65+ sum and for the two shares have to be calculated by the publisher
  (square root of summed squares, and the proportion formula). They are not in the API response.
- No value was suppressed in these three areas, so the omission rule was not exercised.
- The API allows at most 50 variables per request, so a converter must batch (an estimate and a
  margin count as two).

## Not representable

- Suppressed values and the reason for suppression.
- Cell-level annotation flags and data-quality notes.
- The full table structure (ACS tables are multi-dimensional; only chosen cells are mapped).
- Geography vintage: a tract is redrawn every decade. Use a dated `Boundary` for the area.
