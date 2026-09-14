# gov-schema

A shared vocabulary for government operations — organizations, legislation, meetings,
service requests, budgets, and contracts — built as a **profile of schema.org combined with
the open standards already established in each domain**, not as a competing standard.

Designed to work across countries. No national identifier system, government tier, or naming
convention is built in.

## The idea

schema.org covers about half of what a government publishes. Where it fits — organizations,
legislation, meetings — gov-schema uses it directly. Where it has nothing — 311, budgets,
procurement — a mature open standard already exists, so gov-schema adopts that as the source
model and defines a schema.org projection for discovery.

| Domain | schema.org | Source standard |
|---|---|---|
| Org structure | `GovernmentOrganization`, `Person`, `OrganizationRole`, `gs:Post` | Popolo, W3C ORG |
| Code | `Legislation` / `LegislationObject` | Akoma Ntoso, ELI |
| Meetings | `Event`, `EventSeries`, `Schedule` | Popolo, Open Civic Data |
| 311 | *projection only* | Open311 GeoReport v2 |
| Budget | *projection only* | Fiscal Data Package, COFOG |
| Procurement | *projection only* | Open Contracting Data Standard |
| Discovery | `DataCatalog`, `Dataset` | DCAT / DCAT-AP |
| Alerts | *projection only* | Common Alerting Protocol (OASIS) |
| Permits | `GovernmentPermit` | BLDS, national equivalents |
| Elections | *projection only* | NIST SP 1500-100, VIP |
| Services | `GovernmentService`, `PeopleAudience` | Open Referral / HSDS |

## Two rules that shape everything

**A place is not an organization.** A city is a territory; the city government is a body.
Territories have no employees or budgets. They are separate entities linked by `areaServed`.

**Reference, never inline.** Cross-entity links carry `@id` and nothing load-bearing. An
inlined copy is a second assertion that will drift.

Both are enforced by the validator. See [SPEC.md](SPEC.md) for the full rationale.

## Layout

```
context/v1/       the @context every document imports
vocabulary/       gs: terms, each mapped onto a schema.org term
profiles/_core/   Jurisdiction · Organization · Person · Role · Identifier
profiles/…        org · code · meetings · requests · budget · procurement ·
                   catalog · alerts · permits · elections · services
examples/         a coherent, cross-linked fixture set, plus real-publisher pilots
crosswalks/       mapping tables to the standards being profiled
shapes/           SHACL, for semantic validation
tools/validate.py shape + reference-integrity checker
```

## Site

The published site at `https://schema.govfresh.com` is **not just documentation** — it is the
namespace resolution endpoint. Every published gov-schema document pins URLs under
`/v1/`, and SPEC section 6 makes them immutable. `tools/check-namespace.js` verifies that
every such URL resolves in the built site, and CI fails the build if one does not.

Built with [Eleventy](https://www.11ty.dev), following the ScanGov 11ty conventions, themed
with the `lf-ui` layer (Bootstrap 5.3.2). Reference pages are generated from the JSON Schemas
and code lists themselves, so the documentation cannot drift from what the validator enforces.

Beyond the profiles, the site documents every external standard gov-schema profiles against
(schema.org, Popolo, OCDS, and the rest) on its own page under `/standards/`, explains the
project itself under `/about/`, and is fully searchable from `/search/` — one index covering
every profile, field, code list, term, and standard, built at generation time from the same
data the pages themselves are generated from.

```bash
npm install
npm start          # dev server at localhost:8080
npm run build      # build to _site/
npm run check      # build + namespace check + example validation
```

## Validate

```bash
python3 tools/validate.py                  # reference integrity, no dependencies
pip install jsonschema referencing         # adds JSON Schema shape checking
pip install pyshacl rdflib                 # adds SHACL semantic checking
python3 tools/validate.py examples/example-city
python3 tools/shacl.py examples/example-city
npm run check                              # all of the above, as CI runs it
```

## Licensing

The specification, vocabulary, schemas, code lists and examples are dedicated to the public
domain under [CC0 1.0](LICENSE); the tooling is [MIT](LICENSE-CODE). A government can adopt,
adapt or fork the vocabulary with no attribution obligation and no licence review — see
[LICENSING.md](LICENSING.md) for why that choice matters for adoption.

## Status

Every profile listed above is specified, implemented, and validating, and each has been
converted from at least one real government publisher — see [SPEC.md §5](SPEC.md#5-domain-profiles).

The `lf-ui` theme layer in `public/assets/lf-ui/` is vendored from `lukefretwell/lf-ui` and is
expected to move to a GovFresh-owned package; when it does, only that folder changes.

Contributions and crosswalk corrections are welcome, particularly from publishers outside
the US who can tell us where the model makes an assumption it shouldn't.
