"""Download GS1's published SHACL shapes for EPCIS 2.0 (the standard for
supply chain event data) and print what a real, industrial shapes file is
made of, with the three patterns worth borrowing for our own shapes.

    python fetch_epcis.py            # writes workspace/epcis-shacl.ttl

Run from demos/session-04-shacl/. Needs the network once.

Source: https://ref.gs1.org/standards/epcis/epcis-shacl.ttl, the same file as
Ontology/EPCIS-SHACL.ttl in github.com/gs1/EPCIS. Its LICENSE file is GS1's
IP disclaimer (royalty free or RAND terms for GS1 members, and a patent
caveat), not an open source licence: borrow the patterns freely, and read
GS1's IP policy before shipping the file itself in a product.
"""

import sys
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

from rdflib import RDF, BNode, Graph, Literal, Namespace, URIRef

HERE = Path(__file__).resolve().parent
URL = "https://ref.gs1.org/standards/epcis/epcis-shacl.ttl"
OUT = HERE / "workspace" / "epcis-shacl.ttl"
SH = Namespace("http://www.w3.org/ns/shacl#")


def described(g, node, seen=None):
    """Every triple that describes node, following blank nodes and lists."""
    seen = seen or set()
    for p, o in g.predicate_objects(node):
        yield node, p, o
        if isinstance(o, BNode) and o not in seen:
            seen.add(o)
            yield from described(g, o, seen)


def name(x):
    return str(x).rsplit("/", 1)[-1]


def main():
    OUT.parent.mkdir(exist_ok=True)
    if not OUT.exists():
        try:
            OUT.write_bytes(urlopen(URL, timeout=60).read())
        except OSError as e:
            sys.exit(f"Could not download {URL}: {e}")
    text = OUT.read_text(encoding="utf-8")
    g = Graph().parse(OUT)
    named = [s for s in set(g.subjects()) if isinstance(s, URIRef)]
    print(f"{OUT.relative_to(HERE)}: {len(text.splitlines()):,} lines, {len(g):,} triples")
    print(f"  node shapes     {len(set(g.subjects(RDF.type, SH.NodeShape)))}")
    print(f"  property shapes {len(set(g.subjects(RDF.type, SH.PropertyShape)))}")
    print(f"  SPARQL constraints {len(list(g.subjects(SH.sparql, None)))}, severities set {len(list(g.subjects(SH.severity, None)))}"
          "   (all core, all the default severity, Violation)")

    users = defaultdict(set)
    forbidden, messages = [], 0
    for s in named:
        triples = list(described(g, s))
        for _, p, o in triples:
            if p == SH.property:
                users[o].add(s)
        if any(p == SH.maxCount and o == Literal(0) for _, p, o in triples):
            forbidden.append(s)
        if (s, SH.message, None) in g:
            messages += 1
    reused = sorted(((len(v), name(k)) for k, v in users.items() if len(v) > 1), reverse=True)

    print("\nPattern 1 · write a property shape once, reuse it by name.")
    print(f"  {len(reused)} named property shapes are used by more than one node shape, e.g. "
          + ", ".join(f"{n} ({k} shapes)" for k, n in reused[:3]))
    print("\nPattern 2 · say what must NOT be there: sh:maxCount 0.")
    print(f"  {len(forbidden)} 'forbidden' shapes, e.g. " + ", ".join(sorted(name(f) for f in forbidden)[:3]))
    print("\nPattern 3 · a message a person can act on, on every rule.")
    print(f"  {messages} shapes carry an sh:message, e.g.")
    print("  " + str(g.value(URIRef("https://ref.gs1.org/epcis/EventTimeShape"), SH.message)))


if __name__ == "__main__":
    main()
