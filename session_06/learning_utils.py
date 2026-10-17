
"""Session 06: Learning utilities for the Food Knowledge Graph.

Adapted from the professor's learning_utils.py.

Provides:
    1. split_random()
    2. split_by_brand_owner()
    3. precision_at_k()
    4. recall_at_k()
    5. mrr()
    6. hits_at_k()

Unknown labels (-1) are excluded from classification splits.
"""

import numpy as np


# ------------------------------------------------------------
# 1. RANDOM SPLIT
# ------------------------------------------------------------

def split_random(n_foods, y, test_share=0.3, seed=0):
    """Stratified random split of food products.

    Keeps approximately the same proportion of sesame-positive
    and sesame-negative products in training and testing.

    Products with label -1 (UNKNOWN) are excluded.

    Returns:
        train_indices, test_indices
    """

    y = np.asarray(y)

    if len(y) != n_foods:
        raise ValueError("n_foods must equal the length of y.")

    rng = np.random.RandomState(seed)

    test = []

    for label in (0, 1):

        indices = np.flatnonzero(y == label)

        rng.shuffle(indices)

        n_test = int(round(test_share * len(indices)))

        test.extend(indices[:n_test])

    test = np.sort(np.asarray(test, dtype=int))

    known_indices = np.flatnonzero(y >= 0)

    train = np.setdiff1d(
        known_indices,
        test
    )

    return train, test


# ------------------------------------------------------------
# 2. SPLIT BY BRAND OWNER
# ------------------------------------------------------------

def split_by_brand_owner(
    brand_group,
    y,
    test_share=0.3,
    seed=0
):
    """Group-based split of food products.

    All products belonging to the same known brand owner
    must be entirely in training or testing.

    Products without a known brand owner (group -1)
    are excluded from this grouped evaluation.

    Products with unknown sesame labels (-1) are excluded.

    Returns:
        train_indices, test_indices
    """

    brand_group = np.asarray(brand_group)
    y = np.asarray(y)

    if len(brand_group) != len(y):
        raise ValueError(
            "brand_group and y must have the same length."
        )

    rng = np.random.RandomState(seed)

    valid = (y >= 0) & (brand_group >= 0)

    groups = np.unique(brand_group[valid])

    rng.shuffle(groups)

    n_test_groups = int(round(test_share * len(groups)))

    test_groups = groups[:n_test_groups]

    test = np.flatnonzero(
        valid & np.isin(brand_group, test_groups)
    )

    train = np.flatnonzero(
        valid & ~np.isin(brand_group, test_groups)
    )

    return train, test


# ------------------------------------------------------------
# 3. PRECISION AT K
# ------------------------------------------------------------

def precision_at_k(y_true, scores, k=100):
    """Precision@k.

    Of the k highest-ranked products, what fraction
    are actually sesame-positive?

    Example:
        If 20 of the top 100 products are positive,
        Precision@100 = 0.20.
    """

    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    if len(y_true) != len(scores):
        raise ValueError(
            "y_true and scores must have equal length."
        )

    if k <= 0:
        raise ValueError("k must be positive.")

    if len(y_true) == 0:
        return float("nan")

    if not np.isin(y_true, [0, 1]).all():
        raise ValueError(
            "Evaluate only products with known labels."
        )

    top = np.argsort(
        -scores,
        kind="stable"
    )[:k]

    return float(y_true[top].mean())


# ------------------------------------------------------------
# 4. RECALL AT K
# ------------------------------------------------------------

def recall_at_k(y_true, scores, k=100):
    """Recall@k.

    Of all sesame-positive products, what fraction
    appear among the k highest-ranked predictions?
    """

    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    if len(y_true) != len(scores):
        raise ValueError(
            "y_true and scores must have equal length."
        )

    if k <= 0:
        raise ValueError("k must be positive.")

    if not np.isin(y_true, [0, 1]).all():
        raise ValueError(
            "Evaluate only products with known labels."
        )

    positives = int(np.sum(y_true == 1))

    if positives == 0:
        return float("nan")

    top = np.argsort(
        -scores,
        kind="stable"
    )[:k]

    return float(np.sum(y_true[top] == 1) / positives)


# ------------------------------------------------------------
# 5. MEAN RECIPROCAL RANK
# ------------------------------------------------------------

def mrr(ranks):
    """Mean Reciprocal Rank.

    Rank 1 contributes 1.0.
    Rank 2 contributes 0.5.
    Rank 10 contributes 0.1.

    MRR = mean(1 / rank)
    """

    ranks = np.asarray(ranks, dtype=float)

    if len(ranks) == 0:
        return float("nan")

    if np.any(ranks < 1):
        raise ValueError(
            "Ranks must be positive integers."
        )

    return float(
        np.mean(1.0 / ranks)
    )


# ------------------------------------------------------------
# 6. HITS AT K
# ------------------------------------------------------------

def hits_at_k(ranks, k=10):
    """Hits@k for link prediction.

    Fraction of correct answers ranked in the top k.

    Example:
        ranks = [1, 3, 12, 2]
        Hits@10 = 3 / 4 = 0.75
    """

    ranks = np.asarray(ranks, dtype=float)

    if k <= 0:
        raise ValueError("k must be positive.")

    if len(ranks) == 0:
        return float("nan")

    if np.any(ranks < 1):
        raise ValueError(
            "Ranks must be positive integers."
        )

    return float(
        np.mean(ranks <= k)
    )
