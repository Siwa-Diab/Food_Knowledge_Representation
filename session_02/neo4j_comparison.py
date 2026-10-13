
"""Compare the USDA Food Knowledge Graph using Neo4j and Cypher.

Run from session_02:
    python neo4j_comparison.py

Reads the four processed USDA CSV files, imports nodes and
relationships in batches, runs seven Cypher queries, and saves
a report in output/neo4j-comparison.txt.

Safe to rerun: MERGE uses stable source identifiers.
"""

import time
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable


# =========================================================
# 1. CONFIGURATION
# =========================================================

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "processed"
OUTPUT = HERE / "output"

NEO4J_URI = "bolt://localhost:7688"
NEO4J_AUTH = ("neo4j", "food-kr-pw")

BATCH_SIZE = 1000


# =========================================================
# 2. DATA HELPERS
# =========================================================

def clean(value):
    """Convert missing values to None, not string 'nan'."""
    if pd.isna(value):
        return None

    value = str(value).strip()
    return value if value else None


def optional_float(value):
    """Convert a numeric CSV value or return None."""
    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def batches(rows, size=BATCH_SIZE):
    """Yield batches without retaining another full copy."""
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def execute_batches(session, query, rows, label):
    """Execute a parameterized Cypher import in batches."""
    start = time.perf_counter()

    for index, batch in enumerate(batches(rows), start=1):
        session.run(query, rows=batch).consume()

        if index % 50 == 0:
            print(
                f"  {label}: "
                f"{min(index * BATCH_SIZE, len(rows)):,}"
                f"/{len(rows):,}"
            )

    elapsed = time.perf_counter() - start
    print(f"  {label}: {len(rows):,} records in {elapsed:.1f} s")


# =========================================================
# 3. CYPHER IMPORT STATEMENTS
# =========================================================

IMPORT_FOODS = """
UNWIND $rows AS r
MERGE (f:Food {fdc_id: r.fdc_id})
SET f.description = r.description,
    f.data_type = r.data_type
"""

IMPORT_BRANDED = """
UNWIND $rows AS r
MERGE (f:Food {fdc_id: r.fdc_id})
SET f:BrandedFood,
    f.brand_owner = r.brand_owner,
    f.brand_name = r.brand_name,
    f.gtin_upc = r.gtin_upc,
    f.ingredients = r.ingredients,
    f.category = r.category
"""

IMPORT_NUTRIENTS = """
UNWIND $rows AS r
MERGE (n:Nutrient {id: r.id})
SET n.name = r.name,
    n.unit_name = r.unit_name
"""

IMPORT_MEASUREMENTS = """
UNWIND $rows AS r
MATCH (f:Food {fdc_id: r.fdc_id})
MATCH (n:Nutrient {id: r.nutrient_id})
MERGE (m:NutrientMeasurement {id: r.id})
SET m.amount = r.amount
MERGE (f)-[:HAS_MEASUREMENT]->(m)
MERGE (m)-[:OF_NUTRIENT]->(n)
"""


# =========================================================
# 4. CYPHER QUESTIONS
# =========================================================

