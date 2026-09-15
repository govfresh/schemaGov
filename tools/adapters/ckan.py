#!/usr/bin/env python3
"""Convert a real CKAN portal into the schemaGov catalog profile.

CKAN powers most national and municipal open-data portals, and DCAT-AP is the metadata
model behind them. This adapter reads a live CKAN API and projects it.

    python3 tools/adapters/ckan.py --url https://data.gov.ie --rows 60 \
        --out examples/pilot-ie-datasets

Portals use their own theme and frequency vocabularies, so values are normalised through
explicit tables below. Every value that cannot be mapped confidently is reported rather
than silently guessed at - a mapping table that quietly invents codes is worse than one
that admits a gap.
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

UA = "schemaGov-adapter/1.0 (+https://schema.govfresh.com)"

# Portal theme label -> EU data-theme code. Portals rarely use the EU codes directly.
# Confidence is recorded because a wrong theme is worse than an absent one.
THEME_MAP = {
    "government": ("GOVE", "high"), "public sector": ("GOVE", "high"),
    "health": ("HEAL", "high"), "education": ("EDUC", "high"),
    "environment": ("ENVI", "high"), "energy": ("ENER", "high"),
    "transport": ("TRAN", "high"), "transportation": ("TRAN", "high"),
    "economy": ("ECON", "high"), "finance": ("ECON", "high"),
    "agriculture": ("AGRI", "high"), "justice": ("JUST", "high"),
    "society": ("SOCI", "high"), "population": ("SOCI", "high"),
    "science": ("TECH", "high"), "technology": ("TECH", "high"),
    "international": ("INTR", "high"), "regions": ("REGI", "high"),
    # Lower confidence: no exact EU theme exists for these.
    "housing": ("SOCI", "low"), "planning": ("REGI", "low"),
    "culture": ("EDUC", "low"), "sport": ("EDUC", "low"),
}

# Portal frequency label -> ISO 8601 duration, or a bare token.
FREQUENCY_MAP = {
    "continuous": "continuous", "continuously updated": "continuous",
    "real-time": "continuous", "realtime": "continuous",
    "daily": "P1D", "weekly": "P1W", "fortnightly": "P2W", "biweekly": "P2W",
    "monthly": "P1M", "bimonthly": "P2M", "quarterly": "P3M",
    "semiannual": "P6M", "biannual": "P6M", "half-yearly": "P6M",
    "annual": "P1Y", "yearly": "P1Y", "annually": "P1Y",
    "biennial": "P2Y", "triennial": "P3Y",
    "irregular": "irregular", "as needed": "irregular", "unknown": "irregular",
    "never": "never", "not planned": "never", "discontinued": "never",
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:90]


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


def pick_title(pkg):
    """CKAN carries both a plain title and a per-language map.

    schemaGov has one `name` plus `inLanguage`, so a genuinely multilingual dataset
    loses its other titles here. That is a real limitation, reported when it bites -
    and on data.gov.ie it does not: title_translated carries only English.
    """
    tt = pkg.get("title_translated") or {}
    populated = {k: v for k, v in tt.items() if (v or "").strip()}
    return pkg.get("title") or next(iter(populated.values()), pkg.get("name")), populated


def convert(pkgs, base, portal_url, gaps, notes):
    orgs, datasets = {}, []

    for pkg in pkgs:
        title, translations = pick_title(pkg)
        if len(translations) > 1:
            notes["multilingual titles flattened to one name"] += 1

        # publisher -> a _core GovernmentOrganization. No areaServed: a portal states
        # who published a dataset, not which territory that body governs.
        org = pkg.get("organization") or {}
        pub_ref = None
        if org.get("name"):
            oid = f"{base}/organization/{slug(org['name'])}"
            orgs[oid] = {
                "@id": oid, "@type": "GovernmentOrganization",
                "name": org.get("title") or org["name"],
                "identifier": [{"@type": "PropertyValue",
                                "propertyID": "local:ckan-org",
                                "value": org["name"]}],
                "organizationClassification": "agency",
            }
            if org.get("description"):
                orgs[oid]["description"] = org["description"][:500]
            pub_ref = {"@id": oid, "name": orgs[oid]["name"]}

        # themes
        themes, keywords = [], [t["name"] for t in pkg.get("tags") or [] if t.get("name")]
        raw_theme = pkg.get("theme")
        for label in ([raw_theme] if isinstance(raw_theme, str) else (raw_theme or [])):
            if not label:
                continue
            code, conf = THEME_MAP.get(str(label).strip().lower(), (None, None))
            if code:
                if code not in themes:
                    themes.append(code)
                if conf == "low":
                    notes[f"theme '{label}' mapped to {code} with low confidence"] += 1
            else:
                gaps[f"theme:{label}"] += 1
            if str(label) not in keywords:
                keywords.append(str(label))

        # frequency
        freq = None
        raw_freq = pkg.get("frequency")
        if raw_freq:
            freq = FREQUENCY_MAP.get(str(raw_freq).strip().lower())
            if not freq:
                gaps[f"frequency:{raw_freq}"] += 1

        distributions = []
        for res in pkg.get("resources") or []:
            dl = {"@type": "DataDownload"}
            if res.get("name"):
                dl["name"] = res["name"]
            if res.get("url"):
                dl["contentUrl"] = res["url"]
            if res.get("access_url") and res.get("access_url") != res.get("url"):
                dl["accessUrl"] = res["access_url"]
            fmt = res.get("mimetype") or res.get("format")
            if fmt:
                dl["encodingFormat"] = str(fmt)
            if res.get("size"):
                dl["contentSize"] = str(res["size"])
            if res.get("last_modified") or res.get("metadata_modified"):
                dl["dateModified"] = (res.get("last_modified") or res["metadata_modified"])[:19]
            if dl.get("contentUrl") or dl.get("accessUrl"):
                distributions.append(dl)
        if not distributions:
            notes["dataset skipped: no resolvable distribution"] += 1
            continue

        d = {
            "@id": f"{base}/dataset/{slug(pkg.get('name') or pkg['id'])}",
            "@type": "Dataset",
            "name": title,
            "publisher": pub_ref,
            "url": f"{portal_url.rstrip('/')}/dataset/{pkg.get('name')}",
            "identifier": [{"@type": "PropertyValue", "propertyID": "local:ckan-id",
                            "value": pkg["id"]}],
            "includedInDataCatalog": {"@id": f"{base}/catalog/portal"},
            "keywords": keywords or None,
            "dataTheme": themes or None,
            "updateFrequency": freq,
            "accessRights": "public" if pkg.get("isopen") else "restricted",
            "dateModified": (pkg.get("metadata_modified") or "")[:19] or None,
            "datePublished": (pkg.get("metadata_created") or "")[:10] or None,
            "license": pkg.get("license_url") or None,
            "inLanguage": [pkg["language"]] if pkg.get("language") else None,
            "distribution": distributions,
        }
        desc = pkg.get("notes") or (pkg.get("notes_translated") or {}).get("en")
        if desc:
            d["description"] = desc[:1200]
        if pkg.get("temporal_start"):
            d["temporalCoverage"] = f"{pkg['temporal_start'][:10]}/{(pkg.get('temporal_end') or '')[:10]}"

        # Fields the first run of this adapter reported as unmapped, now carried.
        if pkg.get("applicable_legislation"):
            al = pkg["applicable_legislation"]
            d["applicableLegislation"] = al if isinstance(al, list) else [al]
        if pkg.get("hvd_category"):
            d["hvdCategory"] = pkg["hvd_category"]
        if pkg.get("high_value_dataset") is not None:
            d["highValueDataset"] = bool(pkg["high_value_dataset"])
        if pkg.get("srs"):
            srs = pkg["srs"]
            d["spatialReferenceSystem"] = (srs[0] if isinstance(srs, list) else srs)
        if pkg.get("conforms_to"):
            ct = pkg["conforms_to"]
            d["conformsTo"] = ct if isinstance(ct, list) else [str(ct)]
        if pkg.get("provenance"):
            d["provenanceStatement"] = str(pkg["provenance"])[:500]

        # Still unmapped.
        for f in ("spatial_uri", "spatial_resolution", "rights", "collection_name"):
            if pkg.get(f) not in (None, "", [], {}):
                gaps[f"field:{f}"] += 1

        datasets.append({k: v for k, v in d.items() if v is not None})

    return list(orgs.values()), datasets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="CKAN portal root, e.g. https://data.gov.ie")
    ap.add_argument("--rows", type=int, default=50)
    ap.add_argument("--base")
    ap.add_argument("--out", default="examples/pilot-ckan")
    args = ap.parse_args()

    portal = args.url.rstrip("/")
    base = (args.base or f"{portal}/id").rstrip("/")
    api = f"{portal}/api/3/action/package_search?rows={args.rows}"

    payload = fetch(api)
    if not payload.get("success"):
        print("CKAN API returned success=false", file=sys.stderr)
        return 1
    result = payload["result"]
    pkgs = result["results"]

    gaps, notes = defaultdict(int), defaultdict(int)
    orgs, datasets = convert(pkgs, base, portal, gaps, notes)

    catalog = {
        "@id": f"{base}/catalog/portal", "@type": "DataCatalog",
        "name": f"{urllib.parse.urlparse(portal).netloc} open data catalogue",
        "url": portal,
        "publisher": {"@id": orgs[0]["@id"], "name": orgs[0]["name"]} if orgs else None,
        "dataset": [{"@id": d["@id"]} for d in datasets],
    }
    catalog = {k: v for k, v in catalog.items() if v is not None}

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    (out / "organizations.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": orgs}, indent=2, ensure_ascii=False) + "\n")
    (out / "catalog.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [catalog] + datasets}, indent=2, ensure_ascii=False) + "\n")

    print(f"ckan adapter: {portal} ({result['count']:,} datasets on portal)")
    print(f"  converted {len(datasets)} dataset(s), {len(orgs)} organization(s) -> {out}/")
    if notes:
        print("\n  conversion notes:")
        for k, n in sorted(notes.items(), key=lambda x: -x[1]):
            print(f"    {k:56} {n}x")
    if gaps:
        print("\n  values and fields with no schemaGov mapping:")
        for k, n in sorted(gaps.items(), key=lambda x: -x[1]):
            print(f"    {k:56} {n}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
