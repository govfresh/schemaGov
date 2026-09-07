# gov-schema specification

**Version** 1.0.0-draft · **Namespace** `https://schema.govfresh.com/v1/` · **Prefix** `gs:`
**Licence** [CC0 1.0](LICENSE) for the vocabulary and schemas, [MIT](LICENSE-CODE) for the tooling

gov-schema is a **profile**, not a new standard. It describes government entities —
organizations, legislation, meetings, service requests, budgets, contracts — by combining
schema.org with the domain standards that already won in each area, and it mints new terms
only where nothing suitable exists.

The status of every term is explicit: a document that uses only schema.org vocabulary is
readable by any schema.org consumer, and the `gs:` terms it adds are each declared as a
subclass or subproperty of a schema.org term, so nothing is lost by ignoring them.

---

## 1. Design rules

These are the rules that decide every modelling question in this repository.

### 1.1 A place is not an organization

The single most consequential rule. A **Jurisdiction** is a territory — a `Place`. A
**Government Organization** is a body that exercises authority over one — an `Organization`.
They are separate entities with separate identifiers.

A territory has no employees, departments, budget, or legislation. Attaching them to a
`City` produces a document that looks fine and is not valid schema.org: `employee`,
`department`, `parentOrganization`, `subOrganization`, and `member` all have domain
`Organization`, and `City` is a `Place`.

The two are linked by `schema:areaServed`, whose range already includes `AdministrativeArea`.

A third kind sits alongside them: a **Facility**, the physical building a body occupies,
linked with `schema:location`. A Jurisdiction and a Facility are both Places, but an area of
authority is not a building.

```
City (Place)  ←──  areaServed  ──  GovernmentOrganization  ──  location  ──→  CityHall (Place)
     └── containedInPlace → State → Country
```

Beware the schema.org types that look right here but are dual-typed through `LocalBusiness`,
which subclasses **both** `Organization` and `Place`: `GovernmentOffice`, `PoliceStation`,
`FireStation`, and `Library` all collapse this distinction by construction. Use
`GovernmentBuilding` and its Place-only subtypes instead; see `profiles/_core/README.md`.

### 1.2 Reference, never inline

Cross-entity links MUST be reference objects carrying `@id` and at most `@type` and `name`
as display hints:

```json
"parentOrganization": {"@id": "https://example-city.gov/id/organization/city-government"}
```

An inlined copy is a second, unversioned assertion of the entity that will drift from the
original. The validator in `tools/validate.py` treats a reference to an unknown `@id` as an
error.

### 1.3 Mint nothing schema.org already covers

Before adding a `gs:` term, check the vocabulary. The following were checked and are
deliberately **not** minted:

| Need | Use instead |
|---|---|
| Organization → territory | `schema:areaServed` |
| Scheme-qualified identity | `schema:identifier` → `PropertyValue` |
| Organization hierarchy | `schema:parentOrganization` / `subOrganization` / `department` |
| Office held, with term dates | `schema:OrganizationRole` + `roleName` / `startDate` / `endDate` |
| Whether a law is in force | `schema:legislationLegalForce` → `LegalForceStatus` |
| Amendment and repeal history | `schema:legislationAmends` / `legislationRepeals` / `legislationConsolidates` / `legislationChanges` |
| Recurring meeting pattern | `schema:eventSchedule` → `Schedule` (`byDay`, `byMonthWeek`, `repeatFrequency`) |

schema.org's legislation vocabulary derives from the European Legislation Identifier (ELI)
and carries 21 `legislation*` properties. Most of what a municipal code needs is already
there.

### 1.4 Adopt the incumbent standard, project into schema.org

schema.org covers roughly half of this domain. Where it has no types — 311, budget,
procurement — a mature open standard already exists and is in production across many
countries. gov-schema takes that standard as the **source model** and defines a schema.org
**projection** for discovery and general-purpose consumers.

Forcing a budget into `MonetaryGrant` yields something neither a search engine nor a budget
analyst can use. Publishing the Fiscal Data Package and a schema.org `Dataset` description
of it serves both.

### 1.5 No national assumption

The model is used across countries, so no country's structures are privileged:

- Identity is **scheme-qualified** (§2). No identifier system is built in.
- Tiers of government come from an **extensible code list**, not an enumeration of one
  country's tiers.
- Names are multilingual. `name` is authoritative; `givenName` / `familyName` are optional,
  because not every naming culture decomposes that way.
- Language is explicit via `knowsLanguage` (BCP 47) so consumers can select among variants.

### 1.6 Records are retired, not deleted

An entity that ceases to exist gets `dissolutionDate` (organizations) or `endDate` (roles).
It is never removed, because published documents cite it by `@id` and those citations must
keep resolving.

---

## 2. Identity

Every entity has one `@id`: an absolute, dereferenceable IRI the publisher controls.

```
https://{authority}/id/{collection}/{local-id}
```

Beyond that, an entity carries any number of **scheme-qualified identifiers** as
`schema:PropertyValue`, where `propertyID` names the scheme and `value` carries the code:

