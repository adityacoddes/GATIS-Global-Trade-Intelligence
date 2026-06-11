import logging
from pathlib import Path
import pandas as pd
from app.config import LAST_ACTUAL_YEAR, FORECAST_START_YEAR, FORECAST_END_YEAR, INVALID_YEARS

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / "data" / "processed" / "cleaned_faostat.csv"
FORECAST_FILE = BASE_DIR / "data" / "forecasts" / "forecast_results.csv"

# Global data frames populated at startup
_df_historical: pd.DataFrame = pd.DataFrame()
_df_forecast: pd.DataFrame = pd.DataFrame()
_df_merged: pd.DataFrame = pd.DataFrame()

def load_all_data() -> None:
    """Loads and validates agricultural datasets."""
    global _df_historical, _df_forecast, _df_merged
    
    logger.info("Initializing datasets...")
    
    # 1. Historical Dataset
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Historical data file missing at: {DATA_FILE}")

    try:
        df_hist = pd.read_csv(DATA_FILE)
        # Filter strictly <= 2023 and drop any invalid intermediate years
        df_hist = df_hist[df_hist["Year"] <= LAST_ACTUAL_YEAR]
        df_hist = df_hist[~df_hist["Year"].isin(INVALID_YEARS)]
        _df_historical = df_hist
        logger.info(f"Loaded {len(_df_historical):,} historical records up to {LAST_ACTUAL_YEAR}")
    except Exception as e:
        logger.error(f"Failed to load historical data due to error: {e}")
        raise e

    # 2. Forecast Dataset
    if not FORECAST_FILE.exists():
        raise FileNotFoundError(f"Forecast data file missing at: {FORECAST_FILE}")

    try:
        df_fore = pd.read_csv(FORECAST_FILE)
        # Filter strictly inside allowed forecast years and exclude invalid intermediate years
        df_fore = df_fore[(df_fore["Year"] >= FORECAST_START_YEAR) & (df_fore["Year"] <= FORECAST_END_YEAR)]
        df_fore = df_fore[~df_fore["Year"].isin(INVALID_YEARS)]
        _df_forecast = df_fore
        logger.info(f"Loaded {len(_df_forecast):,} forecast records ({FORECAST_START_YEAR}–{FORECAST_END_YEAR})")
    except Exception as e:
        logger.error(f"Failed to load forecast data due to error: {e}")
        raise e

    # 3. Merge Datasets for Unified Queries (e.g. unified crop history)
    _df_merged = pd.concat([_df_historical, _df_forecast], ignore_index=True)
    logger.info(f"Merged memory table ready with {len(_df_merged):,} total rows.")


def get_historical_df() -> pd.DataFrame:
    """Returns the historical only dataframe, ensuring <= 2023."""
    if _df_historical.empty:
        load_all_data()
    return _df_historical

def get_forecast_df() -> pd.DataFrame:
    """Returns the forecast only dataframe, ensuring >= 2027 and <= 2031."""
    if _df_forecast.empty:
        load_all_data()
    return _df_forecast

def get_merged_df() -> pd.DataFrame:
    """Returns merged historical and forecaster dataframes, omitting 2024, 2025, 2026."""
    if _df_merged.empty:
        load_all_data()
    return _df_merged

