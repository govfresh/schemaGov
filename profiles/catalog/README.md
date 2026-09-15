# `catalog` profile — Discovery and data catalogue

**Status:** implemented · **Depends on:** `_core` · **Standard:** [DCAT](https://www.w3.org/TR/vocab-dcat-3/) / DCAT-AP · **schema.org:** `DataCatalog`, `Dataset`, `DataDownload`

## The gap this closes

Seven well-modelled profiles are useless if nobody can find the URLs. Before this profile,
**nothing in schemaGov told a consumer where a government's data lived** — you had to already
know, which means discovery happened by email.

## The manifest

`PublisherManifest` is served at **`/.well-known/schemaGov.json`** (RFC 8615) and is the only
document in schemaGov with a fixed, conventional location. Everything else is discovered
through it.

It declares who publishes, which jurisdiction they cover, which spec version they target,
what conformance level they claim, and — the important part — one `profileEndpoint` per
published profile with its URL and `dateModified`. That is a routing table: a consumer fetches
one well-known URL and knows everything, including what to poll and when it last changed.

The validator checks the manifest is at its conventional path and that no profile is declared
twice, because a duplicated routing entry is undiscoverable by any other means.

## The catalogue

`DataCatalog` and `Dataset` are DCAT-aligned. DCAT is the international standard here —
DCAT-AP across the EU, DCAT-US in the States, and the basis of most national open-data portals
— and schema.org `DataCatalog` is what **Google Dataset Search consumes**. So this projection
has a real consumer today rather than a hypothetical one.

`conformsToProfile` links a catalogue entry to the schemaGov profile it serves. That is the
bridge that matters: someone arriving through an open-data portal finds the structured data,
not just a CSV export of it. The fixtures show a budget dataset offering three distributions —
the schemaGov profile, the Fiscal Data Package, and a CSV — which is exactly the layering
SPEC §1.4 asks for.

## Two fields worth insisting on

**`updateFrequency`** (DCAT `dct:accrualPeriodicity`). A dataset with no stated cadence cannot
be told apart from an abandoned one, and most open-data portals are full of both.

**`accessRights`**. Publishing metadata about restricted data is legitimate and useful.
Publishing it without saying the data is restricted is not.

## Themes are adopted, not invented

`dataTheme` uses the EU data-theme vocabulary unchanged, because national portals across
Europe already tag with these codes. A new set of themes would fragment what is already
aligned — the same reasoning that made COFOG the right choice in `budget`.