```json
"identifier": [
  {"@type": "PropertyValue", "propertyID": "wikidata",  "value": "Q30"},
  {"@type": "PropertyValue", "propertyID": "iso3166-2", "value": "US-CA"}
]
```

This is the mechanism that makes the model work internationally. It is the same pattern
OCDS uses for organization identifiers, so procurement data crosswalks without
transformation.

**Registered scheme tokens:** `wikidata`, `iso3166-1-alpha2`, `iso3166-1-alpha3`,
`iso3166-2`, `geonames`, `lei`, `ocd-division`, `gs:local`; any `org-id:<prefix>` token from
the [org-id.guide](https://org-id.guide) register; or an absolute IRI naming your own scheme.

A **Wikidata QID is strongly recommended** on every jurisdiction. It is the only identifier
system with global coverage across all tiers, which makes it the practical join key between
publishers in different countries.

---

## 3. Repository layout

```
context/v1/context.jsonld    the @context every instance imports; immutable once published
vocabulary/govschema.ttl       gs: terms, each subClassOf/subPropertyOf a schema.org term
profiles/_core/                Jurisdiction · Organization · Person · Role · Identifier
profiles/{org,code,meetings,requests,budget,procurement}/
examples/example-city/         one coherent, cross-linked fixture set
crosswalks/                    mapping tables to the standards being profiled
shapes/                        SHACL, for semantic validation
tools/validate.py              shape + reference-integrity checker
```

Every domain profile carries the same five artifacts, so the pattern is learned once:
`README.md` · `schema/*.schema.json` · `context.jsonld` · `crosswalk.md` · `examples/`.

---

## 4. Validation

Two independent tiers.

**Shape** — JSON Schema 2020-12. Required fields, types, enums, `$ref` across profiles. This
is what publishers run in CI.

**Semantics** — SHACL over expanded JSON-LD, in `shapes/gov-schema.shapes.ttl`, run by
`tools/shacl.py`, which also guards that no code-list value expands into a namespace where it
is not defined. Checks what a reference resolves **to**, which JSON Schema structurally
cannot see: a Role pointing at an Organization instead of a Person, `areaServed` pointing at a
body instead of a territory, a cycle in the jurisdiction hierarchy. Measured against a
deliberately broken fixture, JSON Schema caught 1 of 5 faults and these shapes caught the
other 4.

`tools/validate.py` runs the shape check (when `jsonschema` is installed) and always runs
reference integrity: dangling `@id` references and duplicate declarations are errors. It also
enforces domain rules that neither tier expresses — reporter privacy in `requests`, budget
arithmetic, contract-to-award integrity in `procurement`, alert expiry and supersession, and
manifest routing.

**Conformance claims are verified.** A document declaring `conformsTo` is checked against the
level it claims; an unverified claim is worse than no claim.

### Conformance levels

A publisher declares a level with `conformanceLevel` (`gs:conformanceLevel`). This is
deliberately **not** `dcterms:conformsTo`, which means an external standard the data follows
and is typed as an IRI — a bare level name expanded there becomes a broken relative IRI. The ladder exists so that a small
authority can publish something genuinely useful on day one instead of bouncing off a
forty-field requirement.

| Level | Requirement |
|---|---|
| **Core** | Jurisdiction and Organization present, correctly separated, each with `@id` and one identifier |
| **Standard** | Core, plus every required field of each domain profile in use, and all references resolve |
| **Extended** | Standard, plus recommended optional fields and a crosswalk to the source standard |

---

## 5. Domain profiles

Every profile in the table above is specified, implemented, and validating.

| Profile | schema.org type | Source standard | Status |
|---|---|---|---|
| `_core` | `AdministrativeArea`, `GovernmentOrganization`, `Person`, `OrganizationRole` | Popolo, W3C ORG | **implemented** |
| `org` | `gs:Post`, `schema:DataFeed` | Popolo, W3C ORG | **implemented** |
| `code` | `Legislation` / `LegislationObject` | Akoma Ntoso, ELI | **implemented** |
| `meetings` | `gs:Meeting`, `EventSeries`, `Schedule` | Popolo, OCD | **implemented** |
| `requests` | *none — projection only* | **Open311 GeoReport v2** | **implemented** |
| `budget` | *none — projection only* | **Fiscal Data Package**, COFOG, GFSM 2014 | **implemented** |
| `procurement` | *none — projection only* | **OCDS** | **implemented** |
| `catalog` | `DataCatalog`, `Dataset` | **DCAT / DCAT-AP** | **implemented** |
| `alerts` | `SpecialAnnouncement` (projection only) | **CAP 1.2 (OASIS)** | **implemented** |

Build order follows dependency, not interest: `_core` → `org` → `code` + `meetings`
(coupled: agenda items cite legislation, votes occur at meetings) → `budget` → `procurement`
(contracts cite budget lines). `requests` is independent and can be built at any point; it
is the strongest early adoption driver, because authorities already have 311 data flowing.

---

## 6. Versioning

SemVer on the profile. Context URLs are versioned and **immutable once published** — a
document pinned to `v1` must expand identically forever. Additive term changes are minor;
removing or renarrowing a term is major and requires a new context path.
