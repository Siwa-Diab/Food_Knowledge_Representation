
"""Create a synthetic entity-resolution teaching dataset.

Food Knowledge Representation - Session 05

Adapted from the professor's Brunel/TMS entity-resolution exercise.

Run from the project root:

    python session_05/er/make_teaching_set.py

Outputs:
    reference-brands.csv
    external-brands.csv
    truth.csv

The external system is simulated, not an independent real dataset.
"""

import csv
import re
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

SOURCE = ROOT / "data" / "processed" / "branded_food.csv"

REFERENCE_FILE = HERE / "reference-brands.csv"
EXTERNAL_FILE = HERE / "external-brands.csv"
TRUTH_FILE = HERE / "truth.csv"

MATCH_COUNT = 46
UNMATCHED_COUNT = 6


def normalize_name(name):
    """Normalize whitespace for selecting reference names."""
    return re.sub(r"\s+", " ", str(name)).strip()


def change_name(name, rule):
    """Introduce controlled variations in a company name."""

    if rule == "same":
        return name

    if rule == "lower":
        return name.lower()

    if rule == "upper":
        return name.upper()

    if rule == "spaces":
        return f"  {name}  "

    if rule == "punctuation":
        return name.replace(",", "").replace(".", "")

    if rule == "suffix":
        return re.sub(
            r"\bIncorporated\b",
            "Inc",
            name,
            flags=re.IGNORECASE
        )

    if rule == "missing-letter":
        if len(name) > 5:
            return name[:3] + name[4:]
        return name

    if rule == "extra-spaces":
        return name.replace(" ", "  ")

    return name


RULES = [
    "same",
    "lower",
    "upper",
    "spaces",
    "punctuation",
    "suffix",
    "missing-letter",
    "extra-spaces"
]


