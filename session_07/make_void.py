"""Describe the Food graph with VoID: which classes it has, how many of each,
and which properties link each class to which class or datatype. The same
layout as SIB's void-generator (which needs Java 17 and a SPARQL endpoint).

    python make_void.py            writes void.ttl
"""
import sys
import time
from pathlib import Path

import pyoxigraph as ox

from access_layer import GRAPH, HERE, open_store

QUERY = """
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX void-ext: <http://ldf.fi/void-ext#>
CONSTRUCT {
  <https://example.org/food-kr/void> void:classPartition ?cp .
  ?cp void:class ?c ; void:entities ?n ; void:propertyPartition ?pp .
  ?pp void:property ?p ; void:triples ?t ; void:classPartition ?op ; void-ext:datatypePartition ?dp .
  ?op void:class ?oc .
  ?dp void-ext:datatype ?dt .
} WHERE {
  { SELECT ?c (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a ?c FILTER STRSTARTS(STR(?c), "https://example.org/food-kr/schema#") } GROUP BY ?c }
  BIND (IRI(CONCAT(STR(?c), "-partition")) AS ?cp)
  OPTIONAL {
    { SELECT ?c ?p (COUNT(*) AS ?t) (SAMPLE(?ocls) AS ?oc) (SAMPLE(DATATYPE(?o)) AS ?dt0) WHERE {
        ?s a ?c ; ?p ?o . FILTER (?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        OPTIONAL { ?o a ?ocls } } GROUP BY ?c ?p }
    BIND (IRI(CONCAT(STR(?c), "-", STRAFTER(STR(?p), "#"))) AS ?pp)
    BIND (IF(BOUND(?oc), IRI(CONCAT(STR(?pp), "-class")), ?unbound) AS ?op)
    BIND (IF(BOUND(?dt0) && !BOUND(?oc), ?dt0, ?unbound) AS ?dt)
    BIND (IF(BOUND(?dt), IRI(CONCAT(STR(?pp), "-datatype")), ?unbound) AS ?dp)
  }
}
"""


def main():
    t0 = time.time()
    store = open_store(Path(sys.argv[1]) if len(sys.argv) > 1 else GRAPH)
    triples = list(store.query(QUERY))
    out = HERE / "void.ttl"
    out.write_bytes(ox.serialize(triples, format=ox.RdfFormat.TURTLE, prefixes={"void": "http://rdfs.org/ns/void#", "void-ext": "http://ldf.fi/void-ext#", "food": "https://example.org/food-kr/schema#"}))
    print(f"read {len(store):,} triples; wrote void.ttl: {len(triples)} triples in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
