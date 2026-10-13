
"""Record provenance for the USDA Food Knowledge Representation graph.

Adapted from the professor's Session 4 add_provenance.py.

Run from the project root:

    python session_04/add_provenance.py

Reads:
    session_02/output/food_knowledge_graph.trig
    session_02/convert_to_rdf.py
    data/processed/*.csv

Writes:
    session_04/provenance.ttl

Uses PROV-O to describe:
    - source files and named graphs as Entities
    - RDF conversion as an Activity
    - the converter program as a SoftwareAgent

Answers one provenance question using SPARQL.
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import (
    RDF,
    RDFS,
    XSD,
    Dataset,
    Graph,
    Literal,
    Namespace,
    URIRef,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

TRIG = ROOT / "session_02" / "output" / "food_knowledge_graph.trig"
CONVERTER = ROOT / "session_02" / "convert_to_rdf.py"
PROCESSED = ROOT / "data" / "processed"

DATA = Namespace("https://example.org/food-kr/id/")
FOOD = Namespace("https://example.org/food-kr/schema#")

PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")
VOID = Namespace("http://rdfs.org/ns/void#")

TABLE_FILE = {
    "food": "food.csv",
    "branded_food": "branded_food.csv",
    "food_nutrient": "food_nutrient.csv",
    "nutrient": "nutrient.csv",
}


def sha256(path):
    """Calculate the SHA-256 hash of a file without loading it all into memory."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def when(path):
    """Return a file's last modification time in UTC."""

    return datetime.fromtimestamp(
        path.stat().st_mtime,
        timezone.utc,
    ).replace(microsecond=0)


