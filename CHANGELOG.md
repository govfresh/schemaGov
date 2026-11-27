# Changelog

schemaGov is at `1.0.0-draft`. Until `1.0.0` is released, `v1` can change in ways that a release
would not allow ([SPEC section 6](SPEC.md#6-versioning)). Changes before this file began are in
the git history.

## 1.0.0-draft

### 2026-11-27

**Stricter: data that passed before may now fail**

- An identifier's `propertyID` must be a registered token, `local:<scheme>`, `org-id:<prefix>`,
  or an `http`, `https` or `urn` IRI. An unprefixed code such as `erp-org-unit` is an error.
- `iri` and `date-time` formats are checked. An IRI must be absolute. A date-time needs a time zone.
- `OrganizationRole`, `EmployeeRole`, `Role`, `LegislationObject` and `NGO` records are checked
  against their schemas.
- `fund`, `program` and `project` on a budget line must point at a record of that type.
- `geoWithin` and `geoOverlaps` on a jurisdiction must point at a place.
- A validator whose Python packages are missing fails instead of reporting success.

**Added**

- `BudgetLine.project`.
- `projectCategory` and `estimatedCost` on projects.
- `geoWithin` and `geoOverlaps` on jurisdictions.
- A schema for non-government organizations (`NGO`), which can be a project's member or funder.
- Identifier tokens `census-geoid`, `cpv`, `unspsc` and `nigp`.
- A warning for a property that neither schema.org nor schemaGov defines.

**Changes how `v1` expands**

- `project`, `projectCategory`, `estimatedCost` and `geoWithin` are now mapped in the context. A
  document that already used one of these names now expands it to the mapped term.
