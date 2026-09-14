# Crosswalks

gov-schema profiles existing standards rather than replacing them. Each file here maps one
standard onto the gov-schema representation, in both directions where possible.

| File | Standard | Scope | Status |
|---|---|---|---|
| `identifiers.md` | ISO 3166, Wikidata, org-id.guide, LEI, OCD-IDs | identity across all profiles | drafted |
| `popolo.md` | [Popolo](https://www.popoloproject.com) | organizations, people, memberships | drafted |
| `../profiles/org/crosswalk.md` | Popolo `Post`, W3C ORG | posts, succession, vacancy | drafted |
| `dcat.md` | DCAT / DCAT-AP (W3C) | discovery and data catalogues | drafted |
| `cap.md` | Common Alerting Protocol 1.2 (OASIS) | public warnings | drafted |
| W3C ORG | W3C Organization Ontology | organizations | covered inside [`popolo.md`](popolo.md) |
| `akoma-ntoso.md` | OASIS LegalDocML / ELI | legislation and codes | drafted |
| `open311.md` | Open311 GeoReport v2 | service requests | drafted |
| `fiscal-data-package.md` | Fiscal Data Package, COFOG, GFSM 2014 | budgets | drafted |
| `ocds.md` | Open Contracting Data Standard | procurement | drafted |

A crosswalk is authoritative about the *mapping*, never about the other standard. Where the
two disagree, the other standard wins and the disagreement is recorded here.
