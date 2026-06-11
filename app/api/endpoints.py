import logging
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import plotly.express as px
import pandas as pd
from app.config import LAST_ACTUAL_YEAR, INVALID_YEARS, HISTORICAL_YEARS, FORECAST_YEARS
from app.models.schemas import (
    OptionsResponse, 
    CropDominanceResponse, 
    CountryTopCropsResponse, 
    CountryCropHistoryResponse
)
from app.services.crop_service import CropService, normalize_crop_name

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")

# ── Frontend Template Pages ──────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    """Serves the dashboard home page."""
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/country", response_class=HTMLResponse)
def country_page(request: Request):
    """Serves the country profile page."""
    return templates.TemplateResponse(request=request, name="country.html")

@router.get("/forecast", response_class=HTMLResponse)
def forecast_page(request: Request):
    """Serves the forecast page."""
    return templates.TemplateResponse(request=request, name="forecast.html")

@router.get("/map", response_class=HTMLResponse)
def map_page(request: Request):
    """Serves the global interactive map page."""
    return templates.TemplateResponse(request=request, name="map.html")

# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/api/options", response_model=OptionsResponse)
def get_options():
    """Returns lists of historical and future crops, countries, and years."""
    try:
        options = CropService.get_form_options()
        return options
    except Exception as e:
        logger.error(f"Error loading options: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve field options.")

