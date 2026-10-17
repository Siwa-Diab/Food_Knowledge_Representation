
"""Session 06 - Part B: Food Knowledge Representation exercises."""

import numpy as np


# Y1: Split food products by brand owner
def split_by_brand(brand, test_share=0.3, seed=0):
    """
    Split products into train and test sets.

    Products belonging to the same brand owner must
    remain entirely in either train or test.
    """
    brand = np.asarray(brand)

    if brand.ndim != 1:
        raise ValueError("brand must be a one-dimensional array.")

    if not 0 < test_share < 1:
        raise ValueError("test_share must be between 0 and 1.")

    rng = np.random.RandomState(seed)

    unique_brands = np.unique(brand)
    shuffled_brands = rng.permutation(unique_brands)

    n_test = int(round(test_share * len(unique_brands)))
    test_brands = shuffled_brands[:n_test]

    test_mask = np.isin(brand, test_brands)

    train = np.where(~test_mask)[0]
    test = np.where(test_mask)[0]

    return train, test


# Y2: Recall at K
def recall_at_k(y_true, scores, k=100):
    """
    Recall@K = positives among top K / all positives.
    """
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    if len(y_true) != len(scores):
        raise ValueError("Labels and scores must have the same length.")

    total_positives = np.sum(y_true == 1)

    if total_positives == 0:
        return 0.0

    top_k = np.argsort(-scores, kind="stable")[:k]
    found_positives = np.sum(y_true[top_k] == 1)

    return float(found_positives / total_positives)


# Y3: Hits at K
def hits_at_k(ranks, k=10):
    """
    Hits@K = proportion of correct links ranked at K or better.
    """
    ranks = np.asarray(ranks)

    if len(ranks) == 0:
        return 0.0

    return float(np.mean(ranks <= k))