def main():

    if not TRIG.exists():
        sys.exit(
            "TriG graph not found. Run Session 2 convert_to_rdf.py first."
        )

    if not CONVERTER.exists():
        sys.exit(f"Converter not found: {CONVERTER}")

    for filename in TABLE_FILE.values():
        path = PROCESSED / filename
        if not path.exists():
            sys.exit(f"Source CSV not found: {path}")

    # --------------------------------------------------------
    # Step 1: Load the named graphs
    # --------------------------------------------------------

    ds = Dataset()
    ds.parse(TRIG, format="trig")

    # The file modification time is a proxy for conversion time.
    made = when(TRIG)

    # --------------------------------------------------------
    # Step 2: Create the provenance RDF graph
    # --------------------------------------------------------

    g = Graph()

    for prefix, namespace in (
        ("prov", PROV),
        ("dcterms", DCT),
        ("void", VOID),
        ("xsd", XSD),
        ("rdfs", RDFS),
    ):
        g.bind(prefix, namespace)

    # --------------------------------------------------------
    # Step 3: Describe the converter as a SoftwareAgent
    # --------------------------------------------------------

    program = URIRef(
        f"{DATA}software/session-02/convert_to_rdf.py"
    )

    g.add((program, RDF.type, PROV.SoftwareAgent))
    g.add((
        program,
        RDFS.label,
        Literal("convert_to_rdf.py (Session 2)"),
    ))
    g.add((
        program,
        DCT.identifier,
        Literal("sha256:" + sha256(CONVERTER)),
    ))

    # --------------------------------------------------------
    # Step 4: Describe the conversion Activity
    # --------------------------------------------------------

    run = URIRef(
        f"{DATA}run/usda/convert-"
        f"{made.strftime('%Y%m%dT%H%M%SZ')}"
    )

    g.add((run, RDF.type, PROV.Activity))
    g.add((
        run,
        RDFS.label,
        Literal("Session 2 conversion of USDA processed CSV files to RDF"),
    ))
    g.add((run, PROV.wasAssociatedWith, program))
    g.add((
        run,
        PROV.endedAtTime,
        Literal(made.isoformat(), datatype=XSD.dateTime),
    ))

    # --------------------------------------------------------
    # Step 5: Record each CSV and its corresponding named graph
    # --------------------------------------------------------

    rows = []

    for table, filename in TABLE_FILE.items():

        csv_path = PROCESSED / filename

        file_iri = URIRef(
            f"{DATA}file/usda/{filename}"
        )

        graph_iri = URIRef(
            f"{DATA}graph/usda/{table}"
        )

        triple_count = len(ds.graph(graph_iri))

        # CSV file as a provenance Entity
        g.add((file_iri, RDF.type, PROV.Entity))
        g.add((
            file_iri,
            DCT.title,
            Literal(filename),
        ))
        g.add((
            file_iri,
            DCT.identifier,
            Literal("sha256:" + sha256(csv_path)),
        ))

        # Conversion activity used the CSV
        g.add((run, PROV.used, file_iri))

        # Named graph as a provenance Entity
        g.add((graph_iri, RDF.type, PROV.Entity))
        g.add((
            graph_iri,
            PROV.wasDerivedFrom,
            file_iri,
        ))
        g.add((
            graph_iri,
            PROV.wasGeneratedBy,
            run,
        ))
        g.add((
            graph_iri,
            PROV.generatedAtTime,
            Literal(made.isoformat(), datatype=XSD.dateTime),
        ))
        g.add((
            graph_iri,
            VOID.triples,
            Literal(triple_count),
        ))

        rows.append((table, filename, triple_count))

    # --------------------------------------------------------
    # Step 6: Record the schema graph
    #
    # It is generated by the converter rather than read
    # directly from a separate CSV file.
    # --------------------------------------------------------

    schema_iri = URIRef(
        f"{DATA}graph/usda/schema"
    )

    schema_count = len(ds.graph(schema_iri))

    g.add((schema_iri, RDF.type, PROV.Entity))
    g.add((
        schema_iri,
        PROV.wasGeneratedBy,
        run,
    ))
    g.add((
        schema_iri,
        PROV.generatedAtTime,
        Literal(made.isoformat(), datatype=XSD.dateTime),
    ))
    g.add((
        schema_iri,
        VOID.triples,
        Literal(schema_count),
    ))

    rows.append(("schema", "generated by converter", schema_count))

    # --------------------------------------------------------
    # Step 7: Save provenance RDF
    # --------------------------------------------------------

    output = HERE / "provenance.ttl"

    g.serialize(
        destination=str(output),
        format="turtle",
    )

    print(
        f"provenance.ttl: {len(g)} triples about "
        f"{len(rows)} named graphs, 1 run, 1 program"
    )

    for table, source, count in rows:
        print(
            f"  graph {table:<17} "
            f"{count:>10,} triples "
            f"derived from {source}"
        )

    # --------------------------------------------------------
    # Step 8: Answer a provenance question using SPARQL
    #
    # Find an actual food description triple, then identify
    # its named graph, source CSV, and conversion activity.
    # --------------------------------------------------------

    provenance_graph = URIRef(
        f"{DATA}graph/usda/provenance"
    )

    ds.graph(provenance_graph).parse(
        output,
        format="turtle",
    )

    query = """
    PREFIX food: <https://example.org/food-kr/schema#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT ?product ?description ?g ?file ?run ?time
    WHERE {
        GRAPH ?g {
            ?product food:description ?description .
        }

        GRAPH ?p {
            ?g prov:wasDerivedFrom ?source ;
               prov:wasGeneratedBy ?run .

            ?source dcterms:title ?file .
            ?run prov:endedAtTime ?time .
        }
    }
    LIMIT 1
    """

    results = list(ds.query(query))

    if results:

        result = results[0]

        print("\nProvenance question:")
        print("Where did this food description come from?")

        print(f"  product     {result.product}")
        print(f"  description {result.description}")
        print(f"  named graph {result.g}")
        print(f"  source file {result.file}")
        print(f"  run         {result.run}")
        print(f"  time        {result.time}")

    else:
        print(
            "\nNo matching food description found "
            "for the provenance query."
        )

    print(
        "\nNote: recorded file hashes reflect the current files; "
        "the TriG modification time is only a proxy for conversion time."
    )


if __name__ == "__main__":
    main()
