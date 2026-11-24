# Pilot — County of Marin Personnel Management Regulations (structure only)

**Real structure, no regulation text.** One regulation, PMR 27 (Telework Policy), from the County
of Marin's published Personnel Management Regulations, converted by hand and then reduced to its
structure. It tests the `policy` profile, which sits on the `code` profile.

Source: <https://www.hr.marincounty.gov/regulations-policies-procedures/personnel-management-regulations/all-personnel-management-regulations>

## What is included, and what is not

| Included | Left out on purpose |
|---|---|
| The manual, one group (Section 2), PMR 27 and its nine numbered provisions | The wording of every provision (`text`) |
| Identifiers, headings, order (`position`), levels, the `isPartOf`/`hasPart` tree | The regulation's purpose statement (`description`) |
| PMR 27's effective date (`2006-07-30`), PMR 23's partial date (`2005-01`) and revision numbers | Preparer and approver names, which the source gives as free text naming people |
| The three internal citations, as links | The other 26 regulations. PMR 23 appears only as a stub so a citation resolves |

The source's licence has **not** been checked, and this repo is CC0, so no regulation text is
committed. Headings and identifiers are short factual labels. The `@id`s are minted under the
county's domain for illustration, as the other pilots do; the county has not published them.
The full conversion, with text, was run outside the repo and is not part of schemaGov.

## Mapping

| Source | schemaGov |
|---|---|
| The manual | `Legislation`, `codificationLevel: code` |
| "Section 2" (a group of regulations) | `part`. The source's word "Section" is not the `section` level |
| "PMR 27" | `chapter` |
| "27.1" to "27.9" | `section` |
| Source page | `url` on the manual |

## What the stress test found

These come from converting the whole manual (27 regulations, 241 provisions, 26 definitions) and
are recorded here because they need a decision.

1. **Dates are often partial.** Of 26 effective dates given, 23 are a year and month (`2005-01`)
   and one is a two-digit-year string (`02-07-17`). The date properties required a full
   `YYYY-MM-DD`, which would force a guessed day. **Fixed:** `legislationDate`,
   `legislationDateOfApplicability` and `legislationDateVersion` now accept `YYYY`, `YYYY-MM` or
   `YYYY-MM-DD`, as the `statistics` profile does. PMR 23 here carries `2005-01`. `02-07-17` is
   still rejected: it is not an ISO date and its order (day, month, year or the reverse) is
   ambiguous, so the publisher must resolve it.
2. **`legislationType` is required on every node**, so each provision must carry one. The source
   labels them all regulations, so they carry `regulation`. Nothing is invented, but it is
   repeated on every provision.
3. **Tables** (2 in the manual) have no representation, as expected. They stay in the source.
4. **Two of 79 internal citations** could not be resolved to a PMR in the manual, so they stay
   as unresolved text rather than invented links.
