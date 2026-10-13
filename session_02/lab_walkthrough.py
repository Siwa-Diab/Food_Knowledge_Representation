
"""Session 2 walkthrough: Food Knowledge Representation.

Summarizes existing pipeline outputs and plots query timings.

Run:
    python lab_walkthrough.py

Or run individual # %% cells in VS Code.
"""

# %% [markdown]
# # Session 2: Food Knowledge Representation
#
# CSV data -> RDF -> Fuseki -> SPARQL -> Neo4j/Cypher

# %%
from pathlib import Path
import re

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"

# %% [markdown]
# ## Stage 1: RDF conversion results

# %%
ttl = OUTPUT / "food_knowledge_graph.ttl"
trig = OUTPUT / "food_knowledge_graph.trig"

print("=== Stage 1: RDF files ===")
print("Turtle exists:", ttl.exists())
print("TriG exists:", trig.exists())

for path in (ttl, trig):
    if path.exists():
        print(f"{path.name}: {path.stat().st_size / 1024**2:.2f} MB")

# %% [markdown]
# ## Stage 2: Named graph provenance

# %%
print("\n=== Stage 2: Named graphs ===")
report = OUTPUT / "named_graphs_report.txt"

if report.exists():
    print(report.read_text(encoding="utf-8"))
else:
    print("Run python named_graphs.py first.")

# %% [markdown]
# ## Stage 3: SPARQL query timings

# %%
print("\n=== Stage 3: SPARQL performance ===")

def read_timings(filename, store):
    path = OUTPUT / filename

    if not path.exists():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(
            r"^\[(Q\d+)[^\]]*\]\s+\d+\s+rows\s+in\s+([\d.]+)\s+ms",
            line,
        )
        if match:
            rows.append({
                "question": match.group(1),
                "store": store,
                "milliseconds": float(match.group(2)),
            })
    return rows


timings = (
    read_timings("query-timings-fuseki.txt", "Fuseki")
    + read_timings("query-timings-oxigraph.txt", "Oxigraph")
)

if timings:
    df = pd.DataFrame(timings)
    print(df.to_string(index=False))

    pivot = df.pivot(
        index="question",
        columns="store",
        values="milliseconds",
    )

    ax = pivot.plot.bar(
        figsize=(10, 5),
        title="SPARQL query timings: Fuseki vs Oxigraph",
    )
    ax.set_ylabel("Execution time (ms)")
    ax.set_xlabel("Question")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()
else:
    print("No SPARQL timing reports found.")

# %% [markdown]
# ## Stage 4: Neo4j comparison

# %%
print("\n=== Stage 4: Neo4j ===")
neo4j_report = OUTPUT / "neo4j-comparison.txt"

if neo4j_report.exists():
    lines = neo4j_report.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if line.startswith("[Q"):
            print(line)
else:
    print("Run python neo4j_comparison.py first.")

print("\nSession 2 walkthrough completed.")
