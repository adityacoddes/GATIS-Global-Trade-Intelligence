from pathlib import Path
import pandas as pd
import plotly.express as px
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse


app = FastAPI(title="Global Agricultural Trade Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

BASE_DIR      = Path(__file__).resolve().parent
DATA_FILE     = BASE_DIR / "cleaned_faostat.csv"
FORECAST_FILE = BASE_DIR / "forecast_results.csv"

# ── Data loading & merge ──────────────────────────────────────────────────────
print("Loading historical dataset into memory...")
df = pd.read_csv(DATA_FILE)
historical_count = len(df)
print(f"  → {historical_count:,} historical records loaded  (years up to {int(df['Year'].max())})")

if FORECAST_FILE.exists():
    print("Loading ML forecast results...")
    forecast_df = pd.read_csv(FORECAST_FILE)

    # Sanity-guard: drop any forecast rows that overlap with historical years
    # (protects against re-running the forecaster with a different year range)
    historical_years = set(df["Year"].unique())
    forecast_df = forecast_df[~forecast_df["Year"].isin(historical_years)]

    df = pd.concat([df, forecast_df], ignore_index=True)
    forecast_count = len(forecast_df)
    print(f"  → {forecast_count:,} forecast records merged  (years {int(forecast_df['Year'].min())}–{int(forecast_df['Year'].max())})")
else:
    print(
        f"  ⚠  {FORECAST_FILE.name} not found — running in historical-only mode.\n"
        f"     Run `python ml_forecaster.py` to generate forecasts."
    )

print(f"\nAPI Ready! {len(df):,} total records in memory.\n")
# ─────────────────────────────────────────────────────────────────────────────

CROP_ALIASES = {
    "maize": "Maize (corn)",
}


def _normalize_crop_name(name: str) -> str:
    return CROP_ALIASES.get(name.strip().lower(), name.strip())


def _clean_m49(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace("'", "", regex=False)
        .str.strip()
        .str.split(".")
        .str[0]
        .str.zfill(3)
    )


def _crop_frame(crop: str, year: int) -> tuple[str, pd.DataFrame]:
    normalized_crop = _normalize_crop_name(crop)
    crop_df = df[
        (df["Item"].str.lower() == normalized_crop.lower()) & (df["Year"] == year)
    ].copy()
    return normalized_crop, crop_df


def _country_frame(country: str) -> tuple[list[str], pd.DataFrame]:
    country_mask = df["Area"].str.contains(country.strip(), case=False, na=False)
    country_df = df[country_mask].copy()
    return sorted(country_df["Area"].dropna().unique().tolist()), country_df


def _format_records(records_df: pd.DataFrame, columns: list[str]) -> list[dict]:
    return records_df[columns].to_dict(orient="records")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"status": "online", "message": "GATIS API is live!"}


@app.get("/api/options")
def get_options():
    crops     = sorted(df["Item"].dropna().unique().tolist())
    countries = sorted(df["Area"].dropna().unique().tolist())
    years     = sorted(df["Year"].dropna().astype(int).unique().tolist(), reverse=True)

    return {
        "default_crop":    "Wheat" if "Wheat" in crops else crops[0],
        "default_country": "India" if "India" in countries else countries[0],
        "default_year":    years[0],
        "crops":           crops,
        "countries":       countries,
        "years":           years,
    }


@app.get("/api/crop")
def get_crop_dominance(name: str, year: int):
    crop, crop_df = _crop_frame(name, year)

    if crop_df.empty:
        raise HTTPException(status_code=404, detail="Crop or year not found")

    total_production = crop_df["Production_Value"].sum()
    crop_df["Percentage_Share"] = (
        crop_df["Production_Value"] / total_production
    ) * 100
    crop_df = crop_df.sort_values(by="Percentage_Share", ascending=False)
    crop_df["Area Code (M49)"] = _clean_m49(crop_df["Area Code (M49)"])

    result = crop_df[["Area Code (M49)", "Area", "Percentage_Share"]].to_dict(
        orient="records"
    )
    return {"crop": crop, "year": year, "data": result}


