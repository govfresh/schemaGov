# `org` profile — Organization structure

**Status:** implemented · **Depends on:** `_core` · **Source standard:** [Popolo](https://www.popoloproject.com), W3C ORG

## What this profile is for

`_core` already defines Organization, Person, and Role, so this profile does not redefine
them. What `_core` cannot express is the **temporal and publishing layer**:

- A `Role` binds a person to a body for a span of time. When nobody holds an office, there is
  no Role — and the office still exists. `_core` has no way to say *this seat is empty*.
- A list of officeholders is not a succession. Nothing groups "the people who have been
  mayor" into a single office with a history.
- A pile of entity files is not a directory. Nothing states what the set contains, when it
  was last current, who stands behind it, or what conformance level it claims.

schema.org has no concept for any of this. It has no vacancy, no incumbency, and no
succession — `successorOf` exists but is for products. So this profile mints one class,
`gs:Post`, and the small number of properties that hang off it.

## Post

A **Post** is an office that exists independently of whoever holds it: *Mayor of Example
City*, *Councilmember, District 2*. It is the Popolo `Post`, and it is the hinge that makes
vacancy and succession expressible.

```
Post  ←── post ──  Role  ── member ──→  Person
 │                  │
 │                  └── startDate / endDate   (one tenure)
 └── vacantSince, termDuration, maximumTermCount, roleClassification
```

One Post, many Roles over time, at most one of them current. A vacancy is a Post whose
`vacantSince` is set and which no open Role points at.

`namedPosition` and `numberedPosition` are real schema.org Role properties and carry seat
identity, so no term was minted for them.

## Vacancy is data, not absence

`vacantSince` exists because omitting a vacancy is indistinguishable from never having
collected the information. A consumer cannot tell "this seat is empty" from "this publisher
does not list seats." Stating the vacancy explicitly is the difference between a directory
that can be audited and one that cannot.

## Directory

A `Directory` is a `schema:DataFeed` packaging the whole structure into one dated,
attributed, retrievable document. A consumer polls one URL and reads `dateModified` to learn
whether anything changed, rather than crawling every entity.

`conformsTo` carries the claimed conformance level (SPEC §4), which is how a small authority
signals that it is publishing Core rather than failing at Standard.

## Organization structure

`_core` defines `GovernmentOrganization`. This section is the convention for using it to describe
a real government. It adds no new class and no new property.

| Term | Meaning |
|---|---|
| Jurisdiction | The place or territory that is governed. A place, not a body. |
| Government | The body that governs the jurisdiction. `organizationClassification: "government"`, no parent. |
| Organization unit | A department, agency, office, division, board or similar body inside a government. |
| `organizationClassification` | What kind of body it is. It does not set hierarchy. |
| `parentOrganization` | Where the body sits. This is the only thing that sets hierarchy. |

```
Jurisdiction: Example City
        ▲ areaServed
        │
GovernmentOrganization: Example City Government          (government)
        │
        ├── City Council                                  (legislature)
        └── Community Services                            (serviceArea)
                ├── Community Development Department      (department)
                │       ├── Planning Division             (division)
                │       └── Environmental Health Division (division)
                └── Public Works Department               (department)
```

A **service area** is a grouping of related departments, such as public safety or health and human
services. It is still a `GovernmentOrganization`, with `organizationClassification: "serviceArea"`,
and `parentOrganization` places it in the tree. Not every government has them, so a department
can sit directly under the government. There is no `ServiceArea` class.

Staff, budgets, services, contracts and fees belong to the organization, never to the
jurisdiction. The full working example is `examples/example-gov/organizations.jsonld`.

### Mission and description

`mission` is the organization's formally stated mission or purpose, in its own words.
`description` is a general overview. Source documents usually carry both, so keep them apart:
merging them loses which one is the official statement. Both are optional.

```json
{
  "@type": "GovernmentOrganization",
  "name": "Community Development Department",
  "mission": "Guide how land is used and keep buildings and food businesses safe.",
  "description": "Handles planning, building permits and environmental health."
}
```

schema.org has no mission property, so `mission` is a schemaGov term (`gs:mission`).

### Leadership: offices, not name fields

Who leads an organization is a **Post** (the office), held through a **Role** by a **Person**.
Do not put a name in a field such as `director: "Jane Smith"`. That loses the office, and loses who
held it before.

```
Organization ── Post ── Role ── Person
```

**Elected officials.** A council seat is a Post held through an `OrganizationRole`. A seat elected
from a district points at that district with `representsJurisdiction`:

```
City Council
   └── Post: Councilmember, District 2
         ├── representsJurisdiction → District 2 (an AdministrativeArea)
         └── OrganizationRole → Person
```

**Appointed leaders.** A department head is the same pattern, with an `EmployeeRole`:

```
Public Works Department
   └── Post: Director
         └── EmployeeRole → Person
```

When the director changes, close the old Role with `endDate` and open a new one. The Post and the
department stay the same. Working examples: `examples/example-gov/posts.jsonld` and `people.jsonld`.

### Hierarchy

- `parentOrganization` is the canonical link. Each body names its immediate parent.
- `department` and `subOrganization` on the parent are optional views of the same fact. Use
  `subOrganization` for a body with its own constitution (a council, a commission) and
  `department` for a unit of the parent's administration. If you publish them, each child must
  name that parent. The validator rejects a child listed under one body that names another.
- A `government` has no parent. A parent must be an organization, never a jurisdiction.
- Depth does not set the kind. The second level is not always a department and the third is not
  always a division. Set `organizationClassification` from what the body is, and do not infer it
  from its name or its depth. A "Community Development Agency" may well be a department.
- There are no `Department`, `Division` or `Agency` classes. Governments use these words
  differently, and one class with a code list travels better.
- Departments, boards, offices and similar bodies all sit in a directory. Hierarchy is read from
  `parentOrganization`, never from the order of items in a list or file.

### Identifiers

Three properties, three jobs:

| Property | Job |
|---|---|
| `@id` | Names the entity in the graph. Stable for the life of the organization. |
| `url` | The public web page about it today. |
| `identifier` | Codes assigned by other systems (ERP, HR, a register), qualified by `propertyID`. |

An `@id` is the identity of the body, not the address of its page. A website can move from
`/departments/community-development` to `/government/community-development` while the body keeps
the same `@id`. A good `@id` is:

- stable: it does not change when the site is redesigned or the body is renamed
- unique and persistent: never reused for a different body
- dereferenceable where practical
- not built from a page path or a display name that may change

schemaGov uses `https://<your-domain>/id/organization/<slug>` in its examples. You do not have to
use that shape. Do not make up a URL on a government domain that your organization does not
control or does not intend to keep resolving. If you cannot publish a stable URL, use a `tag:` or
`urn:` URI you control. Do not drop `@id`, because every reference to the body depends on it.

An `identifier` value is only unique inside its own scheme. The same code can appear under
several branches of a source system, so always set `propertyID` (for example `erp-org-unit`) and
never treat a bare code as the body's identity.

### Public and administrative structure

A government often has several overlapping structures: the public organization chart, the ERP
and accounting tree, the budget, HR and service delivery. They do not have to match. Publish the
public chart in `parentOrganization`. Keep source-system codes in `identifier`. schemaGov has no
property for a second, administrative parent, because schema.org, W3C ORG and Popolo do not
define one either. This is a known gap, recorded here rather than papered over.

### Relationships that are not hierarchy

One body appointing, funding or overseeing another is not hierarchy. Existing terms cover most of
it: `funder` and `sponsor` for money, `memberOf` and `affiliation` for belonging, W3C ORG
`org:linkedTo` for a general link. The one real gap is "appoints", which today is only expressible
as a `Post` whose `roleClassification` is `appointed`. No `OrganizationRelationship` class is
defined. Revisit when a profile needs it.

### Keep structure and services apart

A service, permit, program or fee is not an organizational unit, even when a government's website
lists it under a department. Model it as its own entity and point at the owning organization:

```
Environmental Health Division    GovernmentOrganization
   ├── Food facility inspection  GovernmentService
   ├── Food facility permit      GovernmentPermit
   └── Food facility fee         (fees profile, planned)
```

### Decision guide

```
A government body or unit inside one?       → GovernmentOrganization
Does it have a parent?                      → parentOrganization (none for the government itself)
A group of related departments?             → organizationClassification: serviceArea
What kind of body is it?                    → organizationClassification
Does it have a code in another system?      → identifier, with propertyID
Does it have a public page?                 → url (not @id)
Is it a service, permit, program or fee?    → not an organization; reference the owner
```

## Files

| Schema | Type | Purpose |
|---|---|---|
| `schema/post.schema.json` | `gs:Post` | An office, independent of its holder. |
| `schema/directory.schema.json` | `schema:DataFeed` | The packaged, dated org structure. |
| `codelists/role-classification.json` | `DefinedTermSet` | How an office is filled. |

`roleClassification` is mechanism-based (elected, appointed, employed, ex officio, volunteer,
hereditary) rather than title-based, because job titles do not translate across countries but
the mechanism of appointment does.
