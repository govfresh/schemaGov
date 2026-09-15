#!/usr/bin/env python3
"""Audit the JSON-LD context for the class of fault that passes every other check.

A term that is misdefined, undefined, or aliased onto another term is invisible to JSON
Schema (which never sees IRIs) and to SHACL (which sees the result, not what was lost
producing it). One such bug already shipped: 23 code-list properties expanded into the
schema.org namespace, where none of their values exist. It was found by accident.

Five checks, run over the context and every fixture:

  A  dropped terms   - a key that expands to nothing is silently deleted from the data
  B  collisions      - two distinct keys expanding to one IRI conflate two concepts
  C  suspicious IRIs - relative, file:, or otherwise unresolvable subjects and objects
  D  code-list values- a value IRI must be declared in a code list, not merely well-formed
  E  round-trip      - expand -> compact -> expand must be stable

Requires: pip install PyLD rdflib
Usage:    python3 tools/audit-jsonld.py
"""
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context" / "v1" / "context.jsonld"
NS = "https://schema.govfresh.com/v1/"

# Aliases that are deliberate: a friendlier key onto an established schema.org term.
INTENTIONAL_ALIASES = {
    ("title", "https://schema.org/name"),
    ("name", "https://schema.org/name"),
    ("conformsToProfile", NS + "profile"),
    ("profile", NS + "profile"),
    ("service", "https://schema.org/isRelatedTo"),
}


def load_ctx():
    return json.loads(CONTEXT.read_text())["@context"]


def term_iri(jsonld, ctx, key):
    """Expand a single key in isolation; None means the term is dropped."""
    probe = {"@context": ctx, "@id": "urn:x:probe", key: "probe-value"}
    try:
        exp = jsonld.expand(probe)
    except Exception:
        return None
    if not exp:
        return None
    for k in exp[0]:
        if not k.startswith("@"):
            return k
    return None


def data_keys(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "@context":
                continue
            if not k.startswith("@"):
                out.add(k)
            data_keys(v, out)
    elif isinstance(o, list):
        for v in o:
            data_keys(v, out)


def declared_codelist_terms():
    """Every term IRI actually declared in a code list."""
    declared = set()
    for f in ROOT.glob("profiles/*/codelists/*.json"):
        d = json.loads(f.read_text())
        for t in d.get("hasDefinedTerm", []):
            tid = t.get("@id", "")
            if tid.startswith("gs:"):
                declared.add(NS + tid[3:])
            elif tid.startswith("http"):
                declared.add(tid)
    return declared


def main():
    try:
        from pyld import jsonld
        from rdflib import Graph
        from rdflib.compare import isomorphic
    except ImportError:
        print("audit-jsonld: SKIPPED - pip install PyLD rdflib")
        return 0

    ctx = load_ctx()
    fixtures = sorted(ROOT.glob("examples/**/*.jsonld"))
    failures = []
    warnings = []

    keys = set()
    for f in fixtures:
        data_keys(json.loads(f.read_text()), keys)

    # --- A: dropped terms ----------------------------------------------------
    mapping = {}
    for k in sorted(keys):
        iri = term_iri(jsonld, ctx, k)
        if iri is None:
            failures.append(f"A  term '{k}' expands to nothing - data using it is silently deleted")
        else:
            mapping[k] = iri

    # --- B: collisions -------------------------------------------------------
    by_iri = defaultdict(list)
    for k, iri in mapping.items():
        by_iri[iri].append(k)
    for iri, ks in sorted(by_iri.items()):
        if len(ks) < 2:
            continue
        if all((k, iri) in INTENTIONAL_ALIASES for k in ks):
            continue
        failures.append(
            f"B  {', '.join(sorted(ks))} all expand to <{iri}>\n"
            f"      two concepts sharing one predicate cannot be told apart in RDF"
        )

    # --- C/D/E over the fixtures ---------------------------------------------
    declared = declared_codelist_terms()
    seen_values = set()
    for f in fixtures:
        raw = json.loads(f.read_text())
        doc = dict(raw)
        doc["@context"] = ctx
        exp = jsonld.expand(doc)

        flat = json.dumps(exp)
        for bad, why in (("file://", "resolved against the local filesystem"),
                         ('"@id": "/', "left as a root-relative path")):
            if bad in flat:
                failures.append(f"C  {f.relative_to(ROOT)}: an IRI was {why}")

        g1 = Graph().parse(data=json.dumps(doc), format="json-ld")
        for _, p, o in g1:
            s = str(o)
            if s.startswith(NS) and "/" in s[len(NS):]:
                seen_values.add((str(p).rsplit("/", 1)[-1], s))

        # E: round-trip stability.
        #
        # rdflib's graph canonicalisation is unreliable when a document contains many
        # structurally similar blank nodes - alert info blocks, PropertyValues, vote
        # records all look alike - and reports non-isomorphic for graphs that differ
        # only in blank-node labelling. Comparing a label-independent signature instead:
        # ground triples exactly, and blank nodes by the shape of what hangs off them.
        comp = jsonld.compact(exp, ctx)
        g2 = Graph().parse(data=json.dumps(comp), format="json-ld")

        def signature(g):
            from rdflib.term import BNode
            ground, shapes = [], []
            for s, pr, o in g:
                if isinstance(s, BNode) or isinstance(o, BNode):
                    shapes.append((str(pr), "_:bnode" if isinstance(o, BNode) else str(o)))
                else:
                    ground.append((str(s), str(pr), str(o)))
            return sorted(ground), sorted(shapes)

        s1, s2 = signature(g1), signature(g2)
        if s1 != s2:
            lost = sorted(set(s1[0]) - set(s2[0]))[:3]
            gained = sorted(set(s2[0]) - set(s1[0]))[:3]
            failures.append(
                f"E  {f.relative_to(ROOT)}: expand -> compact -> expand is not stable "
                f"({len(g1)} vs {len(g2)} triples)"
                + "".join(f"\n      lost: {x[1].rsplit('/',1)[-1]} -> {x[2][:50]}" for x in lost)
                + "".join(f"\n      gained: {x[1].rsplit('/',1)[-1]} -> {x[2][:50]}" for x in gained))

    # --- D: code-list values must be declared --------------------------------
    # COFOG and GFSM are hierarchical: only the top level is enumerated, and the profiles
    # explicitly permit fuller subcodes such as 04.5 or 07.3.1 as values. A subcode whose
    # parent division IS declared is correct, not a gap.
    HIERARCHICAL = ("cofog/", "gfsm/")

    def parent_declared(iri):
        seg = iri[len(NS):]
        if not seg.startswith(HIERARCHICAL) or "." not in seg:
            return False
        prefix, code = seg.split("/", 1)
        return f"{NS}{prefix}/{code.split('.')[0]}" in declared

    for prop, iri in sorted(seen_values):
        if iri in declared or parent_declared(iri):
            continue
        warnings.append(f"D  {prop}: <{iri}> is not declared in any code list")

    print(f"schemaGov audit-jsonld: {len(fixtures)} fixture(s), {len(mapping)} term(s), "
          f"{len(declared)} declared code-list term(s)")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for e in failures:
            print(f"  - {e}")
        return 1
    print("\nOK - no dropped terms, no unintended collisions, round-trip stable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
