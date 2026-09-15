# Open Contracting Data Standard crosswalk

[OCDS](https://standard.open-contracting.org) remains the source model. schemaGov is a
schema.org projection for discovery and for joining contracts to budgets, organizations, and
the decisions that authorised them. Publishers should keep producing OCDS releases and
records.

## Structure

| OCDS | schemaGov |
|---|---|
| `ocid` | `ocid` — carried unchanged, including the publisher prefix |
| Record (compiled) | `ContractingProcess` |
| Release `tag` | not modelled; this profile projects the compiled record, not the release stream |
| `buyer` | `buyer` → a `_core` GovernmentOrganization reference |
| `parties[]` | `party[]` → `Party` references (non-government only) |
| `planning.budget` | `budgetLine[]` → `BudgetLine` references in the budget profile |

## Tender

| OCDS `tender` | schemaGov |
|---|---|
| `id` | `tenderId` |
| `title` / `description` | `title` / `description` |
| `status` | `status` |
| `procurementMethod` | `procurementMethod` |
| `procurementMethodDetails` | `procurementMethodDetails` |
| `procurementMethodRationale` | `procurementMethodRationale` |
| `mainProcurementCategory` | `mainProcurementCategory` |
| `items[].classification` | `classification[]` as scheme-qualified `PropertyValue` (CPV, UNSPSC, NIGP) |
| `value` | `value` → `MonetaryAmount` |
| `procuringEntity` | `procuringEntity` |
| `tenderPeriod.startDate` / `.endDate` | `tenderPeriodStart` / `tenderPeriodEnd` |
| `enquiryPeriod.endDate` | `enquiryPeriodEnd` |
| `numberOfTenderers` | `numberOfTenderers` |
| `documents[]` | `document[]` |

## Award and contract

| OCDS | schemaGov |
|---|---|
| `awards[].id` | `awardId` |
| `awards[].status` / `date` / `value` | `status` / `date` / `value` |
| `awards[].suppliers[]` | `supplier[]` → Party references |
| `awards[].contractPeriod` | `contractPeriodStart` / `contractPeriodEnd` |
| `contracts[].id` | `contractId` |
| `contracts[].awardID` | `awardId` — validated against the awards in the process |
| `contracts[].dateSigned` | `dateSigned` |
| `contracts[].period` | `periodStart` / `periodEnd` |
| `contracts[].implementation.transactions[]` | `amountPaid` (aggregated) |

## Parties and identifiers

OCDS identifies organizations with `identifier.scheme` + `identifier.id`, where scheme comes
from the [org-id.guide](https://org-id.guide) register. schemaGov carries the same pair as
`propertyID` + `value` on a `PropertyValue`, so the mapping is mechanical:

```
OCDS        {"scheme": "US-EIN", "id": "84-3921776"}
schemaGov  {"@type": "PropertyValue", "propertyID": "org-id:US-EIN", "value": "84-3921776"}
```

## Deliberate differences

**Government participants are not parties.** OCDS puts every organization in `parties[]`.
schemaGov references `_core` GovernmentOrganizations for the buyer and procuring entity
instead, so a department is not simultaneously an org-chart entity and a procurement party
with separate identifiers.

**Transactions are aggregated.** OCDS `implementation.transactions[]` is a payment ledger.
This profile carries `amountPaid` only; publish the full ledger in OCDS.

**Releases are not modelled.** OCDS distinguishes releases (events) from records (compiled
state). This profile projects the compiled record. Consumers needing the audit trail of
changes should read the OCDS release stream.
