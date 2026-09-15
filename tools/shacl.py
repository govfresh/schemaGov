#!/usr/bin/env python3
"""Semantic validation of schemaGov instance data (SPEC section 4, tier two).

JSON Schema validates document shape; tools/validate.py checks that every reference
resolves. Neither can check what a reference resolves TO. A Role pointing at an
Organization instead of a Person is valid JSON, resolves cleanly, and is wrong.

This expands the examples to RDF and runs the SHACL shapes in shapes/ over them.

Requires: pip install pyshacl rdflib
Usage:    python3 tools/shacl.py [examples/example-city ...]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHAPES = ROOT / "shapes" / "schemaGov.shapes.ttl"
CONTEXT = ROOT / "context" / "v1" / "context.jsonld"


def build_graph(paths):
    """Merge every document into one RDF graph.

    The published @context URL is not resolvable during development, and relying on
    the network to validate would make the check flaky. The local context file is
    inlined instead - it is the same file that gets published to that URL.
    """
    from rdflib import Graph

    ctx = json.loads(CONTEXT.read_text())["@context"]
    g = Graph()
    for p in paths:
        doc = json.loads(p.read_text())
        doc["@context"] = ctx
        g.parse(data=json.dumps(doc), format="json-ld")
    return g


def main(argv):
    try:
        from pyshacl import validate
    except ImportError:
        print("shacl: SKIPPED - pip install pyshacl rdflib")
        return 0

    targets = argv[1:] or ["examples/example-city"]
    paths = []
    for t in targets:
        p = ROOT / t
        paths.extend(sorted(p.glob("**/*.jsonld")) if p.is_dir() else [p])
    if not paths:
        print("shacl: no .jsonld files found")
        return 1

    data = build_graph(paths)
    from rdflib import Graph

    # --- vocabulary expansion guard ------------------------------------------
    # A code-list value declared with @type: @vocab expands against whatever @vocab is
    # in scope. With the document-level @vocab set to schema.org, every value silently
    # became a schema.org IRI that does not exist - "municipal", "elected", "yes". JSON
    # Schema validated it and SHACL passed it, because both check structure, not where a
    # token landed. Only expansion reveals it, so it is checked here.
    #
    # schema.org's own enumerations (InForce, EventScheduled, OfflineEventAttendanceMode)
    # are legitimately schema.org IRIs and start uppercase.
    DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
    leaked = {}
    for s, pr, o in data:
        term = str(o)
        if not term.startswith("https://schema.org/"):
            continue
        tail = term.rsplit("/", 1)[-1]
        if tail and tail[0].islower() and tail not in DAYS:
            leaked.setdefault(str(pr).rsplit("/", 1)[-1], set()).add(tail)
    if leaked:
        print(f"schemaGov shacl: {len(paths)} file(s), {len(data)} triples")
        print(f"\n{sum(len(v) for v in leaked.values())} code-list value(s) expanded into "
              f"the schema.org namespace, where they are not defined:")
        for prop in sorted(leaked):
            print(f"  - {prop}: {', '.join(sorted(leaked[prop]))}")
        print("\n  Give the property a scoped @vocab in context/v1/context.jsonld so its "
              "values\n  resolve into the schemaGov term namespace.")
        return 1


    shapes = Graph().parse(str(SHAPES), format="turtle")

    conforms, _, text = validate(
        data_graph=data,
        shacl_graph=shapes,
        advanced=True,          # needed for sh:sparql constraints
        inference="none",       # class lists are explicit; no reasoning required
        abort_on_first=False,
    )

    print(
        f"schemaGov shacl: {len(paths)} file(s), {len(data)} triples, "
        f"{len(set(data.subjects()))} subjects"
    )
    if conforms:
        print("\nOK - all shapes satisfied")
        return 0

    # pyshacl's report is verbose; condense to one line per violation.
    violations = []
    focus = message = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Focus Node:"):
            focus = s.split(":", 1)[1].strip()
        elif s.startswith("Message:"):
            message = s.split(":", 1)[1].strip()
            if focus:
                violations.append((focus, message))
                focus = message = None

    print(f"\n{len(violations)} violation(s):")
    for f, m in violations:
        print(f"  - {f}\n    {m}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
