# Open Referral / HSDS crosswalk

[HSDS](https://docs.openreferral.org) is the source model for the `services` profile. It is
used for human-services directories across the US, UK, Canada and Australia, and publishers
should keep producing it.

| HSDS | schemaGov |
|---|---|
| `Organization` | `_core` `GovernmentOrganization` |
| `Service` | `GovernmentService` |
| `Service.status` | `serviceStatus` |
| `Service.application_process` | `applicationProcess` |
| `Service.eligibility_description` | `eligibility.eligibilityCriteria` |
| `Service.minimum_age` / `maximum_age` | `eligibility.requiredMinAge` / `requiredMaxAge` |
| `Service.fees_description` | `cost.description` |
| `Service.wait_time` | `processingTime` |
| `Service.interpretation_services` | `interpretationAvailable` |
| `Service.alternate_name` | `alternateName` |
| `Location` | `_core` Facility |
| `ServiceAtLocation` | `ServiceAtLocation` |
| `Schedule` | `openingHoursSpecification` on the ServiceAtLocation |
| `RequiredDocument` | `requiredDocument[]` |
| `Cost Option` | `cost` |
| `Language` | `availableLanguage` |
| `Accessibility` | `accessibilityNote` |
| `Phone`, `Contact` | `availableChannel` → `ServiceChannel` |
| `ServiceArea` | `areaServed` → a Jurisdiction reference |
| `Funding` | not modelled — belongs to the `budget` profile |
| `Taxonomy`, `TaxonomyTerm` | `lifeEvent` plus `keywords` |

## Deliberate differences

**Life events replace a taxonomy.** HSDS carries an extensible taxonomy, commonly the AIRS
or 211 human-services taxonomy, which is authoritative in North America and unused elsewhere.
`lifeEvent` is a small universal set that travels, with `keywords` and `serviceType` carrying
the publisher's own classification alongside it. A publisher with an AIRS taxonomy should keep
it in `identifier` or `keywords` rather than discard it.

**`serviceArea` is a reference.** HSDS carries a geographic description; schemaGov points at
a `_core` Jurisdiction so a service joins to the organization providing it and the territory it
covers.

**Funding is out of scope here.** HSDS models funding sources on the service; schemaGov has a
`budget` profile with COFOG and GFSM classification, and duplicating a weaker version would be
worse than referencing it.

## Note on scope

HSDS covers human services generally, including those delivered by charities and non-profits.
This profile is government-focused: `provider` must be a `GovernmentOrganization`. A directory
mixing government and third-sector provision needs the HSDS `Organization` model rather than
`_core`, which is deliberately narrower.
