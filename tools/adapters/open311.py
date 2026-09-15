#!/usr/bin/env python3
"""Convert a real Open311 GeoReport v2 endpoint into the schemaGov requests profile.

The requests profile carries the strongest opinion in schemaGov: reporter privacy is
treated as a schema concern, and the validator fails the build if a published request
carries a reporter-identifying field. This is the test of that opinion against real 311
data.

    python3 tools/adapters/open311.py \
        --url https://bloomington.in.gov/crm/open311/v2 --limit 60 \
        --out examples/pilot-bloomington-311

Handles both response shapes seen in the wild: a bare JSON array, and an object wrapping
`service_requests` as FixMyStreet-derived endpoints return.
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.request
from collections import defaultdict

UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"

STATUS = {"open": "open", "closed": "closed", "in progress": "inProgress",
          "investigating": "inProgress", "action scheduled": "inProgress",
          "planned": "inProgress", "duplicate": "duplicate",
          "not responsible": "rejected", "no further action": "rejected",
          "unable to fix": "rejected", "internal referral": "onHold"}

# Coordinates finer than this, on a request that also carries a street address, locate a
# household rather than an incident. Five places is about a metre.
PRECISION_LIMIT = 5


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


def unwrap(payload):
    if isinstance(payload, list):
        return payload
    for key in ("service_requests", "services", "requests"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def decimals(v):
    s = str(v)
    return len(s.split(".")[1]) if "." in s else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Open311 base, e.g. https://host/open311/v2")
    ap.add_argument("--jurisdiction-id", default=None)
    ap.add_argument("--name", default=None, help="Human name for the jurisdiction")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--round-coordinates", type=int, default=PRECISION_LIMIT,
                    help="Decimal places to keep. Source precision is preserved with 0.")
    ap.add_argument("--out", default="examples/pilot-open311")
    args = ap.parse_args()

    base_api = args.url.rstrip("/")
    q = f"?jurisdiction_id={args.jurisdiction_id}" if args.jurisdiction_id else ""
    gaps, notes = defaultdict(int), defaultdict(int)

    raw = unwrap(fetch(f"{base_api}/requests.json{q}"))[: args.limit]
    try:
        raw_services = unwrap(fetch(f"{base_api}/services.json{q}"))
    except Exception:
        raw_services = []
        notes["services.json unavailable; service catalogue not built"] += 1

    host = re.sub(r"^https?://", "", base_api).split("/")[0]
    base = f"https://{host}/id"
    juris_id = f"{base}/jurisdiction/{slug(host)}"
    name = args.name or host
    jurisdiction = {"@id": juris_id, "@type": "City", "name": name,
                    "governmentLevel": "municipal",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "local:open311-host", "value": host}]}
    org_id = f"{base}/organization/city"
    org = {"@id": org_id, "@type": "GovernmentOrganization", "name": f"{name} city government",
           "identifier": [{"@type": "PropertyValue", "propertyID": "local:open311-host",
                           "value": host}],
           "organizationClassification": "executive",
           "areaServed": {"@id": juris_id, "name": name}}

    services, by_code = [], {}
    for s in raw_services:
        code = str(s.get("service_code", "")).strip()
        if not code:
            continue
        sid = f"{base}/service/{slug(code)}"
        svc = {"@id": sid, "@type": "GovernmentService",
               "name": s.get("service_name") or code,
               "serviceCode": code,
               "provider": {"@id": org_id, "name": org["name"]},
               "areaServed": {"@id": juris_id, "name": name}}
        if s.get("description"):
            svc["description"] = s["description"]
        if s.get("group"):
            svc["serviceType"] = s["group"]
        if s.get("keywords"):
            svc["keywords"] = [k.strip() for k in str(s["keywords"]).split(",") if k.strip()]
        if s.get("type"):
            svc["isRealtime"] = s["type"] == "realtime"
        services.append(svc)
        by_code[code] = sid

    requests_out = []
    for r in raw:
        rid = str(r.get("service_request_id") or "").strip()
        if not rid:
            continue
        code = str(r.get("service_code") or "").strip()
        status = STATUS.get(str(r.get("status") or "").strip().lower())
        if not status:
            gaps[f"status:{r.get('status')}"] += 1
            status = "open"

        req = {
            "@id": f"{base}/request/{slug(rid)}", "@type": "ServiceRequest",
            "serviceRequestId": rid,
            "serviceCode": code or "unknown",
            "requestStatus": status,
            "dateCreated": r.get("requested_datetime"),
        }
        if not req["dateCreated"]:
            notes["request with no requested_datetime; skipped"] += 1
            continue
        if code in by_code:
            req["service"] = {"@id": by_code[code],
                              "name": r.get("service_name") or code}
        elif code:
            gaps[f"service_code not in catalogue:{code}"] += 1

        # FixMyStreet-derived endpoints split title from detail; Open311 proper has one
        # description field.
        desc = r.get("description") or r.get("detail") or r.get("title")
        if desc:
            req["description"] = re.sub(r"\s+", " ", str(desc)).strip()[:1000]
        if r.get("updated_datetime"):
            req["dateModified"] = r["updated_datetime"]
        if r.get("expected_datetime"):
            req["expectedResolutionDate"] = r["expected_datetime"]
        if (r.get("agency_responsible") or "").strip():
            req["statusNote"] = r["agency_responsible"].strip()
            notes["agency_responsible is free text, not a resolvable organization"] += 1

        addr = (r.get("address") or "").strip()
        if addr:
            req["address"] = {"@type": "PostalAddress", "streetAddress": addr,
                              "addressLocality": name}
            if r.get("zipcode"):
                req["address"]["postalCode"] = str(r["zipcode"])

        lat, lon = r.get("lat"), r.get("long")
        if lat is not None and lon is not None:
            try:
                lat_f, lon_f = float(lat), float(lon)
            except (TypeError, ValueError):
                lat_f = lon_f = None
            if lat_f is not None:
                src_dp = max(decimals(lat), decimals(lon))
                if args.round_coordinates and src_dp > args.round_coordinates:
                    lat_f = round(lat_f, args.round_coordinates)
                    lon_f = round(lon_f, args.round_coordinates)
                    notes[f"coordinates reduced from {src_dp} to "
                          f"{args.round_coordinates} decimal places"] += 1
                req["geo"] = {"@type": "GeoCoordinates", "latitude": lat_f, "longitude": lon_f}

        req["jurisdiction"] = {"@id": juris_id, "name": name}
        requests_out.append(req)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    for fname, graph in (("jurisdictions.jsonld", [jurisdiction]),
                         ("organizations.jsonld", [org]),
                         ("services.jsonld", services),
                         ("requests.jsonld", requests_out)):
        (out / fname).write_text(
            json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")

    print(f"open311 adapter: {host} -> {len(requests_out)} request(s), "
          f"{len(services)} service(s)")
    print(f"  written to {out}/")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1]):
                print(f"    {k}  ({n}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
