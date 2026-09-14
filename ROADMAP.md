# Roadmap

All seven domain profiles are implemented and validating. This records what comes next, and
the open questions that need deciding before parts of it can be built.

Nothing here is committed to a date. Order reflects dependency and leverage, not enthusiasm.

---

## 0. Finish what the spec already promises — **DONE**

**SHACL shapes — done.** `shapes/gov-schema.shapes.ttl`, run by `tools/shacl.py`, wired into
`npm run check` and CI. Measured against a deliberately broken fixture, JSON Schema caught 1
of 5 faults and the shapes caught the other 4: a Role pointing at an Organization instead of a
Person, `areaServed` pointing at a body instead of a territory, and a cycle in the
jurisdiction hierarchy.

**Conformance-level checking — done.** `tools/validate.py` now verifies every `conformsTo`
claim against the level it asserts, and rejects unknown levels.

---

## 1. Tier one

### `catalog` — discovery — **DONE**
**Depends on:** `_core` · **Standard:** DCAT / DCAT-AP (W3C) · **schema.org:** `DataCatalog`, `Dataset`, `DataDownload`

The highest-leverage gap, and not a domain at all: **nothing currently tells a consumer where
a government's gov-schema data lives.** Every profile published, and no way to find any of them.

A well-known discovery document plus a DCAT-aligned catalogue fixes that and generalises the
`Directory` pattern already proven in `org`. Google Dataset Search consumes schema.org
`Dataset` directly, so the projection has an immediate consumer.

### `alerts` — emergency and public notices — **DONE**
**Depends on:** `_core` · **Standard:** Common Alerting Protocol (OASIS) · **schema.org:** `SpecialAnnouncement`

Model on **CAP**, not on `SpecialAnnouncement`. The schema.org type exists but every property
is COVID-shaped — `quarantineGuidelines`, `gettingTestedInfo`, `travelBans`,
`schoolClosuresInfo` — and it has no severity, urgency, certainty, or expiry.
`announcementLocation` cannot even target an `AdministrativeArea`, only a `CivicStructure` or
`LocalBusiness`, so a jurisdiction-wide alert is inexpressible.

CAP has all of it and is the international standard (IPAWS in the US, EU-Alert, and national
systems worldwide). Project into `SpecialAnnouncement` for discovery only.

### `permits` — permits and licences
**Depends on:** `_core`, `code` · **schema.org:** `GovernmentPermit` (a real skeleton)

Building permits and business licences are the highest-volume records most governments hold.
`GovernmentPermit` already supplies `issuedBy`, `issuedThrough`, `validFor`, `validFrom`,
`validIn`, `validUntil`. Minting needed for applicant, status, application and decision dates,
the property concerned, fees, and conditions.

BLDS is US-only, so this profile needs an international identifier approach of the kind
`_core` established.

### Legistar adapter — DONE

`tools/adapters/legistar.py` converts the live Legistar Web API. Seattle: 8 meetings, 76
agenda items, 27 votes. It found `position` typed integer-only when real agenda numbers are
`"3."` and `"A."` and schema:position ranges over Integer or Text - which made every real
agenda item unrepresentable.

Three things Legistar does not publish are now recorded rather than assumed: no
`requiredMajority` on any vote, no timezone on any meeting (date and time are separate
untimezoned fields), and no resolvable location or jurisdiction. See
[examples/pilot-seattle-meetings/README.md](examples/pilot-seattle-meetings/README.md).

### `elections`
**Depends on:** `org` · **Standard:** NIST SP 1500-100, VIP

Closes a loop already open in the built data: `org` records `roleClassification: "elected"`
and `Post.termDuration`, but nothing records *the election that produced the officeholder*.
Contests, candidates, results, polling places.

---

## 2. Tier two — after a real pilot