@router.get("/api/crop", response_model=CropDominanceResponse)
def get_crop_dominance(
    name: str = Query(..., description="Crop profile name"),
    year: int = Query(..., description="Year selection")
):
    """Retrieves country production shares for a specific crop in a historical or forecast year."""
    if year in INVALID_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"The intermediate year {year} is omitted from the database."
        )

    is_historical = year in HISTORICAL_YEARS
    is_forecast = year in FORECAST_YEARS

    if not is_historical and not is_forecast:
        raise HTTPException(
            status_code=400,
            detail=f"The requested year {year} is invalid. Only historical (1961–2023) or forecast (2027–2031) years are allowed."
        )

    try:
        if is_historical:
            normalized_name, records = CropService.get_crop_market_share(name, year)
        else:
            normalized_name, records = CropService.get_crop_forecast_market_share(name, year)

        if not records:
            raise HTTPException(status_code=404, detail=f"No market-share profiles found for '{name}' in {year}.")
        return {
            "crop": normalized_name,
            "year": year,
            "data": records
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error fetching crop dominance: {e}")
        raise HTTPException(status_code=500, detail="Internal query failure.")

@router.get("/api/country")
def get_country_profile(
    name: str = Query(..., description="Country search word"),
    year: int = Query(..., description="Year selection")
):
    """Provides structured ranking profile information for a country."""
    if year not in HISTORICAL_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"The requested year {year} is invalid. Historical profile endpoints only support year <= {LAST_ACTUAL_YEAR}."
        )
    if year in INVALID_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"The year {year} is invalid."
        )

    try:
        matched_countries, total_prod, records = CropService.get_country_top_crops(name, year, limit=10)
        if not records:
            raise HTTPException(status_code=404, detail=f"No matching profile records found for country '{name}' in {year}")
        
        # Format list to map original field names in client expectations
        formatted_list = [
            {
                "Item Code (CPC)": r.get("Item Code (CPC)", "N/A"),
                "Item": r["Item"],
                "Production_Value": r["Production_Value"],
                "Unit": r["Unit"]
            } for r in records
        ]

        return {
            "searched_name": name,
            "matched_country_entries": matched_countries,
            "year": year,
            "top_agricultural_contributions": formatted_list
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error reading country profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve country profile details.")

@router.get("/api/country/top-crops", response_model=CountryTopCropsResponse)
def get_country_top_crops(
    country: str = Query(..., description="Country name"),
    year: int = Query(..., description="Year to query"),
    limit: int = Query(10, description="Max amount of records to display")
):
    """Ranked crop list for a specific country & year."""
    if year not in HISTORICAL_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"The requested year {year} is invalid. Historical endpoints only support year <= {LAST_ACTUAL_YEAR}."
        )
    if year in INVALID_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"The intermediate year {year} is invalid."
        )

    try:
        matched_countries, total_production, top_crops = CropService.get_country_top_crops(country, year, limit)
        if not top_crops:
            raise HTTPException(status_code=404, detail=f"No top crop dataset found for '{country}' in {year}")
        
        return {
            "country_query": country,
            "matched_countries": matched_countries,
            "year": year,
            "total_records": len(top_crops),
            "total_production": total_production,
            "top_crops": top_crops
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error loading country top crops: {e}")
        raise HTTPException(status_code=500, detail="Top crops query failed.")

@router.get("/api/country/crop-history", response_model=CountryCropHistoryResponse)
def get_country_crop_history(
    country: str = Query(..., description="Country name"),
    crop: str = Query(..., description="Crop profile to inspect")
):
    """Retrieves standard timelines and statistical peaks for a country and crop."""
    try:
        history_profile = CropService.get_country_crop_history(country, crop)
        return history_profile
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error reading crop history: {e}")
        raise HTTPException(status_code=500, detail="History queries failed.")

@router.get("/map/embed", response_class=HTMLResponse)
def get_plotly_map(
    crop: str = Query("Wheat", description="Crop category"),
    year: int = Query(2023, description="Mapping year (1961-2023 or 2027-2031)")
):
    """Creates a Plotly global market share choropleth for historical or forecast years."""
    if year in INVALID_YEARS:
        return HTMLResponse(
            status_code=400,
            content=f"""
            <div style="font-family: 'DM Sans', sans-serif; padding: 2.5rem; text-align: center; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; margin: 2rem;">
                <h3 style="margin-top: 0;">Access Restriction</h3>
                <p>The year {year} is omitted. Years 2024, 2025, and 2026 do not exist in the system.</p>
            </div>
            """
        )

    is_historical = year in HISTORICAL_YEARS
    is_forecast = year in FORECAST_YEARS

    if not is_historical and not is_forecast:
        return HTMLResponse(
            status_code=400,
            content=f"""
            <div style="font-family: 'DM Sans', sans-serif; padding: 2.5rem; text-align: center; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; margin: 2rem;">
                <h3 style="margin-top: 0;">Access Restriction</h3>
                <p>The requested year {year} is invalid. Only historical (1961–2023) or forecast (2027–2031) years are allowed.</p>
            </div>
            """
        )

    try:
        if is_historical:
            normalized_crop, records = CropService.get_crop_market_share(crop, year)
        else:
            normalized_crop, records = CropService.get_crop_forecast_market_share(crop, year)

        if not records:
            return HTMLResponse(
                content=f"<h3 style='font-family:sans-serif;padding:2rem;text-align:center;'>No map records located for {normalized_crop} in {year}.</h3>"
            )

        df_records = pd.DataFrame(records)
        df_records["Percentage_Share"] = df_records["Percentage_Share"].astype(float)

        fig = px.choropleth(
            df_records,
            locations="Area",
            locationmode="country names",
            color="Percentage_Share",
            hover_name="Area",
            hover_data={
                "Percentage_Share": ":.2f"
            },
            title=f"Global Market Share: {normalized_crop} ({year})",
            color_continuous_scale=px.colors.sequential.YlGnBu,
            labels={"Percentage_Share": "Share (%)"}
        )

        fig.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type="natural earth",
                showcountries=True,
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            paper_bgcolor="rgba(0,0,0,0)"
        )

        html_content = fig.to_html(full_html=True, include_plotlyjs="cdn")
        return HTMLResponse(html_content)
    except Exception as e:
        logger.error(f"Failed to generate Plotly map: {e}")
        return HTMLResponse(
            status_code=500,
            content=f"<h3 style='font-family:sans-serif;padding:2rem;text-align:center;'>Map server error: {e}</h3>"
        )
