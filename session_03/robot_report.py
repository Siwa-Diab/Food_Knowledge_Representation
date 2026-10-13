
"""
Session 3 - Food Knowledge Representation
ROBOT Ontology Reasoning and Quality Report

Run from the project root:

    python session_03/robot_report.py

Use HermiT:

    python session_03/robot_report.py --reasoner HermiT

Specify another ontology:

    python session_03/robot_report.py --input session_03/workspace/domain-mistake.ttl

Outputs:
    session_03/reference-outputs/reasoned.ttl
    session_03/reference-outputs/report.tsv

Requires Java and ROBOT.
"""

import argparse
import csv
import shutil
import subprocess
import sys

from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent

DEFAULT_INPUT = HERE / "workspace" / "food-reasoning-clean.ttl"

OUTPUT_DIR = HERE / "reference-outputs"


# ============================================================
# 1. FIND ROBOT
# ============================================================

def find_robot(jar_path):

    if jar_path:
        jar = Path(jar_path).resolve()

        if not jar.exists():
            sys.exit(f"ROBOT JAR not found: {jar}")

        return ["java", "-Xmx3g", "-jar", str(jar)]

    robot = shutil.which("robot")

    if robot:
        return [robot]

    for candidate in [
        HERE / "robot.jar",
        HERE / "workspace" / "robot.jar"
    ]:
        if candidate.exists():
            return [
                "java",
                "-Xmx3g",
                "-jar",
                str(candidate.resolve())
            ]

    sys.exit(
        "ROBOT not found.\n"
        "Place robot.jar inside session_03/ or specify --jar.\n"
        "Download: https://github.com/ontodev/robot/releases"
    )


# ============================================================
# 2. EXECUTE ROBOT COMMAND
# ============================================================

def run(command):

    print("$ " + " ".join(command), flush=True)

    result = subprocess.run(
        command,
        check=False
    )

    return result.returncode


# ============================================================
# 3. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to the ontology file"
    )

    parser.add_argument(
        "--reasoner",
        default="ELK",
        choices=["ELK", "HermiT"],
        help="OWL reasoner"
    )

    parser.add_argument(
        "--jar",
        default=None,
        help="Path to robot.jar"
    )

    args = parser.parse_args()

    robot = find_robot(args.jar)

    source = Path(args.input).resolve()

    if not source.exists():
        sys.exit(f"Ontology not found: {source}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    reasoned = OUTPUT_DIR / "reasoned.ttl"
    report = OUTPUT_DIR / "report.tsv"
    explain = OUTPUT_DIR / "explain.md"

    print("\nFood Knowledge Representation")
    print("Session 3 - ROBOT Ontology Report")
    print("-" * 48)
    print(f"Ontology: {source.name}")
    print(f"Reasoner: {args.reasoner}")

    # --------------------------------------------------------
    # STEP 1: CHECK OFFLINE IMPORT CATALOG
    # --------------------------------------------------------

    catalog = source.parent / "catalog-v001.xml"

    if catalog.exists():
        base = robot + [
            "--catalog",
            str(catalog)
        ]
        print(f"Offline catalog: {catalog.name}")
    else:
        base = robot
        print("No offline import catalog found.")

    # --------------------------------------------------------
    # STEP 2: RUN ONTOLOGY REASONING
    # --------------------------------------------------------

    print(f"\nStep 1: Reason with {args.reasoner}")

    reason_command = base + [
        "reason",
        "--input",
        str(source),
        "--reasoner",
        args.reasoner,
        "--output",
        str(reasoned)
    ]

    code = run(reason_command)

    if code != 0:

        print("\nReasoning failed.")
        print("Attempting to explain unsatisfiable classes...")

        explain_command = base + [
            "explain",
            "--input",
            str(source),
            "--reasoner",
            args.reasoner,
            "--mode",
            "unsatisfiability",
            "--unsatisfiable",
            "all",
            "--explanation",
            str(explain)
        ]

        explain_code = run(explain_command)

        if explain_code == 0:
            print(f"\nExplanation saved to: {explain}")
        else:
            print(
                "Explanation unavailable. Check the ROBOT error "
                "above; failure does not always mean "
                "an unsatisfiable class."
            )

        sys.exit(1)

    print("\nReasoning completed successfully.")

    # --------------------------------------------------------
    # STEP 3: RUN ROBOT QUALITY REPORT
    # --------------------------------------------------------

    print("\nStep 2: Quality report on source ontology")

    report_command = base + [
        "report",
        "--input",
        str(source),
        "--output",
        str(report),
        "--fail-on",
        "none"
    ]

    report_code = run(report_command)

    if report_code != 0:
        sys.exit("ROBOT report command failed.")

    if not report.exists():
        sys.exit("ROBOT did not generate report.tsv.")

    # --------------------------------------------------------
    # STEP 4: READ REPORT
    # --------------------------------------------------------

    with report.open(
        encoding="utf-8"
    ) as file:
        rows = list(
            csv.DictReader(
                file,
                delimiter="\t"
            )
        )

    print(f"\nQuality findings: {len(rows)}")

    counts = Counter(
        (
            row.get("Level", ""),
            row.get("Rule Name", "")
        )
        for row in rows
    )

    for (level, rule), count in sorted(counts.items()):
        print(f"  {level:5}  {rule:30} {count}")

    # --------------------------------------------------------
    # STEP 5: DISPLAY GENERATED FILES
    # --------------------------------------------------------

    print("\nGenerated files:")
    print(f"  {reasoned}")
    print(f"  {report}")

    print(
        "\nReview report.tsv to distinguish ontology "
        "modeling errors from documentation warnings."
    )


if __name__ == "__main__":
    main()