| Profile | Standard | Note |
|---|---|---|
| `services` | Open Referral / HSDS | The service catalogue beyond 311 reporting: *how do I get a birth certificate*. `GovernmentService` already in use by `requests`. |
| `grants` | IATI, 360Giving | Money **out** to third parties, distinct from procurement. `MonetaryGrant` exists. |
| `consultations` | — | Comment periods, petitions, participatory budgeting. Couples to `meetings` and `code`. |
| `indicators` | SDMX | Performance and SDG reporting. `Observation` and `StatisticalVariable` exist. |

## Extend, don't add

- **Payroll and salaries** → extend `org`. `Role` already has `baseSalary` and `salaryCurrency`.
- **Transaction-level spending (open checkbook)** → extend `budget`. The Fiscal Data Package
  already defines transactional granularity.
- **Zoning applied to parcels** → extend `code`, not a new property profile.

## Probably not

Property and cadastre (LADM is enormous), courts and dockets (Akoma Ntoso already covers
judgments), inspections (narrow, no international standard). Low reuse, high cost.

---

## Geospatial data — SETTLED

Decided and implemented; see [GEOSPATIAL.md](GEOSPATIAL.md) for the design note and
[the boundary work](profiles/_core/schema/boundary.schema.json). The evidence and options are
kept below for the record.

**A design note with a recommendation is now written up in [GEOSPATIAL.md](GEOSPATIAL.md)**, covering the three decisions (inline vs referenced, CRS declaration, whether `_core` gains a boundary concept), the evidence from `catalog`, `alerts` and `_core`, and what implementing it would change. Three questions are left open for decision there; the substantive one is whether historical boundaries are repeated on a jurisdiction or held as separate citable entities.

Summary of the section below, which records the original evidence:

**What GIS/geo data should be included?** Not yet decided. What is known:

**Today** every geo-bearing entity carries at most a point: `geo` → `GeoCoordinates` on
Jurisdiction, Facility, and ServiceRequest. There are no boundaries anywhere.

**`schema:GeoShape` is not sufficient.** Its `polygon` is a whitespace-delimited text string —
no GeoJSON, no coordinate reference system, no multipolygon, no holes. Adequate for a bounding
box, useless for a real jurisdiction boundary.

**Three location models are distinct and should not be conflated:**

| Model | Example | Carrier |
|---|---|---|
| Address | where to post a letter | `PostalAddress` |
| Point | a pothole, a facility entrance | `GeoCoordinates` |
| Boundary / parcel | a ward, a zoning district, a building plot | external geometry + identifier |

**Leading recommendation: reference geometry, never embed it.** A city boundary is thousands
of coordinate pairs; inlining it makes every document carrying it unusable. Publish GeoJSON
(RFC 7946) separately and link to it, the same way `code` links to Akoma Ntoso rather than
absorbing it — consistent with SPEC §1.4.

**Coordinate reference system must be explicit.** GeoJSON mandates WGS84, but national grids
are in daily use everywhere (OSGB36, RD/Amersfoort, GDA2020). An international profile cannot
assume WGS84 silently.

**Where geometry is actually needed in what is already built:**

- `_core` Jurisdiction — boundary (the big one; districts and wards are already jurisdictions)
- `_core` Facility — footprint, and accessible entrance points
- `code` — zoning district geometry, which is what makes a zoning code queryable
- `requests` — points already handled, including the privacy rounding rule
- `procurement` — work site or delivery area

**Likely shape:** a small cross-cutting geo module in `_core` rather than a profile — a
`boundary` reference carrying the geometry URL, its CRS, a validity date, and resolution.
Standards to align with: GeoJSON RFC 7946, OGC API — Features, INSPIRE (EU). Spatial
identifiers are already handled in `_core` via GeoNames, ISO 3166-2, OCD-IDs, and Wikidata.

---

## Scope of `requests`, and where emergency belongs — SETTLED

Resolved when `alerts` was built: alerts are outbound, requests inbound, and they stay
separate profiles linked by `ServiceRequest.relatedAlert`. Update history, duplicate
references and the alert cross-reference are all implemented. The reasoning is kept below.

