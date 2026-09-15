#!/usr/bin/env python3
"""Convert Socrata-published building permits into the schemaGov permits profile.

Socrata runs the open-data portal for a large share of US cities, but each city defines
its own permit schema, so field maps are per city rather than generic. Two are built in,
chosen because they differ in the way that matters: Seattle publishes no applicant at
all, Chicago publishes named individuals at their home addresses.

    python3 tools/adapters/permits-socrata.py --city seattle --limit 60 \
        --out examples/pilot-seattle-permits

The permits profile makes `applicant` optional on the grounds that naming a private
individual against their home address is a disclosure decision the authority must take
deliberately. This adapter applies that: an applicant that is clearly an organization is
carried, one that looks like an individual is omitted and counted. Use
--include-individuals for source fidelity.
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"

CITIES = {
    "seattle": {
        "host": "data.seattle.gov", "dataset": "76t5-zqzr", "name": "Seattle",
        "number": "permitnum", "description": "description",
        "applied": "applieddate", "decided": "issueddate",
        "completed": "completeddate", "expires": "expiresdate",
        "status": "statuscurrent", "work": "permittypedesc", "kind": "permittypemapped",
        "value": "estprojectcost", "url": None,
        "address": ("originaladdress1", "originalcity", "originalstate", "originalzip"),
        "lat": "latitude", "lon": "longitude",
        "applicant": None, "applicant_type": None,
    },
    "chicago": {
        "host": "data.cityofchicago.org", "dataset": "ydr8-5enu", "name": "Chicago",
        "number": "permit_", "description": "work_description",
        "applied": "application_start_date", "decided": "issue_date",
        "completed": None, "expires": None,
        "status": None, "work": "permit_type", "kind": "permit_type",
        "value": "reported_cost", "fee": "total_fee", "url": None,
        "address": None, "lat": "latitude", "lon": "longitude",
        "applicant": "contact_1_name", "applicant_type": "contact_1_type",
    },
}

STATUS = {
    "completed": "completed", "issued": "issued", "closed": "withdrawn",
    "expired": "expired", "canceled": "withdrawn", "cancelled": "withdrawn",
    "ap closed": "withdrawn",
    "withdrawn": "withdrawn", "in review": "underReview",
    "application accepted": "applied", "reviews completed": "approved",
}

WORK = {
    "new": "newBuild", "permit - new construction": "newBuild",
    "addition/alteration": "alteration", "permit - renovation/alteration": "alteration",
    "permit - easy permit process": "alteration",
    "demolition": "demolition", "permit - wrecking/demolition": "demolition",
    "permit - signs": "temporary", "permit - scaffolding": "temporary",
    "permit - porch construction": "extension",
    "permit - express permit program": "alteration",
    "tenant improvment": "alteration", "tenant improvement": "alteration",
    "shoreline exemption": "alteration", "site work": "alteration",
}

KIND = {
    "building": "building", "permit - new construction": "building",
    "permit - renovation/alteration": "building", "permit - easy permit process": "building",
    "permit - wrecking/demolition": "demolition", "permit - signs": "sign",
    "permit - scaffolding": "building", "permit - porch construction": "building",
    "permit - electric wiring": "building", "demolition": "demolition",
    "site development": "planning", "roofing": "building", "mechanical": "building",
    "permit - express permit program": "building",
    "eca and shoreline exemption/street improvement exception request": "environmental",
}

CORPORATE = ("INC", "LLC", "L.L.C", "CORP", "COMPANY", " CO", "LTD", "SERVICES",
             "CONSTRUCTION", "ELECTRIC", "PLUMBING", "HEATING", "ROOFING", "CONTRACTOR",
             "BUILDERS", "BUILDING", "GROUP", "ASSOC", "&", "ENTERPRISE", "DEVELOPMENT",
             "PROPERTIES", "MANAGEMENT", "REMODEL", "HOMES", "CONSTR")


def norm(v):
    """City permit vocabularies are typed by hand and drift. Chicago writes both
    'PERMIT - SIGNS' with a hyphen and 'PERMIT - EXPRESS PERMIT PROGRAM' with an en-dash;
    matching the literal string missed 42 of 60 permits. Normalise dashes and whitespace
    before lookup rather than accumulating spelling variants in the map."""
    s = str(v or "").strip().lower()
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return re.sub(r"\s+", " ", s)


def looks_like_organization(name):
    n = (name or "").strip().upper()
    if not n:
        return False
    return any(tok in n for tok in CORPORATE) or n.count(" ") > 2


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=sorted(CITIES), required=True)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--include-individuals", action="store_true",
                    help="Carry applicant names that look like private individuals.")
    ap.add_argument("--out", default="examples/pilot-permits")
    args = ap.parse_args()

    cfg = CITIES[args.city]
    gaps, notes = defaultdict(int), defaultdict(int)
    url = (f"https://{cfg['host']}/resource/{cfg['dataset']}.json"
           f"?$limit={args.limit}&$order=:id")
    rows = fetch(url)

    base = f"https://{cfg['host']}/id"
    juris_id = f"{base}/jurisdiction/{slug(cfg['name'])}"
    jurisdiction = {"@id": juris_id, "@type": "City", "name": cfg["name"],
                    "governmentLevel": "municipal",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "local:socrata-host", "value": cfg["host"]}]}
    org_id = f"{base}/organization/permitting"
    org = {"@id": org_id, "@type": "GovernmentOrganization",
           "name": f"{cfg['name']} permitting authority",
           "identifier": [{"@type": "PropertyValue", "propertyID": "local:socrata-host",
                           "value": cfg["host"]}],
           "organizationClassification": "department",
           "areaServed": {"@id": juris_id, "name": cfg["name"]}}

    permits, parties = [], {}
    for r in rows:
        num = str(r.get(cfg["number"]) or "").strip()
        if not num:
            continue
        raw_kind = norm(r.get(cfg["kind"]))
        kind = KIND.get(raw_kind)
        if not kind:
            gaps[f"permitType:{r.get(cfg['kind'])}"] += 1
            kind = "building"

        decided = r.get(cfg["decided"])
        raw_status = norm(r.get(cfg["status"])) if cfg["status"] else ""
        status = STATUS.get(raw_status)
        if not status:
            if raw_status:
                gaps[f"status:{r.get(cfg['status'])}"] += 1
            # Chicago publishes issued permits without a status column.
            status = "issued" if decided else "applied"

        p = {"@id": f"{base}/permit/{slug(num)}", "@type": "GovernmentPermit",
             "permitNumber": num, "permitType": kind, "permitStatus": status,
             "issuedBy": {"@id": org_id, "name": org["name"]},
             "validIn": {"@id": juris_id, "name": cfg["name"]}}

        desc = r.get(cfg["description"])
        if desc:
            p["description"] = re.sub(r"\s+", " ", str(desc)).strip()[:600]
        raw_work = norm(r.get(cfg["work"]))
        work = WORK.get(raw_work)
        if work:
            p["workType"] = work
        elif raw_work:
            gaps[f"workType:{r.get(cfg['work'])}"] += 1

        for src, dst in (("applied", "applicationDate"), ("decided", "decisionDate"),
                         ("completed", "completionDate"), ("expires", "validUntil")):
            key = cfg.get(src)
            if key and r.get(key):
                p[dst] = str(r[key])[:10]
        if p.get("validUntil") and p.get("decisionDate") and p["validUntil"] < p["decisionDate"]:
            # Seen in real Seattle data: a permit issued 2010-03-17 recorded as expiring
            # 2008-10-24. A contradiction cannot be published, so it is dropped and
            # counted rather than passed through or silently corrected.
            notes["expiry precedes issue in the source; omitted as inconsistent"] += 1
            p.pop("validUntil")
        if p.get("decisionDate") and status in ("issued", "completed"):
            p.setdefault("validFrom", p["decisionDate"])

        # premises
        premises = {"@type": "Place"}
        if cfg["address"]:
            a, city, st, z = cfg["address"]
            if r.get(a):
                premises["address"] = {k: v for k, v in {
                    "@type": "PostalAddress", "streetAddress": r.get(a),
                    "addressLocality": r.get(city), "addressRegion": r.get(st),
                    "postalCode": str(r.get(z) or "").strip() or None,
                    "addressCountry": "US"}.items() if v}
        else:
            street = " ".join(str(r.get(k, "") or "").strip() for k in
                              ("street_number", "street_direction", "street_name")).strip()
            if street:
                premises["address"] = {"@type": "PostalAddress", "streetAddress": street,
                                       "addressLocality": cfg["name"], "addressCountry": "US"}
        if r.get(cfg["lat"]) and r.get(cfg["lon"]):
            try:
                # Same rule as the Open311 adapter: five places locates an incident,
                # more locates a household.
                premises["geo"] = {"@type": "GeoCoordinates",
                                   "latitude": round(float(r[cfg["lat"]]), 5),
                                   "longitude": round(float(r[cfg["lon"]]), 5)}
            except (TypeError, ValueError):
                pass
        if len(premises) > 1:
            p["premises"] = premises

        def money(v):
            try:
                f = float(v)
            except (TypeError, ValueError):
                return None
            return {"@type": "MonetaryAmount", "value": round(f, 2), "currency": "USD"} if f else None

        if cfg.get("value") and money(r.get(cfg["value"])):
            p["declaredValue"] = money(r[cfg["value"]])
        if cfg.get("fee") and money(r.get(cfg["fee"])):
            p["fee"] = money(r[cfg["fee"]])

        # applicant, per the profile's disclosure stance
        akey = cfg.get("applicant")
        if akey and (r.get(akey) or "").strip():
            nm = r[akey].strip()
            atype = str(r.get(cfg.get("applicant_type") or "") or "").strip()
            if looks_like_organization(nm) or args.include_individuals:
                pid = f"{base}/party/{slug(nm)}"
                parties[pid] = {"@id": pid, "@type": "Organization", "name": nm,
                                "identifier": [{"@type": "PropertyValue",
                                                "propertyID": "local:permit-contact",
                                                "value": slug(nm)}],
                                "role": ["supplier"]}
                p["applicant"] = {"@id": pid, "name": nm}
                if not looks_like_organization(nm):
                    notes["individual applicant carried under --include-individuals"] += 1
            else:
                notes[f"applicant omitted: name looks like a private individual"
                      f"{' (' + atype + ')' if atype else ''}"] += 1
        permits.append(p)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    for fname, graph in (("jurisdictions.jsonld", [jurisdiction]),
                         ("organizations.jsonld", [org]),
                         ("parties.jsonld", list(parties.values())),
                         ("permits.jsonld", permits)):
        (out / fname).write_text(
            json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")

    print(f"permits-socrata adapter: {cfg['name']} -> {len(permits)} permit(s), "
          f"{len(parties)} party(ies)")
    print(f"  written to {out}/")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1])[:8]:
                print(f"    {k}  ({n}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
