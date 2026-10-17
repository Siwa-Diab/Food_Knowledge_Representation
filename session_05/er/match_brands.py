
"""Food brand-owner entity resolution.

Adapted from the professor's Session 05 Fellegi-Sunter exercise.

Run from the project root:

    python session_05/er/match_brands.py

Or specify thresholds:

    python session_05/er/match_brands.py --threshold 4 --threshold 8

Uses synthetic teaching data, not an independent external system.
"""

import argparse
import csv
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent

REFERENCE = HERE / "reference-brands.csv"
EXTERNAL = HERE / "external-brands.csv"
TRUTH = HERE / "truth.csv"

THRESHOLDS = (4, 8)

# Illustrative Fellegi-Sunter probabilities.
# These are manually specified, not estimated from training data.
WEIGHTS = {
    "name exact": (0.60, 0.001),
    "name close": (0.35, 0.02),
    "name different": (0.05, 0.979),
    "category same": (0.90, 0.40),
    "category different": (0.10, 0.60),
}


def clean_name(value):
    """Normalize capitalization, accents, punctuation and spacing."""

    value = str(value or "").strip().upper()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character for character in value
        if not unicodedata.combining(character)
    )

    value = re.sub(r"\bINCORPORATED\b", "INC", value)
    value = re.sub(r"\bCORPORATION\b", "CORP", value)
    value = re.sub(r"\bLIMITED\b", "LTD", value)

    value = re.sub(r"[^A-Z0-9]", "", value)

    return value


def clean_category(value):
    """Normalize category formatting without treating it as identity."""

    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().upper()
    )


def jaro_winkler(a, b):
    """Calculate Jaro-Winkler string similarity."""

    if a == b:
        return 1.0

    if not a or not b:
        return 0.0

    reach = max(0, max(len(a), len(b)) // 2 - 1)

    matched_a = [False] * len(a)
    matched_b = [False] * len(b)

    matches = 0

    for i, character in enumerate(a):

        start = max(0, i - reach)
        end = min(len(b), i + reach + 1)

        for j in range(start, end):

            if matched_b[j]:
                continue

            if character != b[j]:
                continue

            matched_a[i] = True
            matched_b[j] = True

            matches += 1
            break

    if matches == 0:
        return 0.0

    sequence_a = [
        char for char, matched in zip(a, matched_a)
        if matched
    ]

    sequence_b = [
        char for char, matched in zip(b, matched_b)
        if matched
    ]

    transpositions = sum(
        left != right
        for left, right in zip(sequence_a, sequence_b)
    ) / 2

    jaro = (
        matches / len(a)
        + matches / len(b)
        + (matches - transpositions) / matches
    ) / 3

    prefix = 0

    for left, right in zip(a[:4], b[:4]):
        if left != right:
            break
        prefix += 1

    return jaro + prefix * 0.1 * (1 - jaro)


def score(external, reference):
    """Calculate an illustrative Fellegi-Sunter log-likelihood score."""

    similarity = jaro_winkler(
        external["name"],
        reference["name"]
    )

    if external["name"] == reference["name"]:
        name_outcome = "name exact"
    elif similarity >= 0.93:
        name_outcome = "name close"
    else:
        name_outcome = "name different"

    outcomes = [name_outcome]

    if external["category"] and reference["category"]:
        if external["category"] == reference["category"]:
            outcomes.append("category same")
        else:
            outcomes.append("category different")

    total = sum(
        math.log2(
            WEIGHTS[outcome][0] / WEIGHTS[outcome][1]
        )
        for outcome in outcomes
    )

    return total, similarity, outcomes


def read_records(path, id_column):
    """Read and normalize brand-owner records."""

    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False
    )

    return [
        {
            "id": row[id_column],
            "raw_name": row["brand_owner"],
            "name": clean_name(row["brand_owner"]),
            "category": clean_category(row["category"])
        }
        for _, row in df.iterrows()
    ]


