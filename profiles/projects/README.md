# `projects` profile — Projects and initiatives

**Status:** implemented · **Depends on:** `_core` · **Standards:** [OC4IDS](https://standard.open-contracting.org/infrastructure/latest/en/), [OCDS](https://standard.open-contracting.org) milestones, [GOV.UK Service Manual](https://www.gov.uk/service-manual/agile-delivery) · **schema.org:** `Project`, `DefinedTerm`, `DefinedTermSet`, `Article`

## What this profile represents

Bounded government work: a service being rebuilt, a bridge being replaced, a programme being
rolled out. A project record says what the project is, whether work is happening, where it is
in its lifecycle, when it started and is expected to finish, who is responsible, what it has
reached, and what it delivers.

It is deliberately small. It publishes the state of a project, not the work inside it.

```
                    Project
                       │
       ┌───────────────┼───────────────┐
       │               │               │
     status          phase           dates
                       │
                       ▼
                lifecycle scheme
       │                               │
       ├──────── milestones ───────────┤
       │                               │
       └──────── updates ──────────────┘
                       │
                       ▼
                    produces
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Service          App          Dataset
```

## When to use it

Use it to publish a project list or a single project page as linked data. It is for
transparency and discovery. It is not for running a project. Tasks, assignments, sprints,
comments and issues belong in Jira, Asana, GitHub or whatever you use. Budget and spend belong
in the [budget](../budget/) profile.

## Project and service are different things

A project is work that ends. A [service](../services/) is something delivered continuously.
A completed project can produce a service that is live for twenty years:

```
Project  status: completed   ──produces──▶   GovernmentService   serviceStatus: active
```

Do not mark a project active because its output is operating, or complete because its output
launched. Link them with `produces` and let each carry its own state.

## Status and phase

They answer different questions, and both are needed.

| Property | Question | Values |
|---|---|---|
| `status` | Is work happening? | `proposed`, `planned`, `active`, `paused`, `completed`, `cancelled` |
| `phase` | Where is it in its lifecycle? | A term from a lifecycle scheme |

A digital service in beta and a bridge under construction are both `status: active`. Their
phases differ, because the lifecycles differ.

`status` is a closed list. Workflow states (blocked, awaiting approval) are not statuses.
**Health** (on track, at risk, off track) is a third question and is not in v1: no established
standard was found to adopt. [OC4IDS](https://standard.open-contracting.org/infrastructure/latest/en/)
puts lifecycle stages and `cancelled` in one `status` list; this profile separates them.

## Lifecycle schemes

No single lifecycle fits all government work, so `phase` is a reference to a `DefinedTerm`
belonging to a `DefinedTermSet`. The scheme can be anyone's.

schemaGov publishes one scheme, [`DigitalServicePhase`](codelists/digital-service-phase.json):
discovery, alpha, beta, live, retired. It follows the GOV.UK Service Manual. Private beta and
public beta are listed as narrower terms of beta, which is a local refinement: the Service
Manual describes both inside its beta phase. **It applies to digital services only.**

A project in any other field references its own scheme by IRI, as the capital project and the
open data programme in the example do. New York's capital projects dataset has its own phases
(Design, Construction Procurement, Construction, Close-Out); see the
[pilot](../../examples/pilot-nyc-capital/README.md). Terms carry `position`, so an
application can order them.

## Dates

`startDate`, `expectedEndDate`, `endDate` and `dateModified`. The end date is the **actual** end, and
`expectedEndDate` is the current plan, as in OC4IDS (`period.endDate` and
`completion.endDate`). `startDate` and `endDate` are `schema:startDate` and `endDate`, which
schema.org defines on events and roles but not on organizations; see the
[crosswalk](../../crosswalks/project-management.md).

`dateModified` is the date the record was last reported or confirmed. Status, phase and
forecast dates are true as of a date, and without one a stale record looks current. It is
optional, and also outside schema.org's stated domain (it is defined on creative works).

## Milestones

A `Milestone` is a dated point of progress. It points at its project with `about`. Its status
is its own list, taken from OCDS: `scheduled`, `met`, `notMet`, `partiallyMet`, because
`paused` and `cancelled` say nothing about a single milestone. `dueDate` is when it is
scheduled and `dateMet` when it was reached.

## Updates

An update is a schema.org `Article` (or any `CreativeWork`) with `about` pointing at the
project, plus `datePublished`, `author` and `url`. There is no `ProjectUpdate` type and no
list of updates on the project: the update points at the project, so publishing one never
edits the project record.

## Timelines are derived

There is no `Timeline` type. An application builds one from `startDate`, `expectedEndDate`,
`endDate`, the phase terms in `position` order, milestone dates and update dates.

## Outputs

`produces` points at what the project delivers: a service, application, dataset, facility or
document. schema.org has nothing for this: `serviceOutput` runs from a Service to what it
generates, and `result` is for actions. So `produces` is minted.

## A minimal project

```json
{
  "@context": "https://schema.govfresh.com/v1/context.jsonld",
  "@id": "https://example.gov/id/project/website-refresh",
  "@type": "Project",
  "name": "Website refresh",
  "status": "active"
}
```

`@id`, `@type` and `name` are all that is required.

## A fuller project

```json
{
  "@context": "https://schema.govfresh.com/v1/context.jsonld",
  "@id": "https://example.gov/id/project/pothole-reporting-redesign",
  "@type": "Project",
  "name": "Pothole reporting redesign",
  "status": "active",
  "phase": {"@id": "https://schema.govfresh.com/v1/dsphase/public-beta"},
  "startDate": "2026-01-15",
  "expectedEndDate": "2026-12-15",
  "parentOrganization": {"@id": "https://example.gov/id/organization/public-works"},
  "member": [{"@id": "https://example.gov/id/organization/city-government"}],
  "produces": [{"@id": "https://example.gov/id/service/pothole"}]
}
```

[`examples/example-gov/projects.jsonld`](../../examples/example-gov/projects.jsonld) holds
six projects: a digital service with milestones and an update, a programme with its own
scheme, a capital project, a completed project, a cancelled one, and a minimal one.

## Organizations

`parentOrganization` is the responsible organization, `member` are participants and `funder`
funds it. These are schema.org properties inherited from `schema:Project`, which sits under
`schema:Organization`. `parentOrganization` normally means "the larger body this belongs to",
so this is a stretch; it is the weakest mapping in the profile.

## Validation

- **JSON Schema** (`schema/`): required fields, the status lists, ISO dates, phase and
  organization references. A project with only `name` is valid.
- **SHACL** (`shapes/schemaGov.shapes.ttl`): a phase is a term in a scheme, and does not claim
  a scheme that does not list it; a milestone is about a project; organizations are
  organizations.
- **`tools/validate.py`**: end not before start, `dateMet` only on a milestone that is met,
  and dangling references.

`npm run validate:invalid` runs a deliberately broken fixture and fails unless every fault is
caught.

## Extending

- **Another lifecycle:** publish a `DefinedTermSet` and reference its terms from `phase`. No
  change to this profile. A published scheme should carry `position` on each term.
- **Another output:** `produces` takes any typed thing.
- **Health, risk, tasks:** out of scope. If health is added it will be a separate property.
- **Budget and spend:** use the `budget` profile, linked from the project.

## Known limits

- Projects have no history. `dateModified` says when the record was last true, but a publisher
  who snapshots a project every quarter has changing phases and forecast dates, and this profile
  carries only the latest. The NYC pilot shows
  a forecast that slipped from 2018 to 2023 across 24 snapshots.
- `DigitalServicePhase` was tested against the GOV.UK Service Standard reports: alpha, beta and
  live covered every assessed stage. See the
  [pilot](../../examples/pilot-govuk-assessments/README.md). It did not exercise discovery, retired,
  or the private and public beta terms.
- A milestone has a scheduled date and a date met. Something that is held on a date with a
  verdict, such as an assessment, fills both with the same date.
- A non-government organization in `member` or `funder` is typed `Organization`. The validator
  does not hold it to the procurement `Party` schema unless it carries a `role`, and checks only
  that it has an `@id` and a `name`.
