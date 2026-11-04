# `budget` profile — Budgets and spending

**Status:** implemented · **Depends on:** `_core`, `code`, `meetings` · **Source standard:** [Fiscal Data Package](https://specs.frictionlessdata.io/fiscal-data-package/), [COFOG](https://unstats.un.org/unsd/classifications/Family/Detail/4), [GFSM 2014](https://www.imf.org/external/pubs/ft/gfs/manual/2014/gfsfinal.pdf)

## schema.org has nothing here

No budget, no fiscal, no expenditure, no appropriation — the words do not appear in the
vocabulary. `MonetaryAmount` is a value type (a number and a currency), not a model, and
`MonetaryGrant` is about grants awarded, not money appropriated.

So this profile mints `gs:Budget` and `gs:BudgetLine` outright and mirrors the **Fiscal Data
Package**, which stays the source model per SPEC §1.4. Publish the FDP itself in
`distribution`; this projection exists for discovery and for joining the budget to the
organization, meeting, and legislation that produced it.

## Budget phase is the field everyone omits

**A budget figure without its phase is not comparable to any other figure.** Proposed,
approved, adjusted, and executed are four different numbers for the same line, and a
publisher who ships "the budget" without saying which one has published something that cannot
be used.

`budgetPhase` is therefore required on every Budget. `supersedes` links a phase to the one it
revises, and both are retained — comparing a proposal against what was actually approved, and
approved against what was actually spent, is most of what budget transparency is for.

## Direction, and why a bare amount is useless

Every line is `revenue`, `expenditure`, or `financing`. Without it an amount cannot be
interpreted at all: 41,200,000 is meaningless until you know whether it is money coming in or
going out. Required, no default.

## Three classifications, doing different jobs

| Dimension | Standard | Answers |
|---|---|---|
| `functionalClassification` | **COFOG** (UN) | *What is the money for?* Health, education, public order. |
| `economicClassification` | **GFSM 2014** (IMF) | *What kind of transaction?* Salaries, goods, interest, capital. |
| `administrativeClassification` | a `GovernmentOrganization` reference | *Who spends it?* |

COFOG is the one that makes this profile work internationally. Administrative structures
differ in every country and department names do not translate, but *"how much goes to health"*
is answerable anywhere. Both COFOG and GFSM are hierarchical: only the top level is
enumerated, and publishers may use full subcodes such as `04.5` or `07.3.1` as the value.

`administrativeClassification` points at an organization rather than carrying a department
name as text, so budget lines join directly to the `org` profile.

## Budget, line, program and fund

Four things, with different lifetimes:

- **Budget:** a government's financial plan for one period.
- **BudgetLine:** one amount, or one grouping, within one budget.
- **Program:** a persistent activity that appears in many budgets (next section).
- **Fund:** a persistent financial account that appears in many budgets.

The organization, program and fund are durable. A line belongs to one budget.

## Funds: a durable entity, not a text value

A government tracks money by **fund**: a general fund, a building inspection fund, a road fund.
A fund has a number, an official name, a purpose, and a body responsible for it. It also appears in
many budgets over many years. A text value such as `"fundSource": "General Fund"` cannot carry any
of that, and cannot be joined to anything.

So there are two ways to say it, with different jobs:

| Property | Use it for |
|---|---|
| `fund` | A reference to a persistent `Fund` entity. |
| `fundSource` | The fund name as text from the source system, when there is no Fund entity to point at. |

Both stay valid, and a line may carry both. A simple dataset can keep using `fundSource`. Nothing
is removed.

```json
{
  "@id": "https://example.gov/id/fund/2080",
  "@type": "Fund",
  "name": "Building Inspection Fund",
  "identifier": [{"@type": "PropertyValue", "propertyID": "erp-fund-code", "value": "2080"}],
  "description": "A special revenue fund. Building permit fees pay into it, and it pays for inspections.",
  "administeredBy": {"@id": "https://example.gov/id/organization/community-development"}
}
```

A fund code is only unique inside the accounting system that issued it, so give `identifier` a
`propertyID`. The fund's `@id` is its own stable identity and does not change between fiscal years.

### What is durable and what belongs to one budget

```
Budget                                (one period)
  └── BudgetLine                      (one amount, in one budget)
        ├── administrativeClassification → GovernmentOrganization   (durable)
        ├── program                  → Program                      (durable)
        └── fund                     → Fund                         (durable)
```

The organization, the program and the fund last across budgets. A `BudgetLine` belongs to a single budget and
points at them. See `examples/example-gov/budget.jsonld`.

## Programs: the activity a budget pays for

A **program** is an ongoing activity a government organizes, runs or funds: Street Maintenance,
Adult Mental Health, Library Operations. It lasts for years. A budget line for it is written fresh
each fiscal year, so if the program were only a code on each line, there would be nothing that
stays the same across years.

| Property | Use it for |
|---|---|
| `program` | A reference to a persistent `Program` entity. |
| `programClassification` | The publisher's own program or activity code, as text, when there is no Program entity. |

Both stay valid, and a line may carry both. The Program has one `@id` for good. Its budget lines
in FY2026, FY2027 and FY2028 all point at it, so the three years can be followed as one thing.
A `Program` has a name and an optional description, identifiers and `administeredBy` (the
organization that runs it).

```
Public Works Department (organization)
   └── Street Maintenance (Program, administeredBy the department)
         ├── FY2026 BudgetLine ── program
         └── FY2027 BudgetLine ── program
```

### Program, Service and Project

| | What it is | Example |
|---|---|---|
| **Program** | An activity government organizes, manages, runs or funds. | Road Maintenance, Elections Administration |
| **Service** | Something a person or business can request, apply for or receive. | Apply for a building permit, get a library card |
| **Project** | Bounded work with an end. | Replace the Main Street bridge, rebuild a service |

An organization administers programs. A program may be delivered to the public through services.
Not every program is a service, and not every budget program should be published as one. A
program is also not an organization, even when a directory lists it under a department: a program
sits beside the organization tree, linked by `administeredBy`. schemaGov does not yet define a
direct link from a program to its services.

## Currency is required on every amount

Not inherited from the budget. Amounts get copied out of their document, and a figure that
silently assumes a currency is exactly how conversion errors happen. The validator rejects a
line whose currency differs from its budget's.

## Arithmetic is checked

`tools/validate.py` enforces two things that are arithmetic rather than opinion:

- a parent line must equal the sum of its `hasPart` children
- every line must use its budget's currency

It does **not** check whether the budget balances, because deficit budgets are legitimate.

## Coupling

`enactedAt` → the `Meeting` that adopted it; `legislation` → the appropriation ordinance in
the `code` profile. Combined with the meetings profile's vote records, the chain runs:
**budget → appropriation ordinance → meeting → agenda item → vote → each member's vote.**
