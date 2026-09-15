#!/usr/bin/env python3
"""Convert legislation.gov.uk into the schemaGov code profile.

legislation.gov.uk is the UK statute book, published as CLML with ELI-style identifiers
and consolidated ("revised") texts. The code profile makes the strongest claims in
schemaGov - that schema.org's ELI-derived vocabulary does nearly all the work, that the
FRBR work/expression split is real, and that document structure belongs to Akoma Ntoso
rather than here. This is the test of those claims.

    python3 tools/adapters/legislation-uk.py --uri ukpga/2014/30 \
        --out examples/pilot-uk-legislation
"""
import argparse
import json
import pathlib
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

SITE = "https://www.legislation.gov.uk"
UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"
NS = {"l": "http://www.legislation.gov.uk/namespaces/legislation",
      "ukm": "http://www.legislation.gov.uk/namespaces/metadata",
      "dc": "http://purl.org/dc/elements/1.1/"}

# legislation.gov.uk document types -> the profile's legislationType code list.
DOC_TYPE = {
    "ukpga": "act", "asp": "act", "nia": "act", "anaw": "act", "aosp": "act",
    "ukla": "act", "apgb": "act", "aep": "act",
    "uksi": "regulation", "ssi": "regulation", "wsi": "regulation", "nisr": "regulation",
    "ukci": "decree", "ukmo": "decree", "ukcm": "decree",
    "eur": "regulation", "eudn": "decree", "eudr": "directive",
}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return r.read()


