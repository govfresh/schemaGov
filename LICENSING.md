# Licensing

schemaGov is published under two licences, split by what the material is.

| Material | Licence |
|---|---|
| The specification, vocabulary, JSON Schemas, code lists, crosswalks, documentation and example data | [CC0 1.0 Universal](LICENSE) — public domain dedication |
| The tooling: `tools/`, `eleventy.config.js`, `_data/`, `_includes/`, `content/` | [MIT](LICENSE-CODE) |

## Why CC0 for the schema

A standard only works if adopting it is frictionless. **CC0 places the vocabulary in the
public domain**, so a government can use, adapt, translate, embed or fork it with no
attribution obligation, no licence compatibility analysis, and no legal review.

That last point is the practical one. An attribution licence on a vocabulary means every
public body publishing schemaGov data inherits an obligation, and a data-licensing question
that has to go past a lawyer is a question that stops adoption. The material a government
would actually reuse — the terms, the shapes, the classifications — carries no strings.

It also matches the surrounding ecosystem: the standards this profile builds on are freely
reusable, and several of them (COFOG, GFSM, CAP, OCDS, DCAT) are published by bodies whose
whole purpose is unrestricted reuse.

## Why MIT for the tooling

The validators, adapters and site are ordinary software. MIT is the least surprising choice,
keeps the warranty disclaimer that CC0 does not provide, and is what anyone vendoring
`tools/adapters/` into their own pipeline will expect.

## Attribution

CC0 asks for nothing, but attribution is welcome. schemaGov is maintained by
[GovFresh](https://govfresh.com) at `https://schema.govfresh.com`.

## The namespace is vendor-hosted, the vocabulary is not owned

Terms live under `https://schema.govfresh.com/v1/` because that domain is maintained rather
than because the vocabulary is proprietary. The dedication above is what makes that
distinction real: the namespace is an address, not a claim.

## Third-party material

The classifications this profile references remain the work of their publishers and are
referenced, not redistributed: COFOG (United Nations), GFSM 2014 (IMF), CPV (European Union),
UNSPSC, the EU data-theme vocabulary, org-id.guide, CAP (OASIS), OCDS (Open Contracting
Partnership), DCAT (W3C), Popolo, and Akoma Ntoso (OASIS). The `local:` identifier convention
exists precisely so a publisher's own register is never misrepresented as one of these.

Example data in `examples/example-city/` is fictional. Data in `examples/pilot-uk-contracts/`
and `examples/pilot-ie-datasets/` is derived from public open-government sources — UK
Contracts Finder and data.gov.ie — which publish under their own open terms; it is included
as conversion evidence, and those publishers remain the source of record.
