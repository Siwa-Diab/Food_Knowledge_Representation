
"""
Session 3 - Food Knowledge Representation
Check the OWL axioms written in my_axioms.ttl.

Run from the project root:

    python session_03/check_my_axioms.py

Or provide a different ontology file:

    python session_03/check_my_axioms.py session_03/my_axioms.ttl

The checker:
1. Loads the student's ontology.
2. Adds test classes (probes).
3. Runs the HermiT OWL reasoner.
4. Checks the semantic meaning of Y1, Y2 and Y3.
5. Reports a score out of 3.

This version avoids Windows file URI problems by loading
the ontology through an in-memory byte stream.
"""

import sys
from io import BytesIO
from pathlib import Path

from rdflib import Graph, Namespace

HERE = Path(__file__).resolve().parent

FOOD = Namespace("https://example.org/food-kr/schema#")


# ============================================================
# PROBES
# ============================================================

PROBES = """
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix food: <https://example.org/food-kr/schema#> .

# Y1:
# A thing that is both BrandedFood and IngredientDeclaration
# must be logically impossible.

food:ProbeY1
    a owl:Class ;
    rdfs:subClassOf
        food:BrandedFood ,
        food:IngredientDeclaration .


# Y2:
# Exact definition of a branded food with incomplete
# ingredient declaration status.

food:ProbeY2
    a owl:Class ;
    owl:equivalentClass [
        a owl:Class ;
        owl:intersectionOf (
            food:BrandedFood
            [
                a owl:Restriction ;
                owl:onProperty food:hasDeclarationStatus ;
                owl:hasValue food:IncompleteDeclarationStatus
            ]
        )
    ] .


# Y3:
# At least one sesame ingredient declaration AND
# every ingredient linked through hasDeclaredIngredient
# must be a SesameIngredient.

food:ProbeY3
    a owl:Class ;
    owl:equivalentClass [
        a owl:Class ;
        owl:intersectionOf (
            food:BrandedFood
            [
                a owl:Restriction ;
                owl:onProperty food:hasDeclaredIngredient ;
                owl:someValuesFrom food:SesameIngredient
            ]
            [
                a owl:Restriction ;
                owl:onProperty food:hasDeclaredIngredient ;
                owl:allValuesFrom food:SesameIngredient
            ]
        )
    ] .


# Common mistake: ONLY without SOME.

food:ProbeY3NoSome
    a owl:Class ;
    owl:equivalentClass [
        a owl:Class ;
        owl:intersectionOf (
            food:BrandedFood
            [
                a owl:Restriction ;
                owl:onProperty food:hasDeclaredIngredient ;
                owl:allValuesFrom food:SesameIngredient
            ]
        )
    ] .


# Common mistake: SOME without ONLY.

food:ProbeY3NoOnly
    a owl:Class ;
    owl:equivalentClass [
        a owl:Class ;
        owl:intersectionOf (
            food:BrandedFood
            [
                a owl:Restriction ;
                owl:onProperty food:hasDeclaredIngredient ;
                owl:someValuesFrom food:SesameIngredient
            ]
        )
    ] .
"""


# ============================================================
# HINTS
# ============================================================

HINTS = {
    "Y1": (
        "Declare food:BrandedFood owl:disjointWith "
        "food:IngredientDeclaration ."
    ),

    "Y2": (
        "Use owl:equivalentClass with BrandedFood and "
        "hasDeclarationStatus value IncompleteDeclarationStatus."
    ),

    "Y3": (
        "Use owl:equivalentClass with BrandedFood, "
        "someValuesFrom SesameIngredient, and "
        "allValuesFrom SesameIngredient."
    ),
}


# ============================================================
# LOAD THE ONTOLOGY AND PROBES
# ============================================================

def load_graph(path):
    """Load the student's ontology and add the probe classes."""

    graph = Graph()

    graph.parse(
        str(path),
        format="turtle"
    )

    graph.parse(
        data=PROBES,
        format="turtle"
    )

    return graph


# ============================================================
# RUN HERMIT
# ============================================================

