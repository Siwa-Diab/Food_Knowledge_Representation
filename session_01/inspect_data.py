
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"

tables = [
    "food.csv",
    "branded_food.csv",
    "food_nutrient.csv",
    "nutrient.csv"
]

for table in tables:
    file_path = DATA_DIR / table

    print("\n" + "=" * 60)
    print("TABLE:", table)

    if not file_path.exists():
        print("ERROR: File not found:", file_path)
        continue

    df = pd.read_csv(file_path, nrows=1000, low_memory=False)

    print("\nSampled rows:", len(df))
    print("\nColumns:", df.columns.tolist())
    print("\nFirst 5 records:")
    print(df.head().to_string(index=False))
    print("\nMissing values:")
    print(df.isnull().sum())
