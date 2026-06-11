import logging
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.config import LAST_ACTUAL_YEAR, FORECAST_START_YEAR, FORECAST_END_YEAR, INVALID_YEARS, HISTORICAL_YEARS, FORECAST_YEARS
from app.utils.data_loader import get_historical_df, get_forecast_df, get_merged_df

logger = logging.getLogger(__name__)

CROP_ALIASES: Dict[str, str] = {
    "maize": "Maize (corn)",
}

def normalize_crop_name(name: str) -> str:
    """Standardizes crop names according to system conventions."""
    cleaned = name.strip().lower()
    return CROP_ALIASES.get(cleaned, name.strip())

def clean_m49_code(code_str: Any) -> str:
    """Strips and standardizes M49 country codes to secure 3-character zfilled strings."""
    s = str(code_str).replace("'", "").strip()
    parts = s.split(".")
    return parts[0].zfill(3) if parts else "000"

class CropService:
    @staticmethod
    def get_form_options() -> Dict[str, Any]:
        """Calculates dynamic choices for historical and forecast selections."""
        logger.info("Generating form selections options...")
        merged_df = get_merged_df()
        
        crops = sorted(merged_df["Item"].dropna().unique().tolist())
        countries = sorted(merged_df["Area"].dropna().unique().tolist())
        all_years = sorted(merged_df["Year"].dropna().astype(int).unique().tolist(), reverse=True)
        
        # Guard: Filter out the strictly forbidden years 2024, 2025, 2026
        valid_years = [y for y in all_years if y not in INVALID_YEARS]
        
        default_crop = "Wheat" if "Wheat" in crops else (crops[0] if crops else "")
        default_country = "India" if "India" in countries else (countries[0] if countries else "")
        default_year = LAST_ACTUAL_YEAR if LAST_ACTUAL_YEAR in valid_years else (valid_years[0] if valid_years else 2023)
        
        return {
            "default_crop": default_crop,
            "default_country": default_country,
            "default_year": default_year,
            "crops": crops,
            "countries": countries,
            "years": valid_years,
            "historical_years": HISTORICAL_YEARS,
            "forecast_years": FORECAST_YEARS
        }


    @staticmethod
    def get_crop_market_share(crop_name: str, year: int) -> Tuple[str, List[Dict[str, Any]]]:
        """Provides historical global market share breakdown for a year."""
        # ANY API endpoint that serves historical information must reject years greater than LAST_ACTUAL_YEAR
        if year > LAST_ACTUAL_YEAR:
            raise ValueError(f"Historical queries strictly restricted to years <= {LAST_ACTUAL_YEAR}. Got: {year}")
        if year in INVALID_YEARS:
            raise ValueError(f"Selected year {year} is an invalid year.")

        normalized_crop = normalize_crop_name(crop_name)
        hist_df = get_historical_df()
        
        crop_df = hist_df[
            (hist_df["Item"].str.lower() == normalized_crop.lower()) & 
            (hist_df["Year"] == year)
        ].copy()
        
        if crop_df.empty:
            logger.warning(f"No records found for crop: {normalized_crop} and year: {year}")
            return normalized_crop, []

        total_production = crop_df["Production_Value"].sum()
        if total_production > 0:
            crop_df["Percentage_Share"] = (crop_df["Production_Value"] / total_production) * 100
        else:
            crop_df["Percentage_Share"] = 0.0

        crop_df = crop_df.sort_values(by="Percentage_Share", ascending=False)
        
        # Clean and standardise M49 records
        crop_df["Area Code (M49)"] = crop_df["Area Code (M49)"].apply(clean_m49_code)
        
        result_records = crop_df[["Area Code (M49)", "Area", "Percentage_Share"]].to_dict(orient="records")
        return normalized_crop, result_records

    @staticmethod
    def get_crop_forecast_market_share(crop_name: str, year: int) -> Tuple[str, List[Dict[str, Any]]]:
        """Provides forecast global market share breakdown for a year (2027-2031)."""
        if year < FORECAST_START_YEAR or year > FORECAST_END_YEAR:
            raise ValueError(f"Forecast queries restricted to years {FORECAST_START_YEAR}-{FORECAST_END_YEAR}. Got: {year}")
        if year in INVALID_YEARS:
            raise ValueError(f"Selected year {year} is an invalid year.")

        normalized_crop = normalize_crop_name(crop_name)
        fore_df = get_forecast_df()
        
        crop_df = fore_df[
            (fore_df["Item"].str.lower() == normalized_crop.lower()) & 
            (fore_df["Year"] == year)
        ].copy()
        
        if crop_df.empty:
            logger.warning(f"No forecast records found for crop: {normalized_crop} and year: {year}")
            return normalized_crop, []

        total_production = crop_df["Production_Value"].sum()
        if total_production > 0:
            crop_df["Percentage_Share"] = (crop_df["Production_Value"] / total_production) * 100
        else:
            crop_df["Percentage_Share"] = 0.0

        crop_df = crop_df.sort_values(by="Percentage_Share", ascending=False)
        crop_df["Area Code (M49)"] = crop_df["Area Code (M49)"].apply(clean_m49_code)
        
        result_records = crop_df[["Area Code (M49)", "Area", "Percentage_Share"]].to_dict(orient="records")
        return normalized_crop, result_records

    @staticmethod
    def get_country_top_crops(country: str, year: int, limit: int = 10) -> Tuple[List[str], float, List[Dict[str, Any]]]:
        """Retrieves and ranks the top crops of a specific country for a given year."""
        # Check if year is a historical year, then validate if > 2023
        if year > LAST_ACTUAL_YEAR:
            raise ValueError(f"Historical queries strictly restricted to years <= {LAST_ACTUAL_YEAR}. Got: {year}")
        if year in INVALID_YEARS:
            raise ValueError(f"Selected year {year} is invalid.")

        merged_df = get_merged_df()
        
        # Fuzzy match country name
        matching_mask = merged_df["Area"].str.contains(country.strip(), case=False, na=False)
        matched_countries = sorted(merged_df[matching_mask]["Area"].dropna().unique().tolist())
        
        if not matched_countries:
            return [], 0.0, []

        country_df = merged_df[merged_df["Area"].isin(matched_countries)].copy()
        year_df = country_df[country_df["Year"] == year].copy()

        if year_df.empty:
            return matched_countries, 0.0, []

        total_production = year_df["Production_Value"].sum()
        
        if total_production > 0:
            year_df["Country_Share"] = (year_df["Production_Value"] / total_production) * 100
        else:
            year_df["Country_Share"] = 0.0

        top_df = year_df.sort_values(by="Production_Value", ascending=False).head(limit)
        
        # Add ranks sequentially
        top_df["Rank"] = range(1, len(top_df) + 1)
        
        records = top_df[["Rank", "Area", "Item", "Production_Value", "Unit", "Country_Share"]].to_dict(orient="records")
        return matched_countries, float(total_production), records

    @staticmethod
    def get_country_crop_history(country: str, crop: str) -> Dict[str, Any]:
        """Returns the full historical sequence and metrics for a specific country and crop, excluding forbidden years."""
        merged_df = get_merged_df()
        
        # Fuzzy match country name
        matching_mask = merged_df["Area"].str.contains(country.strip(), case=False, na=False)
        matched_countries = sorted(merged_df[matching_mask]["Area"].dropna().unique().tolist())
        
        if not matched_countries:
            raise ValueError(f"No match found for country search pattern: '{country}'")

        normalized_crop = normalize_crop_name(crop)
        
        country_crop_df = merged_df[
            (merged_df["Area"].isin(matched_countries)) & 
            (merged_df["Item"].str.lower() == normalized_crop.lower())
        ].copy()

        if country_crop_df.empty:
            raise ValueError(f"No history found for crop: {normalized_crop} in matching countries: {matched_countries}")

        # Filter out invalid years
        country_crop_df = country_crop_df[~country_crop_df["Year"].isin(INVALID_YEARS)]
        country_crop_df = country_crop_df.sort_values(by="Year")
        
        hist_part = country_crop_df[country_crop_df["Year"] <= LAST_ACTUAL_YEAR]
        if hist_part.empty:
            raise ValueError(f"No historical information <= {LAST_ACTUAL_YEAR} available for crop: {normalized_crop}")

        peak_row = hist_part.loc[hist_part["Production_Value"].idxmax()]
        latest_row = hist_part.iloc[-1]
        first_row = hist_part.iloc[0]
        
        records = country_crop_df[["Year", "Area", "Item", "Production_Value", "Unit"]].to_dict(orient="records")

        return {
            "country_query": country,
            "matched_countries": matched_countries,
            "crop": normalized_crop,
            "first_year": int(first_row["Year"]),
            "latest_year": int(latest_row["Year"]),
            "latest_production": float(latest_row["Production_Value"]),
            "latest_unit": latest_row["Unit"],
            "peak_year": int(peak_row["Year"]),
            "peak_production": float(peak_row["Production_Value"]),
            "peak_unit": peak_row["Unit"],
            "history": records
        }
