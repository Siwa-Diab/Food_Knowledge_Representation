
"""Create CI and Part B samples for Food Knowledge Representation.

Run from the project root:

    python session_04/make_ci_sample.py

Outputs:
    session_04/ci/sample-foods.ttl
    session_04/ci/sample-foods-broken.ttl
    session_04/part-b/test-foods.ttl

The clean CI sample passes.
The broken CI sample has one missing ingredient declaration.

Part B contains four deliberately planted faults:
    Y1: One missing GTIN/UPC and one duplicate GTIN/UPC.
    Y2: One negative nutrient measurement amount.
    Y3: One whitespace-only ingredient declaration.
"""

from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SOURCE = ROOT / "session_02" / "output" / "food_knowledge_graph.ttl"

FOOD = Namespace("https://example.org/food-kr/schema#")
ID = "https://example.org/food-kr/id/"

PRODUCT_IDS = [
    "1000131",
    "1000717",
    "1000843",
    "1001135",
    "1001463",
    "1001635",
]


def product(key):
    return URIRef(f"{ID}food/usda/{key}")


def copy_graph(source):
    result = Graph()
    result.bind("food", FOOD)
    result.bind("xsd", XSD)
    result += source
    return result


def header(title, lines):
    items = [title, ""] + lines + [""]
    return "".join(f"# {line}\n" for line in items)


def save(graph, path, title, lines):
    content = header(title, lines)
    content += graph.serialize(format="turtle")
    path.write_text(content, encoding="utf-8")


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Missing Session 2 graph: {SOURCE}"
        )

    big = Graph().parse(SOURCE)

    print(f"Source graph: {len(big):,} triples")

    # --------------------------------------------------------
    # 1. Select six real USDA branded food products.
    # --------------------------------------------------------

    clean = Graph()
    clean.bind("food", FOOD)
    clean.bind("xsd", XSD)

    for key in PRODUCT_IDS:
        node = product(key)

        if (node, RDF.type, FOOD.BrandedFood) not in big:
            raise ValueError(
                f"Product {key} is not a branded food."
            )

        for predicate, value in big.predicate_objects(node):
            clean.add((node, predicate, value))

        if not list(big.objects(node, FOOD.ingredientDeclaration)):
            raise ValueError(
                f"Product {key} has no ingredient declaration."
            )

        if not list(big.objects(node, FOOD.gtinUpc)):
            raise ValueError(
                f"Product {key} has no GTIN/UPC."
            )

    # --------------------------------------------------------
    # 2. Create clean CI sample.
    # --------------------------------------------------------

    ci_dir = HERE / "ci"
    ci_dir.mkdir(parents=True, exist_ok=True)

    clean_path = ci_dir / "sample-foods.ttl"

    save(
        clean,
        clean_path,
        "Clean CI sample: six real USDA branded foods.",
        [
            "Generated from the Session 2 RDF graph.",
            "Expected result: SHACL gate PASS.",
            "Do not edit this generated file manually.",
        ],
    )

    # --------------------------------------------------------
    # 3. Create broken CI sample.
    # --------------------------------------------------------

    broken = copy_graph(clean)

    broken_product = product("1000131")

    broken.remove(
        (broken_product, FOOD.ingredientDeclaration, None)
    )

    broken_path = ci_dir / "sample-foods-broken.ttl"

    save(
        broken,
        broken_path,
        "Broken CI sample: one deliberately missing declaration.",
        [
            "Product 1000131 has no ingredient declaration.",
            "Expected result: SHACL gate FAIL.",
        ],
    )

    # --------------------------------------------------------
    # 4. Build Part B dataset.
    # --------------------------------------------------------

    test = copy_graph(clean)

    # Include one real nutrient measurement from the
    # Session 2 graph, including its original properties.

    measurement = next(
        (
            node
            for node in big.subjects(
                RDF.type,
                FOOD.NutrientMeasurement,
            )
            if isinstance(
                big.value(node, FOOD.amount),
                Literal,
            )
            and isinstance(
                big.value(node, FOOD.amount).toPython(),
                (int, float),
            )
        ),
        None,
    )

    if measurement is None:
        # Decimal literals commonly convert to Decimal,
        # so use a more general fallback.
        measurement = next(
            (
                node
                for node in big.subjects(
                    RDF.type,
                    FOOD.NutrientMeasurement,
                )
                if big.value(node, FOOD.amount) is not None
            ),
            None,
        )

    if measurement is None:
        raise ValueError(
            "No nutrient measurement with an amount was found."
        )

    for predicate, value in big.predicate_objects(measurement):
        test.add((measurement, predicate, value))

    # --------------------------------------------------------
    # Y1: CARDINALITY
    # --------------------------------------------------------

    # Fault 1: Product 1001463 has no GTIN/UPC.

    missing_gtin = product("1001463")

    test.remove(
        (missing_gtin, FOOD.gtinUpc, None)
    )

    # Fault 2: Product 1001635 has two GTIN/UPC values.

    duplicate_gtin = product("1001635")

    existing_gtins = set(
        test.objects(duplicate_gtin, FOOD.gtinUpc)
    )

    extra_gtin = Literal(
        "TEST-DUPLICATE-GTIN",
        datatype=XSD.string,
    )

    if extra_gtin in existing_gtins:
        raise ValueError(
            "Test GTIN unexpectedly already exists."
        )

    test.add(
        (duplicate_gtin, FOOD.gtinUpc, extra_gtin)
    )

    # --------------------------------------------------------
    # Y2: VALUE RANGE
    # --------------------------------------------------------

    # Fault 3: Change one real measurement's amount to -5.

    test.remove(
        (measurement, FOOD.amount, None)
    )

    test.add(
        (
            measurement,
            FOOD.amount,
            Literal("-5", datatype=XSD.decimal),
        )
    )

    # --------------------------------------------------------
    # Y3: SPARQL
    # --------------------------------------------------------

    # Fault 4: Replace a declaration with whitespace only.

    blank_ingredients = product("1000717")

    test.remove(
        (
            blank_ingredients,
            FOOD.ingredientDeclaration,
            None,
        )
    )

    test.add(
        (
            blank_ingredients,
            FOOD.ingredientDeclaration,
            Literal("   ", datatype=XSD.string),
        )
    )

    # --------------------------------------------------------
    # 5. Save Part B dataset.
    # --------------------------------------------------------

    part_b_dir = HERE / "part-b"
    part_b_dir.mkdir(parents=True, exist_ok=True)

    test_path = part_b_dir / "test-foods.ttl"

    save(
        test,
        test_path,
        "Part B: USDA-derived sample with four planted faults.",
        [
            "Y1: Product 1001463 has no GTIN/UPC.",
            "Y1: Product 1001635 has two GTIN/UPC values.",
            f"Y2: Measurement {measurement} has amount -5.",
            "Y3: Product 1000717 has a whitespace-only "
            "ingredient declaration.",
            "All faults are intentional teaching examples.",
        ],
    )

    # --------------------------------------------------------
    # 6. Print results.
    # --------------------------------------------------------

    print()
    print("Generated files:")
    print(
        f"  ci/sample-foods.ttl: "
        f"{len(clean)} triples"
    )
    print(
        f"  ci/sample-foods-broken.ttl: "
        f"{len(broken)} triples"
    )
    print(
        f"  part-b/test-foods.ttl: "
        f"{len(test)} triples"
    )

    print()
    print("Expected faulty resources:")
    print(f"  Y1: {missing_gtin}")
    print(f"  Y1: {duplicate_gtin}")
    print(f"  Y2: {measurement}")
    print(f"  Y3: {blank_ingredients}")


if __name__ == "__main__":
    main()