@app.get("/api/country")
def get_country_profile(name: str, year: int):
    matched_countries, country_df = _country_frame(name)
    country_df = country_df[country_df["Year"] == year].copy()

    if country_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No records found for country matching '{name}' in {year}.",
        )

    top_10 = country_df.sort_values(by="Production_Value", ascending=False).head(10)
    result = top_10[
        ["Item Code (CPC)", "Item", "Production_Value", "Unit"]
    ].to_dict(orient="records")

    return {
        "searched_name":                  name,
        "matched_country_entries":        matched_countries,
        "year":                           year,
        "top_agricultural_contributions": result,
    }


@app.get("/api/country/top-crops")
def get_country_top_crops(country: str, year: int, limit: int = 10):
    matched_countries, country_df = _country_frame(country)
    year_df = country_df[country_df["Year"] == year].copy()

    if year_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No records found for country matching '{country}' in {year}.",
        )

    limit            = max(1, min(limit, 50))
    total_production = year_df["Production_Value"].sum()
    year_df["Country_Share"] = (year_df["Production_Value"] / total_production) * 100
    top_df = year_df.sort_values(by="Production_Value", ascending=False).head(limit)
    top_df.insert(0, "Rank", range(1, len(top_df) + 1))

    records = _format_records(
        top_df,
        ["Rank", "Area", "Item", "Production_Value", "Unit", "Country_Share"],
    )

    return {
        "country_query":      country,
        "matched_countries":  matched_countries,
        "year":               year,
        "total_records":      int(len(year_df)),
        "total_production":   float(total_production),
        "top_crops":          records,
    }


@app.get("/api/country/crop-history")
def get_country_crop_history(country: str, crop: str):
    matched_countries, country_df = _country_frame(country)
    normalized_crop = _normalize_crop_name(crop)
    history_df = country_df[
        country_df["Item"].str.lower() == normalized_crop.lower()
    ].copy()

    if history_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No production history found for '{normalized_crop}' in country matching '{country}'.",
        )

    history_df = history_df.sort_values(by="Year")
    peak_row   = history_df.loc[history_df["Production_Value"].idxmax()]
    latest_row = history_df.iloc[-1]
    first_row  = history_df.iloc[0]
    records    = _format_records(history_df, ["Year", "Area", "Item", "Production_Value", "Unit"])

    return {
        "country_query":          country,
        "matched_countries":      matched_countries,
        "crop":                   normalized_crop,
        "first_year":             int(first_row["Year"]),
        "latest_year":            int(latest_row["Year"]),
        "latest_production":      float(latest_row["Production_Value"]),
        "latest_unit":            latest_row["Unit"],
        "peak_year":              int(peak_row["Year"]),
        "peak_production":        float(peak_row["Production_Value"]),
        "peak_unit":              peak_row["Unit"],
        "history":                records,
    }


@app.get("/map", response_class=HTMLResponse)
def render_live_map(crop: str = "Wheat", year: int = 2020):
    crop, crop_df = _crop_frame(crop, year)

    if crop_df.empty:
        return HTMLResponse(
            f"<h3 style='font-family:sans-serif;padding:2rem;'>No data found for <b>{crop}</b> in <b>{year}</b>.</h3>",
            headers={"Cache-Control": "no-store"},
        )

    total_production         = crop_df["Production_Value"].sum()
    crop_df["Percentage_Share"] = (crop_df["Production_Value"] / total_production) * 100

    # Surface a subtle visual cue when the selected year is a forecast year
    is_forecast = int(year) >= 2024
    title_suffix = "  ·  ML Forecast" if is_forecast else ""

    fig = px.choropleth(
        crop_df,
        locations="Area",
        locationmode="country names",
        color="Percentage_Share",
        hover_name="Area",
        hover_data={"Percentage_Share": ":.2f"},
        title=f"Global Market Share: {crop.title()} ({year}){title_suffix}",
        color_continuous_scale=px.colors.sequential.YlGnBu,
        labels={"Percentage_Share": "Share (%)"},
    )

    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="natural earth",
            showcountries=True,
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})
