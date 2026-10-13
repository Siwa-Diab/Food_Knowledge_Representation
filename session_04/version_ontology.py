
"""Release the Session 3 food ontology as version 1.0.0.

Adapted from the professor's Session 4 version_ontology.py.

Run from the project root:

    python session_04/version_ontology.py

Reads:
    session_03/workspace/food-reasoning-clean.ttl

Writes:
    session_04/workspace/food-reasoning-1.0.0.ttl

The original Session 3 ontology is not modified.
"""

from pathlib import Path

from rdflib import RDF, OWL, Graph, Literal, URIRef

HERE = Path(__file__).resolve().parent

SOURCE = (
    HERE.parent
    / "session_03"
    / "workspace"
    / "food-reasoning-clean.ttl"
)

VERSION = "1.0.0"

ONTOLOGY_IRI = URIRef(
    "https://example.org/food-kr/ontology"
)

VERSION_IRI = URIRef(
    f"https://example.org/food-kr/ontology/{VERSION}"
)


def main():

    # --------------------------------------------------------
    # Step 1: Load the original ontology
    # --------------------------------------------------------

    if not SOURCE.exists():
        raise SystemExit(
            f"Source ontology not found: {SOURCE}"
        )

    before = Graph()
    before.parse(SOURCE, format="turtle")

    # --------------------------------------------------------
    # Step 2: Verify the ontology identity
    # --------------------------------------------------------

    if (
        ONTOLOGY_IRI,
        RDF.type,
        OWL.Ontology,
    ) not in before:

        raise SystemExit(
            "Expected ontology declaration not found:\n"
            f"  {ONTOLOGY_IRI}\n"
            "Check the ontology IRI in the Session 3 file."
        )

    # --------------------------------------------------------
    # Step 3: Create a separate release graph
    # --------------------------------------------------------

    release = Graph()

    for prefix, namespace in before.namespaces():
        release.bind(prefix, namespace)

    for triple in before:
        release.add(triple)

    # The source ontology must not already have a version IRI.
    if release.value(
        ONTOLOGY_IRI,
        OWL.versionIRI,
    ) is not None:

        raise SystemExit(
            "The source ontology already has an owl:versionIRI."
        )

    # --------------------------------------------------------
    # Step 4: Add version metadata
    # --------------------------------------------------------

    release.add((
        ONTOLOGY_IRI,
        OWL.versionIRI,
        VERSION_IRI,
    ))

    release.add((
        ONTOLOGY_IRI,
        OWL.versionInfo,
        Literal(VERSION),
    ))

    # --------------------------------------------------------
    # Step 5: Save the versioned ontology
    # --------------------------------------------------------

    output = (
        HERE
        / "workspace"
        / f"food-reasoning-{VERSION}.ttl"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    release.serialize(
        destination=str(output),
        format="turtle",
    )

    # --------------------------------------------------------
    # Step 6: Verify the output
    # --------------------------------------------------------

    after = Graph()
    after.parse(output, format="turtle")

    print(
        f"{SOURCE.name}: "
        f"{len(before)} triples, "
        f"version IRI: "
        f"{before.value(ONTOLOGY_IRI, OWL.versionIRI)}"
    )

    print(
        f"{output.relative_to(HERE)}: "
        f"{len(after)} triples, "
        f"version IRI: "
        f"{after.value(ONTOLOGY_IRI, OWL.versionIRI)}, "
        f"version info: "
        f"{after.value(ONTOLOGY_IRI, OWL.versionInfo)}"
    )

    # --------------------------------------------------------
    # Step 7: Display the ontology version metadata
    # --------------------------------------------------------

    print("\nThe versioned ontology header:")

    print(
        f"<{ONTOLOGY_IRI}> a owl:Ontology ;"
    )

    print(
        f"    owl:versionIRI <{VERSION_IRI}> ;"
    )

    print(
        f'    owl:versionInfo "{VERSION}" .'
    )

    
    # --------------------------------------------------------
    # Step 8: Verify that only version metadata was added
    #
    # RDF blank-node identifiers can change during
    # serialization and parsing. Compare graph structures
    # rather than raw sets of triples.
    # --------------------------------------------------------

    from rdflib.compare import to_isomorphic

    # Create a copy of the release graph.
    without_version = Graph()

    for triple in after:
        without_version.add(triple)

    # Remove the two version metadata triples.
    without_version.remove((
        ONTOLOGY_IRI,
        OWL.versionIRI,
        VERSION_IRI,
    ))

    without_version.remove((
        ONTOLOGY_IRI,
        OWL.versionInfo,
        Literal(VERSION),
    ))

    print("\nVersion comparison:")

    print(
        f"  Original triples: {len(before)}"
    )

    print(
        f"  Release triples: {len(after)}"
    )

    print(
        f"  Version metadata added: "
        f"{len(after) - len(without_version)}"
    )

    # Compare the RDF structures, ignoring blank-node IDs.
    equivalent = (
        to_isomorphic(before)
        == to_isomorphic(without_version)
    )

    if equivalent and len(after) - len(without_version) == 2:
        print(
            "  PASS: only the two version metadata "
            "triples were added."
        )
        print(
            "  Original ontology structure is preserved."
        )
    else:
        print(
            "  FAIL: unexpected structural differences "
            "between ontology versions."
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()