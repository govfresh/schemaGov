# DCAT crosswalk

[DCAT](https://www.w3.org/TR/vocab-dcat-3/) (W3C) is the source model for the `catalog`
profile. DCAT-AP (EU) and DCAT-US are national profiles of it; both crosswalk through this
table.

## Catalogue and dataset

| DCAT | schemaGov | schema.org |
|---|---|---|
| `dcat:Catalog` | `Catalog` | `DataCatalog` |
| `dcat:Dataset` | `Dataset` | `Dataset` |
| `dcat:Distribution` | `distribution[]` | `DataDownload` |
| `dct:title` | `name` | `name` |
| `dct:description` | `description` | `description` |
| `dct:publisher` | `publisher` → an organization reference | `publisher` |
| `dct:creator` | `creator` | `creator` |
| `dcat:keyword` | `keywords` | `keywords` |
| `dcat:theme` | `dataTheme` (EU data-theme vocabulary) | — |
| `dct:issued` | `datePublished` | `datePublished` |
| `dct:modified` | `dateModified` | `dateModified` |
| `dct:accrualPeriodicity` | `updateFrequency` | — |
| `dct:accessRights` | `accessRights` | — |
| `dct:spatial` | `spatialCoverage` → a Jurisdiction reference | `spatialCoverage` |
| `dct:temporal` | `temporalCoverage` | `temporalCoverage` |
| `dct:license` | `license` | `license` |
| `dct:language` | `inLanguage` | `inLanguage` |
| `dcat:contactPoint` | `contactPoint` | `contactPoint` |
| `dcat:downloadURL` | `distribution[].contentUrl` | `contentUrl` |
| `dcat:accessURL` | `distribution[].accessUrl` | — |
| `dcat:mediaType` | `distribution[].encodingFormat` | `encodingFormat` |
| `dcat:byteSize` | `distribution[].contentSize` | `contentSize` |
| `dcat:inCatalog` | `includedInDataCatalog` | `includedInDataCatalog` |

## Deliberate differences

**`dct:spatial` is a reference, not a string.** DCAT commonly carries a geographic name or a
URI from an external gazetteer. schemaGov points at a `_core` Jurisdiction, so a dataset
joins directly to the organization publishing it and the territory it covers.

**`conformsToProfile` has no DCAT equivalent.** It names the schemaGov profile a dataset
serves, which is what links an open-data catalogue entry to structured data rather than to a
flat export.

**The manifest is not DCAT at all.** `PublisherManifest` at `/.well-known/schemaGov.json` is
a schemaGov addition. DCAT describes catalogues but says nothing about how to *find* one;
that gap is why the manifest exists.

## Note on Google Dataset Search

schema.org `Dataset` is consumed directly by Google Dataset Search. Publishers already
emitting DCAT get this projection nearly free, and it is the fastest route to a dataset being
findable outside the government's own portal.
