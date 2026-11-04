# `services` profile — Service catalogue

**Status:** implemented · **Depends on:** `_core`, `code`, `budget` · **Standard:** [Open Referral / HSDS](https://docs.openreferral.org) · **schema.org:** `GovernmentService`, `PeopleAudience`, `ServiceChannel`

## The gap this fills

`requests` covers **reporting a problem**. Nothing covered **finding a service** — *how do I
get a birth certificate, register a business, apply for housing support* — which is the most
common thing anyone asks a government website.

## What schema.org already gives

More than expected. `PeopleAudience` carries `requiredMinAge`, `requiredMaxAge`,
`geographicArea` and `audienceType`, which covers much of HSDS eligibility without minting.
`ServiceChannel` carries how to reach a service and `processingTime`. `GovernmentService`
itself is real.

What it has nothing for is the part residents actually need: **how to apply, what to bring,
what it costs, and whether the service still exists.** Those are minted.

## Life events

`lifeEvent` is the field that makes a catalogue usable. **People look for services by what is
happening to them** — having a baby, losing a job, moving home — not by the department that
happens to run them. The EU Single Digital Gateway organises services this way for the same
reason.

It is also the part that travels. The department that issues a birth certificate differs in
every country; the fact of a birth does not.

## Three fields that decide whether a listing is useful

**`applicationProcess`.** A service described without it is a listing rather than a route to
anything. HSDS treats it as central and so does this profile.

**`requiredDocument`.** The single most common reason an application fails at the counter.
`optional: true` marks documents with an accepted alternative.

**`cost.waiverAvailable`.** Publishing a fee without saying a waiver exists deters exactly the
people the waiver is for. `free: true` is stated explicitly rather than by omission, because an
absent cost reads as unknown rather than as nil.

## `serviceStatus` is optional at Core, required at Standard

HSDS distinguishes `defunct` from `temporarilyClosed` because a resident needs to know whether
coming back later is worth it.

But requiring it would make every Open311 service catalogue unrepresentable — Open311 has no
status field, as the Bloomington pilot confirmed across 63 services. That is the `areaServed`
and `procurementMethod` lesson, so it sits at Standard conformance instead: real data can be
represented at Core, and a listing claiming Standard must be able to say whether the service
still exists.

## `ServiceAtLocation` is a join, not a field

A service and a location are independent: one office delivers many services, one service runs
from many offices, and the opening hours belong to the pairing rather than to either alone.
HSDS models this as a separate entity and so does this profile.

## A service is not a program

A **service** is something a person or business can request, apply for, receive or complete:
apply for a building permit, get a library card. A **program** (`gs:Program`, in the `budget`
profile) is an activity a government organizes, runs or funds: Road Maintenance, Library
Operations. Programs appear in budgets. Services appear in this catalogue. Conceptually an
organization administers a program, and a program may be delivered through services.

Do not publish every budget program as a `GovernmentService`. Most programs, like street
maintenance, are not something a resident applies for. This profile does not define a program to
service link yet. See `profiles/budget/README.md`.

## Relationship to `requests`

Both profiles describe `schema:GovernmentService`. **This is the canonical, fuller
definition**; `requests/service.schema.json` describes the same type at the depth Open311
needs — a service code and its form attributes — and remains published for interoperability.
A publisher serving both should use this one. The validator treats the `services` definition
as canonical and it is a superset, so anything valid against the `requests` view is valid
against this.
