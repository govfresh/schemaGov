#!/usr/bin/env python3
"""Convert a real CAP feed into the schemaGov alerts profile.

Reads the US National Weather Service alerts API, which publishes Common Alerting
Protocol content as GeoJSON. CAP is the source model for the alerts profile, so this is
the most direct test available of whether that profile survives contact with real data.

    python3 tools/adapters/cap.py --limit 25 --out examples/pilot-nws-alerts

Unmapped values are reported rather than guessed.
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.request
from collections import defaultdict

FEED = "https://api.weather.gov/alerts/active?status=actual"
UA = "schemaGov-adapter/1.0 (schema.govfresh.com; admin@govfresh.com)"

# CAP values are title-case in the wire format; schemaGov uses lower camel case
# consistently across every code list.
ENUM = {
    "status": {"actual": "actual", "exercise": "exercise", "system": "system",
               "test": "test", "draft": "draft"},
    "messageType": {"alert": "alert", "update": "update", "cancel": "cancel",
                    "ack": "ack", "error": "error"},
    "severity": {"extreme": "extreme", "severe": "severe", "moderate": "moderate",
                 "minor": "minor", "unknown": "unknown"},
    "urgency": {"immediate": "immediate", "expected": "expected", "future": "future",
                "past": "past", "unknown": "unknown"},
    "certainty": {"observed": "observed", "likely": "likely", "possible": "possible",
                  "unlikely": "unlikely", "unknown": "unknown"},
    "category": {"geo": "geo", "met": "met", "safety": "safety", "security": "security",
                 "rescue": "rescue", "fire": "fire", "health": "health", "env": "env",
                 "transport": "transport", "infra": "infra", "cbrne": "cbrne",
                 "other": "other"},
    "response": {"shelter": "shelter", "evacuate": "evacuate", "prepare": "prepare",
                 "execute": "execute", "avoid": "avoid", "monitor": "monitor",
                 "assess": "assess", "allclear": "allClear", "none": "none"},
}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:90]


def as_list(v):
    """CAP allows category and responseType to repeat, but the NWS JSON encoding gives
    a bare string when there is one value. Iterating that yields characters."""
    if v in (None, ""):
        return []
    return v if isinstance(v, list) else [v]


def enum(kind, value, gaps):
    if value in (None, ""):
        return None
    key = re.sub(r"[^a-z]", "", str(value).lower())
    out = ENUM[kind].get(key)
    if not out:
        gaps[f"{kind}:{value}"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=FEED)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--base", default="https://api.weather.gov/id")
    ap.add_argument("--out", default="examples/pilot-cap-alerts")
    args = ap.parse_args()

    payload = fetch(args.feed)
    features = payload.get("features", [])[: args.limit]
    if not features:
        print("no alerts in the feed", file=sys.stderr)
        return 1

    base = args.base.rstrip("/")
    gaps, notes = defaultdict(int), defaultdict(int)
    senders, alerts = {}, []
    seen_ids = set()

    for feat in features:
        p = feat.get("properties", {})
        cap_id = p.get("id") or feat.get("id")
        if not cap_id or cap_id in seen_ids:
            continue
        seen_ids.add(cap_id)

        # The sender is an office name, not an identified organization. CAP carries
        # `sender` as an email-style address, which is the only stable handle available.
        sender_name = p.get("senderName") or "Unknown issuer"
        sid = f"{base}/organization/{slug(p.get('sender') or sender_name)}"
        senders[sid] = {
            "@id": sid, "@type": "GovernmentOrganization", "name": sender_name,
            "identifier": [{"@type": "PropertyValue", "propertyID": "local:cap-sender",
                            "value": p.get("sender") or sender_name}],
            "organizationClassification": "agency",
        }

        info = {
            "@type": "AlertInfo",
            "inLanguage": p.get("language") or "en-US",
            "category": [c for c in (enum("category", x, gaps)
                                     for x in as_list(p.get("category")))
                         if c] or ["other"],
            "event": p.get("event") or "Alert",
            "urgency": enum("urgency", p.get("urgency"), gaps) or "unknown",
            "severity": enum("severity", p.get("severity"), gaps) or "unknown",
            "certainty": enum("certainty", p.get("certainty"), gaps) or "unknown",
        }
        if p.get("expires"):
            info["expires"] = p["expires"]
        else:
            notes["alert with no expires; profile requires one"] += 1
            continue
        for src, dst in (("headline", "headline"), ("description", "description"),
                         ("instruction", "instruction"), ("effective", "effective"),
                         ("onset", "onset"), ("senderName", "senderName")):
            if p.get(src):
                info[dst] = p[src][:160] if dst == "headline" else p[src]
        resp = [r for r in (enum("response", x, gaps)
                            for x in as_list(p.get("response"))) if r]
        if resp:
            info["responseType"] = resp
        if not info.get("instruction"):
            notes["alert with no instruction: informative, not actionable"] += 1

        area = {"@type": "AlertArea",
                "areaDescription": (p.get("areaDesc") or "Unspecified")[:500]}
        # CAP geocodes are scheme-qualified area codes - SAME and UGC in the US.
        codes = []
        for scheme, values in (p.get("geocode") or {}).items():
            for v in (values or [])[:12]:
                codes.append({"@type": "PropertyValue",
                              "propertyID": f"local:{scheme.lower()}", "value": str(v)})
        if codes:
            area["geocode"] = codes
        if feat.get("geometry"):
            # The profile references geometry by URL rather than embedding it. NWS
            # inlines a polygon here, so it is linked to the alert's own endpoint.
            area["geometry"] = cap_id
            notes["geometry inlined by source; linked rather than embedded"] += 1
        elif p.get("affectedZones"):
            area["geometry"] = p["affectedZones"][0]
            notes["no polygon; area given only as zone references"] += 1

        alert = {
            "@id": f"{base}/alert/{slug(cap_id.rsplit('/', 1)[-1])}",
            "@type": "Alert",
            "alertIdentifier": cap_id,
            "sender": {"@id": sid, "name": sender_name},
            "sent": p.get("sent"),
            "alertStatus": enum("status", p.get("status"), gaps) or "actual",
            "messageType": enum("messageType", p.get("messageType"), gaps) or "alert",
            "scope": "public",
            "alertInfo": [info],
            "area": [area],
        }
        refs = [r.get("@id") or r.get("identifier")
                for r in as_list(p.get("references")) if isinstance(r, dict)]
        refs = [r for r in refs if r]
        if refs:
            # References point at CAP identifiers that may not be in this feed window,
            # so they are only emitted when the target is present.
            alert["_pendingRefs"] = refs
        if p.get("web"):
            info["web"] = p["web"]
        alerts.append(alert)

    # resolve references now that every alert in the batch is known
    by_cap = {a["alertIdentifier"]: a["@id"] for a in alerts}
    for a in alerts:
        pending = a.pop("_pendingRefs", [])
        resolved = [{"@id": by_cap[r]} for r in pending if r in by_cap]
        if resolved:
            a["references"] = resolved
        elif pending:
            # The superseded alert has expired out of the active feed. Carry its CAP
            # identifier rather than downgrading the message type, which would lose the
            # fact that this supersedes an earlier warning.
            a["referencesIdentifier"] = pending
            notes["superseded alert outside the feed window; carried by identifier"] += 1

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    (out / "organizations.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": list(senders.values())}, indent=2,
                   ensure_ascii=False) + "\n")
    (out / "alerts.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": alerts}, indent=2, ensure_ascii=False) + "\n")

    print(f"cap adapter: {len(features)} feature(s) -> {len(alerts)} alert(s), "
          f"{len(senders)} issuing office(s)")
    print(f"  written to {out}/")
    for label, data in (("conversion notes", notes), ("values with no schemaGov mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1]):
                print(f"    {k:58} {n}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