**Is `requests` just 311?** The profile is deliberately named `requests`, not `311`, because
the concept is not called 311 outside North America — FixMyStreet, Melde-Portal, and national
equivalents are the same thing. That naming should hold.

**Update history — done.** `statusHistory[]` records each timestamped transition; the
validator checks it is chronological and agrees with the current status.

**Duplicate references — done.** `duplicateOf` is now a resolvable reference, and a request
marked `duplicate` without one is an error.

**Alert cross-reference — done.** `ServiceRequest.relatedAlert` links a report to the
disruption it concerns.

~~**Missing: update history.** The profile currently carries only *current state*
(`requestStatus`, `statusNote`, `dateModified`). There is no record of when a request moved
open → inProgress → closed, which is exactly what a resident wants to see and what any
service-level measurement needs.~~ Resolved as above.

**Emergency is a different direction, and should stay separate.**

| | Direction | Profile |
|---|---|---|
| Service request | inbound: resident → government | `requests` |
| Emergency alert | outbound: government → public | `alerts` (CAP) |

311 is non-emergency by definition — that is the whole point of the 311/911 split. Extending
`requests` to cover emergencies would merge two flows with different urgency, different
authority, and different audiences.

**The genuinely ambiguous middle is service disruption** — a water main break, a road closure.
The answer is that it is both: the disruption is an `alert`, reports about it are `requests`,
and the two should link. Worth an explicit cross-reference in both directions when `alerts` is
built.

---

## Publication path — **partly done**

**Verified.** `tools/check-context.py` serves the built site over local HTTP, rewrites the
`@context` to that origin, and parses fixtures **by fetching the context** rather than
inlining it - then asserts the result is isomorphic to the inlined parse. It is in
`npm run check` and CI. Two failure modes are covered and tested: a context missing from the
published site, and a *stale deploy* where the served context has drifted from the source
file. Before this, no test had ever exercised the path a real consumer takes.

**Still outstanding, and it needs you:**

- `schema.govfresh.com` does not resolve. Every fixture and both pilots declare
  `https://schema.govfresh.com/v1/context.jsonld` as their `@context`, so today a standard
  JSON-LD processor fails on all of them. DNS plus a deploy.
- The `Content-Type` GitHub Pages serves for `.jsonld` is still unverified. The local test
  server sends `application/ld+json` deliberately, so it isolates the document/context path
  rather than masking a MIME problem. If Pages serves `application/octet-stream`, strict
  processors will reject the context and it will look like a data fault. Test this
  immediately after the first deploy.

## JSON-LD audit — findings open

`tools/audit-jsonld.py` (`npm run audit:jsonld`) uses PyLD, the reference JSON-LD processor,
to check the class of fault that passes both validation tiers. It is wired into `npm run check` and CI now that its failures are resolved; the remaining
findings are warnings.

**Fixed while building it:**

- *A `@vocab` fix from the previous session was actively destroying data.* Nulling
  colliding term names inside a scoped context does **not** fall through to `@vocab` -
  JSON-LD treats an explicitly-null term as undefined and the value expands to `null`.
  rdflib tolerated it silently; PyLD raised `"@id" value must be a string`. Nine values
  (`department`, `title`, `code`, `budget`, `supplier`, `geo`, `buyer`, `catalog`, `org`)
  were being discarded. Each colliding token is now mapped explicitly to its full term IRI.
- *`amount` and `totalAmount` both expanded to `schema:amount`*, so a budget's total and a
  line's amount were indistinguishable in RDF. `totalAmount` is now `gs:totalAmount`,
  declared as a subproperty of `schema:amount`.

**Round-trip instability — RESOLVED.** Root cause was self-inflicted and one line wide: the
hardening step wrote a blanket list of colliding token names into *every* scoped context,
**including the property's own name**. A scoped context that redefines the term it is scoped
to replaces that term's `@type: @vocab` with a plain IRI, so inside its own scope the property
stopped expanding values as IRIs and they silently became literals. `role`, `result` and
`status` were affected - precisely the code-list properties whose names also appear as terms.

