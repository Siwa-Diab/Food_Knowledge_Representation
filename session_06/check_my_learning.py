
"""Session 06 - Part B: Check the Food Knowledge Representation exercises.

Run from the Food project root:

    python session_06/check_my_learning.py
"""

import importlib.util
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load(path):
    spec = importlib.util.spec_from_file_location("student", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_y1(f):
    """Products from the same brand must stay in one split."""

    brand = np.array([
        0, 0, 1, 1, 1, 2, 3, 3,
        4, 5, 5, 6, 7, 8, 9, 9
    ])

    train, test = f(brand, 0.3, 0)

    train = np.asarray(train)
    test = np.asarray(test)

    if (
        len(np.intersect1d(train, test))
        or len(train) + len(test) != len(brand)
    ):
        return "Every product must appear in exactly one split."

    both = np.intersect1d(
        np.unique(brand[train]),
        np.unique(brand[test])
    )

    if len(both):
        return "Some brand owners appear in both training and testing."

    n_test = len(np.unique(brand[test]))
    expected = round(0.3 * len(np.unique(brand)))

    if n_test != expected:
        return (
            f"Expected {expected} test brand owners, "
            f"but found {n_test}."
        )

    return None


def check_y2(f):
    """Recall@K: positives found / all positives."""

    y = np.array([1, 0, 1, 0, 0, 1, 0, 0, 0, 1])
    scores = np.array(
        [0.9, 0.8, 0.7, 0.6, 0.5,
         0.4, 0.3, 0.2, 0.1, 0.05]
    )

    got = f(y, scores, 3)

    if abs(got - 0.5) > 1e-9:
        return f"Expected Recall@3 = 0.5, got {got}."

    if abs(f(y, scores, 10) - 1.0) > 1e-9:
        return "Recall@10 should equal 1.0."

    return None


def check_y3(f):
    """Hits@K: fraction of ranks <= K."""

    ranks = [1, 2, 3, 10, 11, 50]

    if abs(f(ranks, 10) - 4 / 6) > 1e-9:
        return "Expected Hits@10 = 4/6."

    if abs(f(ranks, 1) - 1 / 6) > 1e-9:
        return "Expected Hits@1 = 1/6."

    return None


def main():
    mod = load(HERE / "my_learning.py")

    checks = [
        ("Y1", "split_by_brand", check_y1),
        ("Y2", "recall_at_k", check_y2),
        ("Y3", "hits_at_k", check_y3),
    ]

    correct = 0

    for exercise, name, checker in checks:
        try:
            problem = checker(getattr(mod, name))

        except Exception as e:
            problem = f"{type(e).__name__}: {e}"

        if problem is None:
            correct += 1
            print(f"{exercise} right.")
        else:
            print(f"{exercise} not yet: {problem}")

    print(f"\n{correct} of 3 right.")


if __name__ == "__main__":
    main()
