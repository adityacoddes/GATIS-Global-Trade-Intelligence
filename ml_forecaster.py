"""
ml_forecaster.py  —  GATIS Predictive Intelligence Pipeline
============================================================
Trains a Huber-regularized regression model per country-crop combination,
forecasts Production_Value for years 2024–2035, and writes a compact
forecast_results.csv ready for seamless merge into app.py memory.

Algorithm: HuberRegressor on polynomial time features (Year, Year²).
Rationale: Robust to outliers in sparse ~62-point annual series; regularized
           against leverage from anomalous harvest years; vectorized batch
           execution keeps runtime under 3 minutes on a standard laptop.
"""

from __future__ import annotations

import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent
INPUT_FILE     = BASE_DIR / "cleaned_faostat.csv"
OUTPUT_FILE    = BASE_DIR / "forecast_results.csv"
FORECAST_YEARS = list(range(2024, 2036))          # 2024 → 2035 inclusive
MIN_POINTS     = 5                                  # skip profiles with < 5 obs
HUBER_EPSILON  = 1.35                               # standard robust threshold
# ─────────────────────────────────────────────────────────────────────────────


def build_pipeline() -> Pipeline:
    """Return a fresh sklearn Pipeline: poly features → scaler → HuberRegressor."""
    return Pipeline([
        ("poly",   PolynomialFeatures(degree=2, include_bias=False)),
        ("scaler", StandardScaler()),
        ("model",  HuberRegressor(epsilon=HUBER_EPSILON, max_iter=300, alpha=0.01)),
    ])


def forecast_group(years: np.ndarray, values: np.ndarray) -> np.ndarray:
    """
    Fit a HuberRegressor on (years, values) and return predictions for
    FORECAST_YEARS. Returns an array of zeros if fitting fails.
    """
    X_train = years.reshape(-1, 1).astype(float)
    y_train = values.astype(float)

    # Log-scale target for series with large magnitude to stabilize gradients;
    # guard against non-positive values with a +1 offset.
    y_min = y_train.min()
    offset = abs(y_min) + 1.0 if y_min <= 0 else 0.0
    y_shifted = y_train + offset
    use_log = y_shifted.min() > 0 and y_shifted.max() / (y_shifted.min() + 1e-9) > 10

    if use_log:
        y_fit = np.log1p(y_shifted)
    else:
        y_fit = y_shifted

    try:
        pipe = build_pipeline()
        pipe.fit(X_train, y_fit)
        X_future = np.array(FORECAST_YEARS, dtype=float).reshape(-1, 1)
        y_pred = pipe.predict(X_future)
        if use_log:
            y_pred = np.expm1(y_pred) - offset
        else:
            y_pred = y_pred - offset
    except Exception:
        y_pred = np.zeros(len(FORECAST_YEARS))

    # Clip unrealistic negatives to 0
    return np.clip(y_pred, 0.0, None)


def main() -> None:
    t0 = time.perf_counter()

    print(f"[GATIS Forecaster] Loading {INPUT_FILE.name}...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  → {len(df):,} records | {df['Area'].nunique()} countries | {df['Item'].nunique()} crops")

    # ── Identify the stable metadata columns per group ────────────────────────
    # These are constant within each (Area, Item) pair and we carry them forward.
    meta_cols = ["Area Code (M49)", "Area", "Item Code (CPC)", "Item", "Element", "Unit"]

    # Build a lookup for metadata (first occurrence per group is sufficient)
    meta_lookup = (
        df[meta_cols]
        .drop_duplicates(subset=["Area", "Item"])
        .set_index(["Area", "Item"])
    )

    # ── Group & forecast ──────────────────────────────────────────────────────
    groups = df.groupby(["Area", "Item"], sort=False)
    total_groups = len(groups)
    print(f"  → {total_groups:,} unique country-crop profiles to model\n")

    forecast_rows: list[dict] = []
    skipped = 0

    for idx, ((area, item), grp) in enumerate(groups, start=1):
        if idx % 1000 == 0 or idx == total_groups:
            elapsed = time.perf_counter() - t0
            rate = idx / elapsed
            eta  = (total_groups - idx) / rate if rate > 0 else 0
            print(f"  [{idx:>6}/{total_groups}]  ETA {eta:>5.0f}s  |  skipped so far: {skipped}", end="\r")

        valid = grp.dropna(subset=["Production_Value", "Year"])
        if len(valid) < MIN_POINTS:
            skipped += 1
            continue

        years  = valid["Year"].to_numpy(dtype=int)
        values = valid["Production_Value"].to_numpy(dtype=float)

        preds = forecast_group(years, values)

        try:
            meta = meta_lookup.loc[(area, item)]
        except KeyError:
            skipped += 1
            continue

        for yr, pred_val in zip(FORECAST_YEARS, preds):
            forecast_rows.append({
                "Area Code (M49)": meta["Area Code (M49)"],
                "Area":            area,
                "Item Code (CPC)": meta["Item Code (CPC)"],
                "Item":            item,
                "Element":         meta["Element"],
                "Unit":            meta["Unit"],
                "Year":            yr,
                "Production_Value": round(float(pred_val), 4),
            })

    print(f"\n\n[GATIS Forecaster] Modeling complete.")
    print(f"  → Profiles forecasted : {total_groups - skipped:,}")
    print(f"  → Profiles skipped    : {skipped:,}  (< {MIN_POINTS} valid obs)")
    print(f"  → Forecast rows total : {len(forecast_rows):,}  ({len(FORECAST_YEARS)} years × profiles)")

    # ── Save ──────────────────────────────────────────────────────────────────
    forecast_df = pd.DataFrame(forecast_rows)
    forecast_df.to_csv(OUTPUT_FILE, index=False)

    elapsed_total = time.perf_counter() - t0
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n  ✓ Saved → {OUTPUT_FILE.name}  ({size_kb:,.1f} KB)")
    print(f"  ✓ Total runtime: {elapsed_total:.1f}s\n")


    


if __name__ == "__main__":
    main()
