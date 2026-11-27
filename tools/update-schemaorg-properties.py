#!/usr/bin/env python3
"""Refresh tools/schemaorg-properties.txt, the property names validate.py accepts.

Usage:  python3 tools/update-schemaorg-properties.py [downloaded-vocabulary.jsonld]

Without an argument it downloads the current schema.org vocabulary.
"""
import datetime
import json
import pathlib
import sys
import urllib.request

SOURCE = "https://schema.org/version/latest/schemaorg-all-https.jsonld"
OUT = pathlib.Path(__file__).resolve().parent / "schemaorg-properties.txt"


def main(argv):
    if len(argv) > 1:
        text = pathlib.Path(argv[1]).read_text()
    else:
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            text = response.read().decode("utf-8")
    names = set()
    for node in json.loads(text)["@graph"]:
        types = node.get("@type")
        if "rdf:Property" in (types if isinstance(types, list) else [types]):
            names.add(node["@id"].split(":", 1)[1])
    header = (f"# Property names defined by schema.org, including pending ones.\n"
              f"# Source: {SOURCE}\n"
              f"# schema.org vocabulary is licensed CC BY-SA 3.0. Retrieved {datetime.date.today()}.\n"
              f"# Do not edit. Refresh with tools/update-schemaorg-properties.py.\n")
    OUT.write_text(header + "".join(f"{n}\n" for n in sorted(names)))
    print(f"{len(names)} properties -> {OUT}")


if __name__ == "__main__":
    main(sys.argv)
