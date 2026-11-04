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

## Organization structure

| Concept | schemaGov | Source |
|---|---|---|
| Government body | `GovernmentOrganization` | schema.org |
| Parent | `parentOrganization` | schema.org; Popolo `parent_id`; ORG `subOrganizationOf` |
| Child | `subOrganization`, `department` | schema.org. Derived from the parent link, not authoritative |
| Mission statement | `mission` | **schemaGov (`gs:mission`).** No schema.org or Popolo equivalent. The closest is W3C ORG `org:purpose`, which is a looser statement of what an organization is for |
| Kind of body | `organizationClassification` | **schemaGov code list**, aligned with Popolo `classification` and ORG `OrganizationalUnit` / `FormalOrganization` |
| Territory governed | `areaServed` pointing at a Jurisdiction | schema.org; Popolo `area_id` |
| Source-system codes | `identifier` with `propertyID` | schema.org `PropertyValue`; Popolo `identifiers` |
| Funding, sponsorship | `funder`, `sponsor` | schema.org |
| Membership, affiliation | `memberOf`, `affiliation` | schema.org; ORG `memberOf` |
| General link | not defined | ORG `linkedTo` is available if needed |
| Appointing body | `Post.roleClassification: "appointed"` | schemaGov. No Popolo or ORG equivalent |
| Second, administrative parent | not defined | Gap in schema.org, ORG and Popolo |

`organizationClassification` is where schemaGov adds meaning. schema.org has no property for the
kind of government body, and Popolo's `classification` is free text. The code list makes it
checkable. `government` (the root of a tree) and `serviceArea` (a grouping of departments) are schemaGov additions.

## Where publishers get this wrong

**Modelling the office as a Person property.** `jobTitle` on a Person cannot express a
vacancy, a succession, or a term limit, and it silently loses the office when the person
leaves.

**Deleting a Role when someone leaves.** Close it with `endDate`. The historical record is
the reason the Post exists.

**Treating an ex officio seat as a separate appointment.** Use `roleClassification:
"exOfficio"` — the holder is determined by another Post, so recording it as `appointed`
misstates who decides.

**Letting the name or depth decide the kind.** Calling every second-level body a department
because that is how another government draws its chart. Set the classification from what the body
is.

**Using a page URL as `@id`.** The page moves; the body does not. Put the page in `url`.

**Treating a source-system code as identity.** The same ERP code can appear in more than one
branch. Keep it in `identifier` with its `propertyID`.
