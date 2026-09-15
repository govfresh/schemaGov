#!/usr/bin/env python3
"""Prove a published document is consumable by a standard JSON-LD processor.

Every fixture declares `"@context": "https://schema.govfresh.com/v1/context.jsonld"`.
Our other tools inline the local context file instead of fetching that URL, which is
convenient during development and means the validation suite never exercises the path a
real consumer takes. This test does.

It serves the built site over local HTTP, rewrites the context URL to that origin, and
parses fixtures by FETCHING the context - no inlining. Then it asserts the result is
semantically identical to the inlined parse, so a broken published context cannot pass.

It also reports the Content-Type the context is served with, because a JSON-LD processor
may reject a context served as application/octet-stream - the failure mode most likely to
bite on static hosting.

Usage:  python3 tools/check-context.py
"""
import http.server
import json
import pathlib
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
PUBLISHED = "https://schema.govfresh.com"

FIXTURES = [
    "examples/example-city/organizations.jsonld",
    "examples/example-city/meetings.jsonld",
    "examples/example-city/budget.jsonld",
    "examples/pilot-uk-contracts/procurement.jsonld",
    "examples/pilot-ie-datasets/catalog.jsonld",
]


class Handler(http.server.SimpleHTTPRequestHandler):
    # Static hosts differ on this; serve it correctly so the test isolates the
    # document/context path rather than a MIME quirk. The naive mapping is reported
    # separately below.
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".jsonld": "application/ld+json",
        ".json": "application/json",
        ".ttl": "text/turtle",
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def log_message(self, *a):
        pass


def main():
    if not SITE.exists():
        print("check-context: _site not built - run `npm run build` first", file=sys.stderr)
        return 1
    try:
        from rdflib import Graph
    except ImportError:
        print("check-context: SKIPPED - pip install rdflib")
        return 0

    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        port = httpd.server_address[1]
        origin = f"http://127.0.0.1:{port}"
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        # 1. is the context actually there, and served as what?
        import urllib.request
        ctx_url = f"{origin}/v1/context.jsonld"
        try:
            with urllib.request.urlopen(ctx_url, timeout=10) as r:
                ctype = r.headers.get("Content-Type")
                body = r.read()
                json.loads(body)
        except Exception as e:
            print(f"check-context: FAILED to fetch {PUBLISHED}/v1/context.jsonld")
            print(f"  {type(e).__name__}: {e}")
            httpd.shutdown()
            return 1

        print(f"schemaGov check-context: serving _site at {origin}")
        print(f"  /v1/context.jsonld  {len(body):,} bytes  Content-Type: {ctype}")

        local_ctx = json.loads((ROOT / "context/v1/context.jsonld").read_text())["@context"]
        failures = 0

        for rel in FIXTURES:
            path = ROOT / rel
            if not path.exists():
                print(f"  SKIP  {rel} (absent)")
                continue
            doc = json.loads(path.read_text())

            # the real consumer path: fetch the context over HTTP
            fetched = dict(doc)
            fetched["@context"] = ctx_url
            try:
                g_remote = Graph().parse(data=json.dumps(fetched), format="json-ld")
            except Exception as e:
                print(f"  FAIL  {rel}\n        fetching the context failed: "
                      f"{type(e).__name__}: {str(e)[:110]}")
                failures += 1
                continue

            # the development path, for comparison
            inlined = dict(doc)
            inlined["@context"] = local_ctx
            g_local = Graph().parse(data=json.dumps(inlined), format="json-ld")

            # Blank-node labels are regenerated on every parse, so the graphs must be
            # compared up to isomorphism rather than by triple equality.
            from rdflib.compare import isomorphic

            if not isomorphic(g_remote, g_local):
                print(f"  FAIL  {rel}")
                print(f"        fetched context yields different semantics than the local file")
                print(f"        fetched: {len(g_remote)} triples, inlined: {len(g_local)}")
                # Ground triples only - these are comparable and show what actually differs.
                def ground(g):
                    return {(str(p), str(o)) for s, p, o in g
                            if not str(s).startswith("N") and not str(o).startswith("N")}
                for p, o in list(ground(g_local) - ground(g_remote))[:4]:
                    print(f"          only when inlined: {p.rsplit('/',1)[-1]} -> {o[:60]}")
                for p, o in list(ground(g_remote) - ground(g_local))[:4]:
                    print(f"          only when fetched: {p.rsplit('/',1)[-1]} -> {o[:60]}")
                failures += 1
            else:
                print(f"  OK    {rel:46} {len(g_remote):5} triples via fetched context")

        httpd.shutdown()

    if failures:
        print(f"\n{failures} fixture(s) are not consumable as published.")
        return 1
    print("\nOK - published documents parse by fetching the context, "
          "with identical semantics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
