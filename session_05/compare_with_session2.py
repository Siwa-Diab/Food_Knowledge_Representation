
"""Compare Session 02 and Session 05 Food RDF graphs.

Session 02: RDF generated directly from CSV files using rdflib.
Session 05: RDF materialized from PostgreSQL using R2RML and Morph-KGC.

Run from the project root:

    python session_05/compare_with_session2.py
"""

from collections import Counter
from pathlib import Path

from rdflib import Graph, Literal


# ============================================================
# 1. FILE PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SESSION_02 = (
    ROOT
    / "session_02"
    / "output"
    / "food_knowledge_graph.ttl"
)

SESSION_05 = (
    ROOT
    / "session_05"
    / "output"
    / "food-mapped.nt"
)


# ============================================================
# 2. LOAD RDF GRAPHS
# ============================================================

def load_graph(path, rdf_format):
    """Load an RDF file and return its graph."""

    if not path.is_file():
        raise SystemExit(f"Missing RDF file: {path}")

    graph = Graph()

    print(f"\nLoading {path.name}...")

    graph.parse(
        str(path),
        format=rdf_format
    )

    print(f"  {len(graph):,} triples")

    return graph


# ============================================================
# 3. DISPLAY SAMPLE TRIPLES
# ============================================================

def show_examples(graph, label, limit=5):
    """Print a few example triples from a graph."""

    print(f"\n{label}:")

    if len(graph) == 0:
        print("  No differences found.")
        return

    for index, triple in enumerate(graph):
        if index >= limit:
            break

        subject, predicate, obj = triple

        print(f"\n  Example {index + 1}")
        print(f"    Subject   : {subject}")
        print(f"    Predicate : {predicate}")
        print(f"    Object    : {obj}")


# ============================================================
# 4. COUNT DIFFERENCES BY PREDICATE
# ============================================================

def show_predicate_differences(graph, label):
    """Group graph differences by RDF predicate."""

    print(f"\n{label}:")

    counts = Counter(
        str(predicate).split("#")[-1]
        for _, predicate, _ in graph
    )

    if not counts:
        print("  No differences found.")
        return

    for predicate, count in counts.most_common():
        print(f"  {predicate:<35} {count:,}")


# ============================================================
# 5. ANALYZE EXTRA LITERAL VALUES
# ============================================================

def show_extra_literals(graph, limit=15):
    """Display frequent literal values found only in Session 05."""

    print("\n=== EXTRA SESSION 05 LITERAL VALUES ===")

    counts = Counter(
        (
            str(predicate).split("#")[-1],
            str(obj)
        )
        for _, predicate, obj in graph
        if isinstance(obj, Literal)
    )

    if not counts:
        print("No extra literal values found.")
        return

    for (predicate, value), count in counts.most_common(limit):
        shortened_value = repr(value[:70])

        print(
            f"  {predicate:<25} "
            f"{shortened_value:<74} "
            f"{count:,}"
        )


# ============================================================
# 6. CHECK SUSPICIOUS MISSING-VALUE STRINGS
# ============================================================

def show_suspicious_values(graph):
    """Count literal values that may represent missing data."""

    print("\n=== SUSPICIOUS SESSION 05 VALUES ===")

    suspicious = {
        "none",
        "nan",
        "null",
        "n/a",
        "na"
    }

    counts = Counter(
        (
            str(predicate).split("#")[-1],
            str(obj)
        )
        for _, predicate, obj in graph
        if isinstance(obj, Literal)
        and str(obj).strip().lower() in suspicious
    )

    if not counts:
        print("No suspicious missing-value strings found.")
        return

    for (predicate, value), count in counts.most_common():
        print(
            f"  {predicate:<30} "
            f"value={value!r:<15} "
            f"count={count:,}"
        )


# ============================================================
# 7. MAIN COMPARISON
# ============================================================

def main():

    print("=" * 65)
    print("FOOD KNOWLEDGE REPRESENTATION")
    print("SESSION 02 vs SESSION 05 RDF COMPARISON")
    print("=" * 65)

    # Load Session 02 RDF
    graph02 = load_graph(
        SESSION_02,
        "turtle"
    )

    # Load Session 05 RDF
    graph05 = load_graph(
        SESSION_05,
        "nt"
    )

    # Compare triples
    only02 = graph02 - graph05
    only05 = graph05 - graph02

    # --------------------------------------------------------
    # Overall comparison
    # --------------------------------------------------------

    print("\n=== OVERALL COMPARISON ===")

    print(f"Session 02 triples      : {len(graph02):,}")
    print(f"Session 05 triples      : {len(graph05):,}")

    print(f"Only in Session 02      : {len(only02):,}")
    print(f"Only in Session 05      : {len(only05):,}")

    print(
        f"Common triples          : "
        f"{len(graph02) - len(only02):,}"
    )

    print(
        f"Difference in total     : "
        f"{len(graph05) - len(graph02):+,}"
    )

    # --------------------------------------------------------
    # Differences grouped by predicate
    # --------------------------------------------------------

    print("\n=== DIFFERENCES BY PREDICATE ===")

    show_predicate_differences(
        only02,
        "Only in Session 02"
    )

    show_predicate_differences(
        only05,
        "Only in Session 05"
    )

    # --------------------------------------------------------
    # Show example triples
    # --------------------------------------------------------

    show_examples(
        only02,
        "=== EXAMPLES ONLY IN SESSION 02 ==="
    )

    show_examples(
        only05,
        "=== EXAMPLES ONLY IN SESSION 05 ==="
    )

    # --------------------------------------------------------
    # Analyze additional literal values
    # --------------------------------------------------------

    show_extra_literals(only05)

    # --------------------------------------------------------
    # Look for suspicious missing-value representations
    # --------------------------------------------------------

    show_suspicious_values(only05)

    print("\n" + "=" * 65)
    print("COMPARISON COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
