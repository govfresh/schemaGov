# Identifier crosswalk

schemaGov does not define an identifier system. It carries any number of external ones as
scheme-qualified `schema:PropertyValue` pairs (SPEC §2), which is what lets the model work
across countries without privileging one nation's registry.

```json
{"@type": "PropertyValue", "propertyID": "<scheme>", "value": "<code>"}
```

## Registered scheme tokens

| Token | Covers | Coverage | Notes |
|---|---|---|---|
| `wikidata` | any entity | **global, all tiers** | Strongly recommended on every jurisdiction. The only system with global coverage across tiers, so in practice it is the join key between publishers in different countries. |
| `iso3166-1-alpha2` / `-alpha3` | countries | global | Use on `Country`. |
| `iso3166-2` | first-level subdivisions | global | Use on `State` / regional areas. Note ISO 3166-2 does not reach below the first level. |
| `geonames` | populated places | global | Useful below the ISO 3166-2 floor. |
| `lei` | legal entities | global | ISO 17442. Relevant mainly to procurement vendors. |
| `org-id:<prefix>` | organizations | national registers | Any prefix from the [org-id.guide](https://org-id.guide) register, e.g. `org-id:GB-COH`, `org-id:US-EIN`. Same convention OCDS uses, so procurement data crosswalks without transformation. |
| `ocd-division` | US divisions | US, partial elsewhere | Open Civic Data division IDs. Excellent where available; **not** a global system, so never required. |
| `gs:local` | any | publisher-local | The publisher's own key. Always available, never a join key across publishers. |

Any absolute IRI is also valid as a `propertyID`, naming a scheme of your own.

## Below the ISO 3166-2 floor

ISO 3166-2 stops at first-level subdivisions, so municipalities and wards need national
schemes. Register these as `org-id:` prefixes or publisher IRIs; do not attempt to invent a
global municipal identifier system.

| Country | Scheme | Example |
|---|---|---|
| US | OCD division ID | `ocd-division/country:us/state:ca/place:example_city` |
| UK | ONS GSS code | `E06000023` |
| FR | INSEE code | `75056` |
| DE | Amtlicher Gemeindeschlüssel | `05315000` |
| BR | IBGE code | `3550308` |

This table is illustrative, not exhaustive. Contributions adding national schemes are the
most useful thing an outside publisher can send.

## Anti-patterns

- **A bare string identifier.** `"identifier": "12345"` is unusable without its scheme.
- **A national scheme as the primary key.** Use `@id` as the primary key; national schemes
  are additional identifiers.
- **Reusing an identifier after a merger or boundary change.** Mint a new entity, mark the
  old one dissolved, and link them.