def main():

    parser = argparse.ArgumentParser(
        description="Food brand-owner entity resolution"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        action="append"
    )

    args = parser.parse_args()

    thresholds = args.threshold or THRESHOLDS

    reference = read_records(
        REFERENCE,
        "reference_id"
    )

    external = read_records(
        EXTERNAL,
        "external_id"
    )

    print("=" * 65)
    print("FOOD KNOWLEDGE REPRESENTATION")
    print("SESSION 05 - ENTITY RESOLUTION")
    print("=" * 65)

    # --------------------------------------------------------
    # 1. Blocking
    # --------------------------------------------------------

    # Blocking uses the first character of normalized brand name.
    # This reduces comparisons but may exclude true matches if
    # the first character is corrupted.

    pairs = [
        (ext, ref)
        for ext in external
        for ref in reference
        if (
            ext["name"]
            and ref["name"]
            and ext["name"][0] == ref["name"][0]
        )
    ]

    print(f"\nExternal records: {len(external)}")
    print(f"Reference records: {len(reference)}")

    print(
        "Possible pairs without blocking: "
        f"{len(external) * len(reference):,}"
    )

    print(
        f"Candidate pairs after blocking: {len(pairs):,}"
    )

    # --------------------------------------------------------
    # 2. Find best candidate for each external record
    # --------------------------------------------------------

    best = {}

    for ext, ref in pairs:

        match_score, similarity, reasons = score(
            ext,
            ref
        )

        external_id = ext["id"]

        if (
            external_id not in best
            or match_score > best[external_id]["score"]
        ):

            best[external_id] = {
                "score": match_score,
                "reference_id": ref["id"],
                "reference_name": ref["raw_name"],
                "similarity": similarity,
                "reasons": reasons
            }

    # --------------------------------------------------------
    # 3. Load ground truth only for evaluation
    # --------------------------------------------------------

    with open(
        TRUTH,
        newline="",
        encoding="utf-8"
    ) as file:

        truth = {
            row["external_id"]: row["reference_id"]
            for row in csv.DictReader(file)
        }

    raw_names = {
        record["id"]: record["raw_name"]
        for record in external
    }

    total_true_matches = sum(
        bool(reference_id)
        for reference_id in truth.values()
    )

    # --------------------------------------------------------
    # 4. Evaluate thresholds
    # --------------------------------------------------------

    for threshold in thresholds:

        predicted = {
            external_id: candidate["reference_id"]
            for external_id, candidate in best.items()
            if candidate["score"] >= threshold
        }

        true_positives = sum(
            1
            for external_id, reference_id in predicted.items()
            if truth[external_id] == reference_id
        )

        false_positives = [
            external_id
            for external_id, reference_id in predicted.items()
            if truth[external_id] != reference_id
        ]

        false_negatives = [
            external_id
            for external_id, reference_id in truth.items()
            if (
                reference_id
                and predicted.get(external_id) != reference_id
            )
        ]

        precision = (
            true_positives / len(predicted)
            if predicted else 0
        )

        recall = (
            true_positives / total_true_matches
            if total_true_matches else 0
        )

        print("\n" + "-" * 65)
        print(f"THRESHOLD: {threshold:g}")
        print("-" * 65)

        print(f"Predicted matches: {len(predicted)}")
        print(f"Correct matches: {true_positives}")
        print(f"False positives: {len(false_positives)}")
        print(f"False negatives: {len(false_negatives)}")
        print(f"Precision: {precision:.3f}")
        print(f"Recall: {recall:.3f}")

        for external_id in false_positives:

            candidate = best[external_id]

            print(
                f"\nWRONG MATCH: {external_id}"
                f"\n  External: {raw_names[external_id]}"
                f"\n  Predicted: {candidate['reference_name']}"
                f"\n  Truth: {truth[external_id] or 'NO MATCH'}"
            )

        for external_id in false_negatives:

            candidate = best.get(external_id)

            print(
                f"\nMISSED MATCH: {external_id}"
                f"\n  External: {raw_names[external_id]}"
                f"\n  Correct reference: {truth[external_id]}"
                f"\n  Best score: "
                f"{candidate['score']:.2f}"
                if candidate else
                f"\nMISSED MATCH: {external_id}"
                f"\n  External: {raw_names[external_id]}"
                f"\n  Correct reference: {truth[external_id]}"
                f"\n  No candidate survived blocking"
            )

    print("\nEntity resolution evaluation completed.")


if __name__ == "__main__":
    main()
