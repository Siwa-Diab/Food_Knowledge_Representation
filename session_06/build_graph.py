
"""Session 06: Build a Food Knowledge Graph for machine learning.

Adapted from the professor's Brunel build_graph.py.

Run from the project root:

    python session_06/build_graph.py

Reads:
    session_05/output/food-mapped.nt
    or session_02/output/food_knowledge_graph.ttl

Writes:
    session_06/data/food-graph.pt

Prediction target:
    Does a branded food's ingredient declaration mention "sesame"?

IMPORTANT:
    Ingredient declarations are used only to create labels.
    They are not included in the model's input features.
    Missing declarations have label -1 (UNKNOWN).
"""

import re
import time
from pathlib import Path

import numpy as np
import torch
from rdflib import Graph, Namespace, RDF
from torch_geometric.data import HeteroData


# ------------------------------------------------------------
# 1. PATHS AND NAMESPACES
# ------------------------------------------------------------

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SOURCES = [
    ROOT / "session_05" / "output" / "food-mapped.nt",
    ROOT / "session_02" / "output" / "food_knowledge_graph.ttl",
]

OUT = HERE / "data" / "food-graph.pt"

FOOD = Namespace("https://example.org/food-kr/schema#")


def clean_text(value):
    """Normalize whitespace and handle missing values."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def get_node_id(table, value):
    """Return a stable integer ID for a node."""
    if value not in table:
        table[value] = len(table)
    return table[value]


def main():

    start = time.time()

    # --------------------------------------------------------
    # 2. LOAD THE RDF GRAPH
    # --------------------------------------------------------

    source = next(
        (path for path in SOURCES if path.exists()),
        None
    )

    if source is None:
        raise FileNotFoundError(
            "No RDF graph found. Run Session 02 or Session 05 first."
        )

    print(f"Reading RDF graph: {source.name}")

    graph = Graph()

    graph.parse(
        source,
        format="nt" if source.suffix == ".nt" else "turtle"
    )

    print(f"Loaded {len(graph):,} RDF triples.")

    # --------------------------------------------------------
    # 3. FIND BRANDED FOOD NODES
    # --------------------------------------------------------

    foods = sorted(
        set(graph.subjects(RDF.type, FOOD.BrandedFood)),
        key=str
    )

    food_ids = {
        food: index
        for index, food in enumerate(foods)
    }

    # --------------------------------------------------------
    # 4. CREATE LABELS
    # --------------------------------------------------------

    labels = []
    known = []

    for food in foods:

        declaration = graph.value(
            food,
            FOOD.ingredientDeclaration
        )

        ingredients = clean_text(declaration)

        if not ingredients:
            labels.append(-1)
            known.append(False)
        else:
            labels.append(
                1 if "sesame" in ingredients.lower() else 0
            )
            known.append(True)

    labels = np.asarray(labels, dtype=np.int64)
    known = np.asarray(known, dtype=bool)

    # --------------------------------------------------------
    # 5. CREATE NODE DICTIONARIES
    # --------------------------------------------------------

    brand_ids = {}
    category_ids = {}
    nutrient_ids = {}

    # --------------------------------------------------------
    # 6. CREATE TYPED EDGES
    # --------------------------------------------------------

    edges = {
        ("food", "owned_by", "brand"): [],
        ("food", "in_category", "category"): [],
        ("food", "has_nutrient", "nutrient"): [],
    }

    food_features = []
    food_brand_groups = []

    for food in foods:

        food_index = food_ids[food]

        brand = clean_text(
            graph.value(food, FOOD.brandOwner)
        )

        category = clean_text(
            graph.value(food, FOOD.foodCategory)
        )

        # Brand-owner edges
        if brand:

            brand_index = get_node_id(
                brand_ids,
                brand
            )

            edges[
                ("food", "owned_by", "brand")
            ].append(
                (food_index, brand_index)
            )

            food_brand_groups.append(brand_index)

        else:
            food_brand_groups.append(-1)

        # Category edges
        if category:

            category_index = get_node_id(
                category_ids,
                category
            )

            edges[
                ("food", "in_category", "category")
            ].append(
                (food_index, category_index)
            )

        # Nutrient edges and simple numerical features
        nutrient_count = 0
        total_amount = 0.0

        for measurement in graph.objects(
            food,
            FOOD.hasNutrientMeasurement
        ):

            nutrient = graph.value(
                measurement,
                FOOD.measuresNutrient
            )

            if nutrient is None:
                continue

            nutrient_index = get_node_id(
                nutrient_ids,
                nutrient
            )

            edges[
                ("food", "has_nutrient", "nutrient")
            ].append(
                (food_index, nutrient_index)
            )

            nutrient_count += 1

            amount = graph.value(
                measurement,
                FOOD.amount
            )

            if amount is not None:
                try:
                    total_amount += float(amount)
                except (TypeError, ValueError):
                    pass

        # IMPORTANT: no ingredient declaration or sesame flag
        # appears in the input features.
        food_features.append([
            np.log1p(nutrient_count),
            np.log1p(max(0.0, total_amount)),
            float(bool(brand)),
            float(bool(category)),
        ])

    # --------------------------------------------------------
    # 7. BUILD THE HETEROGENEOUS GRAPH
    # --------------------------------------------------------

    data = HeteroData()

    data["food"].x = torch.tensor(
        np.asarray(food_features),
        dtype=torch.float32
    )

    data["food"].y = torch.tensor(
        labels,
        dtype=torch.long
    )

    data["food"].known_mask = torch.tensor(
        known,
        dtype=torch.bool
    )

    # Constant node features avoid memorizing arbitrary IDs.
    for node_type, node_table in [
        ("brand", brand_ids),
        ("category", category_ids),
        ("nutrient", nutrient_ids),
    ]:

        data[node_type].x = torch.ones(
            (len(node_table), 1),
            dtype=torch.float32
        )

    # Forward edges
    for edge_type, pairs in edges.items():

        if pairs:
            edge_index = torch.tensor(
                pairs,
                dtype=torch.long
            ).T.contiguous()
        else:
            edge_index = torch.empty(
                (2, 0),
                dtype=torch.long
            )

        data[edge_type].edge_index = edge_index

    # Reverse edges for message passing
    for source_type, relation, target_type in list(edges):

        forward = data[
            source_type, relation, target_type
        ].edge_index

        data[
            target_type,
            "rev_" + relation,
            source_type
        ].edge_index = forward.flip(0).contiguous()

    # --------------------------------------------------------
    # 8. SAVE GRAPH AND METADATA
    # --------------------------------------------------------

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    torch.save(
        {
            "data": data,
            "food_iri": [str(food) for food in foods],
            "brand_names": list(brand_ids),
            "category_names": list(category_ids),
            "nutrient_iri": [
                str(nutrient) for nutrient in nutrient_ids
            ],
            "brand_group": torch.tensor(
                food_brand_groups,
                dtype=torch.long
            ),
            "source": source.name,
        },
        OUT
    )

    # --------------------------------------------------------
    # 9. DISPLAY RESULTS
    # --------------------------------------------------------

    known_count = int(known.sum())
    positive_count = int((labels == 1).sum())
    unknown_count = int((labels == -1).sum())

    print("\n" + "=" * 60)
    print("SESSION 06 - FOOD LEARNING GRAPH")
    print("=" * 60)

    print(f"RDF triples: {len(graph):,}")

    print(
        f"Nodes: food={len(foods):,}, "
        f"brand={len(brand_ids):,}, "
        f"category={len(category_ids):,}, "
        f"nutrient={len(nutrient_ids):,}"
    )

    for edge_type, pairs in edges.items():
        print(
            f"Edges {edge_type[1]}: {len(pairs):,}"
        )

    print(f"\nKnown labels: {known_count:,}")
    print(f"Sesame-positive labels: {positive_count:,}")
    print(f"Unknown labels: {unknown_count:,}")

    if known_count:
        print(
            f"Positive share: "
            f"{positive_count / known_count:.2%}"
        )

    print(
        "\nIngredient declarations are excluded "
        "from model input features."
    )

    print(f"\nSaved graph: {OUT}")
    print(f"Execution time: {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    main()
