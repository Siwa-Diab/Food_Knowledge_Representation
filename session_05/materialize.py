
"""Materialize the Food R2RML mapping using Morph-KGC.

Run from the project root:

    python session_05/materialize.py

Optional:
    python session_05/materialize.py --sqlite
    python session_05/materialize.py --out session_05/output/custom.nt
"""

import argparse
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

POSTGRES_URL = (
    "postgresql+psycopg2://kr:kr-labs-pw@127.0.0.1:5433/food_kr"
)

SQLITE_DB = HERE / "food_kr.db"
DEFAULT_MAPPING = HERE / "food-mapping.ttl"
DEFAULT_OUTPUT = HERE / "output" / "food-mapped.nt"


def config(mapping, db_url):
    """Build the Morph-KGC configuration."""

    return (
        "[CONFIGURATION]\n"
        "logging_level=WARNING\n\n"
        "[Food]\n"
        f"mappings={mapping}\n"
        f"db_url={db_url}\n"
    )


def run(mapping, sqlite, out):
    """Execute R2RML mappings and write the RDF graph."""

    try:
        import morph_kgc
    except ImportError as exc:
        raise SystemExit(
            "Morph-KGC is not installed. "
            "Install it in your active virtual environment."
        ) from exc

    if not mapping.is_file():
        raise SystemExit(
            f"Mapping file not found: {mapping}"
        )

    if sqlite:
        if not SQLITE_DB.is_file():
            raise SystemExit(
                "SQLite database not found. "
                "Run load_database.py --sqlite first."
            )

        db_url = f"sqlite:///{SQLITE_DB}"
    else:
        db_url = POSTGRES_URL

    out.parent.mkdir(parents=True, exist_ok=True)

    print("Starting Food RDF materialization...")
    print(f"Mapping: {mapping}")
    print(f"Database: {'SQLite' if sqlite else 'PostgreSQL'}")

    start = time.time()

    graph = morph_kgc.materialize(
        config(mapping, db_url)
    )

    elapsed = time.time() - start

    graph.serialize(
        destination=str(out),
        format="nt",
        encoding="utf-8"
    )

    print("\nMaterialization completed.")
    print(f"Triples: {len(graph):,}")
    print(f"Time: {elapsed:.1f} seconds")
    print(f"Output: {out}")

    return graph


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Use SQLite instead of PostgreSQL"
    )

    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT
    )

    args = parser.parse_args()

    run(
        mapping=args.mapping.resolve(),
        sqlite=args.sqlite,
        out=args.out.resolve()
    )


if __name__ == "__main__":
    main()
