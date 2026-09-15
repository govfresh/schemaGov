# Design note — geospatial data

**Status:** decided and implemented. Decisions recorded in "Settled" below. Records the evidence, the options, and a
recommendation for the open geospatial question in [ROADMAP.md](ROADMAP.md).

---

## The problem, stated precisely

Every geo-bearing entity in schemaGov carries at most a **point**. There are no boundaries
anywhere — not for jurisdictions, not for wards, not for zoning districts, not for alert
areas. Three separate pieces of work have now hit this from different directions:

- **`catalog`** — data.gov.ie publishes `srs: ["epsg:2157"]` (Irish Transverse Mercator),
  confirming an international profile cannot silently assume WGS84.
- **`alerts`** — the NWS CAP feed **inlines** warning polygons. The profile says geometry is
  referenced by URL, so the adapter links to the alert's own API endpoint, which resolves to
  the whole alert rather than to a geometry. That is a workaround, not a mapping.
- **`_core`** — jurisdictions have `geo` → a point, and nothing else.

The sharpest finding is the second: **a publisher that inlines geometry currently has nowhere
to put it.** That is not a coverage gap; it is a case the design actively cannot represent.

## What schema.org offers, and why it is not enough

`schema:GeoShape` exists, and its `polygon` is defined as:

> *"a series of four or more space delimited points where the first and final points are
> identical"*

A text string. No coordinate reference system, no multipolygon, no interior rings (holes), no
precision or simplification metadata. Adequate for a bounding box; unusable for a real
administrative boundary, which routinely has thousands of vertices, several disjoint parts
(islands, exclaves) and interior holes.

schema.org knows this. It carries a type called `GeospatialGeometry`, whose entire definition
is:

> *"(Eventually to be defined as) a supertype of GeoShape designed to accommodate definitions
> from Geo-Spatial best practices."*

A declared placeholder that has not been filled in. There is no schema.org answer coming, so
this profile has to make its own decision — the same position `budget`, `procurement` and
`requests` were in.

## The thing that is easy to miss

**Boundaries change.** A jurisdiction's boundary in 2020 is not its boundary in 2026. Wards
are redrawn, municipalities annex and merge, electoral districts are reapportioned.

This is not an edge case for this profile — it is load-bearing:

- the `elections` profile records a 2022 contest in District 2, which was fought on the **2022**
  District 2 boundary
- the `org` profile has a Post whose holder represents a district that may since have moved
- a `budget` line attributed to an area, or a `permit` located in one, is anchored to the
  boundary in force at the time

A boundary without validity dates silently rewrites history. Any design that attaches a single
current geometry to a jurisdiction gets this wrong, and it is the main reason not to simply add
a `polygon` field and move on.

## Three decisions

### 1. Inline, referenced, or both?

| Option | Consequence |
|---|---|
| Reference only (current) | Cannot represent CAP publishers who inline. **Proven gap.** |
| Inline only | A city boundary is thousands of coordinate pairs; every document carrying one becomes unusable, and alerts travel over constrained channels. |
| **Both, with guidance** | Represents real publishers either way; needs a stated rule for which to use. |

**Recommended: both.** Reference is the default and the only sane choice at boundary scale.
Inline is permitted for small geometries — an alert polygon, a parcel outline — because real
standards do it and forbidding it means being unable to describe CAP.

The rule should be about size and reuse rather than a hard byte limit: **inline geometry that
is specific to this record and small; reference geometry that is shared, authoritative, or
large.** A jurisdiction boundary is always referenced — it is shared by every record in that
jurisdiction, and duplicating it into each is exactly the drift SPEC §1.2 exists to prevent.

### 2. How is the coordinate reference system declared?

GeoJSON (RFC 7946) **mandates** WGS84 longitude/latitude and forbids alternatives, so
conformant GeoJSON needs no CRS declaration at all. But publishers hold authoritative geometry
in national grids — `epsg:2157` in Ireland, OSGB36 in Britain, GDA2020 in Australia — and OGC
API Features distinguishes the two explicitly:

