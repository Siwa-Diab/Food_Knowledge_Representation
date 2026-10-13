
"""Validate the Food Knowledge Representation RDF graph with SHACL.

Adapted from the professor's Session 4 validate.py.

Run from the Food_Knowledge_Representation project root:

    python session_04/validate.py
    python session_04/validate.py --shapes session_04/food-shapes-v0.ttl
    python session_04/validate.py --data session_04/ci/sample-foods.ttl
    python session_04/validate.py --data session_04/ci/sample-foods.ttl --data session_04/ci/broken-triple.ttl

The validation gate:
    Violation -> FAIL, exit code 1
    Warning   -> reported, but does not fail the gate
    Info      -> reported, but does not fail the gate

Always check focus-node counts before trusting a clean report.
"""

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, RDFS, Graph, Namespace, URIRef

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

DEFAULT_DATA = (
    PROJECT_ROOT
    / "session_02"
    / "output"
    / "food_knowledge_graph.ttl"
)

DEFAULT_SHAPES = HERE / "food-shapes.ttl"

SH = Namespace("http://www.w3.org/ns/shacl#")
FOOD = Namespace("https://example.org/food-kr/schema#")

SEVERITY = {
    SH.Violation: "Violation",
    SH.Warning: "Warning",
    SH.Info: "Info",
}


def short(node, data=None):
    """Return a readable name for an RDF node."""

    if node is None:
        return "unknown"

    s = str(node)

    for base in (
        "https://example.org/food-kr/id/",
        "https://example.org/food-kr/schema#",
        "https://example.org/food-kr/shapes#",
    ):
        if s.startswith(base):
            return s[len(base):]

    return s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def node_shape_of(shapes, shape):
    """Find the parent node shape of a property shape."""

    parent = shapes.value(
        predicate=SH.property,
        object=shape,
    )

    return parent if parent is not None else shape


def focus_counts(data, shapes):
    """Count the RDF individuals targeted by each SHACL node shape.

    Supports sh:targetClass and sh:targetNode, including subclasses.
    """

    out = {}

    for node_shape in set(
        shapes.subjects(RDF.type, SH.NodeShape)
    ):
        targets = set()

        for cls in shapes.objects(
            node_shape,
            SH.targetClass,
        ):
            classes = {cls}
            classes.update(
                data.transitive_subjects(
                    RDFS.subClassOf,
                    cls,
                )
            )

            for target_class in classes:
                targets.update(
                    data.subjects(
                        RDF.type,
                        target_class,
                    )
                )

        for node in shapes.objects(
            node_shape,
            SH.targetNode,
        ):
            targets.add(node)

        out[node_shape] = len(targets)

    return out


