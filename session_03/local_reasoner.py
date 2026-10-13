
"""
Session 3 - Food Knowledge Representation
Local OWL Reasoner using HermiT.

This script:
1. Loads an OWL ontology.
2. Resolves owl:imports using the local XML catalog.
3. Supports local file:/// imports on Windows.
4. Merges the imported ontologies.
5. Runs HermiT through Owlready2.
6. Reports consistency, impossible classes, and inferred types.

Run from the project root:

    python session_03/local_reasoner.py session_03/workspace/food-reasoning-clean.ttl

    python session_03/local_reasoner.py session_03/workspace/sample-foods.ttl

    python session_03/local_reasoner.py session_03/workspace/domain-mistake.ttl
"""

import sys
import xml.etree.ElementTree as ET

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from rdflib import Graph, OWL


# ============================================================
# 1. PROJECT PATHS AND NAMESPACES
# ============================================================

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "workspace"
CATALOG = WORKSPACE / "catalog-v001.xml"

FOOD_SCHEMA = "https://example.org/food-kr/schema#"
FOOD_IDS = "https://example.org/food-kr/id/"

REFERENCE_ONTOLOGY = WORKSPACE / "food-reasoning-clean.ttl"


# ============================================================
# 2. READ LOCAL ONTOLOGY CATALOG
# ============================================================

def catalog_map(catalog=CATALOG):
    """
    Return a dictionary mapping ontology IRIs to local files.

    Supports catalogs that reference other catalogs.
    """

    namespace = "urn:oasis:names:tc:entity:xmlns:xml:catalog"

    found = {}
    todo = [Path(catalog).resolve()]
    seen = set()

    while todo:
        current = todo.pop()

        if current in seen or not current.exists():
            continue

        seen.add(current)

        root = ET.parse(current).getroot()

        for element in root.iter(f"{{{namespace}}}uri"):
            name = element.get("name")
            uri = element.get("uri")

            if name and uri:
                found.setdefault(
                    name,
                    (current.parent / uri).resolve()
                )

        for element in root.iter(f"{{{namespace}}}nextCatalog"):
            next_catalog = element.get("catalog")

            if next_catalog:
                todo.append(
                    (current.parent / next_catalog).resolve()
                )

    return found


# ============================================================
# 3. PARSE ONTOLOGY FILES
# ============================================================

def parse_ontology(graph, path):
    """
    Load an RDF/OWL ontology into an RDFLib graph.
    """

    path = Path(path).resolve()

    if not path.exists():
        raise SystemExit(
            f"Ontology file not found: {path}"
        )

    suffix = path.suffix.lower()

    if suffix == ".ttl":
        format_name = "turtle"

    elif suffix in [".rdf", ".owl", ".xml"]:
        format_name = "xml"

    elif suffix == ".nt":
        format_name = "nt"

    else:
        raise SystemExit(
            f"Unsupported ontology file format: {suffix}"
        )

    graph.parse(
        path,
        format=format_name
    )


# ============================================================
# 4. RESOLVE IMPORTS
# ============================================================

def resolve_import(import_iri, catalog):
    """
    Resolve an owl:imports IRI to a local file.

    Resolution order:
    1. XML catalog.
    2. Local file:/// URI.
    3. Known project reference-ontology alias.

    Missing imports produce an explicit error.
    """

    key = str(import_iri)

    # First try the XML catalog.
    target = (
        catalog.get(key)
        or catalog.get(key.rstrip("/#"))
        or catalog.get(key + "/")
    )

    if target is not None and Path(target).exists():
        return Path(target).resolve()

    # Handle local file:/// URIs.
    if key.startswith("file:"):
        parsed = urlparse(key)

        if parsed.netloc not in ("", "localhost"):
            raise SystemExit(
                f"Unsupported file URI host: {parsed.netloc}"
            )

        target = Path(
            url2pathname(parsed.path)
        ).resolve()

        if target.exists():
            return target

        # A known alias used by the Session 3 sample files.
        if (
            target.name == "food-ontology-reference.ttl"
            and REFERENCE_ONTOLOGY.exists()
        ):
            print(
                "Using food-reasoning-clean.ttl for "
                "missing food-ontology-reference.ttl"
            )

            return REFERENCE_ONTOLOGY.resolve()

    raise SystemExit(
        f"Imported ontology not found: {key}\n"
        f"Check the local file and catalog: {CATALOG}"
    )


