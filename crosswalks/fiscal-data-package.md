# Fiscal Data Package crosswalk

The [Fiscal Data Package](https://specs.frictionlessdata.io/fiscal-data-package/) (Open
Knowledge / OpenSpending) remains the source model. schemaGov is a schema.org projection of
it — publishers should keep producing the FDP and reference it from `distribution`.

## Package level

| Fiscal Data Package | schemaGov |
|---|---|
| `name`, `title` | `name` |
| `description` | `description` |
| `fiscalPeriod.start` / `.end` | `startDate` / `endDate` |
| `granularity` (aggregated / transactional) | implied by whether lines nest |
| `countryCode` | via `about` → the Jurisdiction's ISO identifier |
| `resources[].path` | `distribution[].contentUrl` |
| `licenses` | `license` |

## Measures and dimensions

FDP describes a tabular budget through a `mapping` of measures and dimensions. schemaGov
turns each row into a `BudgetLine`.

| FDP concept | schemaGov |
|---|---|
| measure `amount` | `amount.value` |
| measure `currency` | `amount.currency` (required per line) |
| dimension `phase` | `budgetPhase` |
| dimension `direction` | `direction` |
| dimension `functional-classification` | `functionalClassification` (COFOG) |
| dimension `economic-classification` | `economicClassification` (GFSM) |
| dimension `administrative-classification` | `administrativeClassification` → an organization reference |
| dimension `activity` / programme | `programClassification` |
| dimension `fin-source` | `fundSource` |
| dimension `geo-source` | via the budget's `about` |
| dimension `date` | `startDate` / `endDate` |
| parent/child rollup | `isPartOf` / `hasPart` |

## Where the two differ

**FDP carries the classification as a bare code; schemaGov carries administrative
classification as a reference.** A department name as text cannot be joined to anything. An
`@id` pointing at a `GovernmentOrganization` connects the budget to the org chart, the
officeholders, and the meetings.

**FDP is a table; schemaGov is a graph.** FDP rows are independent; schemaGov lines nest
through `isPartOf`/`hasPart` and the validator checks that parents equal the sum of their
children.

**schemaGov requires currency per line.** FDP allows it as a package-level measure.

## Classification standards

Neither COFOG nor GFSM is defined by schemaGov; both are enumerated at their top level as
`DefinedTermSet`s for validation convenience, with full subcodes accepted as values.

- **COFOG** — UN Classification of the Functions of Government. Three levels: division (`07`),
  group (`07.3`), class (`07.3.1`).
- **GFSM 2014** — IMF Government Finance Statistics Manual economic classification.

Publishers already reporting to their national statistics office or to the IMF are producing
these codes; this profile asks for the code they already have, not a new one.
