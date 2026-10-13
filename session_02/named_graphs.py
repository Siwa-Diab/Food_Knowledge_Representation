"""Inspect the five source graphs in output/food_knowledge_graph.trig.

Run from session_02/: python named_graphs.py
Requires: python -m pip install pyoxigraph
"""
from pathlib import Path
import time

import pyoxigraph
from food_iri import VOCAB

HERE = Path(__file__).resolve().parent
TRIG = HERE / "output" / "food_knowledge_graph.trig"
REPORT = HERE / "output" / "named_graphs_report.txt"

PER_GRAPH = """
SELECT ?g (COUNT(*) AS ?n)
WHERE { GRAPH ?g { ?s ?p ?o } }
GROUP BY ?g
ORDER BY DESC(?n)
"""

MEASUREMENTS_LIVE_IN = f"""
PREFIX food: <{VOCAB}>
SELECT DISTINCT ?g
WHERE {{ GRAPH ?g {{ ?measurement a food:NutrientMeasurement . }} }}
"""


def main():
    if not TRIG.is_file():
        raise SystemExit(f"Missing {TRIG}. Run python convert_to_rdf.py first.")

    print(f"Loading {TRIG.name} into Oxigraph (may take a little time)...", flush=True)
    store = pyoxigraph.Store()
    store.load(path=str(TRIG), format=pyoxigraph.RdfFormat.TRIG)

    start = time.perf_counter()
    rows = [(solution["g"].value, int(solution["n"].value))
            for solution in store.query(PER_GRAPH)]
    elapsed_ms = (time.perf_counter() - start) * 1000

    lines = [f"[named graphs: triples per source table] {len(rows)} graphs in {elapsed_ms:.1f} ms"]
    lines.extend(f"  {name}: {count:,} triples" for name, count in rows)
    total = sum(count for _, count in rows)
    lines.append(f"Total across named graphs: {total:,} triples")

    locations = [solution["g"].value for solution in store.query(MEASUREMENTS_LIVE_IN)]
    lines.append("NutrientMeasurement instances live in: " + (", ".join(locations) or "[none found]"))

    report = "\n".join(lines) + "\n"
    print(report)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"Report saved to: {REPORT}")


if __name__ == "__main__":
    main()
