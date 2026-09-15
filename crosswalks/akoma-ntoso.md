# Akoma Ntoso and ELI crosswalk

schemaGov does not replace Akoma Ntoso. The two describe different layers of the same
document and are designed to be used together.

| Layer | Standard | What it carries |
|---|---|---|
| Bibliographic / relational | schemaGov `code` (schema.org + ELI) | What the law is, what it changes, who passed it, when it is in force, which file is authoritative |
| Textual / structural | Akoma Ntoso (OASIS LegalDocML) | The text itself: clauses, provisos, definitions, internal cross-references, amendment instructions |

They join at `encoding` → `LegislationObject`, whose `conformsTo` names the AKN namespace and
whose `contentUrl` points at the XML.

## ELI

schema.org's `legislation*` properties are derived directly from ELI, so the mapping is
near-identity.

| ELI | schemaGov |
|---|---|
| `eli:LegalResource` | `Legislation` (the work) |
| `eli:LegalExpression` / `eli:Format` | `LegislationObject` (the file) |
| `eli:date_document` | `legislationDate` |
| `eli:date_applicability` | `legislationDateOfApplicability` |
| `eli:version_date` | `legislationDateVersion` |
| `eli:in_force` | `legislationLegalForce` |
| `eli:amends` / `eli:repeals` / `eli:consolidates` | `legislationAmends` / `legislationRepeals` / `legislationConsolidates` |
| `eli:passed_by` | `legislationPassedBy` |
| `eli:id_local` | `legislationIdentifier` |

An ELI URI is a valid `legislationIdentifier`, and should be used where the jurisdiction
mints them.

## Akoma Ntoso

| AKN | schemaGov |
|---|---|
| `<akomaNtoso>` document | `LegislationObject` with `encodingFormat: application/akn+xml` |
| FRBR Work | `Legislation` |
| FRBR Expression | `LegislationObject` (language and version specific) |
| FRBR Manifestation | `LegislationObject` (`encodingFormat`) |
| `<act>`, `<bill>`, `<judgment>` | `legislationType` |
| `<body>`, `<chapter>`, `<section>` | `codificationLevel` at the level of a whole part; **not** the internal markup |
| `<hcontainer>`, `<blockList>`, `<mod>` | **no equivalent — out of scope** |

## Where publishers get this wrong

**Inventing a status field.** `legislationLegalForce` exists with a real enumeration.
`"status": "Active"` is not interoperable and is the most common error in hand-rolled
government schema.

**One blunt `supersedes` property.** ELI distinguishes amends, repeals, changes,
consolidates, corrects and commences, because they have different legal consequences.

**Publishing only a PDF with no `legislationLegalValue`.** A consumer cannot tell whether it
is the authoritative text or a convenience copy.

**Flattening the code hierarchy.** Use `isPartOf` / `hasPart` with `codificationLevel`; a
section detached from its chapter cannot be cited correctly.
