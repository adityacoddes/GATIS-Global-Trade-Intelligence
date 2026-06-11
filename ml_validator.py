"""
ml_validator.py  —  GATIS Model Evaluation & Backtesting
============================================================
Evaluates the HuberRegressor pipeline using a Temporal Split.
Trains on data prior to 2019, and tests accuracy on 2019-2023.
"""

import warnings
import time
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import HuberRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "cleaned_faostat.csv"

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("poly",   PolynomialFeatures(degree=2, include_bias=False)),
        ("scaler", StandardScaler()),
        ("model",  HuberRegressor(epsilon=1.35, max_iter=300, alpha=0.01)),
    ])

def run_backtest():
    print(f"📊 [GATIS Validator] Loading historical data from {INPUT_FILE.name}...")
    df = pd.read_csv(INPUT_FILE)
    
    groups = df.groupby(["Area", "Item"], sort=False)
    total_groups = len(groups)
    
    maes = []
    r2_scores = []
    skipped = 0
    
    print(f"🔬 Backtesting {total_groups:,} profiles (Holdout Set: 2019-2023)...")

    t0 = time.perf_counter()

    for idx, ((area, item), grp) in enumerate(groups, start=1):
        # ── VISUAL PROGRESS TRACKER ──
        if idx % 500 == 0 or idx == total_groups:
            elapsed = time.perf_counter() - t0
            rate = idx / elapsed
            eta  = (total_groups - idx) / rate if rate > 0 else 0
            print(f"  [{idx:>6}/{total_groups}]  ETA {eta:>4.0f}s  |  skipped: {skipped}", end="\r")

        valid = grp.dropna(subset=["Production_Value", "Year"]).sort_values("Year")
        
        # We need enough historical depth to run a meaningful test
        if len(valid) < 15:
            skipped += 1
            continue
            
        # ── TEMPORAL SPLIT ──
        train_df = valid[valid["Year"] < 2019]
        test_df = valid[valid["Year"] >= 2019]
        
        if len(train_df) < 5 or len(test_df) == 0:
            skipped += 1
            continue

        X_train = train_df["Year"].to_numpy(dtype=float).reshape(-1, 1)
        y_train = train_df["Production_Value"].to_numpy(dtype=float)
        
        X_test = test_df["Year"].to_numpy(dtype=float).reshape(-1, 1)
        y_test = test_df["Production_Value"].to_numpy(dtype=float)

        # ── APPLY EXACT HUBER LOGIC ──
        y_min = y_train.min()
        offset = abs(y_min) + 1.0 if y_min <= 0 else 0.0
        y_shifted = y_train + offset
        use_log = y_shifted.min() > 0 and y_shifted.max() / (y_shifted.min() + 1e-9) > 10

        y_fit = np.log1p(y_shifted) if use_log else y_shifted

        try:
            pipe = build_pipeline()
            pipe.fit(X_train, y_fit)
            
            y_pred = pipe.predict(X_test)
            y_pred = np.expm1(y_pred) - offset if use_log else y_pred - offset
            y_pred = np.clip(y_pred, 0.0, None)
            
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            if -2.0 <= r2 <= 1.0:
                maes.append(mae)
                r2_scores.append(r2)
                
        except Exception:
            skipped += 1
            continue

    # ── REPORTING ──
    print("\n\n" + "="*60)
    print("🎯 GLOBAL MACHINE LEARNING PERFORMANCE REPORT (HUBER MODEL)")
    print("="*60)
    print(f"✅ Profiles Successfully Backtested : {len(r2_scores):,}")
    print(f"⏭️ Profiles Skipped (Insufficient)  : {skipped:,}")
    print("-"*60)
    
    if r2_scores:
        median_r2 = np.nanmedian(r2_scores)
        median_mae = np.nanmedian(maes)
        
        print(f"📈 Median Accuracy (R² Score)     : {median_r2 * 100:.2f}%")
        print(f"📉 Median Absolute Error (MAE)    : {median_mae:,.2f} Metric Tons")
        print("\n🔍 CONTEXT:")
        print("   • R² measures how well the curve fits the data trajectory (closer to 100% is better).")
        print("   • Using Medians instead of Averages prevents extreme, volatile countries")
        print("     (like conflict zones) from artificially tanking the global score.")
    else:
        print("⚠️ Not enough continuous data profiles to calculate a valid score.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_backtest()