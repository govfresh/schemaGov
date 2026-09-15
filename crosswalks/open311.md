# Open311 GeoReport v2 crosswalk

Open311 remains the source model. schemaGov is a schema.org projection of it for discovery
and for joining 311 data to the rest of a government's published record — it is not a
replacement, and a publisher should keep serving their Open311 endpoint.

## Service List — `GET /services.json`

| Open311 | schemaGov |
|---|---|
| `service_code` | `serviceCode` |
| `service_name` | `name` |
| `description` | `description` |
| `keywords` | `keywords` |
| `group` | `serviceType` |
| `type` (realtime / batch / blackbox) | `isRealtime` (boolean; batch and blackbox are both `false`) |
| `metadata` | implied by the presence of `requestAttribute` |

## Service Definition — `GET /services/:service_code.json`

Each Open311 `attribute` becomes a `schema:PropertyValueSpecification` in `requestAttribute`.

| Open311 attribute | schemaGov |
|---|---|
| `code` | `valueName` |
| `description` | `name` |
| `required` | `valueRequired` |
| `order` | `position` |
| `datatype: string` / `text` | default; constrain with `valueMaxLength` |
| `datatype: number` | `minValue` / `maxValue` |
| `datatype: datetime` | no direct equivalent; use `valuePattern` |
| `datatype: singlevaluelist` | `valueOption[]`, `multipleValues: false` |
| `datatype: multivaluelist` | `valueOption[]`, `multipleValues: true` |
| `values[]` (`key`, `name`) | `valueOption[]` as `DefinedTerm` (`termCode`, `name`) |

## Service Request — `GET /requests.json`

| Open311 | schemaGov |
|---|---|
| `service_request_id` | `serviceRequestId` |
| `status` | `requestStatus` (refined; see mapping below) |
| `status_notes` | `statusNote` |
| `service_code` | `serviceCode` |
| `service_name` | via `service` → the GovernmentService |
| `agency_responsible` | `agencyResponsible` → a GovernmentOrganization reference |
| `requested_datetime` | `dateCreated` |
| `updated_datetime` | `dateModified` |
| `expected_datetime` | `expectedResolutionDate` |
| `address` / `zipcode` | `address` → `PostalAddress` |
| `lat` / `long` | `geo` → `GeoCoordinates` |
| `media_url` | `image[]` → `ImageObject` |
| `attribute[]` | `additionalProperty[]` → `PropertyValue`, `propertyID` matching `valueName` |
| `description` | `description` |

### Status mapping

| schemaGov | Open311 |
|---|---|
| `open`, `inProgress`, `onHold` | `open` |
| `closed`, `rejected`, `duplicate` | `closed` |

Round-tripping is lossy in one direction only: Open311 → schemaGov yields `open` or
`closed`, never the finer terms.

## Fields deliberately not mapped

`email`, `first_name`, `last_name`, `phone`, `device_id`, `account_id`, `api_key`.

These exist in the Open311 **POST** payload — the submission — and have no place in published
output. schemaGov has no fields for them and the validator rejects documents that carry
them. See the privacy section of the [profile README](../profiles/requests/README.md).

## Endpoints without a schema equivalent

`GET /tokens/:token.json` (submission-time id lookup) and the `jurisdiction_id` query
parameter are protocol concerns, not data. In schemaGov the jurisdiction is a first-class
entity: a request points at it with `jurisdiction`.