Scoped contexts are now generated from each property's **permitted values**, read from the
schemas and code lists, and explicitly never redefine their own term. `role`'s scoped context
went from 28 blanket entries to two real ones (`buyer`, `supplier`).

Bisecting this also showed the mechanism itself was never at fault: a property-scoped
`@vocab` expands correctly in both PyLD and rdflib. The isolated test passed while the real
context failed, which is what localised the bug.

**A second fault surfaced in the same pass and is also fixed:** `code.jsonld` used
`schema:about` for free-text subject keywords. `about` is typed `@id` because it normally
references entities, so the strings expanded as relative IRIs against the document base -
`file:///Users/.../gov-schema`, the same failure as the original `conformsTo` bug. Subject
keywords moved to `schema:keywords`.

**Code-list values — RESOLVED.** The thirteen missing code lists are written
(`AlertStatus`, `MessageType`, `Urgency`, `Severity`, `Certainty`, `AlertScope`,
`AccessRights`, `BudgetDirection`, `DecisionResult`, `ConformanceLevel`, `TenderStatus`,
`AwardStatus`, `ContractStatus`), taking the declared term count from 137 to 200. Every
value now resolves to a declared term, and the audit reports zero warnings.

The audit also learned that COFOG and GFSM are hierarchical: a subcode such as `04.5` whose
parent division is declared is correct rather than a gap. A subcode with no declared parent
still warns.

**Term dereferencing — RESOLVED.** Individual term IRIs used to 404. Published documents
expand `governmentLevel: "municipal"` into `.../v1/level/municipal`, and that pointed at
nothing on the live site. 229 term pages are now generated, one per declared term, and
`check-namespace.js` covers every one - 259 URLs checked, up from 46. A term that stops
resolving now fails the build.

**Note on check E's design.** rdflib's graph canonicalisation reports non-isomorphic for
graphs differing only in blank-node labelling when a document has many similar blank nodes.
The check compares a label-independent signature instead: ground triples exactly, blank nodes
by shape. The first implementation produced six false positives before this was corrected.

## Licence

Settled: **CC0 1.0** for the specification, vocabulary, schemas, code lists and examples;
**MIT** for the tooling. See [LICENSING.md](LICENSING.md).

The reasoning matters for adoption: an attribution licence on a vocabulary means every public
body publishing gov-schema data inherits an obligation, and a data-licensing question that has
to go past a lawyer is one that stops adoption. CC0 also answers the vendor-namespace
question directly — terms live under a GovFresh domain because it is maintained, not because
the vocabulary is owned.

## CAP adapter — DONE

`tools/adapters/cap.py` converts the live NWS alerts API. Real CAP validated first time with
zero unmapped values, which is the strongest evidence yet for modelling on the incumbent
standard rather than inventing one.

One real defect: the profile required `references` on an update or cancel, but alert feeds are
windowed and ten of twenty-five updates superseded an alert already expired out of the active
feed. The only conformant option was downgrading `update` to `alert`, which turns "this
supersedes an earlier warning" into "this is a new warning". `referencesIdentifier` now
carries the CAP identifier of a superseded alert absent from the dataset.

**Sharpens the open geospatial question.** The profile references geometry by URL; NWS inlines
the polygon in the same document. The adapter links to the alert's own endpoint, which is a
workaround rather than a mapping. A publisher that inlines geometry currently has nowhere to
put it. See [examples/pilot-nws-alerts/README.md](examples/pilot-nws-alerts/README.md).

## Eurostat COFOG adapter — DONE

`tools/adapters/eurostat-cofog.py` converts Eurostat general government expenditure by
function. Ireland 2022: 79 lines across 10 COFOG divisions.

One defect, the same shape as the UK Contracts Finder finding: the budget arithmetic check
demanded exact equality between a parent line and the sum of its parts, which **no statistical
publisher can satisfy**. Four of ten Irish divisions failed by 0.002% - rounding, because
Eurostat reports in millions to one decimal place. The check now infers the rounding unit from
the greatest common divisor of the amounts and allows half a unit per figure; real
discrepancies are still caught.

