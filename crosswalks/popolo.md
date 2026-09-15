# Popolo crosswalk

[Popolo](https://www.popoloproject.com) is the established international data standard for
describing legislatures and the people in them. schemaGov's `_core` profile is a direct
re-expression of Popolo's core classes in schema.org terms, so data moves between the two
without loss.

| Popolo | schemaGov | Notes |
|---|---|---|
| `Person` | `schema:Person` | Identity only in both. |
| `Organization` | `schema:GovernmentOrganization` | |
| `Organization.classification` | `gs:organizationClassification` | Code list in `profiles/_core/codelists/`. |
| `Membership` | `schema:OrganizationRole` | The central mapping. Both bind one person to one organization for one time span. |
| `Membership.role` | `schema:roleName` | |
| `Membership.start_date` / `end_date` | `schema:startDate` / `endDate` | |
| `Post` | `schema:OrganizationRole` with no `member` | A vacant or generic office. |
| `Area` | `schema:AdministrativeArea` (a Jurisdiction) | Popolo `Area` conflates territory and constituency; schemaGov keeps territory in the Jurisdiction and points at it from the Role via `representsJurisdiction`. |
| `Organization.parent_id` | `schema:parentOrganization` | |
| `Person.other_names` | `schema:alternateName` | |
| `Contact detail` | `schema:ContactPoint` | |
| `Motion`, `VoteEvent`, `Count` | *deferred to the `meetings` profile* | Not part of `_core`. |

## Where they differ

**Popolo has no place/organization split.** `Area` serves as both the territory and the
electoral district. schemaGov separates these (SPEC §1.1), so converting Popolo → schemaGov
requires deciding, per `Area`, whether it is a governed territory or a constituency. Most are
both, and become one Jurisdiction referenced from both sides.

**schemaGov requires `areaServed` on every organization.** Popolo does not. A Popolo
organization with no `area_id` cannot reach Core conformance without one being supplied.
