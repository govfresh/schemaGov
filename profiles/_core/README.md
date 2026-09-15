# `_core` profile

The entities every other profile references. Getting these wrong propagates into all six
domains, which is why `_core` is built and validated before anything else.

| Schema | Type | Purpose |
|---|---|---|
| `jurisdiction.schema.json` | `AdministrativeArea` / `Country` / `State` / `City` | A governed territory. A **Place**. |
| `organization.schema.json` | `GovernmentOrganization` | A body exercising authority. An **Organization**. |
| `person.schema.json` | `Person` | Identity only — never the office. |
| `role.schema.json` | `OrganizationRole` | One person, one office, one time span. |
| `facility.schema.json` | `GovernmentBuilding` / `CityHall` / `LegislativeBuilding` / … | A physical place government operates. A **Place**. |
| `identifier.schema.json` | `PropertyValue` | Scheme-qualified identity. |
| `reference.schema.json` | — | A link to another entity. |

## Why Role is separate from Person

A `Person` record holds identity and nothing else. The office, the body, and the dates live
on a `Role`. This is the equivalent of a Popolo Membership, and it is what lets the data
answer *who was mayor in 2019* rather than only *who is mayor*. One person holding several
offices over time produces several Roles and exactly one Person.

schemaGov follows the schema.org Role idiom, where the Role sits in the property slot and
the property name repeats inside it to carry the value:

```json
"member": {
  "@type": "OrganizationRole",
  "roleName": "Mayor",
  "startDate": "2023-01-01",
  "member": {"@id": "https://example-city.gov/id/person/jane-smith"}
}
```

The repetition is deliberate, not a mistake.

## Code lists

`codelists/government-level.json` and `codelists/organization-classification.json` are
`DefinedTermSet`s rather than fixed enumerations, because tiers of government differ
enormously by country. A publisher SHOULD map a local tier onto the closest term and carry
the local name in `alternateName`, rather than requesting a new term.

## `subOrganization` vs `department`

Use `subOrganization` for bodies with their own constitution — councils, committees,
commissions. Use `department` for operating units of this body's administration.

## Three kinds of entity, not two

`_core` separates a territory, a body, and a building:

| | Type | schema.org base | Example |
|---|---|---|---|
| **Jurisdiction** | `City`, `State`, `Country` | `Place` | Example City, the territory |
| **Organization** | `GovernmentOrganization` | `Organization` | Example City Government, the body |
| **Facility** | `CityHall`, `GovernmentBuilding` | `Place` | Example City Hall, the building |

A Jurisdiction and a Facility are both Places, but they are not interchangeable: a
Jurisdiction is an area of authority, a Facility is a building you can stand in. The
organization links to both — `areaServed` to the territory it governs, `location` to the
building it occupies.

## Avoid the dual-typed place types

Some schema.org types that look right for government buildings are subclasses of
`LocalBusiness`, which is `rdfs:subClassOf` **both `Organization` and `Place`**. Using them
collapses the place/organization distinction the whole profile rests on:

| Avoid | Why | Use instead |
|---|---|---|
| `GovernmentOffice` | `LocalBusiness` → Organization **and** Place | `GovernmentBuilding`, or `GovernmentOrganization` with `organizationClassification: "office"` |
| `PoliceStation` | `CivicStructure` **and** `EmergencyService` → `LocalBusiness` | `GovernmentBuilding` for the building; a separate `GovernmentOrganization` for the force |
| `FireStation` | same as above | same as above |
| `Library` | `LocalBusiness` | `GovernmentBuilding`, plus an organization if it is a distinct body |

The types allowed by `facility.schema.json` are all cleanly Place-only:
`GovernmentBuilding`, `CityHall`, `LegislativeBuilding`, `Courthouse`, `Embassy`,
`DefenceEstablishment`, `CivicStructure`, `EventVenue`, `Place`.

If you genuinely want the dual-typed semantics — a library that is both a service provider
and a venue — publish two entities with distinct `@id`s and link them, rather than one
entity wearing both hats.
