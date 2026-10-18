
"""Score SPARQL answers by comparing returned value sets."""


def answer_set(rows):
    """Convert query results into a set of values."""
    if rows is None:
        return set()

    if isinstance(rows, bool):
        return {"true" if rows else "false"}

    return {
        value
        for row in rows
        for value in row.values()
    }


def set_precision(pred, gold):
    """Fraction of predicted values that are correct."""
    return len(pred & gold) / len(pred) if pred else 0.0


def set_recall(pred, gold):
    """Fraction of expected values successfully returned."""
    return len(pred & gold) / len(gold) if gold else 0.0


def set_f1(pred, gold):
    """Harmonic mean of precision and recall."""
    p = set_precision(pred, gold)
    r = set_recall(pred, gold)

    return 2 * p * r / (p + r) if p + r else 0.0
