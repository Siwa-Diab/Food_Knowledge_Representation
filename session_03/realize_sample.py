
"""
Session 3 - Food Knowledge Representation

Compare EquivalentTo and SubClassOf using sample food products.

Run from the project root:

    python session_03/realize_sample.py

Uses HermiT through Owlready2 instead of ROBOT/ELK.
Writes:
    session_03/reference-outputs/realized-sample.txt
"""

from io import BytesIO
from pathlib import Path

import owlready2
from rdflib import Graph, URIRef, RDF, RDFS, OWL

HERE = Path(__file__).resolve().parent

SCHEMA = "https://example.org/food-kr/schema#"
IDENTIFIERS = "https://example.org/food-kr/id/"

CANDIDATE = URIRef(SCHEMA + "SesameDeclarationCandidate")

SAMPLE_FILE = HERE / "workspace" / "sample-foods.ttl"
ONTOLOGY_FILE = HERE / "workspace" / "food-reasoning-clean.ttl"

# These are the individuals used in our earlier reasoning exercise.
PRODUCTS = [
    IDENTIFIERS + "product_sesame_1",
    IDENTIFIERS + "product_sesame_2",
    IDENTIFIERS + "product_other_1",
]


def load_graph():
    """Load the food ontology and sample assertions."""

    graph = Graph()

    graph.parse(
        str(ONTOLOGY_FILE),
        format="turtle"
    )

    graph.parse(
        str(SAMPLE_FILE),
        format="turtle"
    )

    # Remove imports because the relevant ontology is loaded locally.
    graph.remove((None, OWL.imports, None))

    return graph


def classify(graph):
    """Run HermiT and retrieve inferred product classifications."""

    rdfxml = graph.serialize(format="xml")

    if isinstance(rdfxml, str):
        rdfxml = rdfxml.encode("utf-8")

    world = owlready2.World()

    ontology = world.get_ontology(
        "https://example.org/food-kr/realization-check"
    )

    ontology.load(fileobj=BytesIO(rdfxml))

    with ontology:
        owlready2.sync_reasoner_hermit(
            world,
            infer_property_values=False,
            debug=0
        )

    candidate = world[str(CANDIDATE)]

    if candidate is None:
        raise RuntimeError(
            "SesameDeclarationCandidate was not found "
            "in the loaded ontology."
        )

    result = {}

    for product_iri in PRODUCTS:

        product = world[product_iri]

        if product is None:
            result[product_iri.rsplit("/", 1)[-1]] = [
                "not found"
            ]
            continue

        classes = []

        if candidate in product.INDIRECT_is_a:
            classes.append("SesameDeclarationCandidate")

        branded_food = world[SCHEMA + "BrandedFood"]

        if (
            branded_food is not None
            and branded_food in product.INDIRECT_is_a
        ):
            classes.append("BrandedFood")

        if not classes:
            classes.append("No target classification inferred")

        result[product_iri.rsplit("/", 1)[-1]] = classes

    return result


def main():

    print("Food Knowledge Representation")
    print("Session 3 - EquivalentTo vs SubClassOf")
    print("-" * 48)

    if not ONTOLOGY_FILE.exists():
        raise SystemExit(
            f"Ontology file not found: {ONTOLOGY_FILE}"
        )

    if not SAMPLE_FILE.exists():
        raise SystemExit(
            f"Sample file not found: {SAMPLE_FILE}"
        )

    original = load_graph()

    # --------------------------------------------------
    # Experiment 1: EquivalentTo
    # --------------------------------------------------

    equivalent = Graph()
    equivalent += original

    print("Running HermiT: EquivalentTo...")

    equivalent_result = classify(equivalent)

    # --------------------------------------------------
    # Experiment 2: SubClassOf
    # --------------------------------------------------

    primitive = Graph()
    primitive += original

    definitions = list(
        primitive.objects(CANDIDATE, OWL.equivalentClass)
    )

    if not definitions:
        raise SystemExit(
            "No owl:equivalentClass axiom found for "
            "SesameDeclarationCandidate."
        )

    for definition in definitions:

        primitive.remove((
            CANDIDATE,
            OWL.equivalentClass,
            definition
        ))

        primitive.add((
            CANDIDATE,
            RDFS.subClassOf,
            definition
        ))

    print("Running HermiT: SubClassOf...")

    primitive_result = classify(primitive)

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    lines = [
        "Session 3 - Food Ontology Realization",
        "EquivalentTo vs SubClassOf",
        "",
        "Experiment 1: EquivalentTo"
    ]

    for product, classes in equivalent_result.items():
        lines.append(
            f"  {product}: {', '.join(classes)}"
        )

    lines.append("")
    lines.append("Experiment 2: SubClassOf")

    for product, classes in primitive_result.items():
        lines.append(
            f"  {product}: {', '.join(classes)}"
        )

    lines.append("")
    lines.append(
        "Conclusion: EquivalentTo supports classification "
        "from the definition; SubClassOf alone does not."
    )

    text = "\n".join(lines)

    print()
    print(text)

    output_dir = HERE / "reference-outputs"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "realized-sample.txt"

    output_file.write_text(
        text + "\n",
        encoding="utf-8"
    )

    print(f"\nSaved output to: {output_file}")


if __name__ == "__main__":
    main()
