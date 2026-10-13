
"""Session 2: RDFS inference versus validation.

Uses the Food Knowledge Representation RDF graph.

Run:
    python -m pip install owlrl
    python rdfs_entailment_demo.py
"""

import time
from pathlib import Path

import owlrl
from rdflib import Graph, Namespace, RDF, RDFS, URIRef

HERE = Path(__file__).resolve().parent
TTL_PATH = HERE / "output" / "food_knowledge_graph.ttl"

FOOD = Namespace("https://example.org/food-kr/schema#")
DATA = "https://example.org/food-kr/id/"

print("Reading food knowledge graph...")
full = Graph()
full.parse(TTL_PATH, format="turtle")

# Keep only schema declarations and rdf:type triples.
# This avoids reasoning over all 1.2 million triples.
g = Graph()

for s, p, o in full:
    if p == RDF.type or str(p).startswith(str(RDFS)):
        g.add((s, p, o))

# Ensure our subclass relationship is available.
g.add((FOOD.BrandedFood, RDFS.subClassOf, FOOD.Food))

# Select an existing branded food.
branded_foods = list(g.subjects(RDF.type, FOOD.BrandedFood))

if not branded_foods:
    raise RuntimeError(
        "No BrandedFood instances found. Check the RDF converter."
    )

sample_food = branded_foods[0]

print("\n=== Experiment 1: Subclass inference ===")
print("Sample branded food:", sample_food)
print("Explicitly typed as BrandedFood:",
      (sample_food, RDF.type, FOOD.BrandedFood) in g)

# Remove any explicit Food type for the sample so the
# experiment can demonstrate that RDFS derives it.
g.remove((sample_food, RDF.type, FOOD.Food))

print("Typed as Food before reasoning:",
      (sample_food, RDF.type, FOOD.Food) in g)

# Add a deliberately careless triple.
#
# A nutrient is incorrectly used as the subject of
# hasNutrientMeasurement, which normally links a Food
# to a NutrientMeasurement.
#
# If the property's domain is Food, RDFS infers that
# the nutrient is also a Food.
print("\n=== Experiment 2: RDFS is not validation ===")

g.add((FOOD.hasNutrientMeasurement, RDFS.domain, FOOD.Food))

mistake_subject = URIRef(DATA + "nutrient/usda/1003")
mistake_object = URIRef(DATA + "measurement/usda/demo")

g.add((
    mistake_subject,
    FOOD.hasNutrientMeasurement,
    mistake_object,
))

print("Nutrient typed as Food before reasoning:",
      (mistake_subject, RDF.type, FOOD.Food) in g)

print("\nRunning RDFS reasoning...")
start = time.perf_counter()

owlrl.DeductiveClosure(
    owlrl.RDFS_Semantics
).expand(g)

seconds = time.perf_counter() - start

print(f"Reasoning completed in {seconds:.2f} seconds.")

print("\n=== Results ===")
print("BrandedFood inferred to be Food:",
      (sample_food, RDF.type, FOOD.Food) in g)

print("Nutrient incorrectly inferred to be Food:",
      (mistake_subject, RDF.type, FOOD.Food) in g)

print("\nConclusion:")
print("RDFS adds facts implied by the schema.")
print("It does not reject a semantically incorrect relationship.")
print("Use validation mechanisms such as SHACL to detect violations.")
