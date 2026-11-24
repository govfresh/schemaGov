# Policy and regulation crosswalk

schemaGov has no policy-specific document model. A policy manual, a group of regulations, a
regulation and a provision are all `Legislation`, as in the `code` profile. This table shows
how each thing a policy document contains lands on existing vocabulary.

| Concept | schemaGov | schema.org | Gap | Recommendation |
|---|---|---|---|---|
| Policy manual | `Legislation`, `codificationLevel: code` | `Legislation` | none | reuse |
| Group of regulations | `codificationLevel: part` | `hasPart` | none | reuse |
| Policy / regulation / procedure | `legislationType`: `policy`, `regulation`, `procedure`, `directive` | `legislationType` | `policy`, `procedure` missing from list | add two terms |
| Provision, nested | `codificationLevel: section` and below, `isPartOf`, `position` | `hasPart`, `isPartOf`, `position` | levels, if the source needs more | reuse; add a level only on evidence |
| Wording | `text` | `text` | not in schema file | add to schema |
| Number or label | `legislationIdentifier` | `legislationIdentifier` | none | reuse |
| Jurisdiction | `legislationJurisdiction` → core | `legislationJurisdiction` | was required on every node | top-level only |
| Issuing organization | `publisher` | `publisher` | not in schema file | add to schema |
| Approving authority | `legislationPassedBy`, `legislationCountersignedBy` | same | none | reuse |
| Prepared by | `creator` | `creator` | not in schema file | add to schema |
| Adopted | `legislationDate` | `legislationDate` | none | reuse |
| Effective | `legislationDateOfApplicability` | `legislationDateOfApplicability` | none | reuse |
| Revised | `legislationDateVersion` | `legislationDateVersion` | none | reuse |
| Revision number | `version` | `version` | not in schema file | add to schema |
| In force | `legislationLegalForce` | `legislationLegalForce` | none | reuse |
| Source document | `url`, `encoding` → `LegislationObject` | same | none | reuse |
| Definition | `DefinedTerm` in a `DefinedTermSet` | `DefinedTerm`, `DefinedTermSet` | no schema, no link to source | `definition.schema.json`, `subjectOf` |
| Reference, resolvable | `citation` → `{"@id"}` | `citation` | none | reuse |
| Reference, unresolved | `citation` as a string | `citation` | none | reuse; no invented IRI |
| Table | none | none | real gap | keep in the source `LegislationObject` |
| Obligations, deadlines, eligibility | none | none | out of scope | deferred |

## Where publishers get this wrong

**Using `legislationDate` for the effective date.** It is the date of adoption or signature.
The date a text takes effect is `legislationDateOfApplicability`.

**Reading the source's word for a level as the level.** A manual whose top-level groups are
called "Section 4" has groups, not sections. Map by role.

**Inventing a heading or a URL.** A provision with no heading is identified by its number. A
citation that cannot be resolved stays text.

**Repeating the jurisdiction on every provision.** Declare it once on the top-level work.