QUESTIONS = [
    (
        "Q1 - products whose declarations mention sesame",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NOT NULL
          AND toLower(f.ingredients) CONTAINS 'sesame'
        RETURN f.fdc_id AS fdc_id,
               f.description AS description,
               f.ingredients AS ingredients
        ORDER BY f.fdc_id
        LIMIT 10
        """
    ),
    (
        "Q2 - sesame mentions by food category",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NOT NULL
          AND toLower(f.ingredients) CONTAINS 'sesame'
          AND f.category IS NOT NULL
        RETURN f.category AS category,
               count(f) AS products
        ORDER BY products DESC, category
        """
    ),
    (
        "Q3 - sesame mentions by brand owner",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NOT NULL
          AND toLower(f.ingredients) CONTAINS 'sesame'
          AND f.brand_owner IS NOT NULL
        RETURN f.brand_owner AS brandOwner,
               count(f) AS products
        ORDER BY products DESC, brandOwner
        """
    ),
    (
        "Q4 - any sesame candidate without nutrient measurements?",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NOT NULL
          AND toLower(f.ingredients) CONTAINS 'sesame'
          AND NOT EXISTS {
              MATCH (f)-[:HAS_MEASUREMENT]->(:NutrientMeasurement)
          }
        RETURN count(f) > 0 AS answer
        """
    ),
    (
        "Q5 - usable and missing ingredient declarations",
        """
        MATCH (f:BrandedFood)
        RETURN count(f) AS total,
               count(f.ingredients) AS usable,
               count(f) - count(f.ingredients) AS missing
        """
    ),
    (
        "Q6 - UNKNOWN products without ingredient declarations",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NULL
        RETURN f.fdc_id AS fdc_id,
               f.description AS description
        ORDER BY f.fdc_id
        LIMIT 10
        """
    ),
    (
        "Q7 - sesame candidates with category information",
        """
        MATCH (f:BrandedFood)
        WHERE f.ingredients IS NOT NULL
          AND toLower(f.ingredients) CONTAINS 'sesame'
          AND f.category IS NOT NULL
        RETURN count(f) AS productsWithCategory
        """
    ),
]


# =========================================================
# 5. READ CSV DATA
# =========================================================

def read_data():
    print("Reading processed USDA CSV files...")

    food = pd.read_csv(
        DATA / "food.csv",
        dtype={"fdc_id": str},
        low_memory=False,
    )

    branded = pd.read_csv(
        DATA / "branded_food.csv",
        dtype={"fdc_id": str, "gtin_upc": str},
        low_memory=False,
    )

    nutrients = pd.read_csv(
        DATA / "nutrient.csv",
        dtype={"id": str},
        low_memory=False,
    )

    measurements = pd.read_csv(
        DATA / "food_nutrient.csv",
        dtype={
            "id": str,
            "fdc_id": str,
            "nutrient_id": str,
        },
        low_memory=False,
    )

    print(f"  Foods: {len(food):,}")
    print(f"  Branded foods: {len(branded):,}")
    print(f"  Nutrients: {len(nutrients):,}")
    print(f"  Nutrient measurements: {len(measurements):,}")

    return food, branded, nutrients, measurements


# =========================================================
# 6. CREATE DATABASE CONSTRAINTS
# =========================================================

def create_constraints(session):
    print("\nCreating unique identifier constraints...")

    constraints = [
        """
        CREATE CONSTRAINT food_id IF NOT EXISTS
        FOR (f:Food) REQUIRE f.fdc_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT nutrient_id IF NOT EXISTS
        FOR (n:Nutrient) REQUIRE n.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT measurement_id IF NOT EXISTS
        FOR (m:NutrientMeasurement) REQUIRE m.id IS UNIQUE
        """,
    ]

    for statement in constraints:
        session.run(statement).consume()

    print("Constraints ready.")


# =========================================================
# 7. IMPORT THE FOOD GRAPH
# =========================================================

def import_graph(session, food, branded, nutrients, measurements):
    print("\nImporting USDA data into Neo4j...")

    food_rows = [
        {
            "fdc_id": clean(r.fdc_id),
            "description": clean(r.description),
            "data_type": clean(r.data_type),
        }
        for r in food.itertuples(index=False)
    ]

    branded_rows = [
        {
            "fdc_id": clean(r.fdc_id),
            "brand_owner": clean(r.brand_owner),
            "brand_name": clean(r.brand_name),
            "gtin_upc": clean(r.gtin_upc),
            "ingredients": clean(r.ingredients),
            "category": clean(r.branded_food_category),
        }
        for r in branded.itertuples(index=False)
    ]

    nutrient_rows = [
        {
            "id": clean(r.id),
            "name": clean(r.name),
            "unit_name": clean(r.unit_name),
        }
        for r in nutrients.itertuples(index=False)
    ]

    execute_batches(session, IMPORT_FOODS, food_rows, "Foods")
    execute_batches(session, IMPORT_BRANDED, branded_rows, "Branded foods")
    execute_batches(session, IMPORT_NUTRIENTS, nutrient_rows, "Nutrients")

    # Build measurement batches directly from the dataframe
    # to avoid storing another large list in memory.
    start = time.perf_counter()
    total = len(measurements)

    for offset in range(0, total, BATCH_SIZE):
        chunk = measurements.iloc[offset:offset + BATCH_SIZE]

        rows = [
            {
                "id": clean(r.id),
                "fdc_id": clean(r.fdc_id),
                "nutrient_id": clean(r.nutrient_id),
                "amount": optional_float(r.amount),
            }
            for r in chunk.itertuples(index=False)
        ]

        session.run(IMPORT_MEASUREMENTS, rows=rows).consume()

        processed = min(offset + BATCH_SIZE, total)

        if processed % 10000 < BATCH_SIZE or processed == total:
            print(f"  Measurements: {processed:,}/{total:,}")

    elapsed = time.perf_counter() - start
    print(f"  Measurement import completed in {elapsed:.1f} s")


# =========================================================
# 8. RUN CYPHER QUERIES AND SAVE RESULTS
# =========================================================

def run_queries(session):
    print("\nRunning Cypher queries...\n")

    lines = []

    for label, query in QUESTIONS:
        # Warm up the query once, like the professor's script.
        session.run(query).consume()

        start = time.perf_counter()
        records = list(session.run(query))
        elapsed_ms = (time.perf_counter() - start) * 1000

        lines.append(
            f"[{label}] {len(records)} rows in {elapsed_ms:.1f} ms"
        )

        for record in records[:6]:
            lines.append(f"    {dict(record)}")

    report = "\n".join(lines)

    print(report)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    report_path = OUTPUT / "neo4j-comparison.txt"
    report_path.write_text(report + "\n", encoding="utf-8")

    print(f"\nReport saved to: {report_path}")


# =========================================================
# 9. VERIFY GRAPH COUNTS
# =========================================================

def verify_graph(session):
    print("\nVerifying Neo4j graph...")

    queries = [
        ("Foods", "MATCH (n:Food) RETURN count(n) AS n"),
        ("Branded foods", "MATCH (n:BrandedFood) RETURN count(n) AS n"),
        ("Nutrients", "MATCH (n:Nutrient) RETURN count(n) AS n"),
        (
            "Nutrient measurements",
            "MATCH (n:NutrientMeasurement) RETURN count(n) AS n",
        ),
        (
            "Measurement links",
            "MATCH ()-[r:HAS_MEASUREMENT]->() RETURN count(r) AS n",
        ),
    ]

    for label, query in queries:
        count = session.run(query).single()["n"]
        print(f"  {label}: {count:,}")


# =========================================================
# 10. MAIN
# =========================================================

def main():
    food, branded, nutrients, measurements = read_data()

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=NEO4J_AUTH,
    )

    try:
        driver.verify_connectivity()
        print("\nConnected to Neo4j successfully.")

        with driver.session(database="neo4j") as session:
            create_constraints(session)

            import_graph(
                session,
                food,
                branded,
                nutrients,
                measurements,
            )

            verify_graph(session)
            run_queries(session)

    finally:
        driver.close()


if __name__ == "__main__":
    try:
        main()

    except ServiceUnavailable:
        print(
            "ERROR: Cannot connect to Neo4j at localhost:7688.\n"
            "Start the service using: docker compose up -d neo4j"
        )

    except AuthError:
        print(
            "ERROR: Neo4j authentication failed.\n"
            "Check the username and password in docker-compose.yml."
        )
