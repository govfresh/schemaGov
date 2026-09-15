# Common Alerting Protocol crosswalk

[CAP 1.2](http://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) (OASIS) is the
source model for the `alerts` profile. Publishers already emitting CAP should keep doing so;
this is a schema.org projection for discovery and for joining alerts to the rest of a
government's published record.

## Alert element

| CAP | schemaGov |
|---|---|
| `identifier` | `alertIdentifier` |
| `sender` | `sender` → a GovernmentOrganization reference |
| `sent` | `sent` |
| `status` | `alertStatus` |
| `msgType` | `messageType` |
| `scope` | `scope` |
| `references` | `references[]` → Alert references (CAP uses `sender,identifier,sent` triples) |
| `incidents` | `incident` |
| `note` | `note` |
| `code`, `restriction`, `addresses` | not modelled — routing concerns, not public data |

## Info element

| CAP | schemaGov |
|---|---|
| `language` | `inLanguage` |
| `category` | `category[]` |
| `event` | `event` |
| `responseType` | `responseType[]` |
| `urgency` / `severity` / `certainty` | `urgency` / `severity` / `certainty` |
| `effective` / `onset` / `expires` | `effective` / `onset` / `expires` |
| `senderName` | `senderName` |
| `headline` | `headline` |
| `description` | `description` |
| `instruction` | `instruction` |
| `web` | `web` |
| `contact` | `contact` |
| `audience` | `audience` |
| `eventCode`, `parameter` | use `identifier[]` with a scheme-qualified `propertyID` |

CAP values are title-case (`Immediate`, `Severe`, `Observed`); schemaGov uses lower camel
case throughout for consistency with every other code list in the profile. The mapping is
case-insensitive and otherwise identical.

## Area element

| CAP | schemaGov |
|---|---|
| `areaDesc` | `areaDescription` |
| `polygon` | `geometry` — a **URL** to GeoJSON, not inline coordinates |
| `circle` | `circle` (`lat,lon radiusKm`) |
| `geocode` | `geocode[]` as scheme-qualified identifiers (SAME, UGC, ONS, INSEE) |
| `altitude`, `ceiling` | not modelled — aviation-specific |
| — | `jurisdiction` → a `_core` Jurisdiction reference |

**The polygon difference is deliberate.** CAP inlines coordinate pairs as text. schemaGov
references GeoJSON (RFC 7946, WGS84) by URL, because a real warning polygon is thousands of
pairs and alerts travel over constrained channels. Converting CAP → schemaGov means writing
the polygon to a file and linking it; converting back means inlining it.

`jurisdiction` has no CAP equivalent and is the main thing this projection adds: it joins an
alert to the territory, the organization, and everything else in the graph.

## schema.org projection

For discovery only, an alert may additionally be expressed as `SpecialAnnouncement`:

| schemaGov | `SpecialAnnouncement` |
|---|---|
| `headline` | `name` |
| `description` | `text` |
| `sent` | `datePosted` |
| `expires` | `expires` |
| `web` | `url` |
| `category` | `category` |

Everything CAP-specific — urgency, severity, certainty, responseType, area — has no
`SpecialAnnouncement` equivalent and is lost in that projection. Never treat it as the record.
