#!/usr/bin/env python3
"""Every gs: term the context, schemas and shapes use must be defined in the vocabulary.

vocabulary/schemagov.ttl is what the per-term pages are built from, so a term that is used
but not defined has no page: its IRI is published inside documents and resolves to nothing.

Checks:
  1. every `gs:Name` in context/v1/context.jsonld, profiles/*/schema/*.json and
     shapes/schemaGov.shapes.ttl is declared in vocabulary/schemagov.ttl
  2. every code list set (profiles/*/codelists) is declared there as a schema:DefinedTermSet
  3. no two terms differ only by letter case without being listed (informational: those
     share one page, see PLAN-per-term-pages.md)

Usage:  python3 tools/check-vocabulary.py
Requires: pip install rdflib
"""
import json
import pathlib
import re
import sys

from rdflib import Graph, Namespace, RDF, RDFS
SH = Namespace("http://www.w3.org/ns/shacl#")

ROOT = pathlib.Path(__file__).resolve().parent.parent
GS = Namespace("https://schema.govfresh.com/v1/")
SCHEMA = Namespace("https://schema.org/")
# gs:Name, but not a code list value such as gs:orgclass/division
TOKEN = re.compile(r"\bgs:([A-Za-z][A-Za-z0-9]*)(?![A-Za-z0-9/_-])")
NS_URL = re.compile(r"https://schema\.govfresh\.com/v1/([A-Za-z][A-Za-z0-9]*)(?![A-Za-z0-9/_.-])")
# Identifiers that are values in documents, not vocabulary terms.
NOT_TERMS = {"local"}


def defined_terms():
    g = Graph()
    g.parse(ROOT / "vocabulary" / "schemagov.ttl", format="turtle")
    kinds = (RDFS.Class, RDF.Property, SCHEMA.DefinedTermSet)
    names = set()
    for k in kinds:
        for s in g.subjects(RDF.type, k):
            if str(s).startswith(str(GS)):
                names.add(str(s)[len(str(GS)):])
    return names


def shape_names():
    """Names of SHACL shapes, which live in the gs: namespace but are not vocabulary terms."""
    g = Graph()
    g.parse(ROOT / "shapes" / "schemaGov.shapes.ttl", format="turtle")
    return {str(s)[len(str(GS)):] for s in g.subjects(RDF.type, SH.NodeShape) if str(s).startswith(str(GS))}


def used_terms():
    used = {}  # name -> first place

    def scan(text, where):
        for rx in (TOKEN, NS_URL):
            for m in rx.finditer(text):
                used.setdefault(m.group(1), where)

    scan((ROOT / "context/v1/context.jsonld").read_text(), "context/v1/context.jsonld")
    for f in sorted((ROOT / "profiles").glob("*/schema/*.json")):
        scan(f.read_text(), str(f.relative_to(ROOT)))
    scan((ROOT / "shapes/schemaGov.shapes.ttl").read_text(), "shapes/schemaGov.shapes.ttl")
    return used


def main():
    defined = defined_terms()
    used = used_terms()
    shapes = shape_names()
    problems = []

    for name, where in sorted(used.items()):
        if name in defined or name in NOT_TERMS or name in shapes:
            continue
        problems.append(f"gs:{name} is used in {where} but not defined in vocabulary/schemagov.ttl")

    for f in sorted((ROOT / "profiles").glob("*/codelists/*.json")):
        seg = json.loads(f.read_text())["@id"].rsplit("/", 1)[-1]
        if seg not in defined:
            problems.append(f"code list {seg} ({f.relative_to(ROOT)}) is not declared in vocabulary/schemagov.ttl")

    lower = {}
    for n in defined:
        lower.setdefault(n.lower(), []).append(n)
    shared = sum(1 for v in lower.values() if len(v) > 1)

    print(f"check-vocabulary: {len(defined)} terms defined, {len(used)} used, "
          f"{shared} case-colliding group(s) rendered as one page")
    if problems:
        print("\nFAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK - every used term is defined")
    return 0


if __name__ == "__main__":
    sys.exit(main())
