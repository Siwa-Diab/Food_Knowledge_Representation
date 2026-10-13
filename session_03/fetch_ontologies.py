
"""
Session 3 - Food Knowledge Representation
Prepare and verify local OWL ontologies for offline reasoning.

Adapted from the professor's fetch_ontologies.py.

Unlike the supply-chain exercise, this project uses a locally
developed food ontology. No SCRO/IOF downloads are required.

This script:
1. Checks that the food ontology and sample files exist.
2. Creates or updates the local XML import catalog.
3. Replaces the sample's obsolete local-file import with the
   ontology's stable IRI.
4. Preserves a backup before modifying the sample.
5. Writes a provenance and licensing note.
6. Verifies that all local imports resolve.

Run from the project root:

    python session_03/fetch_ontologies.py
"""

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from rdflib import Graph, OWL, URIRef


# ============================================================
# 1. PROJECT PATHS
# ============================================================

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE / "workspace"

ONTOLOGY = WORKSPACE / "food-reasoning-clean.ttl"
SAMPLE = WORKSPACE / "sample-foods.ttl"
DOMAIN_MISTAKE = WORKSPACE / "domain-mistake.ttl"

CATALOG = WORKSPACE / "catalog-v001.xml"
LICENCES = WORKSPACE / "LICENCES.md"

ONTOLOGY_IRI = "https://example.org/food-kr/ontology"

CATALOG_NS = (
    "urn:oasis:names:tc:entity:xmlns:xml:catalog"
)

ET.register_namespace("", CATALOG_NS)


# ============================================================
# 2. CHECK REQUIRED FILES
# ============================================================

def check_files():
    """
    Verify that the ontology and sample files are present.
    """

    print("\nStep 1: Checking project files")

    required = [
        ONTOLOGY,
        SAMPLE,
        DOMAIN_MISTAKE,
    ]

    missing = []

    for path in required:
        if path.exists():
            print(f"  FOUND: {path.name}")
        else:
            print(f"  MISSING: {path.name}")
            missing.append(path)

    if missing:
        raise SystemExit(
            "\nRequired files are missing. "
            "Restore them before continuing."
        )

    # Confirm the ontology file is valid Turtle.
    graph = Graph()
    graph.parse(ONTOLOGY, format="turtle")

    if (
        URIRef(ONTOLOGY_IRI),
        None,
        OWL.Ontology
    ) not in graph:
        raise SystemExit(
            f"Ontology IRI not found in {ONTOLOGY.name}:\n"
            f"  {ONTOLOGY_IRI}"
        )

    print(
        f"  Ontology parsed successfully: "
        f"{len(graph)} triples"
    )


# ============================================================
# 3. CREATE OR UPDATE XML CATALOG
# ============================================================

def update_catalog():
    """
    Register the food ontology's stable IRI.

    Preserve any existing catalog entries.
    """

    print("\nStep 2: Preparing offline catalog")

    WORKSPACE.mkdir(parents=True, exist_ok=True)

    if CATALOG.exists():
        tree = ET.parse(CATALOG)
        root = tree.getroot()
    else:
        root = ET.Element(
            f"{{{CATALOG_NS}}}catalog"
        )
        tree = ET.ElementTree(root)

    entry_tag = f"{{{CATALOG_NS}}}uri"

    entries = [
        entry
        for entry in root.iter(entry_tag)
        if entry.get("name") == ONTOLOGY_IRI
    ]

    if entries:
        entry = entries[0]
        entry.set("uri", "./food-reasoning-clean.ttl")

        # Remove duplicate mappings for the same IRI
        # when they are direct children of this catalog.
        for duplicate in entries[1:]:
            if duplicate in list(root):
                root.remove(duplicate)
    else:
        ET.SubElement(
            root,
            entry_tag,
            {
                "id": "Food KR ontology",
                "name": ONTOLOGY_IRI,
                "uri": "./food-reasoning-clean.ttl",
            }
        )

    tree.write(
        CATALOG,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"  Catalog: {CATALOG.name}")
    print(f"  Registered: {ONTOLOGY_IRI}")
    print("  Local file: food-reasoning-clean.ttl")


# ============================================================
# 4. UPDATE SAMPLE ONTOLOGY IMPORT
# ============================================================

