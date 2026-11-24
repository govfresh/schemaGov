# `policy` profile — Policies, regulations and procedures

**Status:** implemented · **Depends on:** `_core`, `code` · **Source standard:** [schema.org](https://schema.org/Legislation) (ELI-derived legislation vocabulary)

A government's own policies, administrative regulations, procedures and directives are
structured the same way as its law: a manual divided into groups, groups into regulations,
regulations into numbered provisions that nest as deep as the source nests them. So this
profile does **not** define a second legal-document model. It reuses the `code` profile and
adds only what a policy needs that a municipal code does not.

## Decision: reuse `code`, do not parallel it

| Need | How it is modelled |
|---|---|
| A policy manual, a group, a regulation, a provision | `Legislation`, told apart by `codificationLevel` |
| What kind of document | `legislationType`: `policy`, `procedure`, `regulation`, `directive` |
| Nesting to any depth | `isPartOf` (canonical) and `hasPart`, never the shape of an `@id` |
| Order among siblings | `position`. `hasPart` is an unordered set |
| The wording | `text`, exactly as the source states it |
| A provision's number or label | `legislationIdentifier` (`27.2`, `(a)`) |
| Approval, preparation, publication | `legislationPassedBy`, `legislationCountersignedBy`, `creator`, `publisher` |
| Adopted / effective / revised | `legislationDate` / `legislationDateOfApplicability` / `legislationDateVersion` |
| Revision number | `version` |
| Source document | `url`, and `encoding` → `LegislationObject` |
| Internal and external references | `citation` |
| A definition | `DefinedTerm` in a `DefinedTermSet`, linked to its provision by `subjectOf` |

Policies are not statutes, and `Legislation` is schema.org's closest typed work. The `code`
profile already uses it for ordinances and resolutions; `legislationType` is what tells a
policy from a statute.

## Mapping a source onto levels

Map by **role**, not by the source's own word for it. A source that calls its top-level
groups "Section 4" has a group, which is `part`, not a `section`. The source's label stays
in `name` and `legislationIdentifier`.

| Role | `codificationLevel` |
|---|---|
| The manual | `code` |
| A group of related regulations | `part` |
| One policy or regulation | `chapter` |
| A numbered provision | `section` |
| Its sub-parts, however deep | `subsection`, `paragraph` |

Levels are never required to appear in order, and the profile does not cap depth: a
provision's parent is whatever `isPartOf` says.

## Rules this profile adds

- **A provision needs a `name` or a `legislationIdentifier`.** Many provisions have no
  heading. Do not invent one.
- **Jurisdiction is declared on the top-level work.** A part with `isPartOf` may omit
  `legislationJurisdiction` and inherits it from its parent. The validator checks that every
  chain ends at a node that declares one.
- **Preserve the authoritative text.** No summaries, no derived fields such as a deadline in
  days or an eligibility flag.
- **Never invent a URL for an unresolved citation.** `citation` takes `{"@id": ...}` for a
  structured entity you can point at, or the citation as a string. The context does not
  coerce `citation`, so the two coexist.
- **Do not infer dates, authorities or relationships the source does not state.**

## What this profile adds

One schema, `definition.schema.json`, for `DefinedTerm` and `DefinedTermSet`, plus two terms
(`policy`, `procedure`) in the `code` profile's `LegislationType` list. It adds no `gs:`
vocabulary. `legislation.schema.json` gained `text`, `version`, `creator`, `publisher`,
`citation` and `legislationCountersignedBy`, all optional and all real schema.org properties.

## Tables and markup

Tables, inline cross-reference anchors and other markup are not modelled. This follows the
`code` profile's boundary: the addressable numbered units are structured here; what is inside
them is the source's. Keep the whole source file as an `encoding` `LegislationObject`
(`text/html`, with a real `contentUrl`) and give it `legislationLegalValue`, so a consumer
can reach the original table.

## Deliberately not modelled

Obligations, permissions, prohibitions, deadlines, eligibility rules, workflows and
responsible actors. Those are interpretation, not source structure, and belong in a later
extension.

## Example

[`examples/example-gov/policy.jsonld`](../../examples/example-gov/policy.jsonld) — a
fictional manual with a group, two regulations, provisions nested four levels deep, a
definition, and internal, external and unresolved citations.
