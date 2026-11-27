# Projects crosswalk

Maps the `projects` profile to Schema.org and to the incumbent standards for each part of the
model. The profile is a Schema.org
projection. [OC4IDS](https://standard.open-contracting.org/infrastructure/latest/en/) (Open
Contracting for Infrastructure) is the source model for capital projects, and the
[GDS Service Manual](https://www.gov.uk/service-manual/agile-delivery) is the source for the
digital-service lifecycle. Publishers of either should keep publishing them.

Decision key: **reuse** = existing term unchanged · **stretch** = existing term used outside its
stated domain · **mint** = new `gs:` term · **defer** = deliberately not in v1.

## Core

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| `gs:Project` | `schema:Project` (Thing > Organization > Project) | OC4IDS `Project`; W3C ORG `OrganizationalCollaboration` (subclass of `org:Organization`, "a collaboration between two or more Organizations such as a project"; no dates, status or phase); DOAP `Project` (software projects; no status, phase or end date) | **mint** as a subclass of `schema:Project`. A project is not a schema.org `Event`: `eventStatus` values (scheduled, cancelled, rescheduled) describe performances. |
| `@id` | JSON-LD | OC4IDS `id` | reuse |
| `name` | `schema:name` | OC4IDS `title` | reuse |
| `description` | `schema:description` | OC4IDS `description` | reuse |
| `identifier` | `schema:identifier` → `PropertyValue` | OC4IDS `identifier` | reuse (SPEC section 2) |
| `url` | `schema:url` | | reuse |
| `startDate` | `schema:startDate` | OC4IDS `period.startDate` | **stretch.** `startDate` is defined on Event, Role, Schedule and a few others, not on Organization. The alternative, `foundingDate`, means an organization was founded. |
| `endDate` | `schema:endDate` | OC4IDS `completion.endDate` | **stretch**, same reason. Means the **actual** end. |
| `expectedEndDate` | none | OC4IDS `period.endDate` (planned) | **mint** `gs:expectedEndDate` |
| `projectCategory` | none (`category` is already the alert category) | OC4IDS `sector`, a closed list | **mint** `gs:projectCategory` as open text. Capital plans group projects their own way. |
| `estimatedCost` | `schema:estimatedCost` (defined on HowTo) | OC4IDS `budget.amount` is the approved budget, not an estimate | **stretch.** Same meaning, outside its stated domain. |

## Status and phase

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| `status` | `ActionStatusType` (Active, Completed, Failed, Potential) | OC4IDS `status` | **mint** `gs:ProjectStatus`. `ActionStatusType` is defined for `Action`, has no paused, cancelled or proposed, and `Failed` is the wrong semantics. Same decision as `gs:requestStatus`. |
| status: proposed, planned, active, paused, completed, cancelled | | OC4IDS `cancelled` ↔ `cancelled` | mint. OC4IDS `identification`, `preparation`, `implementation`, `completion`, `maintenance`, `decommissioning` are **phases**, not statuses; OC4IDS mixes the two, and schemaGov separates them. |
| `phase` | `DefinedTerm`, `inDefinedTermSet` | GDS Service Manual; OC4IDS `status` (as phase) | **reuse** the DefinedTerm pattern; **mint** `gs:projectPhase` (the property that points at it). |
| lifecycle scheme | `DefinedTermSet`, `hasDefinedTerm` | | reuse |
| term order | none (DefinedTerm has no ordering) | | **stretch** `schema:position` on each term |
| as-of date | `schema:dateModified` (defined on CreativeWork, not on Organization) | | **stretch.** A project's status, phase and forecast are true as of a date. Optional. History (earlier values) is not modelled. |
| health | none | | **defer** |

## Phase schemes

| Scheme | Terms | Provenance |
|---|---|---|
| `DigitalServicePhase` (shipped) | discovery, alpha, beta, live, retired | GDS Service Manual: discovery, alpha, beta, live, retirement. `retired` names the state; GDS names the activity. |
| children of `beta` | private-beta, public-beta | GDS describes both inside the beta phase (private beta, then a beta assessment, then public beta). Local refinement, modelled as `skos:broader beta`. |
| `InfrastructurePhase` (not shipped) | identification, preparation, implementation, completion, maintenance, decommissioning | OC4IDS `projectStatus`. Candidate for a later minor version. |
| publisher-defined (example) | NYC Capital Projects: Design, Construction Procurement, Construction, Close-Out. The source's `IT` value is a project kind, not a stage, and is omitted. | Real data; see the pilot. Shows a publisher can reference a scheme schemaGov does not ship. |

Other governments' digital lifecycles, checked:

- **NSW (Australia):** discovery, alpha, beta (private and public), live; retiring a service is
  documented separately, not as a phase. Supports the private and public beta refinement.
- **Australian DTA Digital Service Standard:** refers to discovery, alpha and beta stages. A full
  phase list was not confirmed.
- **United States:** no federal lifecycle standard was found. Agencies use discovery, alpha, beta
  and live in practice. No alignment is claimed.
- **New Zealand:** page did not load. Not checked.

## Generic project-management standards

| Standard | Finding | Decision |
|---|---|---|
| PMBOK (PMI) | Five **process groups** (initiating, planning, executing, monitoring and controlling, closing). These are groups of activities running through a project, not sequential phases. | Not a phase scheme. Not used. |
| ISO 21502 | A generic phase model (pre-project, initiation, planning, delivery, closure) with decision gates between phases. The text is paywalled; only public summaries were read. | A candidate for a later generic scheme. Not shipped: nothing in the data seen so far uses it. |

Publishers who follow either can reference their own scheme by identifier.

## Milestones

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| `gs:Milestone` | none; closest base is `schema:Event` | OCDS `Milestone` | **mint** as a subclass of `schema:Event` |
| `name`, `description`, `url` | `name`, `description`, `url` | OCDS `title`, `description` | reuse |
| `dueDate` | none | OCDS `dueDate` | **mint** `gs:dueDate` |
| `dateMet` | none | OCDS `dateMet` | **mint** `gs:dateMet` |
| `milestoneStatus`: scheduled, met, notMet, partiallyMet | none | OCDS `Milestone.status` | **mint** the property; **reuse** OCDS values unchanged. Project status values do not describe a milestone. |
| milestone → project | `superEvent`: domain Event, range **Event**, so it cannot point at a Project | OCDS: milestones are nested in the project | **reuse** `schema:about` (defined on Event; range Thing). Same link an update uses. |

## Updates

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| project update | `schema:Article` or `CreativeWork` | | **reuse.** No `gs:ProjectUpdate`. |
| `about` → Project | `schema:about` | | reuse |
| `datePublished`, `author`, `name`, `description`, `url` | same | | reuse |
| Project → its updates | none | | **not modelled.** The Article points at the Project. A forward list would be a second assertion of the same fact (SPEC section 1.2). Consumers query the inverse. |

## Organizations

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| responsible organization | `parentOrganization` (domain Organization, range Organization, so valid on a Project) | OC4IDS party roles | **stretch:** means "larger organization this is part of". Revisit if pilots show confusion. |
| participating organization | `member` (Organization or Person) | OC4IDS parties | reuse |
| funder | `funder` | OC4IDS `budget` | reuse |

## Outputs

| schemaGov | Schema.org | Other standard | Decision |
|---|---|---|---|
| Project → what it produces | `serviceOutput` (domain Service, range Thing) goes **from a Service to what it generates**, the wrong direction. `produces` is superseded. `result` is on `Action`. | none found | **mint** `gs:produces`. No Schema.org superproperty, so it is a documented exception to "every gs: term specialises a schema.org term". |

## Not modelled

| Concept | Reason |
|---|---|
| Timeline | Derived from `startDate`, `expectedEndDate`, `endDate`, ordered `phase`, milestone dates, and update dates. |
| Project health (on track, at risk) | Distinct question from status and phase. No established standard found. Deferred. |
| Tasks, assignments, sprints, issues | Operational project management; belongs in the systems that do it. |
| Budget and spend | The `budget` profile. |

## Terms to be minted

`gs:Project`, `gs:Milestone`, `gs:projectPhase`, `gs:expectedEndDate`, `gs:dueDate`,
`gs:dateMet`, `gs:milestoneStatus`, `gs:produces`; code lists `ProjectStatus`,
`MilestoneStatus`, `DigitalServicePhase`.

## Open points

- `startDate` / `endDate` on a Project is outside Schema.org's stated domain. Valid RDF,
  and valid under `domainIncludes`, but not strictly conformant. Recorded here, not hidden.
- `parentOrganization` for "responsible" is the weakest mapping.
- ISO 21500/21502 text is paywalled and was not read in full. The US, Australian DTA and New Zealand lifecycles are not fully confirmed.
