
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

OUT.mkdir(parents=True, exist_ok=True)

SAMPLE_SIZE = 20000

# Step 1: Select branded products.
# Read only the columns needed to select IDs.
branded_ids = pd.read_csv(
    RAW / "branded_food.csv",
    usecols=["fdc_id"]
)

selected_ids = (
    branded_ids["fdc_id"]
    .dropna()
    .drop_duplicates()
    .sample(
        n=min(SAMPLE_SIZE, branded_ids["fdc_id"].nunique()),
        random_state=42
    )
)

ids = set(selected_ids.tolist())
print("Selected products:", len(ids))

# Step 2: Extract selected rows without
# loading the entire large files into memory.
def filter_table(filename, id_column="fdc_id"):
    source = RAW / filename
    destination = OUT / filename

    first_chunk = True
    total = 0

    for chunk in pd.read_csv(
        source,
        chunksize=100000,
        low_memory=False
    ):
        filtered = chunk[chunk[id_column].isin(ids)]

        filtered.to_csv(
            destination,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False
        )

        first_chunk = False
        total += len(filtered)

    print(f"{filename}: {total} rows")

filter_table("food.csv")
filter_table("branded_food.csv")
filter_table("food_nutrient.csv")

# Step 3: Keep the nutrient dictionary.
nutrients = pd.read_csv(RAW / "nutrient.csv")
nutrients.to_csv(OUT / "nutrient.csv", index=False)

print("nutrient.csv:", len(nutrients), "rows")
print("\nSubset creation completed!")