Deliberately not added: a precision or unit-multiplier field on `amount`. The granularity is
already recoverable from the data, so a declared field would restate what the numbers say and
add something a publisher can get wrong.

See [examples/pilot-eurostat-budget/README.md](examples/pilot-eurostat-budget/README.md).

## legislation.gov.uk adapter — DONE

`tools/adapters/legislation-uk.py` converts the UK statute book. Taxation of Pensions Act
2014: 11 parts, 122 sections.

**Confirms the FRBR claim in the source's own words.** legislation.gov.uk's Akoma Ntoso
carries FRBRWork, FRBRExpression and FRBRManifestation explicitly, which is precisely the
three levels the profile encodes. The Work URI is also what the adapter had independently
chosen as `@id`.

One defect: `legislationDateVersion` was read from `dc:modified` (2017-02-07) when the FRBR
Expression date is 2016-09-15 — eighteen months apart. `dc:modified` is when the record was
touched; the Expression date is what the consolidated text is valid at. Getting it wrong means
citing a consolidation as current when it is not, the exact failure the field exists to
prevent.

**Still untested: the amendment graph.** The profile's most distinctive claim is that ELI's
six relations replace a blunt `supersedes`. This act's AKN carries no `textualMod` elements
and `/changes/affected/` returns HTML rather than data, so those relations remain unexercised.
The part of `code` most likely to be wrong is the part no public source has yet been able to
test. See [examples/pilot-uk-legislation/README.md](examples/pilot-uk-legislation/README.md).

## Open311 adapter — DONE

`tools/adapters/open311.py` converts a live Open311 GeoReport v2 endpoint. Bloomington,
Indiana: 60 requests, 63 services.

**The privacy opinion was right and aimed slightly wrong.** The field check that fails the
build on reporter-identifying columns never fired - Open311's GET response is clean by design,
with no email, name, phone or device id in 1,000 live requests. The real disclosure risk sat
where a field check cannot see: 736 of 1,000 requests carry 14 decimal places of latitude
alongside a street address, on complaints about unmown lawns at named addresses, and 13
descriptions contain a phone number or email written by the public.

Both were warned about in the profile README and neither was checked. They are now, as
warnings rather than errors, since neither is a schema violation and both need human
judgement. The adapter reduces coordinates to five decimal places by default, which clears
51 of 52; the remaining warning is free text, which cannot be fixed mechanically.

Also confirmed: `statusHistory` has no source in Open311, which carries current state only -
exactly why that gap was worth recording.
See [examples/pilot-bloomington-311/README.md](examples/pilot-bloomington-311/README.md).

## Socrata permits adapter — DONE

`tools/adapters/permits-socrata.py` converts building permits from two live Socrata portals,
chosen because they differ in exactly the way the profile's disclosure stance was written for:
Seattle publishes no applicant at all, Chicago publishes named private individuals at their
home addresses. Of 32 Chicago contacts typed OWNER, 17 are individual personal names published
unmasked alongside a residential street address.

**The optional-applicant decision is vindicated.** Had `applicant` been required, Seattle
could not have been represented at all, and every Chicago import would have carried a private
individual's name by default.

Two checks needed calibrating and one caught a real error. A Seattle permit is recorded as
issued 2010-03-17 and expiring 2008-10-24 - the check was right, and the adapter drops the
contradiction rather than passing it through. The completed-without-decision-date check was
too absolute: a record with all four dates null asserts nothing rather than asserting a
completion while hiding when, so partial dating is now an error and no dating a warning.

See [examples/pilot-seattle-permits/README.md](examples/pilot-seattle-permits/README.md).

## Democracy Club elections adapter — DONE

`tools/adapters/elections-democracyclub.py` converts UK election results. 2 May 2024: 5
elections, 40 contests, 292 candidates, 18 parties. Real results validated first time with no
schema change, and AMS mapped cleanly to mmp alongside first-past-the-post contests in the
same election.

