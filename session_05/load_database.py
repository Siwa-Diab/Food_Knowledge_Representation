
"""Load processed USDA FoodData Central tables into PostgreSQL.

Session 05 - Food Knowledge Representation Project

Run from the project root:

    python session_05/load_database.py

Or use SQLite:

    python session_05/load_database.py --sqlite

The four input CSV files are located in:
    data/processed/

IMPORTANT:
    Missing values are stored as SQL NULL, not strings such as
    "None" or "NaN". This keeps the relational database consistent
    with the RDF conversion performed in Session 02.
"""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Text


# ============================================================
# 1. PROJECT PATHS
# ============================================================

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

DATA_DIR = PROJECT_ROOT / "data" / "processed"


# ============================================================
# 2. DATABASE CONNECTIONS
# ============================================================

# PostgreSQL runs inside Docker.
# Port 5433 on Windows maps to port 5432 inside the container.

POSTGRES_URL = (
    "postgresql+psycopg2://"
    "kr:kr-labs-pw@127.0.0.1:5433/food_kr"
)

# SQLite alternative if Docker is unavailable.
SQLITE_URL = f"sqlite:///{HERE / 'food_kr.db'}"


# ============================================================
# 3. SOURCE TABLES
# ============================================================

TABLES = {
    "food": "food.csv",
    "branded_food": "branded_food.csv",
    "food_nutrient": "food_nutrient.csv",
    "nutrient": "nutrient.csv",
}

EXPECTED_ROWS = {
    "food": 20000,
    "branded_food": 20000,
    "food_nutrient": 261255,
    "nutrient": 477,
}


# ============================================================
# 4. READ AND PREPARE CSV DATA
# ============================================================

def load_frame(filename):
    """Read a USDA CSV and normalize missing values.

    Pandas recognizes standard missing-value markers such as:
        - Empty cells
        - None
        - NaN
        - NULL

    Missing values are converted to Python None so SQLAlchemy
    stores them as SQL NULL.

    Identifiers remain strings to preserve their exact values.
    """

    path = DATA_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=True,
        encoding="utf-8-sig"
    )

    # Normalize column names.
    df.columns = [
        col.strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    # Convert Pandas missing values into Python None.
    # SQLAlchemy will store them as SQL NULL.
    df = df.astype(object).where(
        pd.notna(df),
        None
    )

    return df


# ============================================================
# 5. LOAD TABLES INTO DATABASE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Load processed USDA food tables "
            "into PostgreSQL or SQLite."
        )
    )

    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Use SQLite instead of PostgreSQL"
    )

    args = parser.parse_args()

    # Select database.
    if args.sqlite:
        database_url = SQLITE_URL
        database_name = "SQLite"
    else:
        database_url = POSTGRES_URL
        database_name = "PostgreSQL"

    print("=" * 65)
    print("FOOD KNOWLEDGE REPRESENTATION")
    print("SESSION 05 - DATABASE LOADING")
    print("=" * 65)

    print(f"\nDatabase: {database_name}")
    print(f"Source directory: {DATA_DIR}")

    # Create the database connection.
    engine = create_engine(database_url)

    # Verify the database is reachable.
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    except Exception as exc:
        raise SystemExit(
            f"\nCould not connect to {database_name}.\n"
            f"Details: {exc}"
        ) from exc

    print("\nDatabase connection successful.")

    # --------------------------------------------------------
    # Load the four CSV tables
    # --------------------------------------------------------

    print("\nLoading USDA food tables...\n")

    for table_name, filename in TABLES.items():

        df = load_frame(filename)

        # Preserve every source column as SQL TEXT.
        # RDF datatypes are assigned by our R2RML mapping.
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False,
            dtype={
                column: Text()
                for column in df.columns
            },
            chunksize=1000
        )

        actual_rows = len(df)
        expected_rows = EXPECTED_ROWS[table_name]

        print(
            f"{table_name:<20} "
            f"{actual_rows:>8,} rows "
            f"(expected {expected_rows:,})"
        )

        if actual_rows != expected_rows:
            print(
                f"WARNING: Unexpected row count "
                f"for {table_name}!"
            )

    # --------------------------------------------------------
    # Verify row counts in the database
    # --------------------------------------------------------

    print("\nVerifying database row counts...\n")

    with engine.connect() as connection:

        for table_name in TABLES:

            query = text(
                f'SELECT COUNT(*) FROM "{table_name}"'
            )

            count = connection.execute(
                query
            ).scalar_one()

            print(
                f"{table_name:<20} "
                f"{count:>8,} rows"
            )

    # --------------------------------------------------------
    # Check missing ingredient declarations
    # --------------------------------------------------------

    print("\nChecking missing ingredient declarations...\n")

    with engine.connect() as connection:

        query = text("""
            SELECT COUNT(*)
            FROM branded_food
            WHERE ingredients IS NULL
               OR TRIM(ingredients) = ''
        """)

        missing_ingredients = connection.execute(
            query
        ).scalar_one()

        print(
            f"Products with missing ingredient declarations: "
            f"{missing_ingredients:,}"
        )

    print("\nDatabase loading completed successfully.")

    engine.dispose()


if __name__ == "__main__":
    main()
