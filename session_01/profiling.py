from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from data_profiling import ProfileReport

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "session_01" / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

TABLES = [
    "food.csv",
    "branded_food.csv",
    "food_nutrient.csv",
    "nutrient.csv"
]


# ============================================================
# 1. QUALITY SUMMARY 
# ============================================================

def quality_summary(df: pd.DataFrame) -> pd.DataFrame:

    return (
        pd.DataFrame({
            "dtype": df.dtypes.astype(str),
            "n_unique": df.nunique(dropna=True),
            "pct_missing": (
                df.isna().mean() * 100
            ).round(1)
        })
        .sort_values("pct_missing", ascending=False)
    )


# ============================================================
# 2. MISSINGNESS CHART
# ============================================================

def plot_missingness(summary, title, output_path):

    worst = summary[
        summary["pct_missing"] > 0
    ].head(15)

    if worst.empty:
        print(f"{title}: no missing values.")
        return

    fig, ax = plt.subplots(
        figsize=(8, max(3, 0.4 * len(worst)))
    )

    ax.barh(
        worst.index[::-1],
        worst["pct_missing"][::-1]
    )

    ax.set_xlabel("Percentage Missing (%)")
    ax.set_title(title)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


# ============================================================
# 3. PROFILE ALL USDA TABLES
# ============================================================

row_counts = {}

for filename in TABLES:

    name = filename.replace(".csv", "")
    path = DATA_DIR / filename

    print(f"\nLoading {filename}...", flush=True)

    df = pd.read_csv(
        path,
        low_memory=False,
        dtype={"gtin_upc": "string"}
        if filename == "branded_food.csv"
        else None
    )

    print(
        f"{name}: {df.shape[0]} rows, "
        f"{df.shape[1]} columns"
    )

    row_counts[name] = len(df)

    # Full-table quality summary
    summary = quality_summary(df)

    print("\nTop 15 columns by missingness:")
    print(summary.head(15).to_string())

    summary.to_csv(
        REPORT_DIR / f"{name}_quality_summary.csv"
    )

    # Missingness chart
    plot_missingness(
        summary,
        f"{name} - Missing Values",
        REPORT_DIR / f"{name}_missingness.png"
    )

    # Sample only for the expensive HTML profile
    profile_df = df

    if len(df) > 10000:
        profile_df = df.sample(
            n=10000,
            random_state=42
        )

    print(
        f"HTML profiling sample: "
        f"{len(profile_df)} rows"
    )

    report = ProfileReport(
    profile_df,
    title=f"USDA Food Products - {name}",
    minimal=True,
    pool_size=1
    )

    output = REPORT_DIR / f"{name}_profile.html"
    report.to_file(str(output))

    print(f"Saved: {output.name}", flush=True)


# ============================================================
# 4. COMPARE ROW COUNTS 
# ============================================================

fig, ax = plt.subplots(figsize=(9, 4))

ax.bar(
    list(row_counts.keys()),
    list(row_counts.values())
)

ax.set_ylabel("Number of Rows")
ax.set_title("USDA Food Tables - Row Counts")

ax.tick_params(axis="x", rotation=20)

fig.tight_layout()

fig.savefig(
    REPORT_DIR / "table_row_counts.png",
    dpi=150
)

plt.close(fig)

print("\nAll profiling reports generated!")