# ============================================================
# 5. MERGE ONTOLOGY IMPORTS
# ============================================================

def merged_graph(start):
    """
    Load the starting ontology and all its owl:imports.

    All imports are resolved locally.

    The returned graph contains no owl:imports statements.
    """

    catalog = catalog_map()

    graph = Graph()

    todo = [Path(start).resolve()]
    done = set()

    while todo:
        path = todo.pop()

        if path in done:
            continue

        done.add(path)

        part = Graph()

        parse_ontology(part, path)

        for _, _, imported_iri in part.triples(
            (None, OWL.imports, None)
        ):
            target = resolve_import(
                imported_iri,
                catalog
            )

            todo.append(target)

        # Imported ontologies are merged directly.
        part.remove(
            (None, OWL.imports, None)
        )

        graph += part

    return graph


# ============================================================
# 6. RUN HERMIT REASONER
# ============================================================

def reason(start):
    """
    Run HermiT on the merged ontology.

    Returns an Owlready2 World object.
    """

    import owlready2

    graph = merged_graph(start)

    # Serialize to RDF/XML in memory.
    # Avoids Windows temporary-file URI problems.
    rdfxml = graph.serialize(
        format="xml"
    )

    if isinstance(rdfxml, str):
        rdfxml = rdfxml.encode("utf-8")

    world = owlready2.World()

    ontology = world.get_ontology(
        "https://example.org/food-kr/local-reasoner"
    )

    ontology.load(
        fileobj=BytesIO(rdfxml)
    )

    try:
        owlready2.sync_reasoner_hermit(
            world,
            infer_property_values=False,
            debug=0
        )

        world.inconsistent = False

    except owlready2.OwlReadyInconsistentOntologyError:
        world.inconsistent = True

    return world


# ============================================================
# 7. ENTITY LABELS
# ============================================================

def label(entity):
    """
    Return a human-readable label if available.

    Otherwise return the final part of the IRI.
    """

    for text in entity.label:
        return str(text)

    return (
        entity.iri
        .rsplit("#", 1)[-1]
        .rsplit("/", 1)[-1]
    )


# ============================================================
# 8. REASONING SUMMARY
# ============================================================

def summary(world):
    """
    Report:
    - Whether the ontology is inconsistent.
    - Unsatisfiable food classes.
    - Inferred types of food individuals.
    """

    if world.inconsistent:
        return {
            "inconsistent": True,
            "impossible": [],
            "types": {}
        }

    impossible = sorted(
        label(cls)
        for cls in world.inconsistent_classes()
        if cls.iri.startswith(FOOD_SCHEMA)
    )

    types = {}

    for individual in world.individuals():
        if (
            individual.iri.startswith(FOOD_SCHEMA)
            or individual.iri.startswith(FOOD_IDS)
        ):
            types[label(individual)] = sorted(
                label(cls)
                for cls in individual.is_a
                if hasattr(cls, "iri")
            )

    return {
        "inconsistent": False,
        "impossible": impossible,
        "types": types
    }


# ============================================================
# 9. MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        raise SystemExit(__doc__)

    ontology_file = Path(
        sys.argv[1]
    ).resolve()

    print("\nFood Knowledge Representation")
    print("Session 3 - Local HermiT Reasoner")
    print("-" * 48)

    print(f"Ontology: {ontology_file.name}")
    print("Reasoner: HermiT")
    print("Mode: Offline")

    print("\nRunning reasoning...")

    result = summary(
        reason(ontology_file)
    )

    if result["inconsistent"]:
        print("\nThe ontology is INCONSISTENT.")

        print(
            "Its axioms and assertions contradict each other."
        )

    else:
        print("\nOntology is consistent.")

    print(
        "\nImpossible classes (equivalent to owl:Nothing):",
        ", ".join(result["impossible"]) or "none"
    )

    print("\nIndividual classifications:")

    if not result["types"]:
        print("  No food individuals found.")

    for name, classes in sorted(result["types"].items()):
        print(
            f"  {name}: "
            f"{', '.join(classes) or 'No named types'}"
        )
