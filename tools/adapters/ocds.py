#!/usr/bin/env python3
"""Convert real OCDS data into the schemaGov procurement profile.

OCDS publishes a *release stream* (events); the schemaGov procurement profile models
the *compiled record* (current state). This adapter compiles releases by ocid, then
projects them.

Run against a live endpoint, or a saved file:

    python3 tools/adapters/ocds.py --url "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search?limit=25"
    python3 tools/adapters/ocds.py --file releases.json --out examples/pilot-uk-contracts

Anything the adapter cannot map is reported rather than silently dropped: an adapter
that quietly loses fields teaches nothing about where the profile is wrong.
"""
import argparse
import json
import pathlib
import re
import sys
import ssl
import urllib.request
from collections import defaultdict

BASE = "https://example.org/id"          # overridden by --base
UA = "schemaGov-adapter/1.0 (+https://schema.govfresh.com)"

# OCDS fields the profile deliberately does not carry, so they are not reported as gaps.
KNOWN_UNMAPPED = {
    "release": {"initiationType", "language", "id", "tag", "date", "planning"},
    "tender": {"items", "suitability", "awardCriteria", "submissionMethod",
               "hasEnquiries", "amendments", "milestones", "lots"},
    "award":  {"items", "amendments", "relatedLots"},
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def _ssl_context():
    """Some Python installs (notably python.org builds on macOS) ship without a CA
    bundle, so certificate verification fails on every https call. Fall back to
    certifi's bundle rather than disabling verification."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def party_identifiers(party):
    """Return scheme-qualified identifiers for an OCDS party.

    Real publishers are inconsistent here. UK Contracts Finder gives some parties a
    full {scheme, id} and others only a legalName - but the party's own `id` is itself
    scheme-prefixed ("GB-CFS-334419"), so it is a usable fallback. Without this,
    conformant OCDS from a national publisher fails the profile's identifier rule.
    """
    # org-id.guide prefixes are a curated register. A publisher's internal scheme is
    # not one, and labelling it "org-id:" would misstate its provenance - the whole
    # point of scheme-qualified identity is knowing which register a code came from.
    REGISTERED = {"GB-COH", "GB-GOR", "GB-CHC", "GB-SC", "GB-NIC", "GB-EDU",
                  "US-EIN", "US-DOS", "IE-CRO", "NL-KVK", "DE-HRB", "FR-SIRENE",
                  "XI-LEI", "XI-PB"}

    def scheme_token(code):
        return f"org-id:{code}" if code in REGISTERED else f"local:{code}"

    out = []
    ident = party.get("identifier") or {}
    if ident.get("scheme") and ident.get("id"):
        out.append({"@type": "PropertyValue",
                    "propertyID": scheme_token(ident["scheme"]),
                    "value": str(ident["id"])})
    pid = party.get("id")
    if not out and pid and "-" in str(pid):
        m = re.match(r"^([A-Z]{2}-[A-Z0-9]+)-(.+)$", str(pid))
        if m:
            out.append({"@type": "PropertyValue",
                        "propertyID": scheme_token(m.group(1)),
                        "value": m.group(2)})
    if not out and pid:
        out.append({"@type": "PropertyValue", "propertyID": "gs:local", "value": str(pid)})
    return out


def amount(v):
    if not v or v.get("amount") is None or not v.get("currency"):
        return None
    return {"@type": "MonetaryAmount", "value": v["amount"], "currency": v["currency"]}


def compile_records(releases):
    """Merge a release stream into one record per ocid (last write wins per block)."""
    recs = defaultdict(lambda: {"tender": {}, "awards": {}, "contracts": {}, "parties": {}, "buyer": None})
    for rel in sorted(releases, key=lambda r: r.get("date") or ""):
        oc = rel.get("ocid")
        if not oc:
            continue
        rec = recs[oc]
        if rel.get("tender"):
            rec["tender"].update(rel["tender"])
        if rel.get("buyer"):
            rec["buyer"] = rel["buyer"]
        for p in rel.get("parties") or []:
            if p.get("id"):
                rec["parties"][p["id"]] = p
        for a in rel.get("awards") or []:
            if a.get("id"):
                rec["awards"][a["id"]] = a
        for c in rel.get("contracts") or []:
            if c.get("id"):
                rec["contracts"][c["id"]] = c
        rec["date"] = rel.get("date")
    return recs


def convert(releases, base, gaps):
    recs = compile_records(releases)
    orgs, parties, processes = {}, {}, []

    for ocid, rec in recs.items():
        pslug = slug(ocid)
        t = rec["tender"]

        # buyer -> a _core GovernmentOrganization (not a procurement Party)
        buyer_ref = None
        b = rec["buyer"]
        if b and b.get("id"):
            oid = f"{base}/organization/{slug(b['id'])}"
            src = rec["parties"].get(b["id"], b)
            orgs[oid] = {
                "@id": oid, "@type": "GovernmentOrganization",
                "name": b.get("name") or src.get("name") or b["id"],
                "identifier": party_identifiers(src),
                "organizationClassification": "agency",
            }
            if src.get("address"):
                a = src["address"]
                orgs[oid]["address"] = {k: v for k, v in {
                    "@type": "PostalAddress",
                    "streetAddress": a.get("streetAddress"),
                    "addressLocality": a.get("locality"),
                    "addressRegion": a.get("region"),
                    "postalCode": a.get("postalCode"),
                    "addressCountry": a.get("countryName"),
                }.items() if v}
            buyer_ref = {"@id": oid, "name": orgs[oid]["name"]}

        # non-government parties -> Party
        proc_parties = []
        for pid, p in rec["parties"].items():
            roles = [r for r in (p.get("roles") or []) if r != "buyer"]
            if not roles:
                continue
            wid = f"{base}/party/{slug(pid)}"
            parties[wid] = {
                "@id": wid, "@type": "Organization",
                "name": p.get("name") or pid,
                "identifier": party_identifiers(p),
                "role": [r for r in roles if r in
                         {"procuringEntity", "supplier", "tenderer", "payer", "payee",
                          "reviewBody", "funder"}] or ["supplier"],
            }
            proc_parties.append({"@id": wid, "name": parties[wid]["name"]})

        cp = {
            "@id": f"{base}/contracting-process/{pslug}",
            "@type": "ContractingProcess",
            "ocid": ocid,
            "name": t.get("title") or ocid,
            "buyer": buyer_ref,
            "dateModified": (rec.get("date") or "")[:10] or None,
            "party": proc_parties,
        }

        if t:
            tender = {
                "@type": "Tender",
                "tenderId": t.get("id"),
                "title": t.get("title"),
                "description": t.get("description"),
                "status": t.get("status"),
                "procurementMethod": t.get("procurementMethod"),
                "procurementMethodDetails": t.get("procurementMethodDetails"),
                "mainProcurementCategory": t.get("mainProcurementCategory"),
                "value": amount(t.get("value")),
            }
            cls = t.get("classification")
            if cls and cls.get("id"):
                tender["classification"] = [{
                    "@type": "PropertyValue",
                    "propertyID": (cls.get("scheme") or "unknown").lower(),
                    "value": str(cls["id"]),
                    **({"name": cls["description"]} if cls.get("description") else {})}]
            tp = t.get("tenderPeriod") or {}
            tender["tenderPeriodStart"] = tp.get("startDate")
            tender["tenderPeriodEnd"] = tp.get("endDate")
            cp["tender"] = {k: v for k, v in tender.items() if v is not None}
            for k in set(t) - KNOWN_UNMAPPED["tender"] - {
                "id", "title", "description", "status", "procurementMethod",
                "procurementMethodDetails", "mainProcurementCategory", "value",
                "classification", "tenderPeriod", "datePublished", "contractPeriod"}:
                gaps[f"tender.{k}"] += 1

        awards = []
        for aid, a in rec["awards"].items():
            sup = []
            for s in a.get("suppliers") or []:
                if s.get("id"):
                    sid = f"{base}/party/{slug(s['id'])}"
                    if sid not in parties:
                        parties[sid] = {"@id": sid, "@type": "Organization",
                                        "name": s.get("name") or s["id"],
                                        "identifier": party_identifiers(s),
                                        "role": ["supplier"]}
                    if not any(p["@id"] == sid for p in proc_parties):
                        proc_parties.append({"@id": sid, "name": parties[sid]["name"]})
                    sup.append({"@id": sid, "name": parties[sid]["name"]})
            cperiod = a.get("contractPeriod") or {}
            aw = {"@type": "Award", "awardId": aid, "title": a.get("title"),
                  "status": a.get("status"), "date": a.get("date"),
                  "value": amount(a.get("value")), "supplier": sup,
                  "contractPeriodStart": (cperiod.get("startDate") or "")[:10] or None,
                  "contractPeriodEnd": (cperiod.get("endDate") or "")[:10] or None}
            awards.append({k: v for k, v in aw.items() if v not in (None, [])})
            for k in set(a) - KNOWN_UNMAPPED["award"] - {
                "id", "title", "status", "date", "value", "suppliers", "contractPeriod", "description"}:
                gaps[f"award.{k}"] += 1
        if awards:
            cp["award"] = awards

        contracts = []
        for cid, c in rec["contracts"].items():
            per = c.get("period") or {}
            k = {"@type": "Contract", "contractId": cid, "awardId": c.get("awardID"),
                 "title": c.get("title"), "status": c.get("status"),
                 "value": amount(c.get("value")), "dateSigned": c.get("dateSigned"),
                 "periodStart": (per.get("startDate") or "")[:10] or None,
                 "periodEnd": (per.get("endDate") or "")[:10] or None}
            contracts.append({kk: vv for kk, vv in k.items() if vv is not None})
        if contracts:
            cp["contract"] = contracts

        processes.append({k: v for k, v in cp.items() if v is not None})

    return list(orgs.values()), list(parties.values()), processes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--file")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default="examples/pilot")
    args = ap.parse_args()

    if args.url:
        payload = fetch(args.url)
    elif args.file:
        payload = json.loads(pathlib.Path(args.file).read_text())
    else:
        ap.error("give --url or --file")

    releases = payload.get("releases") or payload.get("records") or []
    if not releases:
        print("no releases found", file=sys.stderr)
        return 1

    gaps = defaultdict(int)
    orgs, parties, processes = convert(releases, args.base.rstrip("/"), gaps)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    (out / "organizations.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": orgs}, indent=2, ensure_ascii=False) + "\n")
    (out / "parties.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": parties}, indent=2, ensure_ascii=False) + "\n")
    (out / "procurement.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": processes}, indent=2, ensure_ascii=False) + "\n")

    print(f"ocds adapter: {len(releases)} release(s) -> {len(processes)} process(es), "
          f"{len(orgs)} organization(s), {len(parties)} part(ies)")
    print(f"  written to {out}/")
    if gaps:
        print("\n  source fields with no schemaGov mapping:")
        for k, n in sorted(gaps.items(), key=lambda x: -x[1]):
            print(f"    {k:42} {n}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