```
storageCrs: http://www.opengis.net/def/crs/OGC/1.3/CRS84    the native CRS
crs:       [ ... ]                                          CRSs it can serve
```

**Recommended:** follow OGC and separate them. Referenced GeoJSON is CRS84 by definition and
declares nothing. Where a publisher's authoritative source is a national grid, that is recorded
as provenance — not as a claim about the served coordinates. Accept both OGC CRS URIs and
`epsg:` shorthand, since `catalog` already sees the latter in the wild.

The failure this prevents is silent and severe: coordinates in a national grid interpreted as
WGS84 land in the wrong hemisphere.

### 3. Does `_core` get a boundary concept?

**Recommended: yes**, as a small cross-cutting addition rather than a profile.

Geometry attaches to jurisdictions, facilities, alert areas, permit premises and datasets
alike. A `geo` profile would have no entities of its own — it is a value type, like
`identifier` and `amount`, and belongs in `_core` next to them.

## Sketch

A `Geometry` value carrying either a reference or inline content, never both, plus the
temporal validity that makes historical accuracy possible:

```jsonc
"boundary": {
  "@type": "Geometry",
  "geometryType": "MultiPolygon",
  "contentUrl": "https://example-city.gov/geo/district-2-2022.geojson",
  "encodingFormat": "application/geo+json",
  "validFrom": "2022-01-01",
  "validUntil": "2031-12-31",        // absent means current
  "sourceReferenceSystem": "epsg:2157",  // provenance, not the served CRS
  "simplified": true,                 // a display generalisation, not the legal boundary
  "authoritative": false
}
```

`simplified` and `authoritative` matter more than they look. Published boundary files are
frequently generalised for web display, and a generalised boundary is **not** the legal
boundary — using one to decide whether an address falls inside a district gives wrong answers
at the edges. A consumer needs to know which it has.

## What this would change

| Where | Change |
|---|---|
| `_core` | New `geometry.schema.json`; `boundary` on Jurisdiction and Facility |
| `alerts` | `AlertArea.geometry` accepts an inline Geometry as well as a URL — closes the CAP gap |
| `catalog` | Existing `spatialReferenceSystem` aligns to `sourceReferenceSystem` |
| `permits` | `premises` gains an optional boundary for parcel outlines |
| `elections` | `representsJurisdiction` can be read at the boundary in force on `electionDate` |
| Validator | Geometry has exactly one of `contentUrl` or inline content; `validUntil` after `validFrom`; inline geometry above a vertex threshold warns |

## What is deliberately excluded

**Spatial operations.** No point-in-polygon, no intersection, no area computation. This
profile describes where things are; it is not a spatial engine, and `geoContains` /
`geoWithin` / `geoIntersects` already exist in schema.org for asserting topological
relationships where a publisher wants to.

**Raster and imagery.** Out of scope.

**Coordinate transformation.** schemaGov records which CRS a source used. Converting between
them is a job for a GIS library, and a schema that implied otherwise would be lying about what
it can guarantee.

## Settled

**1. Historical boundaries are separate, citable entities.** A `Boundary` has its own `@id`,
names the place it bounds, and carries its own validity dates. A jurisdiction references its
boundaries rather than embedding them.

This costs a little more to publish and buys the thing that matters: an electoral district
boundary is exactly what gets cited in a dispute, and a citation needs something to point at.
It also means the 2022 District 2 boundary and the current one are distinct resources that can
be fetched, compared and referenced independently, rather than array elements whose identity
depends on their position.

**2. Inline geometry size warns rather than fails.** A large inline geometry is a judgement
about publishing practice, not a correctness error, and a validator that rejects real data on
a threshold someone picked would be making the same mistake `areaServed` made against UK
Contracts Finder.

**3. Facilities do not get boundaries.** A point and an address locate a building. A building
footprint is a cadastral concern, and adding it would put geometry on an entity that has no
use for it.