**Every profile has now been tested against a real publisher.**

Two findings. A latent bug in six SHACL shapes, which listed the jurisdiction class as
AdministrativeArea or City only and omitted Country and State - it would have failed for any
national-level publisher, and surfaced here because this is the first pilot with a national
jurisdiction. And a design decision nearly reversed for the wrong reason: turnout was thought
unrepresentable because the electorate looked absent, but `total_electorate` is published and
had been misread. The original stance - store the register, derive turnout - is demonstrably
better, since Democracy Club rounds turnout to one decimal place and the register recovers the
real figure.

See [examples/pilot-uk-elections/README.md](examples/pilot-uk-elections/README.md).

## GOV.UK services adapter — DONE

`tools/adapters/services-govuk.py` converts GOV.UK services. 40 services from 15 departments.
GOV.UK does not use HSDS, which makes it a harder test than an Open Referral publisher: it
asks whether the profile can represent a catalogue built on entirely different assumptions.

**12 of 18 fields fill at 40/40; six fill at 0/40.** The six are not missing information -
they are information GOV.UK publishes as prose rather than as data. Processing time appears in
prose on 12 of 40 services, eligibility on 8, cost on 3, and none of them as a field. The
profile assumed publishers hold this structured; the best-organised government service
catalogue in the world does not. The adapter does not parse prose into structure, on the same
grounds the elections pilot declined to store a derived turnout figure.

`applicationProcess` being free text by design is what saved the conversion - it fills 40 of
40 while the structured fields sit empty.

One defect: every service was attributed to the Government Digital Service, because the
adapter preferred `primary_publishing_organisation` (who publishes the page) over
`organisations` (the department that owns the service). Corrected, the same 40 services
resolve to 15 real departments.

See [examples/pilot-govuk-services/README.md](examples/pilot-govuk-services/README.md).

## The honest risk

A profile set with one fictional example city is a demo, not an adopted standard. Profiles
eight through fifteen without a single real publisher would be building breadth on an untested
foundation.

What drives adoption is not more domains:

- **Adapters** from systems governments already run — Legistar/Granicus → `meetings`,
  Socrata/CKAN → `catalog`, existing Open311 endpoints → `requests`, OCDS publishers →
  `procurement`
- **A real pilot publisher, ideally non-US** — the fastest way to find where the international
  assumptions break
- **Validation as a service** — a design note with a recommendation is written up in
  [VALIDATOR.md](VALIDATOR.md). Note that "paste a URL" is measurably not achievable
  on static hosting: only three of six publishers this project already converts send
  CORS headers a browser would accept.
- **The SHACL and conformance work in section 0**

If one thing: `catalog` plus one adapter, because together they make the existing seven
profiles usable by someone other than their author.

---

## Suggested order

```
0. SHACL shapes + conformance-level checking     DONE
1. catalog                                        DONE
2. alerts                                         DONE
3. one adapter + one real pilot publisher         DONE (OCDS -> UK Contracts Finder)
4. permits                                        highest-volume records
5. elections                                      closes the org loop
6. tier two, reprioritised by what the pilot taught
```

Steps 0-3 are complete. The UK Contracts Finder pilot found two schema errors in minutes that
nine profiles of self-authored fixtures never surfaced - see
[examples/pilot-uk-contracts/README.md](examples/pilot-uk-contracts/README.md). More adapters
(CKAN, Open311, Legistar) would find more, and are worth more than new profiles.

**Confirmed by the pilot, not yet fixed:** real portals carry per-language titles
(`title_translated: {"en": ..., "ga": ...}` on data.gov.ie), an EU High Value Dataset category,
a spatial reference system (`srs`), and `applicable_legislation` linking a dataset to an ELI
URI - a `catalog` to `code` join this profile does not model. gov-schema currently carries a
single `name` plus `inLanguage`, which cannot represent a bilingual publisher.