def reasoned_world(graph):
    """
    Load the combined RDF graph into Owlready2 and run HermiT.

    Use an in-memory RDF/XML stream to avoid Windows
    file URI problems.
    """

    import owlready2

    # RDF/XML is supported by Owlready2 and avoids
    # the Windows N-Triples file URI issue.
    rdfxml = graph.serialize(format="xml")

    if isinstance(rdfxml, str):
        rdfxml = rdfxml.encode("utf-8")

    stream = BytesIO(rdfxml)

    world = owlready2.World()

    ontology = world.get_ontology(
        "https://example.org/food-kr/axiom-check"
    )

    ontology.load(fileobj=stream)

    try:
        with ontology:
            owlready2.sync_reasoner_hermit(
                world,
                infer_property_values=False,
                debug=0
            )

    except owlready2.OwlReadyInconsistentOntologyError:
        return None, None

    impossible = set(world.inconsistent_classes())

    return world, impossible


# ============================================================
# SEMANTIC COMPARISON HELPERS
# ============================================================

def below(a, b, impossible):
    """
    Return True if the reasoner concludes that
    class a is a subclass of class b.
    """

    if a is None or b is None:
        return False

    if a in impossible:
        return True

    return b in a.ancestors()


def same(a, b, impossible):
    """
    Return True if two classes are logically equivalent.
    """

    return (
        below(a, b, impossible)
        and below(b, a, impossible)
    )


# ============================================================
# MAIN CHECKER
# ============================================================

def main():

    # --------------------------------------------------------
    # Step 1: Locate the ontology file
    # --------------------------------------------------------

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = HERE / "my_axioms.ttl"

    if not path.exists():
        raise SystemExit(
            f"File not found: {path}"
        )

    print("Food Knowledge Representation")
    print("Session 3 - OWL Axiom Checker")
    print("-" * 45)
    print(f"Ontology file: {path.name}")

    # --------------------------------------------------------
    # Step 2: Load ontology and probes
    # --------------------------------------------------------

    try:
        graph = load_graph(path)

    except Exception as error:
        raise SystemExit(
            f"Turtle could not be loaded: {error}"
        )

    print(f"Triples including probes: {len(graph)}")
    print("Running HermiT...\n")

    # --------------------------------------------------------
    # Step 3: Run HermiT
    # --------------------------------------------------------

    try:
        world, impossible = reasoned_world(graph)

    except Exception as error:
        raise SystemExit(
            f"Reasoner failed: {error}\n"
            "Check owlready2, Java, and your ontology."
        )

    if world is None:
        raise SystemExit(
            "The combined ontology is inconsistent. "
            "Check the axioms and individuals."
        )

    # --------------------------------------------------------
    # Step 4: Retrieve classes
    # --------------------------------------------------------

    def cls(name):
        return world[str(FOOD[name])]

    probe_y1 = cls("ProbeY1")
    probe_y2 = cls("ProbeY2")
    probe_y3 = cls("ProbeY3")

    mine_y2 = cls("ProductWithIncompleteDeclaration")
    mine_y3 = cls("SesameOnlyDeclarationCandidate")

    # --------------------------------------------------------
    # Step 5: Check Y1 - Disjointness
    # --------------------------------------------------------

    results = {}

    results["Y1"] = (
        probe_y1 is not None
        and probe_y1 in impossible
    )

    # --------------------------------------------------------
    # Step 6: Check Y2 - Equivalent Class
    # --------------------------------------------------------

    results["Y2"] = (
        mine_y2 is not None
        and mine_y2 not in impossible
        and same(
            mine_y2,
            probe_y2,
            impossible
        )
    )

    # --------------------------------------------------------
    # Step 7: Check Y3 - SOME + ONLY
    # --------------------------------------------------------

    results["Y3"] = (
        mine_y3 is not None
        and mine_y3 not in impossible
        and same(
            mine_y3,
            probe_y3,
            impossible
        )
    )

    # --------------------------------------------------------
    # Step 8: Display results
    # --------------------------------------------------------

    for key in ("Y1", "Y2", "Y3"):

        if results[key]:
            print(f"{key}: right.")

        else:
            print(f"{key}: not yet.")
            print(f"    Hint: {HINTS[key]}")

            if key == "Y3" and mine_y3 is not None:

                no_some = cls("ProbeY3NoSome")
                no_only = cls("ProbeY3NoOnly")

                if same(
                    mine_y3,
                    no_some,
                    impossible
                ):
                    print(
                        "    Problem: ONLY does not guarantee "
                        "that an ingredient exists."
                    )

                elif same(
                    mine_y3,
                    no_only,
                    impossible
                ):
                    print(
                        "    Problem: SOME does not restrict "
                        "all declared ingredients."
                    )

    # --------------------------------------------------------
    # Step 9: Final score
    # --------------------------------------------------------

    score = sum(results.values())

    print(f"\n{score} of 3 right.")


if __name__ == "__main__":
    main()