def update_sample_import():
    """
    Replace the obsolete food-ontology-reference.ttl import.

    Use the ontology's stable IRI instead of a machine-specific
    file:///C:/... path.

    A backup is created before the first modification.
    """

    print("\nStep 3: Checking sample ontology imports")

    graph = Graph()
    graph.parse(SAMPLE, format="turtle")

    imports = list(
        graph.triples((None, OWL.imports, None))
    )

    obsolete = [
        (subject, predicate, target)
        for subject, predicate, target in imports
        if (
            str(target).startswith("file:")
            and Path(
                url2pathname(
                    urlparse(str(target)).path
                )
            ).name == "food-ontology-reference.ttl"
        )
    ]

    if not obsolete:
        print(
            "  No obsolete food-ontology-reference.ttl "
            "imports found."
        )
        return

    backup = SAMPLE.with_suffix(".ttl.bak")

    if not backup.exists():
        shutil.copy2(SAMPLE, backup)
        print(f"  Backup created: {backup.name}")

    for subject, predicate, target in obsolete:
        graph.remove((subject, predicate, target))
        graph.add((
            subject,
            OWL.imports,
            URIRef(ONTOLOGY_IRI)
        ))

    graph.serialize(
        destination=SAMPLE,
        format="turtle"
    )

    print(
        "  Updated sample-foods.ttl to import "
        "the stable food ontology IRI."
    )
    print(
        "  Note: RDFLib may reformat the Turtle file."
    )


# ============================================================
# 5. WRITE PROVENANCE AND LICENSING NOTE
# ============================================================

LICENCES_TEXT = """# Ontology provenance and licensing

## Food Knowledge Representation ontology

- Ontology IRI: https://example.org/food-kr/ontology
- Local file: food-reasoning-clean.ttl
- Purpose: Represent branded food products, ingredient concepts,
  and sesame declaration candidates.
- License: Not yet selected. A license must be chosen by the
  ontology's rights holder before publishing under that license.

## USDA FoodData Central

- Source: https://fdc.nal.usda.gov/
- Data used in this project: A processed subset of branded food
  records and associated nutrient data.
- Dataset attribution, usage conditions, and redistribution rights:
  Review the official source documentation before publishing
  the processed dataset.

## Third-party ontology reuse

- This Session 3 food ontology does not require downloading
  IOF SCRO, IOF Core, BFO, or the GS1 vocabulary.
- No third-party ontology license is asserted by this script.

## Reasoning tools

- RDFLib: RDF parsing and serialization.
- Owlready2 / HermiT: OWL reasoning.
- ROBOT / ELK: Ontology reasoning and quality reports.

Tool software licenses are separate from the license selected
for this project's ontology.
"""


def write_licences_note():
    """
    Write the project's provenance and licensing notes.

    Preserve any existing manually edited note.
    """

    print("\nStep 4: Checking licensing documentation")

    if LICENCES.exists():
        print(
            "  LICENCES.md already exists; "
            "preserving its contents."
        )
    else:
        LICENCES.write_text(
            LICENCES_TEXT,
            encoding="utf-8"
        )
        print("  Created LICENCES.md")


# ============================================================
# 6. VERIFY OFFLINE CATALOG
# ============================================================

def verify_catalog():
    """
    Confirm the food ontology IRI resolves to a real local file.
    """

    print("\nStep 5: Verifying offline catalog")

    tree = ET.parse(CATALOG)
    root = tree.getroot()

    entry_tag = f"{{{CATALOG_NS}}}uri"

    matches = [
        entry
        for entry in root.iter(entry_tag)
        if entry.get("name") == ONTOLOGY_IRI
    ]

    if not matches:
        raise SystemExit(
            "Catalog verification FAILED: "
            "food ontology IRI is not registered."
        )

    local_path = (
        CATALOG.parent / matches[0].get("uri")
    ).resolve()

    if not local_path.exists():
        raise SystemExit(
            "Catalog verification FAILED: "
            f"local file does not exist: {local_path}"
        )

    # Verify the sample's imports can be resolved locally.
    sample_graph = Graph()
    sample_graph.parse(SAMPLE, format="turtle")

    imports = [
        str(target)
        for target in sample_graph.objects(
            None, OWL.imports
        )
    ]

    for imported_iri in imports:
        if imported_iri == ONTOLOGY_IRI:
            continue

        if imported_iri.startswith("file:"):
            parsed = urlparse(imported_iri)
            if parsed.netloc not in ("", "localhost"):
                raise SystemExit(
                    "Unsupported local import host: "
                    f"{imported_iri}"
                )

            imported_path = Path(
                url2pathname(parsed.path)
            )

            if imported_path.exists():
                continue

        raise SystemExit(
            "Sample import not resolved offline: "
            f"{imported_iri}"
        )

    print("  Food ontology resolves offline.")
    print("  Sample ontology imports resolve offline.")
    print("  Catalog verification PASSED.")


# ============================================================
# 7. MAIN
# ============================================================

def main():

    print("\nFood Knowledge Representation")
    print("Session 3 - Prepare Local Ontologies")
    print("-" * 48)

    WORKSPACE.mkdir(
        parents=True,
        exist_ok=True
    )

    check_files()
    update_catalog()
    update_sample_import()
    write_licences_note()
    verify_catalog()

    print("\nPreparation complete.")
    print("\nNext commands:")
    print(
        "  python session_03/local_reasoner.py "
        "session_03/workspace/sample-foods.ttl"
    )
    print(
        "  python session_03/robot_report.py"
    )


if __name__ == "__main__":
    main()
