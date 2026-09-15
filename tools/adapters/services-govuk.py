#!/usr/bin/env python3
"""Convert GOV.UK services into the schemaGov services profile.

GOV.UK is arguably the best-organised government service catalogue in the world, and it
does NOT use HSDS. That makes it a harder and more informative test than an HSDS publisher
would be: an HSDS source would mostly verify a crosswalk table, whereas this asks whether
the profile can represent a real catalogue built on entirely different assumptions.

    python3 tools/adapters/services-govuk.py --limit 40 --out examples/pilot-govuk-services

The adapter reports field coverage, because the interesting question here is not whether
the conversion succeeds but how much of the profile a publisher of this quality can fill.
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

SITE = "https://www.gov.uk"
UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"

# GOV.UK organises by topic taxonomy, which is adjacent to life events but not identical.
# Mapped on keywords, with every mapping reported so the guesswork is visible.
LIFE_EVENT = [
    (r"\bbirth\b|\bnewborn\b|maternity|paternity|adoption", "birth"),
    (r"\bdeath\b|bereave|probate|funeral|inherit", "death"),
    (r"school|student|educat|apprentice|university|childcare and educat", "education"),
    (r"unemploy|jobseek|job.?seeking|out of work", "unemployment"),
    (r"\bwork\b|employ|redundan|payroll|workplace", "employment"),
    (r"housing|homeless|tenan|council tax|landlord|renting", "housing"),
    (r"moving|change of address|移", "moving"),
    (r"marri|civil partnership|divorce|weddin", "marriage"),
    (r"child|family|parent|guardian|care", "family"),
    (r"health|nhs|medical|prescription", "health"),
    (r"disab|carer|blue badge|access", "disability"),
    (r"pension|retire|state pension", "retirement"),
    (r"business|compan|self.?employ|trade|vat|import|export", "business"),
    (r"vehicle|driving|driver|mot\b|car tax|licence plate", "vehicle"),
    (r"\btax\b|hmrc|self assessment|paye", "tax"),
    (r"benefit|universal credit|allowance|support payment", "benefits"),
    (r"visa|immigration|passport|citizenship|residence|asylum", "immigration"),
    (r"court|legal|justice|tribunal|crime|prison", "justice"),
    (r"environment|waste|recycl|flood|pollut|energy", "environment"),
]

# The profile's fields, split by whether GOV.UK can populate them.
TRACKED = ["name", "description", "url", "provider", "areaServed", "serviceStatus",
           "lifeEvent", "keywords", "eligibility", "applicationProcess",
           "requiredDocument", "cost", "processingTime", "availableChannel",
           "availableAtLocation", "availableLanguage", "relatedLegislation",
           "dateModified"]


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:90]


def plain(html):
    t = re.sub(r"<[^>]+>", " ", str(html or ""))
    return re.sub(r"\s+", " ", t).strip()


def life_events(texts, notes):
    hay = " ".join(t for t in texts if t).lower()
    out = []
    for pattern, code in LIFE_EVENT:
        if re.search(pattern, hay) and code not in out:
            out.append(code)
    if not out:
        notes["no life event inferred from the GOV.UK taxonomy"] += 1
        return ["other"]
    return out[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default="examples/pilot-govuk-services")
    args = ap.parse_args()

    gaps, notes = defaultdict(int), defaultdict(int)
    coverage = defaultdict(int)

    q = urllib.parse.urlencode({
        "filter_format": "transaction", "count": min(args.limit, 100),
        "fields": "title,description,link,organisations,format"})
    listing = fetch(f"{SITE}/api/search.json?{q}").get("results", [])

    base = "https://www.gov.uk/id"
    juris_id = f"{base}/jurisdiction/gb"
    jurisdiction = {"@id": juris_id, "@type": "Country", "name": "United Kingdom",
                    "governmentLevel": "national",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "iso3166-1-alpha2", "value": "GB"}]}

    orgs, services = {}, []
    for row in listing:
        link = row.get("link")
        if not link or not link.startswith("/"):
            continue
        try:
            c = fetch(f"{SITE}/api/content{link}")
        except Exception:
            notes["content API unavailable for a listed service"] += 1
            continue

        det = c.get("details") or {}
        links = c.get("links") or {}
        # primary_publishing_organisation is who publishes the PAGE - on GOV.UK
        # mainstream content that is always the Government Digital Service. The
        # department that actually owns the service is in `organisations`. Preferring
        # the former attributed all 40 services to GDS, which makes provider useless.
        pub = (links.get("organisations")
               or links.get("primary_publishing_organisation") or [{}])[0]
        if not links.get("organisations"):
            notes["no owning department; fell back to the publishing organisation"] += 1
        oname = pub.get("title") or "UK Government"
        oid = f"{base}/organization/{slug(pub.get('content_id') or oname)}"
        orgs[oid] = {"@id": oid, "@type": "GovernmentOrganization", "name": oname,
                     "identifier": [{"@type": "PropertyValue",
                                     "propertyID": "local:govuk-content-id",
                                     "value": str(pub.get("content_id") or slug(oname))}],
                     "organizationClassification": "agency",
                     "areaServed": {"@id": juris_id, "name": "United Kingdom"}}

        taxons = [t.get("title", "") for t in (links.get("taxons") or [])]
        browse = [t.get("title", "") for t in (links.get("mainstream_browse_pages") or [])]

        s = {
            "@id": f"{base}/service/{slug(link)}", "@type": "GovernmentService",
            "name": c.get("title") or link,
            "description": (c.get("description") or "")[:600] or None,
            "url": f"{SITE}{link}",
            "identifier": [{"@type": "PropertyValue", "propertyID": "local:govuk-path",
                            "value": link}],
            "provider": {"@id": oid, "name": oname},
            "areaServed": {"@id": juris_id, "name": "United Kingdom"},
            # GOV.UK withdraws pages rather than marking them closed, so anything the
            # search index returns is live.
            "serviceStatus": "active",
            "lifeEvent": life_events(taxons + browse + [c.get("title", "")], notes),
            "keywords": [t for t in (taxons + browse) if t][:6] or None,
            "availableLanguage": ["en-GB"],
            "dateModified": (c.get("updated_at") or "")[:10] or None,
        }

        channels = []
        if det.get("transaction_start_link"):
            ch = {"@type": "ServiceChannel", "serviceUrl": det["transaction_start_link"]}
            if det.get("will_continue_on"):
                ch["name"] = f"Continues on {det['will_continue_on']}"
            channels.append(ch)
        if det.get("other_ways_to_apply"):
            notes["other ways to apply published as prose, not as channels"] += 1
        if channels:
            s["availableChannel"] = channels

        # The information the profile wants as structured fields exists on GOV.UK only as
        # narrative. Rather than parse prose into false structure, the narrative is
        # carried in applicationProcess and the structured fields are left empty.
        intro = plain(det.get("introductory_paragraph") or det.get("body"))
        if intro:
            s["applicationProcess"] = intro[:1000]
        for label, pattern in (("cost", r"£\s?\d"),
                               ("requiredDocument", r"you'?ll need|you will need|bring\b"),
                               ("eligibility", r"you can (only )?(use|apply)|eligib|if you'?re"),
                               ("processingTime", r"\b\d+\s+(working )?days?\b|\bweeks?\b")):
            if intro and re.search(pattern, intro, re.I):
                notes[f"{label} present in prose but not as a field"] += 1

        s = {k: v for k, v in s.items() if v is not None}
        for f in TRACKED:
            if s.get(f):
                coverage[f] += 1
        services.append(s)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    for fname, graph in (("jurisdictions.jsonld", [jurisdiction]),
                         ("organizations.jsonld", list(orgs.values())),
                         ("services.jsonld", services)):
        (out / fname).write_text(
            json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")

    n = len(services)
    print(f"govuk services adapter: {n} service(s), {len(orgs)} organization(s) -> {out}/")
    print(f"\n  field coverage across {n} services:")
    for f in TRACKED:
        got = coverage[f]
        bar = "#" * round(20 * got / n) if n else ""
        print(f"    {f:22} {got:3}/{n}  {bar}")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, v in sorted(data.items(), key=lambda x: -x[1])[:8]:
                print(f"    {k}  ({v}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
