
"""Benchmark individual SHACL node shapes on USDA food RDF data.

Adapted from the professor's Session 4 shape_timings.py.

Run from the project root:

    python session_04/shape_timings.py

    python session_04/shape_timings.py --shape BrandedFoodShape

    python session_04/shape_timings.py --data session_04/ci/sample-foods.ttl

Measures validation time for each selected node shape.
The timing excludes RDF file loading and shape extraction.
"""

import argparse
import time
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, BNode, Graph, Namespace, URIRef

HERE = Path(__file__).resolve().parent

DEFAULT_DATA = (
    HERE.parent
    / "session_02"
    / "output"
    / "food_knowledge_graph.ttl"
)

DEFAULT_SHAPES = HERE / "food-shapes.ttl"

SH = Namespace("http://www.w3.org/ns/shacl#")


def closure(g, start, out, visited=None):
    """Copy a shape and its blank-node property constraints."""

    if visited is None:
        visited = set()

    if start in visited:
        return

    visited.add(start)

    for predicate, obj in g.predicate_objects(start):
        out.add((start, predicate, obj))

        if isinstance(obj, BNode):
            closure(g, obj, out, visited)


def main():

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--shape",
        help="Local name of one node shape, e.g. BrandedFoodShape",
    )

    ap.add_argument(
        "--shapes",
        default=str(DEFAULT_SHAPES),
        help="Path to SHACL shapes Turtle file",
    )

    ap.add_argument(
        "--data",
        default=str(DEFAULT_DATA),
        help="Path to RDF data Turtle file",
    )

    args = ap.parse_args()

    # --------------------------------------------------------
    # Step 1: Load the RDF data and SHACL shapes
    # --------------------------------------------------------

    data_path = Path(args.data)
    shapes_path = Path(args.shapes)

    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")

    if not shapes_path.exists():
        raise SystemExit(f"Shapes file not found: {shapes_path}")

    data = Graph()
    data.parse(data_path, format="turtle")

    shapes = Graph()
    shapes.parse(shapes_path, format="turtle")

    # --------------------------------------------------------
    # Step 2: Discover available node shapes
    # --------------------------------------------------------

    shape_nodes = {
        str(shape).rsplit("#", 1)[-1]: shape
        for shape in shapes.subjects(RDF.type, SH.NodeShape)
    }

    names = sorted(shape_nodes)

    if not names:
        raise SystemExit("No sh:NodeShape declarations found.")

    if args.shape:
        if args.shape not in shape_nodes:
            raise SystemExit(
                f"Shape '{args.shape}' not found. "
                f"Available shapes: {', '.join(names)}"
            )

        names = [args.shape]

    print("Food Knowledge Representation")
    print("Session 4 - SHACL Shape Timings")
    print("-" * 55)

    print(f"data: {data_path.name} ({len(data):,} triples)")
    print(f"shapes: {shapes_path.name}")
    print()

    # --------------------------------------------------------
    # Step 3: Benchmark each shape individually
    # --------------------------------------------------------

    for name in names:

        shape_node = shape_nodes[name]

        one = Graph()

        for prefix, namespace in shapes.namespaces():
            one.bind(prefix, namespace)

        closure(shapes, shape_node, one)

        # Check whether the selected shape contains
        # a SHACL-SPARQL constraint.
        kind = (
            "SPARQL"
            if any(one.triples((None, SH.sparql, None)))
            else "core"
        )

        # Measure validation only, not file loading.
        start = time.perf_counter()

        _, report, _ = validate(
            data,
            shacl_graph=one,
            inference="none",
            advanced=True,
        )

        elapsed = time.perf_counter() - start

        results = len(
            set(
                report.subjects(
                    RDF.type,
                    SH.ValidationResult,
                )
            )
        )

        print(
            f"{name:<24} "
            f"{kind:<6} "
            f"{elapsed:>7.2f} s   "
            f"{results:,} results"
        )


if __name__ == "__main__":
    main()
