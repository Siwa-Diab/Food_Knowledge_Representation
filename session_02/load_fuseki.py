
"""Load the USDA Food Knowledge Graph into Apache Jena Fuseki.

Run:
    python load_fuseki.py

The RDF data is loaded into the default graph of the
persistent 'foodkr' dataset.

HTTP PUT replaces the default graph if the script is rerun.
"""

import time
from pathlib import Path

import requests


# =========================================================
# 1. FUSEKI CONFIGURATION
# =========================================================

FUSEKI_BASE = "http://localhost:3031"
DATASET = "foodkr"

# Location of the generated RDF Turtle file
TTL_PATH = (
    Path(__file__).resolve().parent
    / "output"
    / "food_knowledge_graph.ttl"
)

EXPECTED_TRIPLES = 1_200_721


# =========================================================
# 2. LOAD RDF DATA INTO FUSEKI
# =========================================================

def load():
    """Upload the Turtle file to Fuseki's default graph."""

    if not TTL_PATH.is_file():
        raise FileNotFoundError(
            f"RDF file not found: {TTL_PATH}\n"
            "Run convert_to_rdf.py first."
        )

    print(f"Loading {TTL_PATH.name} into Fuseki...")
    print(f"Dataset: {FUSEKI_BASE}/{DATASET}")

    start = time.perf_counter()

    # Open the file in binary mode to avoid loading it
    # entirely into Python memory.
    with TTL_PATH.open("rb") as rdf_file:

        response = requests.put(
            f"{FUSEKI_BASE}/{DATASET}/data?default",
            data=rdf_file,
            headers={
                "Content-Type": "text/turtle"
            },
            timeout=900,
        )

    # Raise an exception if Fuseki reports an HTTP error.
    response.raise_for_status()

    elapsed = time.perf_counter() - start

    print(f"Upload completed in {elapsed:.1f} seconds.")


# =========================================================
# 3. VERIFY THE LOADED RDF TRIPLES
# =========================================================

def confirm():
    """Run a SPARQL query to count the uploaded triples."""

    query = """
    SELECT (COUNT(*) AS ?n)
    WHERE {
        ?s ?p ?o .
    }
    """

    response = requests.get(
        f"{FUSEKI_BASE}/{DATASET}/sparql",
        params={
            "query": query
        },
        headers={
            "Accept": "application/sparql-results+json"
        },
        timeout=180,
    )

    response.raise_for_status()

    result = response.json()

    count = int(
        result["results"]["bindings"][0]["n"]["value"]
    )

    print(f"Fuseki contains {count:,} triples.")

    if count == EXPECTED_TRIPLES:
        print(
            "SUCCESS: Triple count matches "
            "the RDF conversion!"
        )
    else:
        print(
            f"WARNING: Expected {EXPECTED_TRIPLES:,} "
            f"triples, but found {count:,}."
        )


# =========================================================
# 4. MAIN PROGRAM
# =========================================================

if __name__ == "__main__":

    try:
        load()
        confirm()

    except requests.ConnectionError:
        print(
            "ERROR: Cannot connect to Fuseki.\n"
            "Make sure Docker is running and "
            "http://localhost:3031 is accessible."
        )

    except requests.Timeout:
        print(
            "ERROR: The request timed out.\n"
            "Check Fuseki's status before retrying."
        )

    except requests.HTTPError as error:
        print(f"HTTP ERROR: {error}")
        print(
            "Check that the 'foodkr' dataset exists "
            "and allows updates."
        )

    except FileNotFoundError as error:
        print(f"FILE ERROR: {error}")