def text_of(el, path):
    v = el.findtext(path, namespaces=NS)
    return re.sub(r"\s+", " ", v).strip() if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="ukpga/2014/30",
                    help="legislation.gov.uk path, e.g. ukpga/2014/30")
    ap.add_argument("--base", default=f"{SITE}/id")
    ap.add_argument("--out", default="examples/pilot-uk-legislation")
    args = ap.parse_args()

    gaps, notes = defaultdict(int), defaultdict(int)

    root = ET.fromstring(fetch(f"{SITE}/{args.uri}/contents/data.xml"))
    meta = root.find(".//ukm:Metadata", NS)

    doc_uri = root.get("DocumentURI") or f"{SITE}/{args.uri}"
    id_uri = root.get("IdURI") or doc_uri
    kind = args.uri.split("/")[0]
    title = text_of(meta, "dc:title") or args.uri

    enacted = meta.find(".//ukm:EnactmentDate", NS)
    enacted = enacted.get("Date") if enacted is not None else None
    year = text_of(meta, ".//ukm:Year") or (meta.find(".//ukm:Year", NS).get("Value")
                                            if meta.find(".//ukm:Year", NS) is not None else None)
    number = meta.find(".//ukm:Number", NS)
    number = number.get("Value") if number is not None else None
    status = meta.find(".//ukm:DocumentStatus", NS)
    status = (status.get("Value") if status is not None else None) or root.get("Status")
    version_date = text_of(meta, "dc:modified")

    juris_id = f"{args.base}/jurisdiction/gb"
    jurisdiction = {"@id": juris_id, "@type": "Country", "name": "United Kingdom",
                    "governmentLevel": "national",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "iso3166-1-alpha2", "value": "GB"}]}
    org_id = f"{args.base}/organization/uk-parliament"
    org = {"@id": org_id, "@type": "GovernmentOrganization", "name": "Parliament of the United Kingdom",
           "identifier": [{"@type": "PropertyValue", "propertyID": "local:legislation-gov-uk",
                           "value": "parliament"}],
           "organizationClassification": "legislature",
           "areaServed": {"@id": juris_id, "name": "United Kingdom"}}

    leg_type = DOC_TYPE.get(kind)
    if not leg_type:
        gaps[f"documentType:{kind}"] += 1
        leg_type = "act"

    act = {
        "@id": id_uri, "@type": "Legislation", "name": title,
        "url": doc_uri,
        "legislationType": leg_type,
        "codificationLevel": "code" if kind.endswith("si") else "title",
        "legislationIdentifier": f"{year} c. {number}" if year and number else args.uri,
        "identifier": [{"@type": "PropertyValue", "propertyID": "local:legislation-gov-uk",
                        "value": args.uri}],
        "legislationJurisdiction": {"@id": juris_id, "name": "United Kingdom"},
        "legislationPassedBy": {"@id": org_id, "name": org["name"]},
        "inLanguage": ["en-GB"],
        "hasPart": [],
    }
    if enacted:
        act["legislationDate"] = enacted
    # The Akoma Ntoso rendering carries FRBR identification, which is the authoritative
    # source for the version date. dc:modified is when the RECORD was last touched;
    # the FRBR Expression date is what the consolidated text is valid AT. Using the
    # former for legislationDateVersion is wrong by a year and a half on this act.
    frbr = {}
    try:
        akn = ET.fromstring(fetch(f"{doc_uri}/data.akn"))
        ident = akn.find(".//{*}identification")
        for lvl in ("FRBRWork", "FRBRExpression", "FRBRManifestation"):
            el = ident.find(f".//{{*}}{lvl}") if ident is not None else None
            if el is None:
                continue
            uri = el.find("{*}FRBRuri")
            dt = el.find("{*}FRBRdate")
            frbr[lvl] = {"uri": uri.get("value") if uri is not None else None,
                         "date": dt.get("date") if dt is not None else None,
                         "name": dt.get("name") if dt is not None else None}
        mods = akn.findall(".//{*}passiveModifications/{*}textualMod")
        mods += akn.findall(".//{*}activeModifications/{*}textualMod")
        if not mods:
            notes["no textual modifications in the AKN; the ELI amendment graph "
                  "(legislationAmends/Repeals/...) remains untested"] += 1
    except Exception as e:
        notes[f"Akoma Ntoso rendering unavailable: {type(e).__name__}"] += 1

    expr = frbr.get("FRBRExpression", {})
    if expr.get("date"):
        act["legislationDateVersion"] = expr["date"]
        if version_date and version_date != expr["date"]:
            notes[f"dc:modified {version_date} differs from the FRBR Expression date "
                  f"{expr['date']}; the Expression date is what the text is valid at"] += 1
    elif version_date:
        act["legislationDateVersion"] = version_date
    if status:
        act["legislationLegalForce"] = "InForce" if status.lower() in ("revised", "final") else "PartiallyInForce"
        notes[f"document status '{status}' read as {act['legislationLegalForce']}"] += 1

    # The authoritative text is the CLML itself. The profile's position is that document
    # structure belongs to a legal markup standard, linked rather than absorbed.
    manifest = frbr.get("FRBRManifestation", {}).get("uri") or f"{doc_uri}/data.akn"
    act["encoding"] = [
        {"@type": "LegislationObject",
         "contentUrl": manifest,
         "encodingFormat": "application/akn+xml",
         "legislationLegalValue": "OfficialLegalValue",
         "conformsTo": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0",
         "inLanguage": "en-GB"},
        {"@type": "LegislationObject",
         "contentUrl": f"{doc_uri}/data.xml",
         "encodingFormat": "application/xml",
         "legislationLegalValue": "OfficialLegalValue",
         "conformsTo": "http://www.legislation.gov.uk/namespaces/legislation",
         "inLanguage": "en-GB"},
        {"@type": "LegislationObject",
         "contentUrl": doc_uri,
         "encodingFormat": "text/html",
         "legislationLegalValue": "UnofficialLegalValue",
         "inLanguage": "en-GB"},
    ]
    notes["structure lives in Akoma Ntoso and is linked, not absorbed (SPEC 1.4)"] += 1

    parts = []
    for p in root.iterfind(".//l:ContentsPart", NS):
        pid = p.get("IdURI") or p.get("DocumentURI")
        if not pid:
            continue
        num = text_of(p, "l:ContentsNumber")
        ptitle = text_of(p, "l:ContentsTitle") or num or "Part"
        part = {
            "@id": pid, "@type": "Legislation",
            "name": ptitle,
            "legislationType": leg_type,
            "codificationLevel": "part",
            "legislationIdentifier": num,
            "legislationJurisdiction": {"@id": juris_id},
            "isPartOf": {"@id": act["@id"], "name": act["name"]},
            "hasPart": [],
        }
        if num and num.isdigit():
            part["position"] = int(num)
        # sections nested inside this part
        for item in p.iterfind(".//l:ContentsItem", NS):
            iid = item.get("IdURI") or item.get("DocumentURI")
            if not iid:
                continue
            inum = text_of(item, "l:ContentsNumber")
            sec = {
                "@id": iid, "@type": "Legislation",
                "name": text_of(item, "l:ContentsTitle") or inum or "Section",
                "legislationType": leg_type,
                "codificationLevel": "section",
                "legislationIdentifier": inum,
                "legislationJurisdiction": {"@id": juris_id},
                "isPartOf": {"@id": pid, "name": ptitle},
            }
            if inum and inum.isdigit():
                sec["position"] = int(inum)
            part["hasPart"].append({"@id": iid, "name": sec["name"]})
            parts.append(sec)
        act["hasPart"].append({"@id": pid, "name": ptitle})
        parts.append(part)

    if not act["hasPart"]:
        notes["no Part level; sections hang directly off the act"] += 1
        for item in root.iterfind(".//l:ContentsItem", NS):
            iid = item.get("IdURI")
            if not iid:
                continue
            inum = text_of(item, "l:ContentsNumber")
            sec = {"@id": iid, "@type": "Legislation",
                   "name": text_of(item, "l:ContentsTitle") or inum or "Section",
                   "legislationType": leg_type, "codificationLevel": "section",
                   "legislationIdentifier": inum,
                   "legislationJurisdiction": {"@id": juris_id},
                   "isPartOf": {"@id": act["@id"], "name": act["name"]}}
            act["hasPart"].append({"@id": iid, "name": sec["name"]})
            parts.append(sec)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    CTX = "https://schema.govfresh.com/v1/context.jsonld"
    (out / "jurisdictions.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [jurisdiction]}, indent=2, ensure_ascii=False) + "\n")
    (out / "organizations.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [org]}, indent=2, ensure_ascii=False) + "\n")
    (out / "code.jsonld").write_text(
        json.dumps({"@context": CTX, "@graph": [act] + parts}, indent=2, ensure_ascii=False) + "\n")

    print(f"legislation-uk adapter: {title}")
    print(f"  {len([p for p in parts if p['codificationLevel']=='part'])} part(s), "
          f"{len([p for p in parts if p['codificationLevel']=='section'])} section(s) -> {out}/")
    for label, data in (("conversion notes", notes), ("values with no mapping", gaps)):
        if data:
            print(f"\n  {label}:")
            for k, n in sorted(data.items(), key=lambda x: -x[1]):
                print(f"    {k}  ({n}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
