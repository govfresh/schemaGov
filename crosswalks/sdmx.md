# SDMX and RDF Data Cube → schemaGov statistics

SDMX (and the W3C RDF Data Cube vocabulary that borrowed its model) describe statistics as a
cube: a measure observed at the intersection of dimensions, with attributes. schemaGov does
not adopt either in full. schema.org `Observation` plus `StatisticalVariable` carries the same
information in far fewer terms. This file maps the two.

| SDMX / Data Cube | schemaGov | Note |
|---|---|---|
| Dataflow / Data Structure Definition | `Dataset` (catalog profile) | The structure is not reproduced; link to it with `Dataset.conformsTo` |
| Observation (`qb:Observation`) | `Observation` | |
| Measure (`OBS_VALUE`) | `value` | |
| Concept / measure definition | `StatisticalVariable` | One variable per measure-and-subset combination |
| Dimension `REF_AREA` | `observationAbout` | A reference to a `Jurisdiction` or `Place`, not a code |
| Dimension `TIME_PERIOD` | `observationDate` or `observationPeriod` | Instant or year → date; span → interval |
| Other dimensions (`AGE`, `SEX`) | `additionalProperty` on the `StatisticalVariable` | The subset belongs to the variable, so observations stay uniform |
| Attribute `UNIT_MEASURE` | `unitText`, `unitCode` | |
| Attribute `OBS_STATUS` | not modelled | Estimate, provisional, suppressed and similar flags have no home yet |
| Attribute `CONF_STATUS` (confidentiality) | not modelled | A suppressed value is omitted |
| Attribute `DECIMALS`, `UNIT_MULT` | not modelled | Write `value` in the stated unit |
| Codelist | `DefinedTermSet` | Only for the code lists schemaGov itself defines (`StatisticalAreaType`) |

## Differences worth knowing

- SDMX codes the area. schemaGov points at an entity, so the same observation can be joined to
  budget lines, facilities and boundaries without a code lookup. The agency's own geography
  code goes in that area's `identifier`.
- SDMX keeps dimensions on every observation. schemaGov keeps them on the variable. The
  cost is more variables; the gain is that an observation has one shape.
- The Data Cube vocabulary is not extended or required. Nothing here is expressed in `qb:`.
