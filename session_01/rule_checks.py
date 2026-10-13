"""Food Knowledge Representation — Session 1 rule checks.

Main question:
A food safety agency flags a specific ingredient for review. Which branded
products declare that ingredient, which food categories are affected, and how
many products have incomplete ingredient declarations that prevent a reliable
assessment?

Place this file in session_01/ and the four CSV files in data/processed/,
then run from session_01/:
    python rule_checks.py --ingredient sesame
    python rule_checks.py --ingredient peanut

The matches are text-based screening candidates, NOT verified allergen presence,
contamination, regulatory noncompliance, or a recall decision.
"""

from pathlib import Path
import argparse
import re
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"


def show(number, question, result, meaning):
    print(f"\nCheck {number}: {question}\n  Result : {result}\n  Meaning: {meaning}")


def load_csv(filename, required):
    path = DATA / filename
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Put the four CSV files in data/processed/.")
    df = pd.read_csv(path, low_memory=False, dtype={"fdc_id": "string", "gtin_upc": "string"})
    missing = set(required) - set(df.columns)
    if missing:
        raise SystemExit(f"{filename} is missing required columns: {sorted(missing)}")
    return df


def main():
    parser = argparse.ArgumentParser(description="Six food ingredient-risk rule checks")
    parser.add_argument("--ingredient", default="sesame", help="Ingredient text to screen (default: sesame)")
    parser.add_argument("--top", type=int, default=10, help="Number of top categories/brands to print")
    args = parser.parse_args()
    ingredient = args.ingredient.strip()
    if not ingredient:
        parser.error("--ingredient cannot be empty")

    food = load_csv("food.csv", ["fdc_id", "description"])
    branded = load_csv("branded_food.csv", ["fdc_id", "ingredients", "branded_food_category", "brand_owner", "gtin_upc"])
    food_nutrient = load_csv("food_nutrient.csv", ["fdc_id", "nutrient_id", "amount"])
    nutrient = load_csv("nutrient.csv", ["id", "name"])

    print(f"FOOD SAFETY INGREDIENT SCREEN — {ingredient.upper()}")
    print(f"Source: {len(branded):,} branded records; {len(food):,} food records; "
          f"{len(food_nutrient):,} nutrient measurements; {len(nutrient):,} nutrient definitions")

    declarations = branded["ingredients"].astype("string").str.strip()
    has_declaration = declarations.notna() & declarations.ne("")
    unknown = branded.loc[~has_declaration].copy()
    usable = branded.loc[has_declaration].copy()

    # 1 — Can records be screened?
    show(1, "How many branded foods have a nonempty ingredient declaration?",
         f"{len(usable):,} of {len(branded):,} usable; {len(unknown):,} missing/blank",
         "Only records with ingredient text can be screened by this method. "
         "A nonempty declaration is not guaranteed to be complete or accurate.")

    # 2 — Which products mention the flagged ingredient?
    # Match literal ingredient text at word boundaries; multiword phrases allowed.
    # This intentionally counts 'may contain sesame' as a mention, not confirmed inclusion.
    pattern = r"(?<!\w)" + re.escape(ingredient) + r"(?!\w)"
    matches = usable["ingredients"].astype("string").str.contains(
        pattern, case=False, regex=True, na=False
    )
    flagged = usable.loc[matches].copy()
    show(2, f"Which products mention '{ingredient}' in their ingredient declarations?",
         f"{len(flagged):,} of {len(usable):,} screenable branded records mention it",
         "These are candidates for manual review. Mentions may occur in "
         "'may contain' statements or other contexts; absence of a match does not prove safety.")
    if not flagged.empty:
        print("  Example products (up to 5):")
        descriptions = food[["fdc_id", "description"]].drop_duplicates("fdc_id")
        examples = flagged[["fdc_id", "brand_owner", "gtin_upc"]].merge(
            descriptions, on="fdc_id", how="left"
        ).head(5)
        print(examples.to_string(index=False))

    # 3 — What categories are represented among the candidates?
    categories = flagged["branded_food_category"].astype("string").str.strip().fillna("[missing category]")
    categories = categories.mask(categories.eq(""), "[missing category]")
    show(3, "Which branded food categories contain flagged records?",
         f"{categories.nunique():,} distinct category labels among {len(flagged):,} flagged records",
         "Counts describe categories represented in the screened records, "
         "not proof that every product in a category contains the ingredient.")
    if not categories.empty:
        print(categories.value_counts().head(args.top).to_string())

    # 4 — Which brand owners are associated with candidates?
    owners = flagged["brand_owner"].astype("string").str.strip().fillna("[missing brand owner]")
    owners = owners.mask(owners.eq(""), "[missing brand owner]")
    show(4, "Which brand owners are associated with the flagged products?",
         f"{owners.nunique():,} distinct owner labels among {len(flagged):,} flagged records",
         "Brand-owner names are labels; spelling variations may refer to the same organization.")
    if not owners.empty:
        print(owners.value_counts().head(args.top).to_string())

    # 5 — Can flagged records be traced by IDs/barcodes?
    known_ids = set(food["fdc_id"].dropna())
    broken_food_links = (~flagged["fdc_id"].isin(known_ids)).sum()
    barcodes = flagged["gtin_upc"].astype("string").str.strip()
    missing_barcodes = (barcodes.isna() | barcodes.eq("")).sum()
    repeated_barcode_rows = barcodes[barcodes.notna() & barcodes.ne("")].duplicated(keep=False).sum()
    show(5, "Can flagged products be linked to foods and identified by barcode?",
         f"{broken_food_links:,} flagged records lack a matching food.fdc_id; "
         f"{missing_barcodes:,} lack GTIN/UPC; "
         f"{repeated_barcode_rows:,} flagged rows share a barcode with another flagged row",
         "Missing or repeated identifiers complicate traceability; repeated barcodes "
         "are not automatically errors. These counts concern flagged records only.")

    # 6 — Which products remain unassessable by this text-screening method?
    missing_by_category = unknown["branded_food_category"].astype("string").str.strip().fillna("[missing category]")
    missing_by_category = missing_by_category.mask(missing_by_category.eq(""), "[missing category]")
    show(6, "How many branded products cannot be screened because ingredient text is missing?",
         f"{len(unknown):,} of {len(branded):,} branded records",
         "These are UNKNOWN, not negative matches. Prioritize them for data completion or manual review. "
         "Nonempty but inaccurate/incomplete declarations cannot be detected by this check.")
    if not missing_by_category.empty:
        print("  Categories with most missing declarations:")
        print(missing_by_category.value_counts().head(args.top).to_string())

    # Optional context: measurement availability for the flagged foods, using the fourth CSV.
    valid_nutrient_ids = set(nutrient["id"].astype("string"))
    linked_measurements = food_nutrient[
        food_nutrient["fdc_id"].isin(set(flagged["fdc_id"]))
    ]
    linked_nutrient_ids = linked_measurements["nutrient_id"].astype("string")
    print("\nSupporting context (not an additional rule check):")
    print(f"  Flagged foods with at least one nutrient record: "
          f"{linked_measurements['fdc_id'].nunique():,} of {flagged['fdc_id'].nunique():,} unique flagged fdc_ids")
    print(f"  Nutrient records with an unmatched nutrient definition: "
          f"{(~linked_nutrient_ids.isin(valid_nutrient_ids)).sum():,}")
    print("\nConclusion: screen matches for review, investigate uncertain records, "
          "and never equate missing declarations with confirmed absence.")


if __name__ == "__main__":
    main()
