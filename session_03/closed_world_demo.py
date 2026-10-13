
"""
Session 3: Closed-world database vs open-world OWL.

Run from the project root:

    python session_03/closed_world_demo.py

This demonstration adapts the professor's shipment/carrier
example to branded food products and declared ingredients.

SQLite rejects an ingredient relationship if its product
does not exist in the branded_food table.

OWL can instead infer that the subject is a BrandedFood
from the domain of hasDeclaredIngredient.

Only the Python standard library is required.
"""

import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():

    lines = [
        f"SQLite {sqlite3.sqlite_version}, foreign keys on"
    ]

    # --------------------------------------------------
    # STEP 1: Create an in-memory SQLite database
    # --------------------------------------------------

    db = sqlite3.connect(":memory:")

    db.execute("PRAGMA foreign_keys = ON")

    # --------------------------------------------------
    # STEP 2: Create tables
    # --------------------------------------------------

    db.execute("""
        CREATE TABLE branded_food (
            id TEXT PRIMARY KEY
        )
    """)

    db.execute("""
        CREATE TABLE ingredient (
            id TEXT PRIMARY KEY
        )
    """)

    db.execute("""
        CREATE TABLE has_declared_ingredient (
            product TEXT REFERENCES branded_food(id),
            ingredient TEXT REFERENCES ingredient(id)
        )
    """)

    # --------------------------------------------------
    # STEP 3: Insert a known product and ingredient
    # --------------------------------------------------

    db.execute(
        "INSERT INTO branded_food VALUES ('product_001')"
    )

    db.execute(
        "INSERT INTO ingredient VALUES ('ingredient_sesame')"
    )

    db.execute("""
        INSERT INTO has_declared_ingredient
        VALUES ('product_001', 'ingredient_sesame')
    """)

    lines.append(
        "Known product product_001, ingredient_sesame: "
        "relationship accepted"
    )

    # --------------------------------------------------
    # STEP 4: Try a relationship with an unknown product
    # --------------------------------------------------

    stmt = (
        "INSERT INTO has_declared_ingredient "
        "VALUES ('product_002', 'ingredient_sesame')"
    )

    lines.append(stmt)

    try:
        db.execute(stmt)
        lines.append("accepted")

    except sqlite3.IntegrityError as error:
        lines.append(f"IntegrityError: {error}")

    # --------------------------------------------------
    # STEP 5: Explain the equivalent OWL behavior
    # --------------------------------------------------

    lines.append(
        "OWL, same fact: nothing is rejected solely because "
        "product_002 lacks an explicit BrandedFood type."
    )

    lines.append(
        "The domain of food:hasDeclaredIngredient "
        "allows a reasoner to infer that product_002 "
        "is a BrandedFood."
    )

    lines.append(
        "Important: the relationship is an asserted declaration "
        "in this demonstration, not proof of actual composition."
    )

    # --------------------------------------------------
    # STEP 6: Display and save results
    # --------------------------------------------------

    text = "\n".join(lines)

    print(text)

    output_dir = HERE / "reference-outputs"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "closed-world-demo.txt"

    output_file.write_text(
        text + "\n",
        encoding="utf-8"
    )

    print(f"\nSaved output to: {output_file}")

    db.close()


if __name__ == "__main__":
    main()