def write_csv(path, fieldnames, rows):

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def main():

    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Missing source dataset: {SOURCE}"
        )

    HERE.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(
        SOURCE,
        dtype=str,
        low_memory=False
    )

    required = {
        "brand_owner",
        "branded_food_category"
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    # Keep records with a usable brand-owner name.
    data = data.dropna(subset=["brand_owner"]).copy()

    data["brand_owner"] = (
        data["brand_owner"]
        .map(normalize_name)
    )

    data = data[
        data["brand_owner"] != ""
    ]

    # Select one representative category for each owner.
    # Category is contextual evidence, not a company identifier.
    data["branded_food_category"] = (
        data["branded_food_category"]
        .fillna("")
        .map(normalize_name)
    )

    owners = (
        data.groupby("brand_owner", as_index=False)
        .agg(
            category=(
                "branded_food_category",
                lambda values: (
                    values[values != ""].mode().iloc[0]
                    if not values[values != ""].empty
                    else ""
                )
            )
        )
        .sort_values("brand_owner")
        .reset_index(drop=True)
    )

    if len(owners) < MATCH_COUNT:
        raise ValueError(
            "Not enough distinct brand owners."
        )

    selected = owners.head(MATCH_COUNT)

    reference_rows = []
    external_rows = []
    truth_rows = []

    for index, row in enumerate(
        selected.itertuples(index=False),
        start=1
    ):

        reference_id = f"USDA-BRAND-{index:03d}"
        external_id = f"EXT-BRAND-{index:03d}"

        rule = RULES[(index - 1) % len(RULES)]

        reference_rows.append({
            "reference_id": reference_id,
            "brand_owner": row.brand_owner,
            "category": row.category
        })

        external_rows.append({
            "external_id": external_id,
            "brand_owner": change_name(
                row.brand_owner,
                rule
            ),
            "category": row.category
        })

        truth_rows.append({
            "external_id": external_id,
            "reference_id": reference_id,
            "how_it_was_made": rule
        })

    # Deliberately unmatched synthetic company names.
    # These are fictional examples, not real USDA entities.
    for index in range(UNMATCHED_COUNT):

        external_id = (
            f"EXT-BRAND-"
            f"{MATCH_COUNT + index + 1:03d}"
        )

        external_rows.append({
            "external_id": external_id,
            "brand_owner": (
                f"KR Synthetic Unmatched Company "
                f"{index + 1:03d}"
            ),
            "category": (
                selected.iloc[
                    index % len(selected)
                ]["category"]
            )
        })

        truth_rows.append({
            "external_id": external_id,
            "reference_id": "",
            "how_it_was_made": "synthetic-unmatched"
        })

    write_csv(
        REFERENCE_FILE,
        ["reference_id", "brand_owner", "category"],
        reference_rows
    )

    write_csv(
        EXTERNAL_FILE,
        ["external_id", "brand_owner", "category"],
        external_rows
    )

    write_csv(
        TRUTH_FILE,
        [
            "external_id",
            "reference_id",
            "how_it_was_made"
        ],
        truth_rows
    )

    print("=" * 60)
    print("SESSION 05 - FOOD ENTITY RESOLUTION")
    print("=" * 60)

    print(f"Reference brands: {len(reference_rows)}")
    print(f"External records: {len(external_rows)}")
    print(f"Known matches: {MATCH_COUNT}")
    print(f"Unmatched records: {UNMATCHED_COUNT}")

    print("\nGenerated files:")
    print(REFERENCE_FILE)
    print(EXTERNAL_FILE)
    print(TRUTH_FILE)


if __name__ == "__main__":
    main()

"""Create a synthetic entity-resolution teaching dataset.

Food Knowledge Representation - Session 05

Adapted from the professor's Brunel/TMS entity-resolution exercise.

Run from the project root:

    python session_05/er/make_teaching_set.py

Outputs:
    reference-brands.csv
    external-brands.csv
    truth.csv

The external system is simulated, not an independent real dataset.
"""

import csv
import re
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

SOURCE = ROOT / "data" / "processed" / "branded_food.csv"

REFERENCE_FILE = HERE / "reference-brands.csv"
EXTERNAL_FILE = HERE / "external-brands.csv"
TRUTH_FILE = HERE / "truth.csv"

MATCH_COUNT = 46
UNMATCHED_COUNT = 6


def normalize_name(name):
    """Normalize whitespace for selecting reference names."""
    return re.sub(r"\s+", " ", str(name)).strip()


def change_name(name, rule):
    """Introduce controlled variations in a company name."""

    if rule == "same":
        return name

    if rule == "lower":
        return name.lower()

    if rule == "upper":
        return name.upper()

    if rule == "spaces":
        return f"  {name}  "

    if rule == "punctuation":
        return name.replace(",", "").replace(".", "")

    if rule == "suffix":
        return re.sub(
            r"\bIncorporated\b",
            "Inc",
            name,
            flags=re.IGNORECASE
        )

    if rule == "missing-letter":
        if len(name) > 5:
            return name[:3] + name[4:]
        return name

    if rule == "extra-spaces":
        return name.replace(" ", "  ")

    return name


RULES = [
    "same",
    "lower",
    "upper",
    "spaces",
    "punctuation",
    "suffix",
    "missing-letter",
    "extra-spaces"
]


def write_csv(path, fieldnames, rows):

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def main():

    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Missing source dataset: {SOURCE}"
        )

    HERE.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(
        SOURCE,
        dtype=str,
        low_memory=False
    )

    required = {
        "brand_owner",
        "branded_food_category"
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    # Keep records with a usable brand-owner name.
    data = data.dropna(subset=["brand_owner"]).copy()

    data["brand_owner"] = (
        data["brand_owner"]
        .map(normalize_name)
    )

    data = data[
        data["brand_owner"] != ""
    ]

    # Select one representative category for each owner.
    # Category is contextual evidence, not a company identifier.
    data["branded_food_category"] = (
        data["branded_food_category"]
        .fillna("")
        .map(normalize_name)
    )

    owners = (
        data.groupby("brand_owner", as_index=False)
        .agg(
            category=(
                "branded_food_category",
                lambda values: (
                    values[values != ""].mode().iloc[0]
                    if not values[values != ""].empty
                    else ""
                )
            )
        )
        .sort_values("brand_owner")
        .reset_index(drop=True)
    )

    if len(owners) < MATCH_COUNT:
        raise ValueError(
            "Not enough distinct brand owners."
        )

    selected = owners.head(MATCH_COUNT)

    reference_rows = []
    external_rows = []
    truth_rows = []

    for index, row in enumerate(
        selected.itertuples(index=False),
        start=1
    ):

        reference_id = f"USDA-BRAND-{index:03d}"
        external_id = f"EXT-BRAND-{index:03d}"

        rule = RULES[(index - 1) % len(RULES)]

        reference_rows.append({
            "reference_id": reference_id,
            "brand_owner": row.brand_owner,
            "category": row.category
        })

        external_rows.append({
            "external_id": external_id,
            "brand_owner": change_name(
                row.brand_owner,
                rule
            ),
            "category": row.category
        })

        truth_rows.append({
            "external_id": external_id,
            "reference_id": reference_id,
            "how_it_was_made": rule
        })

    # Deliberately unmatched synthetic company names.
    # These are fictional examples, not real USDA entities.
    for index in range(UNMATCHED_COUNT):

        external_id = (
            f"EXT-BRAND-"
            f"{MATCH_COUNT + index + 1:03d}"
        )

        external_rows.append({
            "external_id": external_id,
            "brand_owner": (
                f"KR Synthetic Unmatched Company "
                f"{index + 1:03d}"
            ),
            "category": (
                selected.iloc[
                    index % len(selected)
                ]["category"]
            )
        })

        truth_rows.append({
            "external_id": external_id,
            "reference_id": "",
            "how_it_was_made": "synthetic-unmatched"
        })

    write_csv(
        REFERENCE_FILE,
        ["reference_id", "brand_owner", "category"],
        reference_rows
    )

    write_csv(
        EXTERNAL_FILE,
        ["external_id", "brand_owner", "category"],
        external_rows
    )

    write_csv(
        TRUTH_FILE,
        [
            "external_id",
            "reference_id",
            "how_it_was_made"
        ],
        truth_rows
    )

    print("=" * 60)
    print("SESSION 05 - FOOD ENTITY RESOLUTION")
    print("=" * 60)

    print(f"Reference brands: {len(reference_rows)}")
    print(f"External records: {len(external_rows)}")
    print(f"Known matches: {MATCH_COUNT}")
    print(f"Unmatched records: {UNMATCHED_COUNT}")

    print("\nGenerated files:")
    print(REFERENCE_FILE)
    print(EXTERNAL_FILE)
    print(TRUTH_FILE)


if __name__ == "__main__":
    main()

