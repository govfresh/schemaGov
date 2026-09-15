#!/usr/bin/env python3
"""Convert Eurostat COFOG government expenditure into the schemaGov budget profile.

Eurostat publishes general government expenditure by function for every EU member
state, using COFOG - the same classification the budget profile adopted. That makes it
the most direct available test of whether that profile can hold real fiscal data from a
publisher outside the US.

    python3 tools/adapters/eurostat-cofog.py --geo IE --year 2022 \
        --out examples/pilot-eurostat-budget

This is outturn statistics rather than an adopted budget document, so it maps to
budgetPhase "executed".
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

API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_exp"
       "?format=JSON&lang=en&sector=S13&na_item=TE")
UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"

# Eurostat unit codes carry a multiplier the amount itself does not.
UNITS = {"MIO_EUR": ("EUR", 1_000_000), "MIO_NAC": (None, 1_000_000),
         "EUR": ("EUR", 1), "MRD_EUR": ("EUR", 1_000_000_000)}


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


def cofog_code(eurostat_code):
    """Eurostat writes COFOG as GF01 and GF0101; the profile uses 01 and 01.1.

    A pure notation difference, but one that has to be handled: a consumer matching
    'GF0101' against a code list of '01' finds nothing.
    """
    m = re.fullmatch(r"GF(\d{2})(\d{2})?(\d{2})?", eurostat_code)
    if not m:
        return None
    parts = [p for p in m.groups() if p]
    out = parts[0]
    for p in parts[1:]:
        out += "." + p.lstrip("0").rjust(1, "0")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="IE")
    ap.add_argument("--year", default="2022")
    ap.add_argument("--unit", default="MIO_EUR")
    ap.add_argument("--out", default="examples/pilot-eurostat-budget")
    args = ap.parse_args()

    url = f"{API}&time={args.year}&unit={args.unit}&geo={args.geo}"
    d = fetch(url)
    gaps, notes = defaultdict(int), defaultdict(int)

    dims = d["dimension"]
    cofog = dims["cofog99"]["category"]
    idx = {v: k for k, v in cofog["index"].items()}          # position -> code
    labels = cofog["label"]
    country = dims["geo"]["category"]["label"][args.geo]

    currency, multiplier = UNITS.get(args.unit, (None, 1))
    if currency is None:
        print(f"unit {args.unit} has no known currency mapping", file=sys.stderr)
        return 1
    if multiplier != 1:
        notes[f"source reports in {dims['unit']['category']['label'][args.unit]}; "
              f"multiplied to whole {currency}"] += 1

    base = f"https://ec.europa.eu/eurostat/id/{args.geo.lower()}"
    juris_id = f"{base}/jurisdiction/{args.geo.lower()}"
    budget_id = f"{base}/budget/{args.year}-cofog"

    jurisdiction = {
        "@id": juris_id, "@type": "Country", "name": country,
        "governmentLevel": "national",
        "identifier": [{"@type": "PropertyValue", "propertyID": "iso3166-1-alpha2",
                        "value": args.geo}],
    }
    org_id = f"{base}/organization/general-government"
    org = {
        "@id": org_id, "@type": "GovernmentOrganization",
        "name": f"{country} general government",
        "description": "ESA 2010 sector S13, general government. A statistical sector "
                       "rather than a named body: Eurostat reports the sector, not the "
                       "ministries within it.",
        "identifier": [{"@type": "PropertyValue", "propertyID": "local:esa-sector",
                        "value": "S13"}],
        "organizationClassification": "executive",
        "areaServed": {"@id": juris_id, "name": country},
    }

    lines, total = [], None
    for pos, value in d["value"].items():
        code = idx.get(int(pos))
        if not code:
            continue
        if code == "TOTAL":
            # A total row sits alongside the breakdown. Importing it as a line would
            # double every figure, so it becomes the budget total instead.
            total = value * multiplier
            notes["TOTAL row carried as the budget total, not as a line"] += 1
            continue
        mapped = cofog_code(code)
        if not mapped:
            gaps[f"cofog:{code}"] += 1
            continue
        # Eurostat publishes divisions and their sub-groups in the same response.
        # Emitting both would double-count, so only divisions are taken as lines and
        # the sub-groups are recorded as their parts.
        depth = mapped.count(".")
        lines.append({
            "@id": f"{base}/budget-line/{args.year}/{mapped.replace('.', '-')}",
            "@type": "BudgetLine",
            "name": labels.get(code, code),
            "budget": {"@id": budget_id},
            "amount": {"@type": "MonetaryAmount", "value": round(value * multiplier, 2),
                       "currency": currency},
            "direction": "expenditure",
            "functionalClassification": mapped,
            "budgetPhase": "executed",
            "_depth": depth,
        })

    # nest sub-groups under their division
    by_code = {l["functionalClassification"]: l for l in lines}
    for l in lines:
        c = l["functionalClassification"]
        if "." in c:
            parent = by_code.get(c.split(".")[0])
            if parent:
                l["isPartOf"] = {"@id": parent["@id"], "name": parent["name"]}
                parent.setdefault("hasPart", []).append({"@id": l["@id"]})
    top = [l for l in lines if "." not in l["functionalClassification"]]
    for l in lines:
        l.pop("_depth", None)

    budget = {
        "@id": budget_id, "@type": "Budget",
        "name": f"{country} general government expenditure by function, {args.year}",
        "description": "Outturn statistics published by Eurostat, classified by COFOG.",
        "publisher": {"@id": org_id, "name": org["name"]},
        "about": {"@id": juris_id, "name": country},
        "budgetPhase": "executed",
        "fiscalYear": args.year,
        "startDate": f"{args.year}-01-01", "endDate": f"{args.year}-12-31",
        "currency": currency,
        "dateModified": (d.get("updated") or "")[:10],
        "sourceDataset": url,
        "budgetLine": [{"@id": l["@id"]} for l in lines],
    }
    if total is not None:
        budget["totalAmount"] = {"@type": "MonetaryAmount", "value": round(total, 2),
                                 "currency": currency}
        s = round(sum(l["amount"]["value"] for l in top), 2)
        if abs(s - round(total, 2)) > 1:
            notes[f"divisions sum to {s:,.0f} against a published total of {total:,.0f}"] += 1

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    (out / "jurisdictions.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [jurisdiction]}, indent=2, ensure_ascii=False) + "\n")
    (out / "organizations.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [org]}, indent=2, ensure_ascii=False) + "\n")
    (out / "budget.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [budget] + lines}, indent=2, ensure_ascii=False) + "\n")

    print(f"eurostat-cofog adapter: {country} {args.year} -> {len(lines)} budget line(s) "
          f"({len(top)} divisions)")
    print(f"  written to {out}/")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1]):
                print(f"    {k}  ({n}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
