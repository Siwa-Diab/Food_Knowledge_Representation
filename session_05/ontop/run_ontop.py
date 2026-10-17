
"""Run SPARQL queries through Ontop virtualization.

Food Knowledge Representation - Session 05

Usage from the project root:

    python session_05/ontop/run_ontop.py

    python session_05/ontop/run_ontop.py --query session_05/ontop/q4-sesame-product-details.sparql
"""

import argparse
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

HERE = Path(__file__).resolve().parent
SESSION = HERE.parent
ROOT = SESSION.parent

CLI = HERE / "ontop-cli" / (
    "ontop.bat" if platform.system() == "Windows" else "ontop"
)

MAPPING = SESSION / "food-mapping.ttl"
PROPERTIES = HERE / "food.properties"
DEFAULT_QUERY = HERE / "q1-sesame-products.sparql"
LOG = HERE / "last-run.log"


def relative(path):
    """Return a path relative to the project root."""
    return os.path.relpath(
        Path(path).resolve(),
        ROOT
    ).replace("\\", "/")


def main():

    parser = argparse.ArgumentParser(
        description="Execute a Food SPARQL query using Ontop."
    )

    parser.add_argument(
        "--query",
        type=Path,
        default=DEFAULT_QUERY,
        help="Path to the SPARQL query file"
    )

    args = parser.parse_args()
    query = args.query.resolve()

    # --------------------------------------------------------
    # Verify required files
    # --------------------------------------------------------

    for path in [CLI, MAPPING, PROPERTIES, query]:
        if not path.is_file():
            sys.exit(f"Required file not found: {path}")

    # --------------------------------------------------------
    # Create temporary output file
    # --------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        prefix="food-ontop-",
        suffix=".csv",
        delete=False
    ) as output:
        output_path = Path(output.name)

    command = [
        str(CLI),
        "query",
        "-m", relative(MAPPING),
        "-p", relative(PROPERTIES),
        "-q", relative(query),
        "-o", str(output_path)
    ]

    environment = dict(
        os.environ,
        ONTOP_LOG_LEVEL="DEBUG"
    )

    print("=" * 65)
    print("FOOD KNOWLEDGE REPRESENTATION")
    print("SESSION 05 - ONTOP VIRTUALIZATION")
    print("=" * 65)

    print("\nStarting Ontop virtualization...")
    print(f"Query: {query.name}")
    print("Database: PostgreSQL (food_kr)")
    print(f"Mapping: {relative(MAPPING)}")
    print(f"Properties: {relative(PROPERTIES)}")

    try:

        # ----------------------------------------------------
        # Execute Ontop
        # ----------------------------------------------------

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            env=environment,
            cwd=ROOT
        )

        log_text = result.stdout + "\n" + result.stderr

        LOG.write_text(
            log_text,
            encoding="utf-8"
        )

        # ----------------------------------------------------
        # Detect Ontop errors
        # ----------------------------------------------------

        error_patterns = [
            r"Exception in thread",
            r"MalformedQueryException",
            r"InvalidOntopConfigurationException",
            r"(?m)^Caused by:",
            r"(?m)^java\.\w+.*Exception:",
            r"(?m)^it\.unibz\..*Exception:"
        ]

        has_exception = any(
            re.search(pattern, log_text)
            for pattern in error_patterns
        )

        if result.returncode != 0 or has_exception:

            print("\nOntop execution failed.")
            print(f"Exit code: {result.returncode}")

            print("\nLast 25 log lines:\n")

            for line in log_text.splitlines()[-25:]:
                print(line)

            sys.exit(
                f"\nFull error log: {LOG}"
            )

        # ----------------------------------------------------
        # Read query results
        # ----------------------------------------------------

        if not output_path.is_file():
            sys.exit(
                f"Ontop did not create an output file. See {LOG}"
            )

        answers = output_path.read_text(
            encoding="utf-8-sig"
        ).splitlines()

        print("\n=== SPARQL QUERY RESULTS ===\n")

        if answers:
            for line in answers:
                print(line)
        else:
            print("The query returned no results.")

        print("\nOntop virtualization completed successfully.")
        print(f"Execution log: {LOG}")

    finally:

        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
