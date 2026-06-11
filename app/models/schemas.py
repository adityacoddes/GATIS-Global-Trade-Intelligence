from pydantic import BaseModel, Field
from typing import List, Optional

class OptionsResponse(BaseModel):
    default_crop: str = Field(..., description="Default crop for UI selections")
    default_country: str = Field(..., description="Default country for UI selections")
    default_year: int = Field(..., description="Default year for UI selections")
    crops: List[str] = Field(..., description="List of all unique available crops")
    countries: List[str] = Field(..., description="List of all unique available countries")
    years: List[int] = Field(..., description="List of all unique available years, excluding 2024-2026")
    historical_years: List[int] = Field(..., description="List of all historical years: 1961-2023")
    forecast_years: List[int] = Field(..., description="List of all forecast years: 2027-2031")


class CropDominanceItem(BaseModel):
    area_code_m49: str = Field(..., alias="Area Code (M49)")
    area: str = Field(..., alias="Area")
    percentage_share: float = Field(..., alias="Percentage_Share")

    class Config:
        populate_by_name = True

class CropDominanceResponse(BaseModel):
    crop: str
    year: int
    data: List[CropDominanceItem]

class TopCropItem(BaseModel):
    rank: int = Field(..., alias="Rank")
    area: str = Field(..., alias="Area")
    item: str = Field(..., alias="Item")
    production_value: float = Field(..., alias="Production_Value")
    unit: str = Field(..., alias="Unit")
    country_share: float = Field(..., alias="Country_Share")

    class Config:
        populate_by_name = True

class CountryTopCropsResponse(BaseModel):
    country_query: str
    matched_countries: List[str]
    year: int
    total_records: int
    total_production: float
    top_crops: List[TopCropItem]

class CropHistoryItem(BaseModel):
    year: int = Field(..., alias="Year")
    area: str = Field(..., alias="Area")
    item: str = Field(..., alias="Item")
    production_value: float = Field(..., alias="Production_Value")
    unit: str = Field(..., alias="Unit")

    class Config:
        populate_by_name = True

class CountryCropHistoryResponse(BaseModel):
    country_query: str
    matched_countries: List[str]
    crop: str
    first_year: int
    latest_year: int
    latest_production: float
    latest_unit: str
    peak_year: int
    peak_production: float
    peak_unit: str
    history: List[CropHistoryItem]
