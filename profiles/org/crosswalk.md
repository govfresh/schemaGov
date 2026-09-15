# `org` crosswalk

Extends the [`_core` Popolo crosswalk](../../crosswalks/popolo.md), which maps Person,
Organization, Membership, and Area. This file covers only what the `org` profile adds.

| Popolo | schemaGov | Notes |
|---|---|---|
| `Post` | `gs:Post` | Direct equivalent. Both are an office independent of its holder. |
| `Post.label` | `roleName` | |
| `Post.organization_id` | `memberOf` | Required in both. |
| `Post.area_id` | `representsJurisdiction` | Popolo `Area` conflates territory and constituency; schemaGov points at a Jurisdiction. |
| `Post.role` | `roleClassification` | Popolo's `role` is free text; schemaGov constrains it to a mechanism code list. |
| `Membership.post_id` | `post` on the `_core` Role | The link that turns Roles into a succession. |
| — | `vacantSince` | **No Popolo equivalent.** Popolo represents a vacancy as a Post with no current Membership, which is indistinguishable from incomplete data. |
| — | `termDuration`, `maximumTermCount` | **No Popolo equivalent.** |

## W3C Organization Ontology

| ORG | schemaGov |
|---|---|
| `org:Post` | `gs:Post` |
| `org:Membership` | `schema:OrganizationRole` (`_core`) |
| `org:holds` / `org:heldBy` | `post` / `member` |
| `org:Organization` | `schema:GovernmentOrganization` (`_core`) |
| `org:subOrganizationOf` | `parentOrganization` |

ORG models a Post as held by at most one agent at a time, which matches this profile. It has
no vacancy or term-limit concept either.

## Where publishers get this wrong

**Modelling the office as a Person property.** `jobTitle` on a Person cannot express a
vacancy, a succession, or a term limit, and it silently loses the office when the person
leaves.

**Deleting a Role when someone leaves.** Close it with `endDate`. The historical record is
the reason the Post exists.

**Treating an ex officio seat as a separate appointment.** Use `roleClassification:
"exOfficio"` — the holder is determined by another Post, so recording it as `appointed`
misstates who decides.
