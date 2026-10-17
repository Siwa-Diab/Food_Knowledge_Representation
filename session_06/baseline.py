
"""Session 06: Logistic Regression baseline for the Food Knowledge Graph.

Adapted from the professor's baseline.py.

Experiments:
  1. Random split with intentional label leakage
  2. Random split without leakage
  3. Brand-owner split over five seeds

Run from the project root:

    python session_06/baseline.py

Prediction target:
    Does the ingredient declaration mention sesame?

Unknown ingredient declarations (label -1) are excluded.
"""

from pathlib import Path

import numpy as np
import torch

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    roc_auc_score,
)
from sklearn.preprocessing import OneHotEncoder

from learning_utils import (
    precision_at_k,
    split_by_brand_owner,
    split_random,
)


HERE = Path(__file__).resolve().parent
SEEDS = range(5)


# ------------------------------------------------------------
# 1. LOAD THE GRAPH
# ------------------------------------------------------------

def load():

    bundle = torch.load(
        HERE / "data" / "food-graph.pt",
        weights_only=False
    )

    data = bundle["data"]

    x = data["food"].x.numpy()
    y = data["food"].y.numpy()

    brand_group = bundle["brand_group"].numpy()

    # A food's category ID is obtained from its category edge.
    category = np.full(len(y), -1, dtype=int)

    category_edges = data[
        "food", "in_category", "category"
    ].edge_index.numpy()

    category[
        category_edges[0]
    ] = category_edges[1]

    # The baseline uses the food's numerical features,
    # plus categorical identifiers for brand and category.
    ids = np.column_stack([
        brand_group,
        category
    ])

    return x, ids, y, brand_group


# ------------------------------------------------------------
# 2. TRAIN AND EVALUATE LOGISTIC REGRESSION
# ------------------------------------------------------------

def fit_score(x, ids, y, train, test, extra=None):

    # Some group splits may contain no positive training
    # examples, so skip them rather than crashing.
    if len(train) == 0 or len(test) == 0:
        return None

    if len(np.unique(y[train])) < 2:
        return None

    encoder = OneHotEncoder(
        handle_unknown="ignore"
    ).fit(ids[train])

    def rows(indices):

        categorical = encoder.transform(
            ids[indices]
        )

        # Keep categorical columns sparse to reduce memory.
        from scipy.sparse import csr_matrix, hstack

        parts = [
            categorical,
            csr_matrix(x[indices])
        ]

        if extra is not None:
            parts.append(
                csr_matrix(
                    extra[indices].reshape(-1, 1)
                )
            )

        return hstack(parts, format="csr")

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="liblinear",
        random_state=0
    )

    model.fit(
        rows(train),
        y[train]
    )

    probabilities = model.predict_proba(
        rows(test)
    )[:, 1]

    actual = y[test]

    positive_count = int(actual.sum())

    return {
        "positive in test": positive_count,
        "test size": len(test),
        "PR-AUC": (
            average_precision_score(
                actual,
                probabilities
            )
            if positive_count else float("nan")
        ),
        "ROC-AUC": (
            roc_auc_score(
                actual,
                probabilities
            )
            if 0 < positive_count < len(test)
            else float("nan")
        ),
        "precision@100": precision_at_k(
            actual,
            probabilities,
            k=100
        ),
        "accuracy": accuracy_score(
            actual,
            probabilities > 0.5
        ),
    }


# ------------------------------------------------------------
# 3. FORMAT RESULTS
# ------------------------------------------------------------

def line(name, result):

    if result is None:
        return (
            f"{name:<38} "
            "Skipped: insufficient training/test data"
        )

    if result["positive in test"] == 0:
        return (
            f"{name:<38} "
            "No sesame-positive products in test set"
        )

    return (
        f"{name:<38} "
        f"positive in test {result['positive in test']:>4}  "
        f"PR-AUC {result['PR-AUC']:.3f}  "
        f"ROC-AUC {result['ROC-AUC']:.3f}  "
        f"precision@100 {result['precision@100']:.3f}  "
        f"accuracy {result['accuracy']:.3f}"
    )


# ------------------------------------------------------------
# 4. MAIN EXPERIMENT
# ------------------------------------------------------------

def main():

    x, ids, y, brand_group = load()

    known = y >= 0
    known_labels = y[known]

    positive_count = int(
        (known_labels == 1).sum()
    )

    total_known = len(known_labels)

    positive_share = positive_count / total_known

    print("=" * 75)
    print("SESSION 06 - FOOD LOGISTIC REGRESSION BASELINE")
    print("=" * 75)

    print(
        f"\n{total_known:,} foods with known ingredient declarations"
    )

    print(
        f"Sesame-positive: {positive_count:,} "
        f"({positive_share:.2%})"
    )

    print(
        f"Guessing PR-AUC: {positive_share:.3f}"
    )

    print(
        f'Always predicting "no sesame" accuracy: '
        f"{1 - positive_share:.3f}\n"
    )

    # --------------------------------------------------------
    # Experiment 1: Intentional leakage
    # --------------------------------------------------------

    train, test = split_random(
        len(y),
        y,
        seed=0
    )

    print(
        line(
            "1 - random split, label leaked",
            fit_score(
                x,
                ids,
                y,
                train,
                test,
                extra=y
            )
        )
    )

    # --------------------------------------------------------
    # Experiment 2: Random split
    # --------------------------------------------------------

    print(
        line(
            "2 - random split, no label feature",
            fit_score(
                x,
                ids,
                y,
                train,
                test
            )
        )
    )

    # --------------------------------------------------------
    # Experiment 3: Brand-owner splits
    # --------------------------------------------------------

    for seed in SEEDS:

        train, test = split_by_brand_owner(
            brand_group,
            y,
            seed=seed
        )

        result = fit_score(
            x,
            ids,
            y,
            train,
            test
        )

        print(
            line(
                f"3 - brand-owner split, seed {seed}",
                result
            )
        )

    # --------------------------------------------------------
    # Final observations
    # --------------------------------------------------------

    known_brand = (y >= 0) & (brand_group >= 0)

    positive_brands = np.unique(
        brand_group[
            known_brand & (y == 1)
        ]
    )

    all_brands = np.unique(
        brand_group[known_brand]
    )

    print(
        f"\n{len(positive_brands):,} of "
        f"{len(all_brands):,} brand owners have at least "
        "one sesame-positive product."
    )

    print(
        "\nImportant: The first experiment intentionally "
        "includes the answer as a feature."
    )

    print(
        "Only experiments 2 and 3 are candidates "
        "for meaningful evaluation."
    )


if __name__ == "__main__":
    main()
