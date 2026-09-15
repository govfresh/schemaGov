# SHACL shapes

The semantic validation tier promised by [SPEC §4](../SPEC.md#4-validation), implemented in
`schemaGov.shapes.ttl` and run by `tools/shacl.py`.

## What these catch that JSON Schema cannot

JSON Schema validates the *shape* of a document. `tools/validate.py` checks that every
reference *resolves*. Neither can check what a reference resolves **to** — and a reference
pointing at the wrong kind of thing is valid JSON, resolves cleanly, and is still wrong.

Measured against a deliberately broken fixture, JSON Schema caught 1 of 5 faults; these
shapes caught the other 4:

| Fault | JSON Schema | SHACL |
|---|---|---|
| Entity typed as both an Organization and a Jurisdiction | caught | caught |
| A Role pointing at an Organization instead of a Person | missed | **caught** |
| `areaServed` pointing at a body instead of a territory | missed | **caught** |
| A cycle in the jurisdiction hierarchy | missed | **caught** |

## Design notes

**Class lists are enumerated explicitly** rather than relying on subclass inference, because
the data graph does not carry schema.org's class hierarchy. Explicit lists are also easier to
audit than inference results.

**Cycle detection uses `sh:sparql`** with a transitive property path, so `tools/shacl.py`
runs pyshacl with `advanced=True`.

**The published `@context` URL is inlined from the local file** when building the graph. The
namespace is not resolvable during development, and a validator that needs the network to
work is a validator that fails in CI.

## Running

```bash
pip install pyshacl rdflib
python3 tools/shacl.py examples/example-city
```
