#!/usr/bin/env python3
"""Validate schemaGov instance documents.

Two independent checks:

  1. Shape      - each entity against its JSON Schema. Needs `pip install jsonschema`;
                  skipped with a notice if absent.
  2. References - every {"@id": ...} points at an entity that actually exists in the
                  document set, and no entity is declared twice. This is the check that
                  matters most here: the profile forbids inlining copies of entities, so
                  a dangling reference is the characteristic failure mode.

Usage:  python3 tools/validate.py [examples/example-city ...]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "profiles" / "_core" / "schema"
PROFILE_DIRS = [ROOT / "profiles" / d / "schema" for d in ("_core", "org", "code", "meetings", "requests", "budget", "procurement", "catalog", "alerts", "permits", "elections", "services")]

# @type -> schema file. Roles are validated where they are nested, not standalone.
SCHEMA_FOR = {
    "AdministrativeArea": "jurisdiction.schema.json",
    "Country": "jurisdiction.schema.json",
    "State": "jurisdiction.schema.json",
    "City": "jurisdiction.schema.json",
    "GovernmentOrganization": "organization.schema.json",
    "Person": "person.schema.json",
    "Boundary": "boundary.schema.json",
    "GovernmentBuilding": "facility.schema.json",
    "CityHall": "facility.schema.json",
    "LegislativeBuilding": "facility.schema.json",
    "Courthouse": "facility.schema.json",
    "Embassy": "facility.schema.json",
    "DefenceEstablishment": "facility.schema.json",
    "CivicStructure": "facility.schema.json",
    "EventVenue": "facility.schema.json",
    "Post": "post.schema.json",
    "DataFeed": "directory.schema.json",
    "Legislation": "legislation.schema.json",
    "Meeting": "meeting.schema.json",
    "EventSeries": "meeting.schema.json",
    "ServiceRequest": "service-request.schema.json",
    # services/ carries the canonical GovernmentService; both files define the
    # same type and services/ is the superset.
    "GovernmentService": "service.schema.json",
    "Budget": "budget.schema.json",
    "BudgetLine": "budget-line.schema.json",
    "ContractingProcess": "contracting-process.schema.json",
    "Organization": "party.schema.json",
    "PublisherManifest": "manifest.schema.json",
    "DataCatalog": "catalog.schema.json",
    "Dataset": "dataset.schema.json",
    "Alert": "alert.schema.json",
    "GovernmentPermit": "permit.schema.json",
    "Election": "election.schema.json",
    "Contest": "contest.schema.json",
    "PoliticalParty": "political-party.schema.json",
}


def load_graph(paths):
    """Return (entities, sources) for every top-level node across the given files."""
    entities, sources = {}, {}
    dupes = []
    for path in paths:
        doc = json.loads(path.read_text())
        nodes = doc.get("@graph", [doc])
        for node in nodes:
            nid = node.get("@id")
            if not nid:
                continue
            if nid in entities:
                dupes.append((nid, sources[nid], path))
            entities[nid] = node
            sources[nid] = path
    return entities, sources, dupes


def collect_refs(node, path, out):
    """Every {"@id": ...} that is a reference rather than an entity declaration.

    A nested object whose only meaningful key is @id (plus display hints) is a
    reference; a nested object carrying real content is an inline entity.
    """
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "@id":
                continue
            if isinstance(val, dict) and "@id" in val:
                if set(val) <= {"@id", "@type", "name"}:
                    out.append((val["@id"], f"{path}.{key}"))
                else:
                    collect_refs(val, f"{path}.{key}", out)
            else:
                collect_refs(val, f"{path}.{key}", out)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            collect_refs(item, f"{path}[{i}]", out)


def main(argv):
    targets = argv[1:] or ["examples/example-city"]
    paths = []
    for t in targets:
        p = ROOT / t
        paths.extend(sorted(p.glob("**/*.jsonld")) if p.is_dir() else [p])
    if not paths:
        print("no .jsonld files found")
        return 1

    entities, sources, dupes = load_graph(paths)
    errors, warnings, notes = [], [], []

    for nid, first, second in dupes:
        errors.append(f"duplicate @id {nid}\n    declared in {first} and {second}")

    # --- reference integrity -------------------------------------------------
    refs = []
    for nid, node in entities.items():
        collect_refs(node, nid, refs)
    for target, where in refs:
        if target not in entities:
            errors.append(f"dangling reference -> {target}\n    from {where}")

    # --- reporter privacy ----------------------------------------------------
    # Open311's POST payload carries the reporter's name, email, phone, device id
    # and account id. Those fields must not survive into published data. Documenting
    # that is not enough, so it is checked.
    PERSONAL_FIELDS = {
        "email", "telephone", "phone", "mobile",
        "firstname", "first_name", "lastname", "last_name",
        "deviceid", "device_id", "accountid", "account_id",
        "reportername", "reporter_name", "requestorname", "requestor_name",
        "requestername", "requester_name", "submittername", "submitter_name",
        "ipaddress", "ip_address", "reporter", "requestor", "requester", "submitter",
    }
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ServiceRequest" not in types_:
            continue
        for key in node:
            if key.lower().replace("-", "_").replace("_", "") in {
                f.replace("_", "") for f in PERSONAL_FIELDS
            }:
                errors.append(
                    f"reporter personal data in published request: {nid}\n"
                    f"    field '{key}' identifies the person who reported this. "
                    f"Strip it before publishing."
                )

    # --- budget arithmetic ---------------------------------------------------
    # A budget whose lines do not sum is worse than no budget: it looks
    # authoritative and is wrong. Two things are checked, both of which are
    # arithmetic rather than opinion. Whether a budget balances is NOT checked,
    # because deficit budgets are legitimate.
    def amount_of(node):
        a = node.get("amount") or {}
        return a.get("value"), a.get("currency")

    def reporting_granularity(nodes):
        """Infer the unit a publisher rounds to, from the amounts themselves.

        Statistical fiscal data is published at a stated precision - Eurostat reports
        COFOG in millions to one decimal place - so independently rounded children
        cannot sum exactly to an independently rounded parent. Demanding exact equality
        rejects every such publisher; four of Ireland's ten COFOG divisions failed by
        0.002%. The greatest common divisor of the amounts recovers the rounding unit
        without the publisher having to declare it.
        """
        from math import gcd
        vals = []
        for n in nodes:
            v, _ = amount_of(n)
            if isinstance(v, (int, float)) and v:
                scaled = round(abs(v) * 100)
                if scaled:
                    vals.append(scaled)
        if len(vals) < 2:
            return 1
        g = 0
        for v in vals:
            g = gcd(g, v)
        return max(g, 1) / 100

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]

        # 1. a parent line must equal the sum of its children
        if "BudgetLine" in types_ and node.get("hasPart"):
            parent_val, _ = amount_of(node)
            child_total, missing = 0, False
            for child in node["hasPart"]:
                c = entities.get(child.get("@id"))
                if not c:
                    missing = True
                    break
                cv, _ = amount_of(c)
                if cv is None:
                    missing = True
                    break
                child_total += cv
            if not missing and parent_val is not None:
                # Tolerance is half the rounding unit per figure, across the children
                # and the parent. Anything larger is a real discrepancy.
                unit = reporting_granularity(
                    [node] + [entities[c["@id"]] for c in node["hasPart"]
                              if c.get("@id") in entities])
                tolerance = unit * (len(node["hasPart"]) + 1) / 2
                if abs(child_total - parent_val) > tolerance:
                    errors.append(
                        f"budget line does not equal the sum of its parts: {nid}\n"
                        f"    parent {parent_val:,} but children total {child_total:,} "
                        f"(difference {parent_val - child_total:,}; "
                        f"rounding tolerance {tolerance:,.0f})"
                    )

        # 2. every line must use its budget's currency
        if "BudgetLine" in types_:
            _, cur = amount_of(node)
            b = entities.get((node.get("budget") or {}).get("@id"))
            if b and cur and b.get("currency") and cur != b["currency"]:
                errors.append(
                    f"currency mismatch: {nid}\n"
                    f"    line is {cur} but budget {b['@id']} is {b['currency']}"
                )

    # --- procurement integrity -----------------------------------------------
    # Contract data that does not tie together cannot be audited, and the specific
    # ways it fails to tie together are well known.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ContractingProcess" not in types_:
            continue

        awards = {a.get("awardId"): a for a in node.get("award", [])}
        party_ids = {p.get("@id") for p in node.get("party", [])}

        for contract in node.get("contract", []):
            aid = contract.get("awardId")

            # 1. every contract must trace to an award in the same process
            if aid not in awards:
                errors.append(
                    f"contract references an unknown award: {nid}\n"
                    f"    contract {contract.get('contractId')} cites awardId "
                    f"'{aid}', which is not an award in this process"
                )
                continue

            # 2. a contract worth more than its award is an unrecorded variation
            av = (awards[aid].get("value") or {}).get("value")
            cv = (contract.get("value") or {}).get("value")
            if av is not None and cv is not None and cv > av:
                errors.append(
                    f"contract exceeds its award: {nid}\n"
                    f"    contract {contract.get('contractId')} is {cv:,} but award "
                    f"{aid} is {av:,}. Record the variation on the award."
                )

            # 3. paying more than the contract is worth
            pv = (contract.get("amountPaid") or {}).get("value")
            if cv is not None and pv is not None and pv > cv:
                errors.append(
                    f"amount paid exceeds contract value: {nid}\n"
                    f"    contract {contract.get('contractId')} paid {pv:,} "
                    f"against a value of {cv:,}"
                )

        # 4. a supplier must be a declared party, or it cannot be joined to anything
        for award in node.get("award", []):
            for sup in award.get("supplier", []):
                if sup.get("@id") not in party_ids:
                    errors.append(
                        f"supplier is not a declared party: {nid}\n"
                        f"    award {award.get('awardId')} names {sup.get('@id')}, "
                        f"which is absent from this process's party list"
                    )

    # --- shape ---------------------------------------------------------------
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        # Register every schema under its $id so that relative $refs resolve the
        # way they will once published, not the way the repo happens to be laid out.
        resources = []
        for d in PROFILE_DIRS:
            for f in d.glob("*.schema.json"):
                contents = json.loads(f.read_text())
                resources.append((contents["$id"], Resource.from_contents(contents)))
        registry = Registry().with_resources(resources)

        checked = 0
        for nid, node in entities.items():
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            name = next((SCHEMA_FOR[t] for t in types if t in SCHEMA_FOR), None)
            if not name:
                notes.append(f"no schema mapped for @type {types} ({nid})")
                continue
            # Two profiles define service.schema.json for the same type; the
            # services/ definition is canonical because it is the superset.
            candidates = [d for d in PROFILE_DIRS if (d / name).exists()]
            base = next((d for d in candidates if d.parent.name == "services"), candidates[0])
            schema = json.loads((base / name).read_text())
            # format is annotation-only by default; dates and IRIs matter here.
            v = Draft202012Validator(
                schema,
                registry=registry,
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            )
            for e in sorted(v.iter_errors(node), key=lambda e: list(e.path)):
                loc = "/".join(str(x) for x in e.path) or "(root)"
                errors.append(f"{nid}\n    {loc}: {e.message}")
            checked += 1
        notes.append(f"shape-checked {checked} entities against {len(SCHEMA_FOR)} schemas")
    except ImportError:
        notes.append("shape check SKIPPED - pip install jsonschema referencing")

    # --- alerts ---------------------------------------------------------------
    # A malformed warning is worse than no warning: it either fails to reach people
    # or fails to stop reaching them.
    from datetime import datetime

    def parse_dt(v):
        try:
            return datetime.fromisoformat(str(v))
        except (ValueError, TypeError):
            return None

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "Alert" not in types_:
            continue

        if node.get("messageType") in ("update", "cancel") \
                and not node.get("references") and not node.get("referencesIdentifier"):
            errors.append(
                f"alert '{node.get('messageType')}' does not say what it supersedes: {nid}\n"
                f"    set references, or referencesIdentifier where the superseded alert is\n"
                f"    outside the published window. Without either, consumers show the old\n"
                f"    and new alert side by side."
            )

        sent = parse_dt(node.get("sent"))
        for info in node.get("alertInfo", []):
            expires = parse_dt(info.get("expires"))
            if sent and expires and expires <= sent:
                errors.append(
                    f"alert expires before it was sent: {nid}\n"
                    f"    sent {node.get('sent')}, expires {info.get('expires')} "
                    f"({info.get('inLanguage')})"
                )

    # --- service request disclosure risk ---------------------------------------
    # The field check above catches reporter-identifying COLUMNS. Real 311 data shows
    # the residual risk is not in fields at all: of 1,000 live Bloomington requests,
    # 736 carried 14 decimal places of latitude alongside a street address, and 13
    # descriptions contained a phone number or an email address written by the public.
    # Neither is a schema violation, so both warn rather than fail.
    COORD_PRECISION_LIMIT = 5          # about a metre; finer locates a household
    CONTACT_IN_TEXT = re.compile(
        r"[\w.+-]+@[\w-]+\.[\w.]+"                    # email
        r"|\b(?:\+?\d[\d ().-]{7,}\d)\b"             # phone-like run of digits
    )

    def _decimals(v):
        s = str(v)
        return len(s.split(".")[1]) if "." in s else 0

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ServiceRequest" not in types_:
            continue

        geo = node.get("geo") or {}
        street = (node.get("address") or {}).get("streetAddress")
        if geo.get("latitude") is not None and street:
            dp = max(_decimals(geo.get("latitude")), _decimals(geo.get("longitude")))
            if dp > COORD_PRECISION_LIMIT:
                warnings.append(
                    f"{nid}: {dp} decimal places of coordinate alongside a street address\n"
                    f"    that locates a household rather than an incident; "
                    f"{COORD_PRECISION_LIMIT} places is about a metre")

        desc = node.get("description") or ""
        if CONTACT_IN_TEXT.search(desc):
            warnings.append(
                f"{nid}: description appears to contain a phone number or email address\n"
                f"    free text is written by the public and is not covered by the field\n"
                f"    check; review before publishing")

    # --- service request status history ---------------------------------------
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ServiceRequest" not in types_:
            continue

        history = node.get("statusHistory") or []
        dates = [parse_dt(h.get("date")) for h in history]
        if any(d is None for d in dates):
            pass
        elif dates != sorted(dates):
            errors.append(
                f"status history is not in chronological order: {nid}"
            )
        if history and history[-1].get("requestStatus") != node.get("requestStatus"):
            errors.append(
                f"status history disagrees with current status: {nid}\n"
                f"    request is '{node.get('requestStatus')}' but history ends at "
                f"'{history[-1].get('requestStatus')}'"
            )
        if node.get("requestStatus") == "duplicate" and not node.get("duplicateOf"):
            errors.append(
                f"request marked duplicate without saying of what: {nid}\n"
                f"    set duplicateOf; a status note naming the other request cannot be followed"
            )

    # --- boundaries and geometry -----------------------------------------------
    INLINE_VERTEX_WARN = 500

    def count_vertices(coords):
        if not isinstance(coords, list):
            return 0
        if coords and all(isinstance(x, (int, float)) for x in coords):
            return 1
        return sum(count_vertices(c) for c in coords)

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "Boundary" not in types_:
            continue

        vf = parse_dt(node.get("validFrom"))
        vu = parse_dt(node.get("validUntil"))
        if vf and vu and vu < vf:
            errors.append(
                f"boundary ceases before it takes effect: {nid}\n"
                f"    validFrom {node.get('validFrom')}, validUntil {node.get('validUntil')}")

        sup = entities.get((node.get("supersedes") or {}).get("@id"))
        if sup:
            sup_from = parse_dt(sup.get("validFrom"))
            if vf and sup_from and sup_from > vf:
                errors.append(
                    f"boundary supersedes one that took effect later: {nid}\n"
                    f"    this from {node.get('validFrom')}, superseded from {sup.get('validFrom')}")
            if (sup.get("boundaryOf") or {}).get("@id") != (node.get("boundaryOf") or {}).get("@id"):
                errors.append(
                    f"boundary supersedes the boundary of a different area: {nid}")

        g = node.get("geometry") or {}
        # A generalised rendering is not the legal boundary, so it must not also claim to
        # be authoritative - that combination tells a consumer two contradictory things.
        if g.get("simplified") and node.get("authoritative"):
            errors.append(
                f"boundary is both simplified and authoritative: {nid}\n"
                f"    a generalised rendering is not the legal boundary; using one to decide\n"
                f"    whether an address falls inside gives wrong answers at the edges")

        # Inline size is a publishing judgement, not a correctness error, so it warns.
        n = g.get("vertexCount") or count_vertices(g.get("coordinates"))
        if g.get("coordinates") and n > INLINE_VERTEX_WARN:
            warnings.append(
                f"inline geometry has ~{n:,} vertices ({nid}); consider contentUrl above "
                f"{INLINE_VERTEX_WARN:,}")

    # --- elections ---------------------------------------------------------------
    # Election returns that do not add up are the classic sign of a transcription
    # error, and every vote share published from them is wrong. This is arithmetic,
    # not interpretation.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "Contest" not in types_:
            continue

        valid = node.get("validVotes")
        invalid = node.get("invalidVotes")
        total = node.get("totalVotes")

        counted = [c.get("voteCount") for c in node.get("candidacy", [])
                   if c.get("candidacyResult") not in ("withdrawn", "disqualified")]
        counted += [o.get("voteCount") for o in node.get("ballotOption", [])]
        counted = [v for v in counted if isinstance(v, int)]

        if counted and valid is not None and sum(counted) != valid:
            errors.append(
                f"contest votes do not sum to validVotes: {nid}\n"
                f"    entries total {sum(counted):,} but validVotes is {valid:,} "
                f"(difference {valid - sum(counted):,})")

        if valid is not None and invalid is not None and total is not None \
                and valid + invalid != total:
            errors.append(
                f"valid + invalid does not equal totalVotes: {nid}\n"
                f"    {valid:,} + {invalid:,} = {valid + invalid:,}, but totalVotes is {total:,}")

        # A contest for an office must say which office.
        if node.get("contestType") == "office" and not node.get("post"):
            errors.append(
                f"office contest does not say which post it fills: {nid}\n"
                f"    set post; without it an election cannot be joined to the office it filled")

        if node.get("contestType") == "ballotMeasure" and node.get("candidacy"):
            errors.append(
                f"ballot measure carries candidacies: {nid}\n"
                f"    a proposition has ballotOption, not candidates")

        elected = [c for c in node.get("candidacy", [])
                   if c.get("candidacyResult") == "elected"]
        seats = node.get("seatsToFill")
        if seats and len(elected) > seats:
            errors.append(
                f"more candidates elected than seats available: {nid}\n"
                f"    {len(elected)} elected for {seats} seat(s)")

    # --- permits ---------------------------------------------------------------
    # Permit dates are the basis of every processing-time statistic drawn from this
    # data, so an impossible sequence is worth failing on rather than averaging over.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "GovernmentPermit" not in types_:
            continue

        applied = parse_dt(node.get("applicationDate"))
        decided = parse_dt(node.get("decisionDate"))
        completed = parse_dt(node.get("completionDate"))
        valid_from = parse_dt(node.get("validFrom"))
        valid_until = parse_dt(node.get("validUntil"))

        if applied and decided and decided < applied:
            errors.append(
                f"permit decided before it was applied for: {nid}\n"
                f"    applied {node.get('applicationDate')}, "
                f"decided {node.get('decisionDate')}")
        if decided and completed and completed < decided:
            errors.append(
                f"permit completed before it was decided: {nid}\n"
                f"    decided {node.get('decisionDate')}, "
                f"completed {node.get('completionDate')}")
        if valid_from and valid_until and valid_until < valid_from:
            errors.append(
                f"permit expires before it becomes valid: {nid}")
        if node.get("permitStatus") in ("issued", "completed") and not decided:
            # Distinguish a record that asserts a completion while hiding when from one
            # that asserts nothing. Real Seattle data carries a permit marked Completed
            # with all four dates null - an undated historical record, not a claim that
            # contradicts itself. Partial dating is the error; no dating is a warning.
            if applied or completed:
                errors.append(
                    f"permit is {node.get('permitStatus')} but carries no decisionDate: {nid}\n"
                    f"    it has other lifecycle dates, so the decision date is missing rather\n"
                    f"    than unrecorded, and processing time cannot be derived")
            else:
                warnings.append(
                    f"{nid}: permit is {node.get('permitStatus')} with no lifecycle dates at "
                    f"all; processing time cannot be derived")

    # --- discovery manifest ---------------------------------------------------
    # The manifest is the routing table. A duplicate or misplaced entry makes a
    # publisher's data undiscoverable in a way nothing else surfaces.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "PublisherManifest" not in types_:
            continue

        if "/.well-known/schemaGov.json" not in nid:
            errors.append(
                f"manifest is not at its conventional location: {nid}\n"
                f"    serve it at /.well-known/schemaGov.json (RFC 8615), or consumers "
                f"cannot find it without being told the URL"
            )

        seen = {}
        for ep in node.get("profileEndpoint", []):
            prof = ep.get("profile")
            if prof in seen:
                errors.append(
                    f"manifest declares '{prof}' twice: {nid}\n"
                    f"    {seen[prof]} and {ep.get('url')} - a routing table needs one "
                    f"entry per profile"
                )
            seen[prof] = ep.get("url")

    # --- conformance levels ---------------------------------------------------
    # SPEC section 4 defines three levels; documents declare one with conformanceLevel.
    # An unverified claim is worse than no claim, so every declaration is checked.
    JURISDICTION_TYPES = {"AdministrativeArea", "Country", "State", "City"}

    def types_of(node):
        v = node.get("@type")
        return set(v if isinstance(v, list) else [v])

    claims = [
        (nid, lvl)
        for nid, node in entities.items()
        for lvl in (node.get("conformanceLevel") or [])
    ]

    if claims:
        jurisdictions = [n for n in entities.values() if types_of(n) & JURISDICTION_TYPES]
        orgs = [n for n in entities.values() if "GovernmentOrganization" in types_of(n)]
        conflated = [
            n["@id"] for n in entities.values()
            if "GovernmentOrganization" in types_of(n) and types_of(n) & JURISDICTION_TYPES
        ]
        unidentified = [
            n["@id"] for n in jurisdictions + orgs if not n.get("identifier")
        ]

        core_failures = []
        if not jurisdictions:
            core_failures.append("no Jurisdiction present")
        if not orgs:
            core_failures.append("no GovernmentOrganization present")
        for c in conflated:
            core_failures.append(f"{c} is typed as both a Jurisdiction and an Organization")
        for u in unidentified:
            core_failures.append(f"{u} carries no identifier")

        # errors accumulated so far are the Standard criterion
        pre_conformance_errors = len(errors)

        for nid, lvl in claims:
            if lvl not in ("core", "standard", "extended"):
                errors.append(f"unknown conformance level '{lvl}' claimed by {nid}")
                continue
            for f in core_failures:
                errors.append(f"conformance: {nid} claims '{lvl}' but Core is not met\n    {f}")
            if lvl in ("standard", "extended") and pre_conformance_errors:
                errors.append(
                    f"conformance: {nid} claims '{lvl}', which requires a clean document set\n"
                    f"    {pre_conformance_errors} error(s) above must be resolved first"
                )
            if lvl in ("standard", "extended"):
                # Requirements enforced at Standard rather than in the schema, so that
                # real-world data can still be represented at Core.
                for oid, o in entities.items():
                    ot = o.get("@type")
                    ot = ot if isinstance(ot, list) else [ot]
                    if "GovernmentOrganization" in ot and not o.get("areaServed"):
                        errors.append(
                            f"conformance: {nid} claims '{lvl}' but {oid}\n"
                            f"    has no areaServed. Standard requires every organization to be "
                            f"placed in the territorial hierarchy."
                        )
                    if "GovernmentService" in ot and not o.get("serviceStatus"):
                        errors.append(
                            f"conformance: {nid} claims '{lvl}' but {oid}\n"
                            f"    has no serviceStatus. Standard requires it: a service listing "
                            f"that cannot say whether the service still exists is of limited use."
                        )
                    if "ContractingProcess" in ot:
                        tn = o.get("tender") or {}
                        if tn and not tn.get("procurementMethod"):
                            errors.append(
                                f"conformance: {nid} claims '{lvl}' but {oid}\n"
                                f"    has a tender with no procurementMethod. Standard requires it, "
                                f"so that non-competitive awards remain visible."
                            )
            if lvl == "extended":
                node = entities[nid]
                if not (node.get("distribution") or node.get("sourceDataset")):
                    errors.append(
                        f"conformance: {nid} claims 'extended' but provides no machine-readable\n"
                        f"    link to its source standard (distribution or sourceDataset)"
                    )

    # --- report --------------------------------------------------------------
    print(f"schemaGov validate: {len(paths)} file(s), {len(entities)} entities, "
          f"{len(refs)} cross-references")
    if claims:
        shown = ", ".join(sorted({lvl for _, lvl in claims}))
        print(f"  note: conformance claimed ({len(claims)} declaration(s)): {shown}")
    for n in notes:
        print(f"  note: {n}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK - all references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