def main():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--data",
        action="append",
        help="RDF data file; repeat to merge multiple files",
    )

    parser.add_argument(
        "--shapes",
        default=str(DEFAULT_SHAPES),
        help="SHACL shapes file",
    )

    parser.add_argument(
        "--report",
        help="Save the complete SHACL validation report as Turtle",
    )

    parser.add_argument(
        "--examples",
        type=int,
        default=3,
        help="Number of example focus nodes per result group",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Step 1: Load RDF data
    # --------------------------------------------------------

    data_files = args.data or [str(DEFAULT_DATA)]

    data = Graph()

    for filename in data_files:

        path = Path(filename)

        if not path.exists():
            sys.exit(
                f"Data file not found: {filename}\n"
                "Run Session 2's convert_to_rdf.py first."
            )

        data.parse(path)

    # --------------------------------------------------------
    # Step 2: Load SHACL shapes
    # --------------------------------------------------------

    shapes_path = Path(args.shapes)

    if not shapes_path.exists():
        sys.exit(
            f"SHACL shapes file not found: {shapes_path}"
        )

    shapes = Graph()
    shapes.parse(shapes_path)

    print("\nFood Knowledge Representation")
    print("Session 4 - SHACL Validation")
    print("-" * 55)

    print(
        f"data: {len(data):,} triples from "
        + ", ".join(Path(f).name for f in data_files)
    )

    print(f"shapes: {shapes_path.name}")

    # --------------------------------------------------------
    # Step 3: Check focus nodes
    # --------------------------------------------------------

    labels = {
        node: str(
            shapes.value(node, RDFS.label)
            or short(node)
        )
        for node in shapes.subjects(
            RDF.type,
            SH.NodeShape,
        )
    }

    counts = focus_counts(data, shapes)

    for node_shape, count in sorted(
        counts.items(),
        key=lambda item: labels[item[0]],
    ):

        flag = (
            " <- targets nothing: this shape checks nothing"
            if count == 0
            else ""
        )

        print(
            f"  focus nodes {count:>8,}  "
            f"{labels[node_shape]}{flag}"
        )

    # --------------------------------------------------------
    # Step 4: Execute SHACL validation
    # --------------------------------------------------------

    start = time.time()

    conforms, report, _ = validate(
        data,
        shacl_graph=shapes,
        inference="none",
        advanced=True,
    )

    elapsed = time.time() - start

    # --------------------------------------------------------
    # Step 5: Group validation results
    # --------------------------------------------------------

    groups = defaultdict(list)

    for result in report.subjects(
        RDF.type,
        SH.ValidationResult,
    ):

        severity = SEVERITY.get(
            report.value(
                result,
                SH.resultSeverity,
            ),
            "?",
        )

        source_shape = report.value(
            result,
            SH.sourceShape,
        )

        component = short(
            report.value(
                result,
                SH.sourceConstraintComponent,
            )
        ).replace(
            "ConstraintComponent",
            "",
        )

        path = report.value(
            result,
            SH.resultPath,
        )

        if path is not None:
            description = (
                f"{component} on {short(path)}"
            )
        else:
            description = component

        parent_shape = node_shape_of(
            shapes,
            source_shape,
        )

        shape_label = labels.get(
            parent_shape,
            short(source_shape),
        )

        focus_node = report.value(
            result,
            SH.focusNode,
        )

        groups[
            (
                severity,
                shape_label,
                description,
            )
        ].append(focus_node)

    # --------------------------------------------------------
    # Step 6: Count results by severity
    # --------------------------------------------------------

    by_severity = Counter()

    for (severity, _, _), nodes in groups.items():
        by_severity[severity] += len(nodes)

    print(
        f"\nvalidated in {elapsed:.1f} s. "
        f"conforms (SHACL): {conforms}. "
        + ", ".join(
            f"{by_severity[severity]:,} {severity}"
            for severity in (
                "Violation",
                "Warning",
                "Info",
            )
        )
    )

    order = {
        "Violation": 0,
        "Warning": 1,
        "Info": 2,
    }

    for (severity, shape, problem), nodes in sorted(
        groups.items(),
        key=lambda item: (
            order.get(item[0][0], 3),
            -len(item[1]),
        ),
    ):

        examples = ", ".join(
            short(node, data)
            for node in sorted(
                nodes,
                key=str,
            )[:args.examples]
        )

        print(
            f"  {severity:<9} "
            f"{len(nodes):>8,} "
            f"{shape} - {problem} "
            f"e.g. {examples}"
        )

    # --------------------------------------------------------
    # Step 7: Save full report if requested
    # --------------------------------------------------------

    if args.report:

        report_path = Path(args.report)

        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        report.serialize(
            destination=str(report_path),
            format="turtle",
        )

        print(
            f"\nFull SHACL report written to: "
            f"{report_path}"
        )

    # --------------------------------------------------------
    # Step 8: Validation gate
    # --------------------------------------------------------

    if by_severity["Violation"]:

        print(
            f"\nGATE: FAIL, "
            f"{by_severity['Violation']:,} violations. "
            "Exit code 1."
        )

        sys.exit(1)

    print(
        "\nGATE: PASS, no violations"
        + (
            " (warnings are listed above)."
            if by_severity["Warning"]
            else "."
        )
    )


if __name__ == "__main__":
    main()
