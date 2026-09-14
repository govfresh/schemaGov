# Design note — a browser validator

**Status:** proposal, not implemented. The last unticked adoption item in
[ROADMAP.md](ROADMAP.md).

---

## The problem

Twelve profiles, thirty-seven schemas and a validation suite that has caught fifteen real
defects across ten publishers — and to run any of it you must clone the repository and install
Python, Node, `jsonschema`, `referencing`, `pyshacl`, `rdflib` and `PyLD`.

That is a reasonable ask of a contributor and an unreasonable one of a city clerk with a
JSON file. **The work is documented but not usable**, and everything else in the adoption list
is done.

## What can actually run in a browser

The suite is six gates. They do not port equally.

| Gate | In a browser? |
|---|---|
| `check-namespace.js` | **N/A** — checks the built site, not user data |
| `check-context.py` | **Yes** — our context sends `Access-Control-Allow-Origin: *` |
| `audit-jsonld.py` | **Yes** — JSON-LD expansion, given a processor |
| `validate.py` | **Yes** — the core: shape, references, domain rules, conformance |
| `shacl.py` | **Only via a Python runtime** — no mature JS SHACL engine handles `sh:sparql` |
| pilot validation | **N/A** — CI concern |

`validate.py` is the one that matters. It is 705 lines carrying **41 distinct error and
warning emissions across 13 rule groups** — reporter privacy, budget arithmetic, contract
integrity, permit date sequences, election tallies, boundary validity, conformance levels.
That is the part with no schema equivalent, and the part that has found the most real defects.

## The central decision: how not to build it twice

A JavaScript reimplementation of those 41 rules would be fast and small, and it would
**drift**. The entire discipline of this project is anti-drift: documentation generated from
schemas, term pages generated from code lists, a namespace check that fails the build, an
audit that catches context faults both other tiers miss. Hand-maintaining the same rules in
two languages contradicts all of it, and the drift would be silent — a browser saying "valid"
where CI says otherwise is worse than no browser validator.

| Option | Parity | Cost |
|---|---|---|
| Reimplement in JS | drifts by construction | small bundle, fast |
| **Run the Python via WASM** | **exact — same code CI runs** | ~10MB, seconds to start |
| Extract rules to declarative data | exact, if the extraction is total | large refactor, and not all 41 rules are declarative |
| Serverless endpoint | exact | leaves static hosting, adds an operator |

**Recommended: run the actual Python in the browser via Pyodide.**

The deciding evidence is that **every dependency is pure Python** — verified, no native
extensions in `jsonschema`, `referencing`, `rdflib`, `pyshacl` or `PyLD`. All five install
under `micropip`. That means the browser runs `validate.py`, `shacl.py` and `audit-jsonld.py`
**unchanged**, including SHACL, which no JavaScript path could offer.

The cost is real: roughly ten megabytes and a few seconds of cold start. For a tool used
occasionally, deliberately, on a file someone is about to publish, that is an acceptable
trade for never being wrong about whether the answer matches CI.

## "Paste a URL" does not work, and the plan should say so

The obvious interface is a URL box. Measured against the publishers this project already
converts:

| Publisher | `Access-Control-Allow-Origin` |
|---|---|
| `schema.govfresh.com` | `*` |
| NWS alerts | `*` |
| GOV.UK content API | `*` |
| data.gov.ie | restricted to another origin |
| UK Contracts Finder | none |
| Legistar | none (and 403) |

**Three of six.** A browser cannot fetch the others; no header, no read. Fixing it needs a
proxy, which needs a server, which is the thing static hosting avoids.

So: **paste and file-upload are the primary inputs**, and URL fetching is offered as a
best-effort extra that says plainly when the publisher's server refuses. Advertising "paste a
URL" as the headline would fail for the majority of real sources — including two this project
has pilots for.

## The property worth advertising instead

**The document never leaves the browser.** Static hosting plus client-side execution means
there is no upload, no server log, no retention.

That matters more here than it would elsewhere. This project has spent real effort on
disclosure risk — reporter privacy in `requests`, optional applicants in `permits`,
coordinate rounding, the individual-name omission in the Chicago pilot. A validator that asked
publishers to upload unreviewed data to a third party in order to check it for privacy
problems would be self-defeating.

## What it should report

Not a boolean. The suite already produces something better, and the adapters established the
format:

- **Conformance level reached** — Core, Standard or Extended, computed rather than claimed
- **Errors** with the entity and the reason, as the CLI prints them
- **Warnings** separately — the disclosure risks and rounding notes that need judgement
- **Field coverage per profile**, as the GOV.UK pilot reports it. Knowing that 12 of 18
  fields are populated is more actionable than "valid", and it is what turns the tool from a
  gate into guidance.

## Phasing

1. **Shape and references only.** Pyodide, `jsonschema`, `validate.py` with SHACL skipped.
   Proves the runtime and the load time before committing to the rest.
2. **Full suite.** Add `rdflib`, `pyshacl`, `PyLD`; SHACL and the JSON-LD audit come with them
   at no extra design cost.
3. **Coverage report and conformance ladder**, presented as guidance rather than a verdict.
4. **URL input**, best-effort, with an honest failure message naming CORS as the cause.

Stopping after phase 1 still delivers most of the value.

## Open questions

1. Is a ~10MB download acceptable for the audience, or does phase 1 need a lightweight
   shape-only path in JS for a fast first answer, accepting drift on that path alone?
2. Should the validator accept a whole directory of documents, as the CLI does, since
   reference integrity across files is where a third of the defects were found?
3. Should it offer a copyable CI snippet once a document validates, so a publisher can move
   from checking once to checking continuously?

Question 1 is the real one. Everything else follows from it.
