
"""Session 4 - Part B: Check custom SHACL shapes.

Run from the project root:

    python session_04/check_my_shapes.py

Or check another shapes file:

    python session_04/check_my_shapes.py path/to/shapes.ttl

The checker runs Y1, Y2 and Y3 independently and compares
the exact RDF resources flagged with expected faulty resources.

Y1: Exactly one GTIN/UPC per branded food.
Y2: Nutrient amount must be non-negative.
Y3: Ingredient declaration cannot be whitespace-only.
"""

import sys
from pathlib import Path

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef


# ============================================================
# PATHS AND NAMESPACES
# ============================================================

HERE = Path(__file__).resolve().parent

SH = Namespace("http://www.w3.org/ns/shacl#")
FOOD = Namespace("https://example.org/food-kr/schema#")
MY = Namespace("https://example.org/food-kr/shapes/my#")

ONTO = URIRef("https://example.org/food-kr/shapes/my")

DATA_PATH = HERE / "part-b" / "test-foods.ttl"

FOOD_ID = "https://example.org/food-kr/id/food/usda/"



# ============================================================
# EXPECTED RESULTS
# ============================================================

FOOD_ID = "https://example.org/food-kr/id/food/usda/"

# Read the generated Part B dataset to identify the
# deliberately modified nutrient measurement.
#
# This is only for the expected-answer configuration.
# It does not run SHACL validation.

def expected_measurement():
    data = Graph().parse(DATA_PATH)

    faulty = {
        str(node)
        for node in data.subjects(
            RDF.type,
            FOOD.NutrientMeasurement,
        )
        if any(
            value.toPython() < 0
            for value in data.objects(node, FOOD.amount)
            if isinstance(value, Literal)
            and isinstance(
                value.toPython(),
                (int, float, __import__("decimal").Decimal),
            )
        )
    }

    if len(faulty) != 1:
        raise ValueError(
            "Expected exactly one planted negative "
            "nutrient measurement."
        )

    return faulty


EXPECTED = {
    "Y1": {
        FOOD_ID + "1001463",
        FOOD_ID + "1001635",
    },
    "Y2": expected_measurement(),
    "Y3": {
        FOOD_ID + "1000717",
    },
}



# ============================================================
# SHACL CONSTRAINT PREDICATES
# ============================================================

CONSTRAINTS = {
    SH.property,
    SH.sparql,
    SH["in"],
    SH.datatype,
    SH["class"],
    SH.minCount,
    SH.maxCount,
    SH.pattern,
    SH.minInclusive,
    SH.maxInclusive,
    SH["or"],
    SH["and"],
    SH["not"],
    SH.node,
}


# ============================================================
# HELPER: COPY A SHAPE AND ITS BLANK NODES
# ============================================================

def closure(graph, start, output, visited=None):
    """Copy a shape and all blank nodes reachable from it."""

    if visited is None:
        visited = set()

    if start in visited:
        return

    visited.add(start)

    for predicate, obj in graph.predicate_objects(start):
        output.add((start, predicate, obj))

        if isinstance(obj, BNode):
            closure(graph, obj, output, visited)


# ============================================================
# HELPER: EXPLAIN MISMATCHES
# ============================================================

def hint(y, got):
    """Explain missing or extra SHACL validation results."""

    wanted = EXPECTED[y]

    missing = wanted - got
    extra = got - wanted

    messages = []

    if missing:
        messages.append(
            "misses " + ", ".join(sorted(missing))
        )

    if extra:
        messages.append(
            "also flags " + ", ".join(sorted(extra))
        )

    if not messages:
        return "No mismatch."

    return "Your shape " + " and ".join(messages) + "."


# ============================================================
# MAIN CHECKER
# ============================================================

def main():

    # Load shapes.

    shapes_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else HERE / "my_shapes.ttl"
    )

    try:
        shapes = Graph().parse(shapes_path)

    except Exception as exc:
        sys.exit(
            f"{shapes_path.name} is not valid Turtle:\n{exc}"
        )

    # Load test data.

    if not DATA_PATH.exists():
        sys.exit(
            f"Missing test dataset: {DATA_PATH}\n"
            "Create the Part B test dataset first."
        )

    try:
        data = Graph().parse(DATA_PATH)

    except Exception as exc:
        sys.exit(
            f"Could not parse the test dataset:\n{exc}"
        )

    print("=" * 60)
    print("SESSION 4 - PART B: SHACL EXERCISE CHECKER")
    print("=" * 60)

    print(f"Shapes:  {shapes_path.name}")
    print(f"Dataset: {DATA_PATH.name}")
    print(f"Triples: {len(data)}")
    print()

    right = 0

    # Validate each exercise separately.

    for y in EXPECTED:

        print("-" * 60)
        print(f"Checking {y}")
        print("-" * 60)

        shape = MY[f"{y}Shape"]

        one = Graph()

        closure(shapes, shape, one)
        closure(shapes, ONTO, one)

        # Check whether the shape has a constraint.

        if not any(
            predicate in CONSTRAINTS
            for predicate in one.predicates(shape)
        ):
            print(
                f"{y} NOT YET: shape has no constraint.\n"
            )
            continue

        # Determine which RDF resources are targeted.

        targets = set(
            one.objects(shape, SH.targetClass)
        )

        reached = set(
            one.objects(shape, SH.targetNode)
        )

        for target_class in targets:
            reached.update(
                data.subjects(RDF.type, target_class)
            )

        if not reached:
            print(
                f"{y} NOT YET: shape targets no resources "
                "in the test dataset.\n"
            )
            continue

        print(f"Focus nodes: {len(reached)}")

        # Avoid false passes from empty expected sets.

        if not EXPECTED[y]:
            print(
                f"{y} NOT READY: no expected faulty "
                "resources have been configured."
            )
            print(
                "Generate the planted test fault and "
                "update EXPECTED before testing.\n"
            )
            continue

        # Validate the current shape.

        try:
            _, report, _ = validate(
                data,
                shacl_graph=one,
                inference="none",
                advanced=True,
            )

        except Exception as exc:
            print(
                f"{y} NOT YET: validation error:\n"
                f"{str(exc).splitlines()[0][:300]}\n"
            )
            continue

        # Extract the exact focus nodes flagged.

        got = {
            str(report.value(result, SH.focusNode))
            for result in report.subjects(
                RDF.type,
                SH.ValidationResult,
            )
            if report.value(result, SH.focusNode) is not None
        }

        wanted = EXPECTED[y]

        # Compare actual results with expected results.

        if got == wanted:
            right += 1

            print(
                f"{y} RIGHT: flagged exactly "
                f"{len(got)} expected resource(s)."
            )

            for resource in sorted(got):
                print(f"  {resource}")

        else:
            print(
                f"{y} NOT YET: {hint(y, got)}"
            )

            print("\nExpected:")
            for resource in sorted(wanted):
                print(f"  {resource}")

            print("\nActual:")
            for resource in sorted(got):
                print(f"  {resource}")

        print()

    # Final result.

    print("=" * 60)
    print(f"FINAL RESULT: {right} of {len(EXPECTED)} right.")
    print("=" * 60)

    if right != len(EXPECTED):
        sys.exit(1)


if __name__ == "__main__":
    main()
